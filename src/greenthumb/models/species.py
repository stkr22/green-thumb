"""Species table model."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from greenthumb.models.base import utc_datetime_type, utcnow


class Species(SQLModel, table=True):
    """Shared care knowledge for one kind of plant.

    Plants reference a species so care guidance isn't retyped per plant.
    default_intervals holds the default care plan (event_type -> days); it is
    materialized into per-plant Reminder rows rather than evaluated live, so
    tuning one plant's schedule never affects its siblings.
    """

    __tablename__ = "species"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True)
    scientific_name: str | None = Field(default=None)
    light: str | None = Field(default=None)
    watering_hint: str | None = Field(default=None)
    soil_hint: str | None = Field(default=None)
    deadheading: bool = Field(default=False)
    deadheading_hint: str | None = Field(default=None)
    toxicity: str | None = Field(default=None)
    common_issues: str | None = Field(default=None)
    default_intervals: dict[str, int] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(utc_datetime_type(), nullable=False))
    updated_at: datetime = Field(default_factory=utcnow, sa_column=Column(utc_datetime_type(), nullable=False))
