"""Runs one check: replay from a save point, count passes, report it through the sink."""

import asyncio
from dataclasses import dataclass
from uuid import UUID

from fd_engine.errors import CheckBudgetError, ReplayUnavailableError
from fd_engine.models import Check, CheckPhase, CheckResult, Message, ReplayOutcome
from fd_engine.ports import CheckSink, ReplayRunner
from fd_engine.settings import EngineSettings


@dataclass(frozen=True, slots=True)
class CheckRequest:
    """What one check replays and how many passes it needs to count as `can_succeed`."""

    phase: CheckPhase
    save_point: int
    samples: int
    required_passes: int
    model_override: str | None = None
    replacement_output: Message | None = None


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

    @property
    def remaining(self) -> int:
        """How many more checks the budget allows."""
        return self._settings.max_checks - self.check_count

    async def run(self, request: CheckRequest) -> Check:
        """Run one check and return it with its passes and result.

        Raises:
            CheckBudgetError: The diagnosis has used all of `max_checks`.
            ReplayUnavailableError: No replay in the check completed.
        """
        if self.remaining <= 0:
            raise CheckBudgetError
        pending = Check(
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
        finished = pending.model_copy(update={"passes": passes, "result": result})
        await self._sink.check_finished(finished)
        return finished

    async def _replay(self, request: CheckRequest) -> list[ReplayOutcome]:
        try:
            async with asyncio.timeout(self._settings.replay_timeout_seconds):
                return await self._runner.replay(
                    self._run_id,
                    from_step=request.save_point,
                    samples=request.samples,
                    model_override=request.model_override,
                    replacement_output=request.replacement_output,
                )
        except TimeoutError:
            return [ReplayOutcome.ERRORED] * request.samples
