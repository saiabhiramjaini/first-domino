"""Baseline: the schema `create_all` made before Alembic.

A database created by `create_all` before this revision existed is stamped here, not upgraded.
Enum values and constraint names are frozen as they were then; Postgres names the unnamed
constraints the same way `create_all` did.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUMS: dict[str, tuple[str, ...]] = {
    "cause_category": (
        "wrong_date",
        "wrong_entity",
        "wrong_filter",
        "bad_tool_args",
        "hallucination",
        "tool_issue",
        "other",
    ),
    "check_phase": ("precheck", "bisect", "verify", "fallback"),
    "check_result": ("pending", "can_succeed", "doomed"),
    "diagnosis_status": ("queued", "bisecting", "verifying", "explaining", "done", "failed"),
    "verdict_kind": ("step_verified", "step_unverified", "multiple_causes", "task_or_tool_issue"),
    "replay_job_status": ("queued", "leased", "succeeded", "failed", "expired"),
    "replay_outcome": ("passed", "failed", "errored"),
    "run_source": ("recorded", "replay"),
    "run_status": ("running", "passed", "failed", "errored"),
}

# (table, column, parent): FOREIGN KEY (project_id, column) REFERENCES parent (project_id, id).
# Added after every table exists, because runs, replay jobs, checks and diagnoses refer to
# each other.
TENANT_FOREIGN_KEYS: tuple[tuple[str, str, str], ...] = (
    ("checks", "diagnosis_id", "diagnoses"),
    ("diagnoses", "cause_id", "causes"),
    ("diagnoses", "run_id", "runs"),
    ("replay_jobs", "check_id", "checks"),
    ("replay_jobs", "diagnosis_id", "diagnoses"),
    ("replay_jobs", "leased_by_id", "api_keys"),
    ("replay_jobs", "replay_run_id", "runs"),
    ("replay_jobs", "run_id", "runs"),
    ("runs", "check_id", "checks"),
    ("runs", "created_by_id", "api_keys"),
    ("runs", "latest_diagnosis_id", "diagnoses"),
    ("runs", "parent_run_id", "runs"),
    ("runs", "replay_job_id", "replay_jobs"),
    ("steps", "run_id", "runs"),
)

TABLES = (
    "users",
    "projects",
    "api_keys",
    "causes",
    "checks",
    "diagnoses",
    "replay_jobs",
    "runs",
    "steps",
)


def _enum(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(*ENUMS[name], name=name, create_type=False)


def _jsonb() -> postgresql.JSONB:
    return postgresql.JSONB(astext_type=sa.Text())


def _id_and_timestamps() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def _tenant_foreign_key_name(column: str, parent: str) -> str:
    return f"fk_{column}_{parent}_tenant"


def _create_people_and_projects() -> None:
    op.create_table(
        "users",
        sa.Column("google_sub", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        *_id_and_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("google_sub"),
    )
    op.create_table(
        "projects",
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("slack_webhook_url", sa.Text(), nullable=True),
        *_id_and_timestamps(),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id"),
    )
    op.create_table(
        "api_keys",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("prefix", sa.String(length=12), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_id", sa.Uuid(), nullable=True),
        *_id_and_timestamps(),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["revoked_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
        sa.UniqueConstraint("project_id", "id"),
    )
    op.create_index("ix_api_keys_project_created", "api_keys", ["project_id", "created_at"])


def _create_causes_and_checks() -> None:
    op.create_table(
        "causes",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("category", _enum("cause_category"), nullable=False),
        sa.Column("step_name", sa.String(length=128), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("suggested_fix", sa.Text(), nullable=False),
        sa.Column("run_count", sa.Integer(), nullable=False),
        sa.Column("verified_count", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        *_id_and_timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "id"),
    )
    op.create_index("ix_causes_project_run_count", "causes", ["project_id", "run_count", "id"])
    op.create_table(
        "checks",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("diagnosis_id", sa.Uuid(), nullable=False),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column("phase", _enum("check_phase"), nullable=False),
        sa.Column("save_point", sa.Integer(), nullable=False),
        sa.Column("samples", sa.Integer(), nullable=False),
        sa.Column("passes", sa.Integer(), nullable=False),
        sa.Column("result", _enum("check_result"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        *_id_and_timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "diagnosis_id", "index"),
        sa.UniqueConstraint("project_id", "id"),
    )


def _create_diagnoses() -> None:
    op.create_table(
        "diagnoses",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("status", _enum("diagnosis_status"), nullable=False),
        sa.Column("verdict_kind", _enum("verdict_kind"), nullable=True),
        sa.Column("first_domino_step", sa.Integer(), nullable=True),
        sa.Column("search_low", sa.Integer(), nullable=True),
        sa.Column("search_high", sa.Integer(), nullable=True),
        sa.Column("verify_passes", sa.Integer(), nullable=True),
        sa.Column("verify_samples", sa.Integer(), nullable=True),
        sa.Column("fixed_output", _jsonb(), nullable=True),
        sa.Column("explanation", _jsonb(), nullable=True),
        sa.Column("cause_id", sa.Uuid(), nullable=True),
        sa.Column("check_count", sa.Integer(), nullable=False),
        sa.Column("replay_count", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=12, scale=6), nullable=False),
        # DiagnosisErrorCode is a non-native enum with no CHECK constraint: plain text.
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("runner_id", sa.Uuid(), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        *_id_and_timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "id"),
    )
    op.create_index("ix_diagnoses_project_created", "diagnoses", ["project_id", "created_at", "id"])
    op.create_index(
        "uq_diagnoses_one_active_per_run",
        "diagnoses",
        ["project_id", "run_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'bisecting', 'verifying', 'explaining')"),
    )


def _create_replay_jobs() -> None:
    op.create_table(
        "replay_jobs",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("diagnosis_id", sa.Uuid(), nullable=True),
        sa.Column("check_id", sa.Uuid(), nullable=True),
        sa.Column("agent_name", sa.String(length=128), nullable=False),
        sa.Column("task_input", _jsonb(), nullable=False),
        sa.Column("from_step", sa.Integer(), nullable=False),
        sa.Column("messages", _jsonb(), nullable=False),
        sa.Column("replacement_output", _jsonb(), nullable=True),
        sa.Column("model_override", sa.String(length=128), nullable=True),
        sa.Column("status", _enum("replay_job_status"), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("leased_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("leased_by_id", sa.Uuid(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", _enum("replay_outcome"), nullable=True),
        sa.Column("replay_run_id", sa.Uuid(), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        *_id_and_timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "id"),
    )
    op.create_index("ix_replay_jobs_lease_expiry", "replay_jobs", ["status", "lease_expires_at"])
    op.create_index(
        "ix_replay_jobs_queue",
        "replay_jobs",
        ["project_id", "status", "agent_name", "created_at"],
    )


def _create_runs_and_steps() -> None:
    op.create_table(
        "runs",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("agent_name", sa.String(length=128), nullable=False),
        sa.Column("source", _enum("run_source"), nullable=False),
        sa.Column("parent_run_id", sa.Uuid(), nullable=True),
        sa.Column("replay_job_id", sa.Uuid(), nullable=True),
        sa.Column("replay_from_step", sa.Integer(), nullable=True),
        sa.Column("check_id", sa.Uuid(), nullable=True),
        sa.Column("task_input", _jsonb(), nullable=False),
        sa.Column("tool_names", postgresql.ARRAY(sa.String(length=128)), nullable=False),
        sa.Column("status", _enum("run_status"), nullable=False),
        sa.Column("step_count", sa.Integer(), nullable=False),
        sa.Column("final_output", sa.Text(), nullable=True),
        sa.Column("latest_diagnosis_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        *_id_and_timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "id"),
    )
    op.create_index("ix_runs_project_check", "runs", ["project_id", "check_id"])
    op.create_index(
        "ix_runs_project_source_started", "runs", ["project_id", "source", "started_at", "id"]
    )
    op.create_table(
        "steps",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("output", _jsonb(), nullable=False),
        sa.Column("tool_results", _jsonb(), nullable=False),
        sa.Column("messages", _jsonb(), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        *_id_and_timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "run_id", "index"),
    )


def upgrade() -> None:
    bind = op.get_bind()
    for name in ENUMS:
        _enum(name).create(bind)
    _create_people_and_projects()
    _create_causes_and_checks()
    _create_diagnoses()
    _create_replay_jobs()
    _create_runs_and_steps()
    for table, column, parent in TENANT_FOREIGN_KEYS:
        op.create_foreign_key(
            _tenant_foreign_key_name(column, parent),
            table,
            parent,
            ["project_id", column],
            ["project_id", "id"],
        )


def downgrade() -> None:
    for table, column, parent in TENANT_FOREIGN_KEYS:
        op.drop_constraint(_tenant_foreign_key_name(column, parent), table, type_="foreignkey")
    for table in reversed(TABLES):
        op.drop_table(table)
    bind = op.get_bind()
    for name in ENUMS:
        _enum(name).drop(bind)
