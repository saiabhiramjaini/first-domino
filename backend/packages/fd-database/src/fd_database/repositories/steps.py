"""Steps repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from fd_database.pages import IndexKey
from fd_database.tables import Step
from fd_database.tables.base import utc_now
from fd_shared.models import Message


class StepsRepository:
    """Steps of a run and the message snapshot saved after each."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        project_id: UUID,
        run_id: UUID,
        index: int,
        model: str,
        output: Message,
        tool_results: list[Message],
        messages: list[Message],
        tokens_in: int,
        tokens_out: int,
        latency_ms: int,
    ) -> Step:
        """Stores a step. A repeat of (`run_id`, `index`) returns the stored step unchanged."""
        now = utc_now()
        statement = (
            insert(Step)
            .values(
                project_id=project_id,
                run_id=run_id,
                index=index,
                model=model,
                output=output,
                tool_results=tool_results,
                messages=messages,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing(index_elements=[Step.project_id, Step.run_id, Step.index])
            .returning(Step)
        )
        inserted = (await self._session.scalars(statement)).one_or_none()
        if inserted is not None:
            return inserted
        stored = await self.get_by_index(project_id=project_id, run_id=run_id, index=index)
        if stored is None:
            raise LookupError(index)
        return stored

    async def get(self, *, project_id: UUID, step_id: UUID) -> Step | None:
        """One step of the project."""
        return await self._session.scalar(
            select(Step).where(Step.project_id == project_id, Step.id == step_id)
        )

    async def get_by_index(self, *, project_id: UUID, run_id: UUID, index: int) -> Step | None:
        """The step of a run at a given index."""
        return await self._session.scalar(
            select(Step).where(
                Step.project_id == project_id, Step.run_id == run_id, Step.index == index
            )
        )

    async def list_page(
        self, *, project_id: UUID, run_id: UUID, limit: int, after: IndexKey | None
    ) -> list[Step]:
        """A page of a run's steps in index order."""
        statement = select(Step).where(Step.project_id == project_id, Step.run_id == run_id)
        if after is not None:
            statement = statement.where(Step.index > after.index)
        statement = statement.order_by(Step.index).limit(limit)
        return list(await self._session.scalars(statement))

    async def list_all(self, *, project_id: UUID, run_id: UUID) -> list[Step]:
        """Every step of a run in index order, for the engine."""
        statement = (
            select(Step)
            .where(Step.project_id == project_id, Step.run_id == run_id)
            .order_by(Step.index)
        )
        return list(await self._session.scalars(statement))
