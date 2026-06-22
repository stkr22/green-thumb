"""Request/response schemas for plants."""

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class PlantCreate(SQLModel):
    """Payload to create a plant."""

    name: str = Field(min_length=1, max_length=200)
    species_name: str | None = None
    scientific_name: str | None = None
    location_id: uuid.UUID | None = None
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)


class PlantUpdate(SQLModel):
    """Partial update for a plant; only provided fields are changed."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    species_name: str | None = None
    scientific_name: str | None = None
    location_id: uuid.UUID | None = None
    notes: str | None = None
    tags: list[str] | None = None


class PlantRead(SQLModel):
    """Full plant representation."""

    id: uuid.UUID
    name: str
    species_name: str | None
    scientific_name: str | None
    location_id: uuid.UUID | None
    notes: str | None
    tags: list[str]
    cover_photo_id: uuid.UUID | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class PlantListItem(PlantRead):
    """Plant card data: includes the last watering for the 'X days ago' indicator."""

    last_watered_at: datetime | None = None


class PlantDetail(PlantRead):
    """Plant detail: last care event per event type (e.g. watering/fertilising/repotting)."""

    last_events: dict[str, datetime] = Field(default_factory=dict)


class CoverPhotoUpdate(SQLModel):
    """Payload for POST /plants/{id}/cover."""

    photo_id: uuid.UUID
