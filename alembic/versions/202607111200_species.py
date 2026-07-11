"""Add the species table and plants.species_id, backfilling from free text.

Existing plants are grouped by their free-text species_name; each distinct
name becomes a species row (first non-null scientific_name wins) and the
plants are linked to it. The free-text fields are kept as-is so nothing is
lost for plants without a species. batch_alter_table is required because
SQLite cannot ADD CONSTRAINT in place.

Revision ID: 0003_species
Revises: 0002_drop_floracodex
Create Date: 2026-07-11
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op
from greenthumb.models.base import utc_datetime_type

revision: str = "0003_species"
down_revision: str | None = "0002_drop_floracodex"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Lightweight table stubs so values round-trip through the proper column
# types (sa.Uuid serialization differs from raw strings on SQLite).
_plants = sa.table(
    "plants",
    sa.column("id", sa.Uuid()),
    sa.column("species_name", sa.String()),
    sa.column("scientific_name", sa.String()),
    sa.column("species_id", sa.Uuid()),
    sa.column("created_by", sa.Uuid()),
)
_species = sa.table(
    "species",
    sa.column("id", sa.Uuid()),
    sa.column("name", sa.String()),
    sa.column("scientific_name", sa.String()),
    sa.column("deadheading", sa.Boolean()),
    sa.column("default_intervals", sa.JSON()),
    sa.column("created_by", sa.Uuid()),
    sa.column("created_at", utc_datetime_type()),
    sa.column("updated_at", utc_datetime_type()),
)


def upgrade() -> None:
    """Create species, link plants to it, and backfill from species_name."""
    op.create_table(
        "species",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("scientific_name", sa.String(), nullable=True),
        sa.Column("light", sa.String(), nullable=True),
        sa.Column("watering_hint", sa.String(), nullable=True),
        sa.Column("soil_hint", sa.String(), nullable=True),
        sa.Column("deadheading", sa.Boolean(), nullable=False),
        sa.Column("deadheading_hint", sa.String(), nullable=True),
        sa.Column("toxicity", sa.String(), nullable=True),
        sa.Column("common_issues", sa.String(), nullable=True),
        sa.Column("default_intervals", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", utc_datetime_type(), nullable=False),
        sa.Column("updated_at", utc_datetime_type(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_species_name", "species", ["name"])

    with op.batch_alter_table("plants") as batch_op:
        batch_op.add_column(sa.Column("species_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key("fk_plants_species_id", "species", ["species_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index("ix_plants_species_id", ["species_id"])

    _backfill_species()


def _backfill_species() -> None:
    """Create one species per distinct species_name and link its plants."""
    conn = op.get_bind()
    rows = conn.execute(
        sa.select(_plants.c.id, _plants.c.species_name, _plants.c.scientific_name, _plants.c.created_by).where(
            _plants.c.species_name.is_not(None), _plants.c.species_name != ""
        )
    ).all()

    by_name: dict[str, list] = {}
    for row in rows:
        by_name.setdefault(row.species_name.strip(), []).append(row)

    now = datetime.now(UTC)
    for name, plants in by_name.items():
        if not name:
            continue
        species_id = uuid.uuid4()
        scientific = next((plant.scientific_name for plant in plants if plant.scientific_name), None)
        conn.execute(
            _species.insert().values(
                id=species_id,
                name=name,
                scientific_name=scientific,
                deadheading=False,
                default_intervals={},
                created_by=plants[0].created_by,
                created_at=now,
                updated_at=now,
            )
        )
        conn.execute(
            _plants.update().where(_plants.c.id.in_([plant.id for plant in plants])).values(species_id=species_id)
        )


def downgrade() -> None:
    """Drop plants.species_id and the species table (backfilled rows are lost)."""
    with op.batch_alter_table("plants") as batch_op:
        batch_op.drop_index("ix_plants_species_id")
        batch_op.drop_constraint("fk_plants_species_id", type_="foreignkey")
        batch_op.drop_column("species_id")
    op.drop_index("ix_species_name", table_name="species")
    op.drop_table("species")
