"""The migrations build exactly the tables, and adopt a database `create_all` made before them."""

from collections.abc import AsyncIterator

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import Connection, Enum, inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from fd_database.schema import (
    BASELINE_REVISION,
    VERSION_TABLE,
    alembic_config,
    current_revision,
    schema_differences,
    upgrade,
)
from fd_database.settings import DatabaseSettings
from fd_database.tables import Base
from fd_database.testing import create_empty_database, drop_database


@pytest.fixture
async def empty_engine() -> AsyncIterator[AsyncEngine]:
    settings = await create_empty_database(DatabaseSettings())
    if settings is None:
        pytest.skip("Postgres is not reachable at FD_DATABASE_URL")
    engine = create_async_engine(settings.url.get_secret_value(), poolclass=NullPool)
    yield engine
    await engine.dispose()
    await drop_database(settings)


def _run_alembic(connection: Connection, action: str, revision: str) -> None:
    with alembic_config(connection) as config:
        getattr(command, action)(config, revision)
    connection.commit()


def _head(connection: Connection) -> str | None:
    with alembic_config(connection) as config:
        return ScriptDirectory.from_config(config).get_current_head()


def _declared_enums() -> dict[str, list[str]]:
    return {
        column.type.name: list(column.type.enums)
        for table in Base.metadata.tables.values()
        for column in table.columns
        if isinstance(column.type, Enum) and column.type.native_enum and column.type.name
    }


def _stored_enums(connection: Connection) -> dict[str, list[str]]:
    # Alembic autogenerate does not compare enum values, so they are checked here, in order.
    rows = connection.execute(
        text(
            "SELECT t.typname, e.enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
            "ORDER BY t.typname, e.enumsortorder"
        )
    )
    stored: dict[str, list[str]] = {}
    for name, label in rows:
        stored.setdefault(name, []).append(label)
    return stored


async def test_migrated_schema_matches_the_tables(database_settings: DatabaseSettings) -> None:
    engine = create_async_engine(database_settings.url.get_secret_value(), poolclass=NullPool)
    async with engine.connect() as connection:
        differences = await connection.run_sync(schema_differences)
        stored_enums = await connection.run_sync(_stored_enums)
    await engine.dispose()
    assert differences == []
    assert stored_enums == _declared_enums()


async def test_database_from_before_alembic_is_stamped_then_upgraded(
    empty_engine: AsyncEngine,
) -> None:
    async with empty_engine.connect() as connection:
        await connection.run_sync(_run_alembic, "upgrade", BASELINE_REVISION)
        await connection.execute(text(f"DROP TABLE {VERSION_TABLE}"))
        await connection.execute(
            text(
                "INSERT INTO users (id, google_sub, email, name, created_at, updated_at) "
                "VALUES (gen_random_uuid(), 'sub', 'a@x.test', 'A', now(), now())"
            )
        )
        await connection.commit()

    await upgrade(empty_engine)
    await upgrade(empty_engine)

    async with empty_engine.connect() as connection:
        assert await connection.run_sync(current_revision) == await connection.run_sync(_head)
        assert await connection.run_sync(schema_differences) == []
        assert await connection.run_sync(_stored_enums) == _declared_enums()
        assert await connection.scalar(text("SELECT count(*) FROM users")) == 1


async def test_downgrade_to_nothing_and_upgrade_again(empty_engine: AsyncEngine) -> None:
    await upgrade(empty_engine)
    async with empty_engine.connect() as connection:
        await connection.run_sync(_run_alembic, "downgrade", "base")
        tables = await connection.run_sync(lambda sync: inspect(sync).get_table_names())
        await connection.commit()
    assert tables == [VERSION_TABLE]

    await upgrade(empty_engine)
    async with empty_engine.connect() as connection:
        assert await connection.run_sync(schema_differences) == []
