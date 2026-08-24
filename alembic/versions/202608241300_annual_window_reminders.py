"""Add annual-window reminders for care that belongs in a fixed part of the year.

Season multipliers slow a schedule down; a window instead lets it run at full
speed and defers the due date into the allowed months, which is what repotting,
pruning and overwintering actually need. Existing reminders default to
'interval' with no window, so nothing changes until a window is set.

Revision ID: 0007_annual_window
Revises: 0006_seasonal_care
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_annual_window"
down_revision: str | None = "0006_seasonal_care"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the reminder schedule kind, its month bounds, and species.default_windows."""
    op.add_column(
        "reminders",
        sa.Column("schedule_kind", sa.String(), nullable=False, server_default=sa.text("'interval'")),
    )
    op.add_column("reminders", sa.Column("window_start_month", sa.Integer(), nullable=True))
    op.add_column("reminders", sa.Column("window_end_month", sa.Integer(), nullable=True))
    op.add_column("species", sa.Column("default_windows", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))


def downgrade() -> None:
    """Drop the annual-window columns."""
    op.drop_column("species", "default_windows")
    op.drop_column("reminders", "window_end_month")
    op.drop_column("reminders", "window_start_month")
    op.drop_column("reminders", "schedule_kind")
