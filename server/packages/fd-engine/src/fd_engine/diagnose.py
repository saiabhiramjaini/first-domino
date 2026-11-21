"""Runs one diagnosis end to end: calibrate, bisect, verify or fallback, then explain.

Grouping is a separate call (`fd_engine.group.CauseGrouper`) because the API owns the causes.
"""

from uuid import UUID

from fd_engine.bisect import Bisector
from fd_engine.calibrate import Calibrator
from fd_engine.checks import CheckRunner
from fd_engine.explain import LlmExplainer, StepExplainer
from fd_engine.fallback import Fallback, FallbackOutcome
from fd_engine.fix import LlmStepFixer
from fd_engine.llm import Llm
from fd_engine.ports import CheckSink, CostSink, ReplayRunner, RunReader
from fd_engine.settings import EngineSettings
from fd_engine.verify import FixAttempt, FixedStep, StepFixer, Verifier
from fd_shared.enums import CheckPhase, DiagnosisStatus, VerdictKind
from fd_shared.errors import FirstDominoError
from fd_shared.logging import get_logger
from fd_shared.models import DiagnosisResult, RunView, StepView

log = get_logger(__name__)


class Diagnoser:
    """Finds and proves the first doomed step of a failed run."""

    def __init__(
        self,
        *,
        reader: RunReader,
        runner: ReplayRunner,
        sink: CheckSink,
        fixer: StepFixer,
        explainer: StepExplainer,
        settings: EngineSettings | None = None,
        cost_sink: CostSink | None = None,
    ) -> None:
        self._reader = reader
        self._cost_sink = cost_sink
        self._runner = runner
        self._sink = sink
        self._fixer = fixer
        self._explainer = explainer
        self._settings = settings or EngineSettings()  # pyright: ignore[reportCallIssue] fields come from the environment

    @classmethod
    def with_llm(
        cls,
        llm: Llm,
        *,
        reader: RunReader,
        runner: ReplayRunner,
        sink: CheckSink,
        settings: EngineSettings,
        cost_sink: CostSink | None = None,
    ) -> "Diagnoser":
        """Build a diagnoser whose fixer and explainer use the process's shared `Llm`.

        Pass `cost_sink` to receive each model call's cost as it happens.
        """
        return cls(
            reader=reader,
            runner=runner,
            sink=sink,
            fixer=LlmStepFixer(llm),
            explainer=LlmExplainer(llm),
            settings=settings,
            cost_sink=cost_sink,
        )

    async def diagnose(self, run_id: UUID, diagnosis_id: UUID) -> DiagnosisResult:
        """Diagnose one failed run and return the verdict for the API to store.

        Raises:
            CheckInconsistentError: The success check passed a replay keeping every step.
            ReplayNotFaithfulError: A check's replays drifted from the steps they kept.
            ReplayUnavailableError: A check got no completed replay.
            CheckBudgetError: Bisect needed more than `max_checks` checks.
        """
        log.info("diagnosis.started", run_id=str(run_id), diagnosis_id=str(diagnosis_id))
        try:
            result = await self._diagnose(run_id, diagnosis_id)
        except FirstDominoError as error:
            log.warning("diagnosis.stopped", diagnosis_id=str(diagnosis_id), error_code=error.code)
            raise
        log.info(
            "diagnosis.finished",
            diagnosis_id=str(diagnosis_id),
            verdict_kind=result.verdict_kind,
            first_domino_step=result.first_domino_step,
            verify_passes=result.verify_passes,
            check_count=result.check_count,
            replay_count=result.replay_count,
            cost_usd=result.cost_usd,
        )
        return result

    async def _diagnose(self, run_id: UUID, diagnosis_id: UUID) -> DiagnosisResult:
        run = await self._reader.get_run(run_id)
        steps = await self._reader.get_steps(run_id)
        checks = CheckRunner(
            diagnosis_id=diagnosis_id,
            run_id=run_id,
            runner=self._runner,
            sink=self._sink,
            settings=self._settings,
        )
        await Calibrator(
            diagnosis_id=diagnosis_id, checks=checks, sink=self._sink, settings=self._settings
        ).calibrate(len(steps))
        bisector = Bisector(
            diagnosis_id=diagnosis_id, checks=checks, sink=self._sink, settings=self._settings
        )
        found = await bisector.find_first_domino(len(steps))
        if found is None:
            return _result(VerdictKind.TASK_OR_TOOL_ISSUE, None, checks, cost_usd=0.0)
        await self._sink.progress(
            diagnosis_id, status=DiagnosisStatus.VERIFYING, search_low=found, search_high=found
        )
        result = await self._prove(run, steps, found, checks, diagnosis_id)
        await self._sink.progress(
            diagnosis_id,
            status=DiagnosisStatus.EXPLAINING,
            search_low=result.first_domino_step,
            search_high=result.first_domino_step,
        )
        return await self._explain(run, steps, result, diagnosis_id)

    async def _prove(
        self,
        run: RunView,
        steps: list[StepView],
        found: int,
        checks: CheckRunner,
        diagnosis_id: UUID,
    ) -> DiagnosisResult:
        fixer = _CostReportingFixer(self._fixer, self._cost_sink, diagnosis_id)
        verifier = Verifier(checks=checks, fixer=fixer, settings=self._settings)
        attempt = await verifier.try_fix(run, steps, found, CheckPhase.VERIFY)
        if attempt.verified:
            return _result(VerdictKind.STEP_VERIFIED, attempt, checks, cost_usd=attempt.cost_usd)
        fallback = await Fallback(checks=checks, verifier=verifier, settings=self._settings).search(
            run, steps, found
        )
        cost_usd = attempt.cost_usd + fallback.cost_usd
        if fallback.verified is not None:
            return _result(VerdictKind.STEP_VERIFIED, fallback.verified, checks, cost_usd=cost_usd)
        return _result(_unproven_kind(attempt, fallback), attempt, checks, cost_usd=cost_usd)

    async def _explain(
        self, run: RunView, steps: list[StepView], result: DiagnosisResult, diagnosis_id: UUID
    ) -> DiagnosisResult:
        if result.first_domino_step is None:
            return result
        explained = await self._explainer.explain(
            run, steps, result.first_domino_step, result.fixed_output
        )
        await _report_cost(self._cost_sink, diagnosis_id, explained.cost_usd)
        return result.model_copy(
            update={
                "explanation": explained.explanation,
                "cost_usd": result.cost_usd + explained.cost_usd,
            }
        )


class _CostReportingFixer:
    """A `StepFixer` that reports each fix's cost as soon as the fix comes back."""

    def __init__(self, fixer: StepFixer, cost_sink: CostSink | None, diagnosis_id: UUID) -> None:
        self._fixer = fixer
        self._cost_sink = cost_sink
        self._diagnosis_id = diagnosis_id

    async def fix(self, run: RunView, steps: list[StepView], step_index: int) -> FixedStep:
        fixed = await self._fixer.fix(run, steps, step_index)
        await _report_cost(self._cost_sink, self._diagnosis_id, fixed.cost_usd)
        return fixed


async def _report_cost(cost_sink: CostSink | None, diagnosis_id: UUID, cost_usd: float) -> None:
    if cost_sink is not None and cost_usd > 0:
        await cost_sink.cost_added(diagnosis_id, cost_usd)


def _unproven_kind(attempt: FixAttempt, fallback: FallbackOutcome) -> VerdictKind:
    """Multiple causes only when the found step and at least one neighbor were really replayed."""
    if attempt.passes is not None and fallback.tried > 0:
        return VerdictKind.MULTIPLE_CAUSES
    return VerdictKind.STEP_UNVERIFIED


def _result(
    kind: VerdictKind, attempt: FixAttempt | None, checks: CheckRunner, *, cost_usd: float
) -> DiagnosisResult:
    return DiagnosisResult(
        verdict_kind=kind,
        first_domino_step=attempt.step if attempt else None,
        verify_passes=attempt.passes if attempt else None,
        verify_samples=attempt.samples if attempt else None,
        fixed_output=attempt.fixed_output if attempt else None,
        explanation=None,
        check_count=checks.check_count,
        replay_count=checks.replay_count,
        cost_usd=cost_usd,
    )
