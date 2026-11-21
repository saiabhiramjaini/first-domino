"""Postgres fixtures. Each test runs in a transaction that is rolled back afterwards.

The tests use `FD_DATABASE_URL` (start one with `make db-up`) and skip when it is unreachable.
"""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from fd_database.repositories import ProjectsRepository
from fd_database.settings import DatabaseSettings
from fd_database.tables import Base, Project


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(DatabaseSettings().url.get_secret_value(), poolclass=NullPool)
    try:
        connection = await engine.connect()
    except OSError:
        await engine.dispose()
        pytest.skip("Postgres is not reachable at FD_DATABASE_URL")
    await connection.run_sync(Base.metadata.create_all)
    await connection.commit()
    transaction = await connection.begin()
    async with AsyncSession(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    ) as session:
        yield session
    await transaction.rollback()
    await connection.close()
    await engine.dispose()


async def make_project(session: AsyncSession, google_sub: str) -> Project:
    projects = ProjectsRepository(session)
    user = await projects.upsert_user(google_sub=google_sub, email=f"{google_sub}@x.test", name="T")
    return await projects.create(owner_id=user.id, name="Test project")


@pytest.fixture
async def project(session: AsyncSession) -> Project:
    return await make_project(session, "owner-a")


@pytest.fixture
async def other_project(session: AsyncSession) -> Project:
    return await make_project(session, "owner-b")
