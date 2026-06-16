"""Care log table model."""

import uuid
from datetime import datetime

from sqlalchemy import Column
from sqlmodel import Field, SQLModel

from greenthumb.models.base import utc_datetime_type, utcnow


class CareLog(SQLModel, table=True):
    """A care event (watering, fertilising, repotting, or a custom type)."""

    __tablename__ = "care_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    plant_id: uuid.UUID = Field(foreign_key="plants.id", ondelete="CASCADE", index=True)
    # Free-form on purpose: well-known values are "watering" / "fertilising" /
    # "repotting", but users may log custom event types.
    event_type: str = Field(index=True)
    notes: str | None = Field(default=None)
    logged_by: uuid.UUID = Field(foreign_key="users.id")
    # User-supplied event time (backdating is allowed); created_at is the insert time.
    logged_at: datetime = Field(default_factory=utcnow, sa_column=Column(utc_datetime_type(), nullable=False))
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(utc_datetime_type(), nullable=False))
