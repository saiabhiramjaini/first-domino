"""Why a run failed, and who flagged a passed run as failed."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for column in (
        sa.Column("failure_reason", sa.String(length=2000), nullable=True),
        sa.Column("flagged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("flagged_by_id", sa.Uuid(), nullable=True),
    ):
        op.add_column("runs", column, if_not_exists=True)


def downgrade() -> None:
    op.drop_column("runs", "flagged_by_id")
    op.drop_column("runs", "flagged_at")
    op.drop_column("runs", "failure_reason")
