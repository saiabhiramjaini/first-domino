"""Schema migrations with Alembic: the upgrade the API runs at startup, and new revisions.

The Alembic environment and revisions ship inside this package (`fd_database/migrations/`), so
the wheel and the Docker image carry them. There is no `alembic.ini`; the configuration is built
here and Alembic always runs on a connection this module opens.
"""

from argparse import Namespace
from collections.abc import Iterator
from contextlib import contextmanager
from importlib.resources import as_file, files
from typing import Any

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection, func, inspect, select
from sqlalchemy.ext.asyncio import AsyncEngine

from fd_database.tables import Base
from fd_shared.logging import get_logger

log = get_logger(__name__)

MIGRATIONS_DIRECTORY = "migrations"
REVISION_FILE_TEMPLATE = "%%(rev)s_%%(slug)s"
VERSION_TABLE = "alembic_version"
# The schema `create_all` made before Alembic. A database that has the tables but no version
# table is stamped at this revision before it is upgraded.
BASELINE_REVISION = "0001"
# Postgres advisory lock key held while migrating, so two processes never migrate at once.
MIGRATION_LOCK_KEY = 0x6664_6D69_6772_6174

# Options shared by the Alembic environment and the schema comparison.
COMPARE_OPTIONS: dict[str, Any] = {"compare_type": True, "compare_server_default": True}


@contextmanager
def alembic_config(connection: Connection) -> Iterator[Config]:
    """Yields an Alembic configuration that runs on `connection`.

    Args:
        connection: An open connection with no transaction in progress. Alembic begins and
            commits its own transactions on it.
    """
    with as_file(files("fd_database") / MIGRATIONS_DIRECTORY) as directory:
        # Quiet: Alembic would write its own progress to stdout; this module logs instead.
        config = Config(cmd_opts=Namespace(quiet=True))
        config.set_main_option("script_location", str(directory))
        config.set_main_option("file_template", REVISION_FILE_TEMPLATE)
        config.attributes["connection"] = connection
        yield config


def current_revision(connection: Connection) -> str | None:
    """Returns the revision the database is at, or None when it has no version table."""
    revision = MigrationContext.configure(connection).get_current_revision()
    connection.commit()
    return revision


def schema_differences(connection: Connection) -> list[Any]:
    """Returns how the database schema differs from the tables, as Alembic autogenerate sees it."""
    context = MigrationContext.configure(connection, opts=COMPARE_OPTIONS)
    differences = compare_metadata(context, Base.metadata)
    connection.commit()
    return differences


def _predates_alembic(connection: Connection) -> bool:
    tables = set(inspect(connection).get_table_names())
    connection.commit()
    return VERSION_TABLE not in tables and bool(tables & set(Base.metadata.tables))


def _upgrade(connection: Connection) -> None:
    with alembic_config(connection) as config:
        if _predates_alembic(connection):
            command.stamp(config, BASELINE_REVISION)
            connection.commit()
            log.info("database.stamped", revision=BASELINE_REVISION)
        before = current_revision(connection)
        command.upgrade(config, "head")
        connection.commit()
        after = current_revision(connection)
    log.info("database.migrated", from_revision=before, to_revision=after)


async def upgrade(engine: AsyncEngine) -> None:
    """Upgrades the database to the latest revision, under a Postgres advisory lock.

    A fresh database is built from the first revision. A database whose tables `create_all`
    made before Alembic is stamped at the baseline first, then upgraded.

    Args:
        engine: The engine of the database to upgrade.
    """
    async with engine.connect() as connection:
        await connection.execute(select(func.pg_advisory_lock(MIGRATION_LOCK_KEY)))
        await connection.commit()
        try:
            await connection.run_sync(_upgrade)
        finally:
            await connection.rollback()
            await connection.execute(select(func.pg_advisory_unlock(MIGRATION_LOCK_KEY)))
            await connection.commit()


def _write_revision(connection: Connection, message: str) -> None:
    if not schema_differences(connection):
        log.info("database.revision_skipped", reason="no_changes")
        return
    with alembic_config(connection) as config:
        head = ScriptDirectory.from_config(config).get_current_head()
        revision_id = f"{int(head or 0) + 1:04d}"
        script = command.revision(config, message=message, autogenerate=True, rev_id=revision_id)
        connection.commit()
    path = script.path if script is not None and not isinstance(script, list) else None
    log.info("database.revision_written", revision=revision_id, path=path)


async def write_revision(engine: AsyncEngine, message: str) -> None:
    """Upgrades the database, then writes a revision for how the tables differ from it.

    Writes nothing when the tables match the database.

    Args:
        engine: The database to compare against. It is upgraded to the latest revision first.
        message: What the revision changes, used in its file name and docstring.
    """
    await upgrade(engine)
    async with engine.connect() as connection:
        await connection.run_sync(_write_revision, message)
