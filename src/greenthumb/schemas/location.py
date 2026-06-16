"""Request/response schemas for locations."""

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class LocationCreate(SQLModel):
    """Payload to create a location."""

    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class LocationUpdate(SQLModel):
    """Partial update for a location."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class LocationRead(SQLModel):
    """A location plus its plant count (the list page shows counts)."""

    id: uuid.UUID
    name: str
    description: str | None
    created_by: uuid.UUID
    created_at: datetime
    plant_count: int = 0
