"""Users, projects and API keys tables."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from fd_database.tables.base import Base, IdMixin, TimestampMixin, optional_timestamp

API_KEY_HASH_LENGTH = 64
API_KEY_PREFIX_LENGTH = 12


class User(IdMixin, TimestampMixin, Base):
    """A person who signs in to the web app with Google."""

    __tablename__ = "users"

    google_sub: Mapped[str] = mapped_column(String(255), unique=True)
    email: Mapped[str] = mapped_column(String(320))
    name: Mapped[str] = mapped_column(String(256))


class Project(IdMixin, TimestampMixin, Base):
    """The tenant. During the hackathon each person owns exactly one."""

    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(256))
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    slack_webhook_url: Mapped[str | None] = mapped_column(Text)


class ApiKey(IdMixin, TimestampMixin, Base):
    """A project API key. Only the SHA-256 hash of the secret is stored."""

    __tablename__ = "api_keys"
    __table_args__ = (
        UniqueConstraint("project_id", "id"),
        Index("ix_api_keys_project_created", "project_id", "created_at"),
    )

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(128))
    prefix: Mapped[str] = mapped_column(String(API_KEY_PREFIX_LENGTH))
    key_hash: Mapped[str] = mapped_column(String(API_KEY_HASH_LENGTH), unique=True)
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    last_used_at: Mapped[datetime | None] = optional_timestamp()
    revoked_at: Mapped[datetime | None] = optional_timestamp()
    revoked_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
