"""Postgres fixtures. Each test runs in a transaction that is rolled back afterwards.

The tests use a throwaway `<database>_test_<random>` on the `FD_DATABASE_URL` server (start
one with `make db-up`), never the database itself, and skip when the server is unreachable.
"""

from collections.abc import AsyncIterator, Iterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from fd_database.repositories import ProjectsRepository
from fd_database.settings import DatabaseSettings
from fd_database.tables import Base, Project
from fd_database.testing import temporary_test_database


@pytest.fixture(scope="session")
def database_settings() -> Iterator[DatabaseSettings]:
    with temporary_test_database(DatabaseSettings()) as settings:
        if settings is None:
            pytest.skip("Postgres is not reachable at FD_DATABASE_URL")
        yield settings


@pytest.fixture
async def session(database_settings: DatabaseSettings) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(database_settings.url.get_secret_value(), poolclass=NullPool)
    connection = await engine.connect()
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
