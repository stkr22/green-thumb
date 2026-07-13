"""Add reminders.snoozed_until for user-initiated deferral of due care actions.

Revision ID: 0005_reminder_snooze
Revises: 0004_push_subscriptions
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from greenthumb.models.base import utc_datetime_type

revision: str = "0005_reminder_snooze"
down_revision: str | None = "0004_push_subscriptions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add reminders.snoozed_until."""
    op.add_column("reminders", sa.Column("snoozed_until", utc_datetime_type(), nullable=True))


def downgrade() -> None:
    """Drop reminders.snoozed_until."""
    op.drop_column("reminders", "snoozed_until")
