"""Plant table model."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, ForeignKey, Uuid
from sqlmodel import Field, SQLModel

from greenthumb.models.base import utc_datetime_type, utcnow


class Plant(SQLModel, table=True):
    """A tracked plant. Species fields are free text, set directly via the API."""

    __tablename__ = "plants"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True)
    species_name: str | None = Field(default=None)
    scientific_name: str | None = Field(default=None)
    location_id: uuid.UUID | None = Field(default=None, foreign_key="locations.id", ondelete="SET NULL")
    notes: str | None = Field(default=None)
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    # Circular FK with plant_photos.plant_id, hence use_alter so DDL is emitted
    # as a separate ALTER TABLE after both tables exist.
    cover_photo_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            Uuid(),
            ForeignKey("plant_photos.id", ondelete="SET NULL", use_alter=True, name="fk_plants_cover_photo_id"),
            nullable=True,
        ),
    )
    created_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(utc_datetime_type(), nullable=False))
    updated_at: datetime = Field(default_factory=utcnow, sa_column=Column(utc_datetime_type(), nullable=False))
