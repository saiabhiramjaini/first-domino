"""Replay jobs repository: enqueue, lease, expire leases, record results."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fd_database.tables import ReplayJob
from fd_shared.enums import ReplayJobStatus, ReplayOutcome
from fd_shared.models import Message, ReplayDrift, TaskInput


@dataclass(frozen=True, slots=True)
class WaitingReplays:
    """Replays of one diagnosis still queued: no worker has picked them up yet."""

    count: int
    oldest_queued_at: datetime


class ReplayJobsRepository:
    """The replay job queue. Every read and write is scoped to one project."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(
        self,
        *,
        project_id: UUID,
        run_id: UUID,
        diagnosis_id: UUID | None,
        check_id: UUID | None,
        agent_name: str,
        task_input: TaskInput,
        from_step: int,
        messages: list[Message],
        replacement_output: Message | None,
        model_override: str | None,
        samples: int,
    ) -> list[ReplayJob]:
        """Queues `samples` identical jobs, one per replay."""
        jobs = [
            ReplayJob(
                project_id=project_id,
                run_id=run_id,
                diagnosis_id=diagnosis_id,
                check_id=check_id,
                agent_name=agent_name,
                task_input=task_input,
                from_step=from_step,
                messages=messages,
                replacement_output=replacement_output,
                model_override=model_override,
                status=ReplayJobStatus.QUEUED,
                attempt=0,
            )
            for _ in range(samples)
        ]
        self._session.add_all(jobs)
        await self._session.flush()
        return jobs

    async def lease_next(
        self,
        *,
        project_id: UUID,
        agent_names: Sequence[str],
        leased_by_id: UUID,
        now: datetime,
        lease_seconds: int,
    ) -> ReplayJob | None:
        """Leases the oldest queued job for one of the agents, skipping rows others hold."""
        statement = (
            select(ReplayJob)
            .where(
                ReplayJob.project_id == project_id,
                ReplayJob.status == ReplayJobStatus.QUEUED,
                ReplayJob.agent_name.in_(agent_names),
            )
            .order_by(ReplayJob.created_at, ReplayJob.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        job = await self._session.scalar(statement)
        if job is None:
            return None
        job.status = ReplayJobStatus.LEASED
        job.attempt += 1
        job.leased_at = now
        job.leased_by_id = leased_by_id
        job.lease_expires_at = now + timedelta(seconds=lease_seconds)
        await self._session.flush()
        return job

    async def expire_for_diagnoses(self, *, diagnosis_ids: Sequence[UUID], now: datetime) -> None:
        """Ends the unfinished replay jobs of diagnoses that restarted; nobody waits for them."""
        if not diagnosis_ids:
            return
        await self._session.execute(
            update(ReplayJob)
            .where(
                ReplayJob.diagnosis_id.in_(diagnosis_ids),
                ReplayJob.status.in_([ReplayJobStatus.QUEUED, ReplayJobStatus.LEASED]),
            )
            .values(status=ReplayJobStatus.EXPIRED, lease_expires_at=None, finished_at=now)
        )

    async def expire_unfinished(
        self, *, project_id: UUID, replay_job_ids: Sequence[UUID], now: datetime
    ) -> int:
        """Ends the jobs that have no result yet, because nobody waits for them any more.

        A worker running one of them sees it ended and stops the replay. Returns how many ended.
        """
        if not replay_job_ids:
            return 0
        ended = await self._session.scalars(
            update(ReplayJob)
            .where(
                ReplayJob.project_id == project_id,
                ReplayJob.id.in_(replay_job_ids),
                ReplayJob.status.in_([ReplayJobStatus.QUEUED, ReplayJobStatus.LEASED]),
            )
            .values(status=ReplayJobStatus.EXPIRED, finished_at=now)
            .returning(ReplayJob.id)
        )
        return len(ended.all())

    async def expire_leases(self, *, project_id: UUID, now: datetime, max_attempts: int) -> None:
        """Returns jobs whose lease ended to the queue, or ends them after `max_attempts`."""
        expired = (
            ReplayJob.project_id == project_id,
            ReplayJob.status == ReplayJobStatus.LEASED,
            ReplayJob.lease_expires_at < now,
        )
        await self._session.execute(
            update(ReplayJob)
            .where(*expired, ReplayJob.attempt >= max_attempts)
            .values(status=ReplayJobStatus.EXPIRED, lease_expires_at=None, finished_at=now)
        )
        await self._session.execute(
            update(ReplayJob)
            .where(*expired)
            .values(status=ReplayJobStatus.QUEUED, lease_expires_at=None)
        )

    async def submit(
        self,
        *,
        project_id: UUID,
        replay_job_id: UUID,
        outcome: ReplayOutcome,
        replay_run_id: UUID | None,
        error_code: str | None,
        drift: ReplayDrift | None,
        now: datetime,
    ) -> ReplayJob | None:
        """Stores the first result of a leased job and its drift. A later result changes nothing.

        Returns the job as stored, or None when the project has no such job.
        """
        status = (
            ReplayJobStatus.FAILED
            if outcome is ReplayOutcome.ERRORED
            else ReplayJobStatus.SUCCEEDED
        )
        await self._session.execute(
            update(ReplayJob)
            .where(
                ReplayJob.project_id == project_id,
                ReplayJob.id == replay_job_id,
                ReplayJob.status == ReplayJobStatus.LEASED,
            )
            .values(
                status=status,
                outcome=outcome,
                replay_run_id=replay_run_id,
                error_code=error_code,
                drift_step=drift.step if drift else None,
                drift_tool_name=drift.tool_name if drift else None,
                lease_expires_at=None,
                finished_at=now,
                updated_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        return await self.get(project_id=project_id, replay_job_id=replay_job_id, refresh=True)

    async def get(
        self, *, project_id: UUID, replay_job_id: UUID, refresh: bool = False
    ) -> ReplayJob | None:
        """One job of the project. `refresh` rereads a job this session already holds."""
        statement = select(ReplayJob).where(
            ReplayJob.project_id == project_id, ReplayJob.id == replay_job_id
        )
        if refresh:
            statement = statement.execution_options(populate_existing=True)
        return await self._session.scalar(statement)

    async def waiting_by_diagnosis(
        self, *, project_id: UUID, diagnosis_ids: Sequence[UUID]
    ) -> dict[UUID, WaitingReplays]:
        """For each diagnosis, its replays no worker has leased yet, and the oldest one's age."""
        if not diagnosis_ids:
            return {}
        statement = (
            select(ReplayJob.diagnosis_id, func.count(), func.min(ReplayJob.created_at))
            .where(
                ReplayJob.project_id == project_id,
                ReplayJob.diagnosis_id.in_(diagnosis_ids),
                ReplayJob.status == ReplayJobStatus.QUEUED,
            )
            .group_by(ReplayJob.diagnosis_id)
        )
        rows = (await self._session.execute(statement)).all()
        return {
            diagnosis_id: WaitingReplays(count=count, oldest_queued_at=oldest)
            for diagnosis_id, count, oldest in rows
            if diagnosis_id is not None
        }

    async def get_many(
        self, *, project_id: UUID, replay_job_ids: Sequence[UUID]
    ) -> list[ReplayJob]:
        """The project's jobs with these ids, freshly read."""
        statement = (
            select(ReplayJob)
            .where(ReplayJob.project_id == project_id, ReplayJob.id.in_(replay_job_ids))
            .execution_options(populate_existing=True)
        )
        return list(await self._session.scalars(statement))
