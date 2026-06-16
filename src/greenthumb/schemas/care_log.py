"""Request/response schemas for care logs."""

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class CareLogCreate(SQLModel):
    """Payload to log a care event; logged_at may be backdated and defaults to now."""

    event_type: str = Field(min_length=1, max_length=100)
    notes: str | None = None
    logged_at: datetime | None = None


class CareLogRead(SQLModel):
    """A recorded care event."""

    id: uuid.UUID
    plant_id: uuid.UUID
    event_type: str
    notes: str | None
    logged_by: uuid.UUID
    logged_at: datetime
    created_at: datetime
