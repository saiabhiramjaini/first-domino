"""Replays of a flagged run, with each outcome decided by the judge instead of the worker."""

from uuid import UUID

from fd_engine.judge import ReplayJudge
from fd_engine.ports import CostSink, ReplayRunner, RunReader
from fd_shared.enums import ReplayOutcome
from fd_shared.logging import get_logger
from fd_shared.models import Message, ReplayResult, RunView, StepView

log = get_logger(__name__)


class JudgedReplayRunner:
    """A `ReplayRunner` that has the judge re-decide every replay that is evidence.

    It wraps the real runner, so each replay is judged inside its own check task: early
    stopping, the replay timeout and drift work as for any replay. An errored or drifted replay
    is left as it is, and one with no recorded replay run to read becomes `errored`.
    """

    def __init__(
        self,
        runner: ReplayRunner,
        *,
        judge: ReplayJudge,
        reader: RunReader,
        run: RunView,
        steps: list[StepView],
        diagnosis_id: UUID,
        cost_sink: CostSink | None,
    ) -> None:
        self._runner = runner
        self._judge = judge
        self._reader = reader
        self._run = run
        self._steps = steps
        self._diagnosis_id = diagnosis_id
        self._cost_sink = cost_sink
        self.cost_usd = 0.0
        """What the judge calls that came back have cost so far."""

    async def replay(
        self,
        run_id: UUID,
        *,
        from_step: int,
        samples: int,
        model_override: str | None,
        replacement_output: Message | None,
    ) -> list[ReplayResult]:
        """Replay through the real runner, then judge each result that is evidence."""
        results = await self._runner.replay(
            run_id,
            from_step=from_step,
            samples=samples,
            model_override=model_override,
            replacement_output=replacement_output,
        )
        return [await self._judged(result, from_step) for result in results]

    async def _judged(self, result: ReplayResult, from_step: int) -> ReplayResult:
        if not result.is_evidence:
            return result
        if result.replay_run_id is None:
            log.warning("judge.no_replay_run", diagnosis_id=str(self._diagnosis_id))
            return result.model_copy(update={"outcome": ReplayOutcome.ERRORED})
        replay = await self._reader.get_run(result.replay_run_id)
        replay_steps = await self._reader.get_steps(result.replay_run_id)
        judged = await self._judge.judge(
            self._run, replay, self._transcript(from_step, replay_steps)
        )
        self.cost_usd += judged.cost_usd
        if self._cost_sink is not None and judged.cost_usd > 0:
            await self._cost_sink.cost_added(self._diagnosis_id, judged.cost_usd)
        log.info(
            "judge.decided",
            diagnosis_id=str(self._diagnosis_id),
            replay_run_id=str(result.replay_run_id),
            from_step=from_step,
            worker_outcome=result.outcome,
            outcome=judged.outcome,
            cost_usd=judged.cost_usd,
        )
        return result.model_copy(update={"outcome": judged.outcome})

    def _transcript(self, from_step: int, replay_steps: list[StepView]) -> list[StepView]:
        """The replay's whole run: the kept original steps, then the steps the replay made.

        A replay run records only the steps after the ones it kept, so the kept ones come from
        the original run.
        """
        kept = [step for step in self._steps if step.index <= from_step]
        return kept + [step for step in replay_steps if step.index > from_step]
