"""Runs one check: replay from a save point, count passes, report it through the sink.

A check's replays run at once, one replay per call, and the rest are cancelled as soon as the
result is decided: one pass is enough for `can_succeed` at bisect, and verify stops once its
threshold is reached or can no longer be reached. A doomed bisect check still waits for every
replay, because only all of them failing makes it doomed.
"""

import asyncio
from dataclasses import dataclass, field
from uuid import UUID

from fd_engine.errors import CheckBudgetError, ReplayUnavailableError
from fd_engine.ports import CheckSink, ReplayRunner
from fd_engine.settings import EngineSettings
from fd_shared.enums import CheckPhase, CheckResult, ReplayOutcome
from fd_shared.logging import get_logger
from fd_shared.models import CheckView, Message

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
    """The outcomes of one check's replays so far."""

    required_passes: int
    samples: int
    outcomes: list[ReplayOutcome] = field(default_factory=list)

    @property
    def passes(self) -> int:
        return sum(outcome is ReplayOutcome.PASSED for outcome in self.outcomes)

    @property
    def decided(self) -> bool:
        """The result can no longer change. Until a replay completes, keep waiting.

        A check whose finished replays all errored waits for the rest, so a check is only
        unavailable when every replay errored.
        """
        if all(outcome is ReplayOutcome.ERRORED for outcome in self.outcomes):
            return len(self.outcomes) == self.samples
        left = self.samples - len(self.outcomes)
        return self.passes >= self.required_passes or self.passes + left < self.required_passes

    def fill_errored(self) -> None:
        self.outcomes.extend([ReplayOutcome.ERRORED] * (self.samples - len(self.outcomes)))


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

        Raises:
            CheckBudgetError: The diagnosis has used all of `max_checks`.
            ReplayUnavailableError: No replay in the check completed.
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
        outcomes = await self._replay(request)
        self.replay_count += len(outcomes)
        if all(outcome is ReplayOutcome.ERRORED for outcome in outcomes):
            raise ReplayUnavailableError
        passes = sum(outcome is ReplayOutcome.PASSED for outcome in outcomes)
        result = (
            CheckResult.CAN_SUCCEED if passes >= request.required_passes else CheckResult.DOOMED
        )
        finished = pending.model_copy(
            update={"samples": len(outcomes), "passes": passes, "result": result}
        )
        await self._sink.check_finished(finished)
        log.info(
            "check.finished",
            diagnosis_id=str(self._diagnosis_id),
            index=finished.index,
            phase=finished.phase,
            save_point=finished.save_point,
            passes=passes,
            samples=finished.samples,
            stopped=request.samples - len(outcomes),
            result=result,
        )
        return finished

    async def _replay(self, request: CheckRequest) -> list[ReplayOutcome]:
        """Start every replay, collect outcomes until the result is decided, stop the rest."""
        tally = _Tally(required_passes=request.required_passes, samples=request.samples)
        replays = [asyncio.create_task(self._replay_one(request)) for _ in range(request.samples)]
        try:
            async with asyncio.timeout(self._settings.replay_timeout_seconds):
                for finished in asyncio.as_completed(replays):
                    tally.outcomes.append(await finished)
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
        return tally.outcomes

    async def _replay_one(self, request: CheckRequest) -> ReplayOutcome:
        outcomes = await self._runner.replay(
            self._run_id,
            from_step=request.save_point,
            samples=1,
            model_override=request.model_override,
            replacement_output=request.replacement_output,
        )
        return outcomes[0] if outcomes else ReplayOutcome.ERRORED


async def _stop(replays: list[asyncio.Task[ReplayOutcome]]) -> None:
    """Cancel the replays still running and wait until they have stopped."""
    for replay in replays:
        replay.cancel()
    await asyncio.gather(*replays, return_exceptions=True)
