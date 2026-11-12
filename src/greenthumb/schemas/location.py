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

    # NOT NULL columns are typed non-optional with a None default: omitting the
    # field leaves it unchanged, while an explicit null is a 422 instead of an
    # IntegrityError. Nullable columns keep `| None` so null clears them.
    name: str = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class LocationRead(SQLModel):
    """A location plus its plant count (the list page shows counts)."""

    id: uuid.UUID
    name: str
    description: str | None
    created_by: uuid.UUID
    created_at: datetime
    plant_count: int = 0
