"""Creating a diagnosis: the rules shared by `createDiagnosis` and auto-diagnosis."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from fd_database import tables
from fd_database.repositories import DiagnosesRepository, RunsRepository
from fd_shared.enums import RunSource, RunStatus
from fd_shared.errors import ConflictError
from fd_shared.logging import get_logger

log = get_logger(__name__)


def can_diagnose(run: tables.Run) -> bool:
    """Only failed recorded runs are diagnosed."""
    return run.source is RunSource.RECORDED and run.status is RunStatus.FAILED


async def create_diagnosis(
    session: AsyncSession, *, run: tables.Run, created_by_id: UUID | None
) -> tables.Diagnosis:
    """Queues a diagnosis of a failed recorded run and makes it the run's latest.

    Raises:
        ConflictError: The run cannot be diagnosed, or a diagnosis of it is running.
    """
    diagnoses = DiagnosesRepository(session)
    if not can_diagnose(run):
        raise ConflictError
    if await diagnoses.has_active(project_id=run.project_id, run_id=run.id):
        raise ConflictError
    diagnosis = await diagnoses.create(
        project_id=run.project_id, run_id=run.id, created_by_id=created_by_id
    )
    await RunsRepository(session).set_latest_diagnosis(run=run, diagnosis_id=diagnosis.id)
    log.info("diagnoses.created", diagnosis_id=str(diagnosis.id), run_id=str(run.id))
    return diagnosis
