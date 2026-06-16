"""Location (room / area) table model."""

import uuid
from datetime import datetime

from sqlalchemy import Column
from sqlmodel import Field, SQLModel

from greenthumb.models.base import utc_datetime_type, utcnow


class Location(SQLModel, table=True):
    """A room or area where plants live."""

    __tablename__ = "locations"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    description: str | None = Field(default=None)
    created_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(utc_datetime_type(), nullable=False))
