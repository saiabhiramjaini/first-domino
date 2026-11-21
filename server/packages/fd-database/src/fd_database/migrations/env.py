"""Alembic environment. `fd_database.schema` runs it on a connection it has already opened."""

from typing import Any, Literal

from alembic import context
from alembic.autogenerate.api import AutogenContext
from sqlalchemy import Connection

from fd_database.schema import COMPARE_OPTIONS
from fd_database.tables import Base
from fd_database.tables.types import PydanticJson


def _render_item(type_: str, item: Any, autogen_context: AutogenContext) -> str | Literal[False]:
    # A revision describes the stored column (JSONB), never the application type that validates it.
    if type_ == "type" and isinstance(item, PydanticJson):
        autogen_context.imports.add("from sqlalchemy.dialects import postgresql")
        return "postgresql.JSONB(astext_type=sa.Text())"
    return False


def _run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        # A revision with an autocommit block (such as ALTER TYPE ... ADD VALUE) commits what ran
        # before it, so every revision gets its own transaction.
        transaction_per_migration=True,
        render_item=_render_item,
        **COMPARE_OPTIONS,
    )
    with context.begin_transaction():
        context.run_migrations()


_run_migrations(context.config.attributes["connection"])
