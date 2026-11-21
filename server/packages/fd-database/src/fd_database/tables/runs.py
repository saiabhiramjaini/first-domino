"""Runs and steps tables."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from fd_database.tables.base import (
    Base,
    IdMixin,
    TimestampMixin,
    optional_timestamp,
    project_foreign_key,
    timestamp,
)
from fd_database.tables.types import RUN_SOURCE, RUN_STATUS, PydanticJson
from fd_shared.enums import RunSource, RunStatus
from fd_shared.models import Message, TaskInput


class Run(IdMixin, TimestampMixin, Base):
    """One agent run, recorded or replayed."""

    __tablename__ = "runs"
    __table_args__ = (
        UniqueConstraint("project_id", "id"),
        project_foreign_key("parent_run_id", "runs"),
        project_foreign_key("replay_job_id", "replay_jobs"),
        project_foreign_key("latest_diagnosis_id", "diagnoses"),
        project_foreign_key("created_by_id", "api_keys"),
        project_foreign_key("check_id", "checks"),
        Index("ix_runs_project_source_started", "project_id", "source", "started_at", "id"),
        Index("ix_runs_project_check", "project_id", "check_id"),
    )

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"))
    agent_name: Mapped[str] = mapped_column(String(128))
    source: Mapped[RunSource] = mapped_column(RUN_SOURCE)
    parent_run_id: Mapped[UUID | None]
    replay_job_id: Mapped[UUID | None]
    replay_from_step: Mapped[int | None]
    check_id: Mapped[UUID | None]
    task_input: Mapped[TaskInput] = mapped_column(PydanticJson(TaskInput))
    tool_names: Mapped[list[str]] = mapped_column(ARRAY(String(128)))
    status: Mapped[RunStatus] = mapped_column(RUN_STATUS)
    step_count: Mapped[int]
    final_output: Mapped[str | None] = mapped_column(Text)
    latest_diagnosis_id: Mapped[UUID | None]
    created_by_id: Mapped[UUID]
    started_at: Mapped[datetime] = timestamp()
    finished_at: Mapped[datetime | None] = optional_timestamp()


class Step(IdMixin, TimestampMixin, Base):
    """One step of a run, with the message snapshot saved after it."""

    __tablename__ = "steps"
    __table_args__ = (
        UniqueConstraint("project_id", "run_id", "index"),
        project_foreign_key("run_id", "runs"),
    )

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"))
    run_id: Mapped[UUID]
    index: Mapped[int]
    model: Mapped[str] = mapped_column(String(128))
    output: Mapped[Message] = mapped_column(PydanticJson(Message))
    tool_results: Mapped[list[Message]] = mapped_column(PydanticJson(list[Message]))
    messages: Mapped[list[Message]] = mapped_column(PydanticJson(list[Message]))
    tokens_in: Mapped[int]
    tokens_out: Mapped[int]
    latency_ms: Mapped[int]
