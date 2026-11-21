"""Stores the engine's verdict on a diagnosis and files it under a cause group."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from fd_api.services.engine import CauseMatcher
from fd_database import tables
from fd_database.repositories import CausesRepository, DiagnosesRepository, StepsRepository
from fd_database.session import Database
from fd_database.tables.base import utc_now
from fd_engine.group import CauseCandidate, CauseMatch
from fd_shared.enums import VerdictKind
from fd_shared.errors import NotFoundError
from fd_shared.models import DiagnosisResult, Explanation

_GROUPED_VERDICTS = frozenset({VerdictKind.STEP_VERIFIED, VerdictKind.STEP_UNVERIFIED})


class StoredVerdict(BaseModel):
    """The cause a verdict was filed under, and whether that cause is new."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    cause: tables.Cause | None
    cause_is_new: bool


def step_label(step: tables.Step | None) -> str:
    """The first tool the step called, or its role when it called none."""
    if step is None:
        return "unknown"
    if step.output.tool_calls:
        return step.output.tool_calls[0].name
    return step.output.role.value


async def store_verdict(
    database: Database,
    matcher: CauseMatcher,
    *,
    project_id: UUID,
    diagnosis_id: UUID,
    result: DiagnosisResult,
) -> StoredVerdict:
    """Groups the explanation (one model call), then stores the verdict and the cause together."""
    match = CauseMatch(cause_id=None, cost_usd=0.0)
    explanation = result.explanation
    grouped = explanation is not None and result.verdict_kind in _GROUPED_VERDICTS
    step_name = step_label(None)
    if explanation is not None and grouped:
        step_name = await _failing_step_name(database, project_id, diagnosis_id, result)
        candidates = await _candidates(database, project_id)
        match = await matcher.match(explanation, candidates, step_name=step_name)
    async with database.transaction() as session:
        diagnoses = DiagnosesRepository(session)
        diagnosis = await diagnoses.get(project_id=project_id, diagnosis_id=diagnosis_id)
        if diagnosis is None:
            raise NotFoundError
        stored = StoredVerdict(cause=None, cause_is_new=False)
        if explanation is not None and grouped:
            stored = await _file_cause(session, diagnosis, result, explanation, match, step_name)
        await diagnoses.finish(
            diagnosis=diagnosis,
            verdict_kind=result.verdict_kind,
            first_domino_step=result.first_domino_step,
            verify_passes=result.verify_passes,
            verify_samples=result.verify_samples,
            fixed_output=result.fixed_output,
            explanation=result.explanation,
            cause_id=stored.cause.id if stored.cause else None,
            check_count=result.check_count,
            replay_count=result.replay_count,
            cost_usd=Decimal(str(result.cost_usd + match.cost_usd)),
            finished_at=utc_now(),
        )
    return stored


async def _candidates(database: Database, project_id: UUID) -> list[CauseCandidate]:
    async with database.transaction() as session:
        causes = await CausesRepository(session).list_all(project_id=project_id)
    return [
        CauseCandidate(
            id=cause.id,
            title=cause.title,
            category=cause.category,
            step_name=cause.step_name,
            summary=cause.summary,
        )
        for cause in causes
    ]


async def _failing_step_name(
    database: Database, project_id: UUID, diagnosis_id: UUID, result: DiagnosisResult
) -> str:
    if result.first_domino_step is None:
        return step_label(None)
    async with database.transaction() as session:
        diagnosis = await DiagnosesRepository(session).get(
            project_id=project_id, diagnosis_id=diagnosis_id
        )
        if diagnosis is None:
            return step_label(None)
        step = await StepsRepository(session).get_by_index(
            project_id=project_id, run_id=diagnosis.run_id, index=result.first_domino_step
        )
    return step_label(step)


async def _file_cause(
    session: AsyncSession,
    diagnosis: tables.Diagnosis,
    result: DiagnosisResult,
    explanation: Explanation,
    match: CauseMatch,
    step_name: str,
) -> StoredVerdict:
    causes = CausesRepository(session)
    verified = result.verdict_kind is VerdictKind.STEP_VERIFIED
    now = utc_now()
    if match.cause_id is not None:
        cause = await causes.get(
            project_id=diagnosis.project_id, cause_id=match.cause_id, for_update=True
        )
        if cause is not None:
            cause = await causes.add_run(cause=cause, verified=verified, seen_at=now)
            return StoredVerdict(cause=cause, cause_is_new=False)
    cause = await causes.create(
        project_id=diagnosis.project_id,
        title=explanation.title,
        category=explanation.category,
        step_name=step_name,
        summary=explanation.summary,
        suggested_fix=explanation.suggested_fix,
        verified=verified,
        seen_at=now,
    )
    return StoredVerdict(cause=cause, cause_is_new=True)
