"""A throwaway database per test run, so tests never touch the one the API and web app use.

Each run gets its own `<database>_test_<random>` on the configured server, migrated to the
latest revision the way the API migrates at startup, and dropped when the run ends. Parallel
runs from other worktrees never see each other's data.
"""

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import uuid4

from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from fd_database.session import Database
from fd_database.settings import DatabaseSettings

MAINTENANCE_DATABASE = "postgres"
TEST_DATABASE_INFIX = "_test_"


async def _execute_on_server(url: URL, statement: str) -> None:
    admin = create_async_engine(
        url.set(database=MAINTENANCE_DATABASE), isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    try:
        async with admin.connect() as connection:
            await connection.execute(text(statement))
    finally:
        await admin.dispose()


def _quoted(url: URL) -> str:
    # CREATE and DROP DATABASE take no bind parameters; the generated name is quoted instead.
    return '"' + (url.database or "").replace('"', '""') + '"'


async def create_empty_database(settings: DatabaseSettings) -> DatabaseSettings | None:
    """Creates a new empty database beside the configured one.

    Returns:
        Settings for the new database, or None when the server is unreachable.
    """
    base = make_url(settings.url.get_secret_value())
    url = base.set(database=f"{base.database}{TEST_DATABASE_INFIX}{uuid4().hex[:8]}")
    try:
        await _execute_on_server(url, f"CREATE DATABASE {_quoted(url)}")
    except OSError:
        return None
    rendered = SecretStr(url.render_as_string(hide_password=False))
    return settings.model_copy(update={"url": rendered})


async def drop_database(settings: DatabaseSettings) -> None:
    """Drops the database, closing any connection still open to it."""
    url = make_url(settings.url.get_secret_value())
    await _execute_on_server(url, f"DROP DATABASE IF EXISTS {_quoted(url)} WITH (FORCE)")


async def migrate_database(settings: DatabaseSettings) -> None:
    """Upgrades the database to the latest revision."""
    database = Database(settings)
    try:
        await database.migrate()
    finally:
        await database.dispose()


@contextmanager
def temporary_test_database(settings: DatabaseSettings) -> Iterator[DatabaseSettings | None]:
    """Yields settings for a new migrated database, or None when the server is unreachable."""
    created = asyncio.run(create_empty_database(settings))
    if created is None:
        yield None
        return
    try:
        asyncio.run(migrate_database(created))
        yield created
    finally:
        asyncio.run(drop_database(created))
