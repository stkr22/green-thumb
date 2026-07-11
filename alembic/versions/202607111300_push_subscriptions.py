"""Add the push_subscriptions table for Web Push (VAPID) notifications.

Revision ID: 0004_push_subscriptions
Revises: 0003_species
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from greenthumb.models.base import utc_datetime_type

revision: str = "0004_push_subscriptions"
down_revision: str | None = "0003_species"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create push_subscriptions."""
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("endpoint", sa.String(), nullable=False),
        sa.Column("p256dh", sa.String(), nullable=False),
        sa.Column("auth", sa.String(), nullable=False),
        sa.Column("created_at", utc_datetime_type(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"])
    op.create_index("ix_push_subscriptions_endpoint", "push_subscriptions", ["endpoint"], unique=True)


def downgrade() -> None:
    """Drop push_subscriptions."""
    op.drop_index("ix_push_subscriptions_endpoint", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_user_id", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
