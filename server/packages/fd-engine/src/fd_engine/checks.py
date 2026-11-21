"""Runs one check: replay from a save point, count passes, report it through the sink.

A check's replays run at once, one replay per call, and the rest are cancelled as soon as the
result is decided: one pass is enough for `can_succeed` at bisect, and verify stops once its
threshold is reached or can no longer be reached. A doomed bisect check still waits for every
replay, because only all of them failing makes it doomed.

Only evidence counts: a replay that ran and reproduced the steps it kept. An errored replay
says nothing, and a drifted one replayed a different run; the check reports how many drifted.
"""

import asyncio
from dataclasses import dataclass, field
from uuid import UUID

from fd_engine.errors import CheckBudgetError, ReplayNotFaithfulError, ReplayUnavailableError
from fd_engine.ports import CheckSink, ReplayRunner
from fd_engine.settings import EngineSettings
from fd_shared.enums import CheckPhase, CheckResult, ReplayOutcome
from fd_shared.logging import get_logger
from fd_shared.models import CheckView, Message, ReplayDrift, ReplayResult

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class CheckRequest:
    """What one check replays and how many passes it needs to count as `can_succeed`."""

    phase: CheckPhase
    save_point: int
    samples: int
    required_passes: int
    model_override: str | None = None
    replacement_output: Message | None = None


@dataclass(slots=True)
class _Tally:
    """The results of one check's replays so far.

    Only evidence (a replay that ran and reproduced the kept steps) can decide the check.
    """

    required_passes: int
    samples: int
    results: list[ReplayResult] = field(default_factory=list)

    @property
    def evidence(self) -> list[ReplayResult]:
        return [result for result in self.results if result.is_evidence]

    @property
    def passes(self) -> int:
        return sum(result.outcome is ReplayOutcome.PASSED for result in self.evidence)

    @property
    def drifts(self) -> list[ReplayDrift]:
        return [result.drift for result in self.results if result.drift is not None]

    @property
    def decided(self) -> bool:
        """The result can no longer change. Until a replay gives evidence, keep waiting.

        A check with no evidence yet waits for the rest, so it ends without a result only when
        no replay at all gave evidence.
        """
        left = self.samples - len(self.results)
        if not self.evidence:
            return left == 0
        return self.passes >= self.required_passes or self.passes + left < self.required_passes

    def fill_errored(self) -> None:
        missing = self.samples - len(self.results)
        self.results.extend([ReplayResult(outcome=ReplayOutcome.ERRORED)] * missing)


class CheckRunner:
    """Runs the checks of one diagnosis in order and counts checks and replays."""

    def __init__(
        self,
        *,
        diagnosis_id: UUID,
        run_id: UUID,
        runner: ReplayRunner,
        sink: CheckSink,
        settings: EngineSettings,
    ) -> None:
        self._diagnosis_id = diagnosis_id
        self._run_id = run_id
        self._runner = runner
        self._sink = sink
        self._settings = settings
        self.check_count = 0
        self.replay_count = 0
        """Replays that finished; a timed-out one counts as errored, a stopped one not at all."""

    @property
    def remaining(self) -> int:
        """How many more checks the budget allows."""
        return self._settings.max_checks - self.check_count

    async def run(self, request: CheckRequest) -> CheckView:
        """Run one check and return it with its passes and result.

        A check that ends with no evidence is still reported finished, with no result, before
        it raises.

        Raises:
            CheckBudgetError: The diagnosis has used all of `max_checks`.
            ReplayNotFaithfulError: No replay gave evidence and at least one drifted.
            ReplayUnavailableError: No replay gave evidence and none drifted.
        """
        if self.remaining <= 0:
            raise CheckBudgetError
        pending = CheckView(
            diagnosis_id=self._diagnosis_id,
            index=self.check_count,
            phase=request.phase,
            save_point=request.save_point,
            samples=request.samples,
            passes=0,
            result=CheckResult.PENDING,
        )
        self.check_count += 1
        await self._sink.check_started(pending)
        tally = await self._replay(request)
        self.replay_count += len(tally.results)
        finished = _finished(pending, tally)
        await self._sink.check_finished(finished)
        log.info(
            "check.finished",
            diagnosis_id=str(self._diagnosis_id),
            index=finished.index,
            phase=finished.phase,
            save_point=finished.save_point,
            passes=finished.passes,
            samples=finished.samples,
            drifted=finished.drifted,
            stopped=request.samples - len(tally.results),
            result=finished.result,
        )
        if not tally.evidence:
            raise ReplayNotFaithfulError if tally.drifts else ReplayUnavailableError
        return finished

    async def _replay(self, request: CheckRequest) -> _Tally:
        """Start every replay, collect results until the check is decided, stop the rest."""
        tally = _Tally(required_passes=request.required_passes, samples=request.samples)
        replays = [asyncio.create_task(self._replay_one(request)) for _ in range(request.samples)]
        try:
            async with asyncio.timeout(self._settings.replay_timeout_seconds):
                for finished in asyncio.as_completed(replays):
                    tally.results.append(await finished)
                    if tally.decided:
                        break
        except TimeoutError:
            log.warning(
                "check.replay_timeout",
                diagnosis_id=str(self._diagnosis_id),
                save_point=request.save_point,
                timeout_seconds=self._settings.replay_timeout_seconds,
            )
            tally.fill_errored()
        finally:
            await _stop(replays)
        return tally

    async def _replay_one(self, request: CheckRequest) -> ReplayResult:
        results = await self._runner.replay(
            self._run_id,
            from_step=request.save_point,
            samples=1,
            model_override=request.model_override,
            replacement_output=request.replacement_output,
        )
        return results[0] if results else ReplayResult(outcome=ReplayOutcome.ERRORED)


def _finished(pending: CheckView, tally: _Tally) -> CheckView:
    """The check as its replays left it. Without evidence it has no result."""
    if not tally.evidence:
        result = CheckResult.PENDING
    elif tally.passes >= tally.required_passes:
        result = CheckResult.CAN_SUCCEED
    else:
        result = CheckResult.DOOMED
    drifts = tally.drifts
    return pending.model_copy(
        update={
            "samples": len(tally.evidence),
            "passes": tally.passes,
            "drifted": len(drifts),
            "drift_tool_name": drifts[0].tool_name if drifts else None,
            "result": result,
        }
    )


async def _stop(replays: list[asyncio.Task[ReplayResult]]) -> None:
    """Cancel the replays still running and wait until they have stopped."""
    for replay in replays:
        replay.cancel()
    await asyncio.gather(*replays, return_exceptions=True)
