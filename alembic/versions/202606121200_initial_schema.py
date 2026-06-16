"""Initial schema: users, locations, plants, plant_photos, care_logs, reminders.

Column types reuse the SQLModel definitions (models.base) so the migration and
the ORM stay in lockstep across dialects. The plants.cover_photo_id foreign key
is declared inline (not via ALTER TABLE) because SQLite cannot add a constraint
after the fact; SQLite permits a foreign key whose parent table is created later.

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from greenthumb.models.base import json_dict_type, string_array_type, utc_datetime_type

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply the migration."""
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("oidc_sub", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("ntfy_enabled", sa.Boolean(), nullable=False),
        sa.Column("ntfy_topic_override", sa.String(), nullable=True),
        sa.Column("created_at", utc_datetime_type(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_oidc_sub", "users", ["oidc_sub"], unique=True)

    op.create_table(
        "locations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", utc_datetime_type(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "plants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("species_name", sa.String(), nullable=True),
        sa.Column("scientific_name", sa.String(), nullable=True),
        sa.Column("location_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("tags", string_array_type(), nullable=False),
        sa.Column("cover_photo_id", sa.Uuid(), nullable=True),
        sa.Column("floracodex_pid", sa.String(), nullable=True),
        sa.Column("floracodex_data", json_dict_type(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", utc_datetime_type(), nullable=False),
        sa.Column("updated_at", utc_datetime_type(), nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        # Forward reference to plant_photos (created next); allowed by SQLite.
        sa.ForeignKeyConstraint(
            ["cover_photo_id"], ["plant_photos.id"], name="fk_plants_cover_photo_id", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plants_name", "plants", ["name"])

    op.create_table(
        "plant_photos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plant_id", sa.Uuid(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("thumbnail", sa.LargeBinary(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), nullable=False),
        sa.Column("uploaded_at", utc_datetime_type(), nullable=False),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plant_photos_plant_id", "plant_photos", ["plant_id"])

    op.create_table(
        "care_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plant_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("logged_by", sa.Uuid(), nullable=False),
        sa.Column("logged_at", utc_datetime_type(), nullable=False),
        sa.Column("created_at", utc_datetime_type(), nullable=False),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["logged_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_care_logs_plant_id", "care_logs", ["plant_id"])
    op.create_index("ix_care_logs_event_type", "care_logs", ["event_type"])

    op.create_table(
        "reminders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plant_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("interval_days", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("last_notified_at", utc_datetime_type(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", utc_datetime_type(), nullable=False),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reminders_plant_id", "reminders", ["plant_id"])


def downgrade() -> None:
    """Revert the migration."""
    op.drop_table("reminders")
    op.drop_table("care_logs")
    # cover_photo_id FK is inline in plants, so dropping the tables is enough;
    # SQLite has no standalone DROP CONSTRAINT. Drop in FK-dependency order.
    op.drop_table("plant_photos")
    op.drop_table("plants")
    op.drop_table("locations")
    op.drop_table("users")
