"""Add season plans so care intervals can vary across the year.

Both columns default to an empty object, which the scheduler reads as "no
seasonal change", so existing species and reminders keep their current
behaviour until someone fills a plan in.

Revision ID: 0006_seasonal_care
Revises: 0005_reminder_snooze
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_seasonal_care"
down_revision: str | None = "0005_reminder_snooze"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add species.season_plan and reminders.season_multipliers."""
    op.add_column("species", sa.Column("season_plan", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column(
        "reminders", sa.Column("season_multipliers", sa.JSON(), nullable=False, server_default=sa.text("'{}'"))
    )


def downgrade() -> None:
    """Drop the season plan columns."""
    op.drop_column("reminders", "season_multipliers")
    op.drop_column("species", "season_plan")
