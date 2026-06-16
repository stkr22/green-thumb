"""Request/response schemas for reminders."""

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class ReminderCreate(SQLModel):
    """Payload to create a reminder."""

    event_type: str = Field(min_length=1, max_length=100)
    interval_days: int = Field(gt=0, le=3650)
    enabled: bool = True


class ReminderUpdate(SQLModel):
    """Partial update for a reminder."""

    event_type: str | None = Field(default=None, min_length=1, max_length=100)
    interval_days: int | None = Field(default=None, gt=0, le=3650)
    enabled: bool | None = None


class ReminderRead(SQLModel):
    """A reminder as stored."""

    id: uuid.UUID
    plant_id: uuid.UUID
    event_type: str
    interval_days: int
    enabled: bool
    last_notified_at: datetime | None
    created_by: uuid.UUID
    created_at: datetime
