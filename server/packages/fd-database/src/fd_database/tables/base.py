"""Declarative base and columns shared by every table."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKeyConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    """The current time in UTC."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Base of every table."""


class IdMixin:
    """A UUID primary key minted by the application."""

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)


class TimestampMixin:
    """`created_at` and `updated_at`.

    Set in Python, not by the database, so a returned row never needs a reload to read them.
    """

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


def timestamp() -> Mapped[datetime]:
    """A required timezone-aware timestamp column."""
    return mapped_column(DateTime(timezone=True))


def optional_timestamp() -> Mapped[datetime | None]:
    """A nullable timezone-aware timestamp column."""
    return mapped_column(DateTime(timezone=True), nullable=True)


def project_foreign_key(column: str, target: str) -> ForeignKeyConstraint:
    """Pairs a parent reference with the tenant, so a row can never name another project's row.

    Created after every table (`use_alter`), because runs, replay jobs and diagnoses refer
    to each other.

    Args:
        column: The referencing column, such as `run_id`.
        target: The parent table, such as `runs`.
    """
    return ForeignKeyConstraint(
        ["project_id", column],
        [f"{target}.project_id", f"{target}.id"],
        use_alter=True,
        name=f"fk_{column}_{target}_tenant",
    )
