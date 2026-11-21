"""Turns a cause's diagnosed runs into regression test cases."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from fd_api.models.causes import CauseExport, RegressionCase
from fd_api.services.snapshots import messages_after
from fd_database import tables
from fd_database.repositories import DiagnosesRepository, RunsRepository, StepsRepository
from fd_database.tables.base import utc_now
from fd_shared.enums import DiagnosisStatus, VerdictKind


async def export_cause(
    session: AsyncSession, *, project_id: UUID, cause_id: UUID, max_cases: int
) -> CauseExport:
    """The cause's finished diagnoses, newest first, as one case per diagnosed run."""
    diagnoses = await DiagnosesRepository(session).list_filtered(
        project_id=project_id,
        run_ids=None,
        cause_ids=[cause_id],
        statuses=[DiagnosisStatus.DONE],
        verdict_kinds=None,
        limit=max_cases,
        after=None,
    )
    cases = [await _case(session, project_id, diagnosis) for diagnosis in diagnoses]
    return CauseExport(
        cause_id=cause_id,
        exported_at=utc_now(),
        cases=[case for case in cases if case is not None],
    )


async def _case(
    session: AsyncSession, project_id: UUID, diagnosis: tables.Diagnosis
) -> RegressionCase | None:
    step_index = diagnosis.first_domino_step
    run = await RunsRepository(session).get(project_id=project_id, run_id=diagnosis.run_id)
    if step_index is None or run is None:
        return None
    step = await StepsRepository(session).get_by_index(
        project_id=project_id, run_id=run.id, index=step_index
    )
    if step is None:
        return None
    return RegressionCase(
        run_id=run.id,
        diagnosis_id=diagnosis.id,
        agent_name=run.agent_name,
        task_input=run.task_input,
        first_domino_step=step_index,
        messages=await messages_after(
            session, project_id=project_id, run=run, save_point=step_index - 1
        ),
        original_output=step.output,
        fixed_output=diagnosis.fixed_output,
        verified=diagnosis.verdict_kind is VerdictKind.STEP_VERIFIED,
    )
