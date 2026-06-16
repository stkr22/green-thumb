"""Reminder table model."""

import uuid
from datetime import datetime

from sqlalchemy import Column
from sqlmodel import Field, SQLModel

from greenthumb.models.base import utc_datetime_type, utcnow


class Reminder(SQLModel, table=True):
    """A recurring care reminder: notify when no matching care log exists within the interval."""

    __tablename__ = "reminders"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    plant_id: uuid.UUID = Field(foreign_key="plants.id", ondelete="CASCADE", index=True)
    event_type: str
    interval_days: int = Field(gt=0)
    enabled: bool = Field(default=True)
    # Dedup marker: re-notify only after interval_days / 2 has passed since the
    # last notification, so an ignored reminder doesn't spam every hour.
    last_notified_at: datetime | None = Field(default=None, sa_column=Column(utc_datetime_type(), nullable=True))
    created_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(utc_datetime_type(), nullable=False))
