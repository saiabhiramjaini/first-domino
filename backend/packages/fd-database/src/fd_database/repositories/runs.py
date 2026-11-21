"""Runs repository."""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from fd_database.pages import TimeKey
from fd_database.tables import Run
from fd_shared.enums import RunSource, RunStatus
from fd_shared.models import TaskInput


class RunsRepository:
    """Recorded and replayed runs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        project_id: UUID,
        agent_name: str,
        task_input: TaskInput,
        created_by_id: UUID,
        started_at: datetime,
        source: RunSource = RunSource.RECORDED,
        parent_run_id: UUID | None = None,
        replay_job_id: UUID | None = None,
        replay_from_step: int | None = None,
    ) -> Run:
        """Starts a run in `running`."""
        run = Run(
            project_id=project_id,
            agent_name=agent_name,
            source=source,
            parent_run_id=parent_run_id,
            replay_job_id=replay_job_id,
            replay_from_step=replay_from_step,
            task_input=task_input,
            status=RunStatus.RUNNING,
            step_count=0,
            created_by_id=created_by_id,
            started_at=started_at,
        )
        self._session.add(run)
        await self._session.flush()
        return run

    async def get(self, *, project_id: UUID, run_id: UUID, for_update: bool = False) -> Run | None:
        """One run of the project. `for_update` locks it until the transaction ends."""
        statement = select(Run).where(Run.project_id == project_id, Run.id == run_id)
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def finish(
        self, *, run: Run, status: RunStatus, final_output: str | None, finished_at: datetime
    ) -> Run:
        """Moves a running run to its final status."""
        run.status = status
        run.final_output = final_output
        run.finished_at = finished_at
        await self._session.flush()
        return run

    async def set_step_count(self, *, run: Run, step_count: int) -> Run:
        """Raises the run's step count to cover a newly recorded step."""
        run.step_count = max(run.step_count, step_count)
        await self._session.flush()
        return run

    async def set_latest_diagnosis(self, *, run: Run, diagnosis_id: UUID) -> Run:
        """Points the run at its newest diagnosis."""
        run.latest_diagnosis_id = diagnosis_id
        await self._session.flush()
        return run

    async def list_filtered(
        self,
        *,
        project_id: UUID,
        statuses: Sequence[RunStatus] | None,
        sources: Sequence[RunSource] | None,
        agent_name: str | None,
        limit: int,
        after: TimeKey | None,
    ) -> list[Run]:
        """A page of matching runs, newest first."""
        statement = select(Run).where(*_filters(project_id, statuses, sources, agent_name))
        if after is not None:
            statement = statement.where(tuple_(Run.started_at, Run.id) < (after.at, after.id))
        statement = statement.order_by(Run.started_at.desc(), Run.id.desc()).limit(limit)
        return list(await self._session.scalars(statement))

    async def count_filtered(
        self,
        *,
        project_id: UUID,
        statuses: Sequence[RunStatus] | None,
        sources: Sequence[RunSource] | None,
        agent_name: str | None,
    ) -> int:
        """The number of matching runs."""
        statement = select(func.count()).select_from(Run)
        statement = statement.where(*_filters(project_id, statuses, sources, agent_name))
        return (await self._session.scalar(statement)) or 0


def _filters(
    project_id: UUID,
    statuses: Sequence[RunStatus] | None,
    sources: Sequence[RunSource] | None,
    agent_name: str | None,
) -> list[ColumnElement[bool]]:
    conditions = [Run.project_id == project_id]
    if statuses is not None:
        conditions.append(Run.status.in_(statuses))
    if sources is not None:
        conditions.append(Run.source.in_(sources))
    if agent_name is not None:
        conditions.append(Run.agent_name == agent_name)
    return conditions
