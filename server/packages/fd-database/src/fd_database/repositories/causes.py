"""Causes repository."""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from fd_database.pages import CountKey
from fd_database.tables import Cause
from fd_shared.enums import CauseCategory


class CausesRepository:
    """Root cause groups."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        project_id: UUID,
        title: str,
        category: CauseCategory,
        step_name: str,
        summary: str,
        suggested_fix: str,
        verified: bool,
        seen_at: datetime,
    ) -> Cause:
        """Starts a cause group with its first run."""
        cause = Cause(
            project_id=project_id,
            title=title,
            category=category,
            step_name=step_name,
            summary=summary,
            suggested_fix=suggested_fix,
            run_count=1,
            verified_count=int(verified),
            first_seen_at=seen_at,
            last_seen_at=seen_at,
        )
        self._session.add(cause)
        await self._session.flush()
        return cause

    async def add_run(self, *, cause: Cause, verified: bool, seen_at: datetime) -> Cause:
        """Counts one more diagnosed run in the group."""
        cause.run_count += 1
        cause.verified_count += int(verified)
        cause.last_seen_at = max(cause.last_seen_at, seen_at)
        await self._session.flush()
        return cause

    async def remove_run(self, *, cause: Cause, verified: bool) -> Cause | None:
        """Counts one run fewer in the group. Deletes the group when no run is left in it."""
        cause.run_count -= 1
        cause.verified_count -= int(verified)
        if cause.run_count <= 0:
            await self._session.delete(cause)
            await self._session.flush()
            return None
        await self._session.flush()
        return cause

    async def get(
        self, *, project_id: UUID, cause_id: UUID, for_update: bool = False
    ) -> Cause | None:
        """One cause of the project. `for_update` locks it until the transaction ends."""
        statement = select(Cause).where(Cause.project_id == project_id, Cause.id == cause_id)
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def list_all(self, *, project_id: UUID) -> list[Cause]:
        """Every cause of the project, for grouping a new explanation."""
        statement = select(Cause).where(Cause.project_id == project_id).order_by(Cause.created_at)
        return list(await self._session.scalars(statement))

    async def list_filtered(
        self,
        *,
        project_id: UUID,
        categories: Sequence[CauseCategory] | None,
        limit: int,
        after: CountKey | None,
    ) -> list[Cause]:
        """A page of matching causes, most runs first."""
        statement = select(Cause).where(*_filters(project_id, categories))
        if after is not None:
            key = tuple_(Cause.run_count, Cause.id)
            statement = statement.where(key < (after.count, after.id))
        statement = statement.order_by(Cause.run_count.desc(), Cause.id.desc()).limit(limit)
        return list(await self._session.scalars(statement))

    async def count_filtered(
        self, *, project_id: UUID, categories: Sequence[CauseCategory] | None
    ) -> int:
        """The number of matching causes."""
        statement = select(func.count()).select_from(Cause).where(*_filters(project_id, categories))
        return (await self._session.scalar(statement)) or 0


def _filters(
    project_id: UUID, categories: Sequence[CauseCategory] | None
) -> list[ColumnElement[bool]]:
    conditions = [Cause.project_id == project_id]
    if categories is not None:
        conditions.append(Cause.category.in_(categories))
    return conditions
