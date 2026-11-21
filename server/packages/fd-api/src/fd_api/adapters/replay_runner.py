"""ReplayRunner port over the replay job queue."""

import asyncio
from collections.abc import Sequence
from uuid import UUID

from fd_api.adapters.check_tracker import CheckTracker
from fd_api.services.snapshots import messages_after
from fd_api.settings import ApiSettings
from fd_database import tables
from fd_database.repositories import (
    DiagnosesRepository,
    ReplayJobsRepository,
    RunsRepository,
)
from fd_database.session import Database
from fd_database.tables.base import utc_now
from fd_shared.enums import ReplayJobStatus, ReplayOutcome
from fd_shared.errors import NotFoundError
from fd_shared.logging import get_logger
from fd_shared.models import Message

log = get_logger(__name__)

_FINAL_STATUSES = frozenset(
    {ReplayJobStatus.SUCCEEDED, ReplayJobStatus.FAILED, ReplayJobStatus.EXPIRED}
)


def outcome_of(job: tables.ReplayJob) -> ReplayOutcome | None:
    """The job's replay outcome, `errored` for a job that never ran, or None while it is open."""
    if job.status not in _FINAL_STATUSES:
        return None
    return job.outcome or ReplayOutcome.ERRORED


class QueueReplayRunner:
    """Turns the engine's replay requests into jobs for one diagnosis and waits for them."""

    def __init__(
        self,
        database: Database,
        *,
        project_id: UUID,
        diagnosis_id: UUID,
        tracker: CheckTracker,
        settings: ApiSettings,
    ) -> None:
        self._database = database
        self._tracker = tracker
        self._project_id = project_id
        self._diagnosis_id = diagnosis_id
        self._settings = settings

    async def replay(
        self,
        run_id: UUID,
        *,
        from_step: int,
        samples: int,
        model_override: str | None,
        replacement_output: Message | None,
    ) -> list[ReplayOutcome]:
        """Queues `samples` replays and waits until each has a result.

        The engine cancels this call when the check is decided early or times out. Then the
        jobs without a result are ended: the customer's worker skips the queued ones and
        stops the running ones, since nobody will read their outcome.
        """
        job_ids = await self._enqueue(
            run_id,
            from_step=from_step,
            samples=samples,
            model_override=model_override,
            replacement_output=replacement_output,
        )
        log.info("replays.queued", diagnosis_id=str(self._diagnosis_id), from_step=from_step)
        try:
            return await self._wait(job_ids)
        except asyncio.CancelledError:
            await asyncio.shield(self._end_unfinished(job_ids))
            raise

    async def _end_unfinished(self, job_ids: Sequence[UUID]) -> None:
        async with self._database.transaction() as session:
            ended = await ReplayJobsRepository(session).expire_unfinished(
                project_id=self._project_id, replay_job_ids=job_ids, now=utc_now()
            )
        if ended:
            log.info("replays.ended_unfinished", diagnosis_id=str(self._diagnosis_id), count=ended)

    async def _enqueue(
        self,
        run_id: UUID,
        *,
        from_step: int,
        samples: int,
        model_override: str | None,
        replacement_output: Message | None,
    ) -> list[UUID]:
        async with self._database.transaction() as session:
            run = await RunsRepository(session).get(project_id=self._project_id, run_id=run_id)
            if run is None:
                raise NotFoundError
            jobs = await ReplayJobsRepository(session).enqueue(
                project_id=self._project_id,
                run_id=run.id,
                diagnosis_id=self._diagnosis_id,
                check_id=self._tracker.current_check_id,
                agent_name=run.agent_name,
                task_input=run.task_input,
                from_step=from_step,
                messages=await messages_after(
                    session, project_id=self._project_id, run=run, save_point=from_step
                ),
                replacement_output=replacement_output,
                model_override=model_override,
                samples=samples,
            )
            await DiagnosesRepository(session).count_progress(
                project_id=self._project_id,
                diagnosis_id=self._diagnosis_id,
                checks_at_least=0,
                replays_added=samples,
            )
        return [job.id for job in jobs]

    async def _wait(self, job_ids: Sequence[UUID]) -> list[ReplayOutcome]:
        while True:
            outcomes = await self._outcomes(job_ids)
            finished = [outcome for outcome in outcomes if outcome is not None]
            if len(finished) == len(job_ids):
                return finished
            await asyncio.sleep(self._settings.replay_poll_interval_seconds)

    async def _outcomes(self, job_ids: Sequence[UUID]) -> list[ReplayOutcome | None]:
        async with self._database.transaction() as session:
            jobs = ReplayJobsRepository(session)
            await jobs.expire_leases(
                project_id=self._project_id,
                now=utc_now(),
                max_attempts=self._settings.max_job_attempts,
            )
            rows = await jobs.get_many(project_id=self._project_id, replay_job_ids=job_ids)
        return [outcome_of(row) for row in rows]
