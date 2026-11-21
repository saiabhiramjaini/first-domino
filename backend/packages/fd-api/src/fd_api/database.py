"""The request's database session: one transaction per request, committed before the response."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from fd_database.session import Database


def get_database(request: Request) -> Database:
    """The process's database, set up at startup."""
    return request.app.state.database


async def _session(request: Request) -> AsyncIterator[AsyncSession]:
    async with get_database(request).transaction() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(_session, scope="function")]
