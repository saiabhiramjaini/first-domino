"""CheckSink port that stores each check for the web app."""

from uuid import UUID

from fd_api.adapters.check_tracker import CheckTracker
from fd_database.repositories import DiagnosesRepository
from fd_database.session import Database
from fd_database.tables.base import utc_now
from fd_shared.enums import DiagnosisStatus
from fd_shared.errors import NotFoundError
from fd_shared.models import CheckView


class DatabaseCheckSink:
    """Stores one project's checks and live search range as the engine reports them."""

    def __init__(self, database: Database, project_id: UUID, tracker: CheckTracker) -> None:
        self._database = database
        self._project_id = project_id
        self._tracker = tracker

    async def check_started(self, check: CheckView) -> None:
        """Stores a new `pending` check, counts it, and marks it as the running check."""
        self._tracker.current_check_id = await self._save(check, finished=False)
        async with self._database.transaction() as session:
            await DiagnosesRepository(session).count_progress(
                project_id=self._project_id,
                diagnosis_id=check.diagnosis_id,
                checks_at_least=check.index + 1,
                replays_added=0,
            )

    async def check_finished(self, check: CheckView) -> None:
        """Stores a check's passes and result over the pending one with the same index."""
        await self._save(check, finished=True)

    async def progress(
        self,
        diagnosis_id: UUID,
        *,
        status: DiagnosisStatus,
        search_low: int | None,
        search_high: int | None,
    ) -> None:
        """Stores the diagnosis status and current search range.

        Raises:
            NotFoundError: The project has no such diagnosis.
        """
        async with self._database.transaction() as session:
            diagnoses = DiagnosesRepository(session)
            diagnosis = await diagnoses.get(project_id=self._project_id, diagnosis_id=diagnosis_id)
            if diagnosis is None:
                raise NotFoundError
            await diagnoses.set_progress(
                diagnosis=diagnosis, status=status, search_low=search_low, search_high=search_high
            )

    async def _save(self, check: CheckView, *, finished: bool) -> UUID:
        async with self._database.transaction() as session:
            stored = await DiagnosesRepository(session).save_check(
                project_id=self._project_id,
                diagnosis_id=check.diagnosis_id,
                index=check.index,
                phase=check.phase,
                save_point=check.save_point,
                samples=check.samples,
                passes=check.passes,
                result=check.result,
                finished_at=utc_now() if finished else None,
            )
        return stored.id
