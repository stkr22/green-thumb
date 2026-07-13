"""Request/response schemas for plants."""

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from greenthumb.schemas.species import SpeciesRead


class PlantCreate(SQLModel):
    """Payload to create a plant.

    Linking a species materializes its default care intervals as reminders.
    """

    name: str = Field(min_length=1, max_length=200)
    species_name: str | None = None
    scientific_name: str | None = None
    species_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)


class PlantUpdate(SQLModel):
    """Partial update for a plant; only provided fields are changed."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    species_name: str | None = None
    scientific_name: str | None = None
    species_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    notes: str | None = None
    tags: list[str] | None = None


class PlantRead(SQLModel):
    """Full plant representation."""

    id: uuid.UUID
    name: str
    species_name: str | None
    scientific_name: str | None
    species_id: uuid.UUID | None
    location_id: uuid.UUID | None
    notes: str | None
    tags: list[str]
    cover_photo_id: uuid.UUID | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class PlantListItem(PlantRead):
    """Plant card data.

    Includes the last watering for the 'X days ago' indicator and the species
    label resolved from the linked species or the free-text fallback.
    """

    last_watered_at: datetime | None = None
    species_display_name: str | None = None
    # Event types of enabled reminders currently overdue (snooze-aware), so
    # cards can flag due care without a per-plant request.
    due_events: list[str] = Field(default_factory=list)


class PlantDetail(PlantRead):
    """Plant detail: last care event per event type, plus the linked species.

    The species is embedded so the detail page can render care guidance
    without a second request.
    """

    last_events: dict[str, datetime] = Field(default_factory=dict)
    species: SpeciesRead | None = None


class CoverPhotoUpdate(SQLModel):
    """Payload for POST /plants/{id}/cover."""

    photo_id: uuid.UUID
