"""Drop the FloraCodex columns from plants.

The FloraCodex integration was removed; species information is now supplied
directly through the plant API (e.g. populated by an external LLM) using the
free-text species_name/scientific_name fields. batch_alter_table is required
because SQLite cannot DROP COLUMN in place.

Revision ID: 0002_drop_floracodex
Revises: 0001_initial
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_drop_floracodex"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop the floracodex_pid and floracodex_data columns."""
    with op.batch_alter_table("plants") as batch_op:
        batch_op.drop_column("floracodex_data")
        batch_op.drop_column("floracodex_pid")


def downgrade() -> None:
    """Re-add the columns (nullable, no data restored)."""
    with op.batch_alter_table("plants") as batch_op:
        batch_op.add_column(sa.Column("floracodex_pid", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("floracodex_data", sa.JSON(), nullable=True))
