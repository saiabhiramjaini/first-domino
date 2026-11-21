"""Diagnoses, checks and causes tables."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from fd_database.tables.base import (
    Base,
    IdMixin,
    TimestampMixin,
    optional_timestamp,
    project_foreign_key,
    timestamp,
)
from fd_database.tables.types import (
    CAUSE_CATEGORY,
    CHECK_PHASE,
    CHECK_RESULT,
    DIAGNOSIS_ERROR_CODE,
    DIAGNOSIS_STATUS,
    VERDICT_KIND,
    PydanticJson,
)
from fd_shared.enums import (
    CauseCategory,
    CheckPhase,
    CheckResult,
    DiagnosisErrorCode,
    DiagnosisStatus,
    VerdictKind,
)
from fd_shared.models import Explanation, Message

COST_PRECISION = 12
COST_SCALE = 6

ACTIVE_DIAGNOSIS_STATUSES = (
    DiagnosisStatus.QUEUED,
    DiagnosisStatus.BISECTING,
    DiagnosisStatus.VERIFYING,
    DiagnosisStatus.EXPLAINING,
)

_ACTIVE_STATUS_SQL = ", ".join(f"'{status.value}'" for status in ACTIVE_DIAGNOSIS_STATUSES)


class Diagnosis(IdMixin, TimestampMixin, Base):
    """One search for the first domino step of a failed run."""

    __tablename__ = "diagnoses"
    __table_args__ = (
        UniqueConstraint("project_id", "id"),
        project_foreign_key("run_id", "runs"),
        project_foreign_key("cause_id", "causes"),
        Index("ix_diagnoses_project_created", "project_id", "created_at", "id"),
        Index(
            "uq_diagnoses_one_active_per_run",
            "project_id",
            "run_id",
            unique=True,
            postgresql_where=text(f"status IN ({_ACTIVE_STATUS_SQL})"),
        ),
    )

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"))
    run_id: Mapped[UUID]
    status: Mapped[DiagnosisStatus] = mapped_column(DIAGNOSIS_STATUS)
    verdict_kind: Mapped[VerdictKind | None] = mapped_column(VERDICT_KIND)
    first_domino_step: Mapped[int | None]
    search_low: Mapped[int | None]
    search_high: Mapped[int | None]
    verify_passes: Mapped[int | None]
    verify_samples: Mapped[int | None]
    fixed_output: Mapped[Message | None] = mapped_column(PydanticJson(Message))
    explanation: Mapped[Explanation | None] = mapped_column(PydanticJson(Explanation))
    cause_id: Mapped[UUID | None]
    check_count: Mapped[int]
    replay_count: Mapped[int]
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(COST_PRECISION, COST_SCALE))
    error_code: Mapped[DiagnosisErrorCode | None] = mapped_column(DIAGNOSIS_ERROR_CODE)
    created_by_id: Mapped[UUID | None]
    finished_at: Mapped[datetime | None] = optional_timestamp()
    runner_id: Mapped[UUID | None]
    heartbeat_at: Mapped[datetime | None] = optional_timestamp()


class Check(IdMixin, TimestampMixin, Base):
    """One replay check inside a diagnosis."""

    __tablename__ = "checks"
    __table_args__ = (
        UniqueConstraint("project_id", "id"),
        UniqueConstraint("project_id", "diagnosis_id", "index"),
        project_foreign_key("diagnosis_id", "diagnoses"),
    )

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"))
    diagnosis_id: Mapped[UUID]
    index: Mapped[int]
    phase: Mapped[CheckPhase] = mapped_column(CHECK_PHASE)
    save_point: Mapped[int]
    samples: Mapped[int]
    passes: Mapped[int]
    result: Mapped[CheckResult] = mapped_column(CHECK_RESULT)
    drifted: Mapped[int] = mapped_column(default=0, server_default="0")
    drift_tool_name: Mapped[str | None] = mapped_column(String(128))
    finished_at: Mapped[datetime | None] = optional_timestamp()


class Cause(IdMixin, TimestampMixin, Base):
    """A root cause shared by one or more diagnosed runs."""

    __tablename__ = "causes"
    __table_args__ = (
        UniqueConstraint("project_id", "id"),
        Index("ix_causes_project_run_count", "project_id", "run_count", "id"),
    )

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(String(256))
    category: Mapped[CauseCategory] = mapped_column(CAUSE_CATEGORY)
    step_name: Mapped[str] = mapped_column(String(128))
    summary: Mapped[str] = mapped_column(Text)
    suggested_fix: Mapped[str] = mapped_column(Text)
    run_count: Mapped[int]
    verified_count: Mapped[int]
    first_seen_at: Mapped[datetime] = timestamp()
    last_seen_at: Mapped[datetime] = timestamp()
