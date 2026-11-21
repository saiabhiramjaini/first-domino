"""Replay drift on checks and replay jobs, and the calibrate check phase."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # IF NOT EXISTS: a local database that `create_all` built from these tables before Alembic
    # already has the columns, yet is stamped at the baseline.
    for table, column in (
        ("checks", sa.Column("drifted", sa.Integer(), server_default="0", nullable=False)),
        ("checks", sa.Column("drift_tool_name", sa.String(length=128), nullable=True)),
        ("replay_jobs", sa.Column("drift_step", sa.Integer(), nullable=True)),
        ("replay_jobs", sa.Column("drift_tool_name", sa.String(length=128), nullable=True)),
    ):
        op.add_column(table, column, if_not_exists=True)
    # Before 'precheck', so the type lists its values in the order `CheckPhase` declares them.
    # Postgres cannot use a new enum value in the transaction that adds it.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE check_phase ADD VALUE IF NOT EXISTS 'calibrate' BEFORE 'precheck'")


def downgrade() -> None:
    # Postgres cannot drop an enum value, so 'calibrate' stays in check_phase.
    op.drop_column("replay_jobs", "drift_tool_name")
    op.drop_column("replay_jobs", "drift_step")
    op.drop_column("checks", "drift_tool_name")
    op.drop_column("checks", "drifted")
