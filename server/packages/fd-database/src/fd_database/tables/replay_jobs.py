"""Replay jobs table: the queue the customer's worker leases from."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from fd_database.tables.base import (
    Base,
    IdMixin,
    TimestampMixin,
    optional_timestamp,
    project_foreign_key,
)
from fd_database.tables.types import REPLAY_JOB_STATUS, REPLAY_OUTCOME, PydanticJson
from fd_shared.enums import ReplayJobStatus, ReplayOutcome
from fd_shared.models import Message, TaskInput


class ReplayJob(IdMixin, TimestampMixin, Base):
    """A request to replay a run from a save point, and its result."""

    __tablename__ = "replay_jobs"
    __table_args__ = (
        UniqueConstraint("project_id", "id"),
        project_foreign_key("run_id", "runs"),
        project_foreign_key("diagnosis_id", "diagnoses"),
        project_foreign_key("check_id", "checks"),
        project_foreign_key("replay_run_id", "runs"),
        project_foreign_key("leased_by_id", "api_keys"),
        Index("ix_replay_jobs_queue", "project_id", "status", "agent_name", "created_at"),
        Index("ix_replay_jobs_lease_expiry", "status", "lease_expires_at"),
    )

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"))
    run_id: Mapped[UUID]
    diagnosis_id: Mapped[UUID | None]
    check_id: Mapped[UUID | None]
    agent_name: Mapped[str] = mapped_column(String(128))
    task_input: Mapped[TaskInput] = mapped_column(PydanticJson(TaskInput))
    from_step: Mapped[int]
    messages: Mapped[list[Message]] = mapped_column(PydanticJson(list[Message]))
    replacement_output: Mapped[Message | None] = mapped_column(PydanticJson(Message))
    model_override: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[ReplayJobStatus] = mapped_column(REPLAY_JOB_STATUS)
    attempt: Mapped[int]
    leased_at: Mapped[datetime | None] = optional_timestamp()
    leased_by_id: Mapped[UUID | None]
    lease_expires_at: Mapped[datetime | None] = optional_timestamp()
    outcome: Mapped[ReplayOutcome | None] = mapped_column(REPLAY_OUTCOME)
    replay_run_id: Mapped[UUID | None]
    error_code: Mapped[str | None] = mapped_column(String(128))
    finished_at: Mapped[datetime | None] = optional_timestamp()
