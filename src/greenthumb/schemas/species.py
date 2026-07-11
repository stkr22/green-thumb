"""Request/response schemas for species."""

import uuid
from datetime import datetime

from pydantic import field_validator
from sqlmodel import Field, SQLModel

# Same bounds as ReminderCreate, since these entries become reminders.
_EVENT_TYPE_MAX_LENGTH = 100
_INTERVAL_MAX_DAYS = 3650


def _check_intervals(value: dict[str, int]) -> dict[str, int]:
    """Apply the ReminderCreate bounds to each default-interval entry."""
    for event_type, days in value.items():
        if not 1 <= len(event_type) <= _EVENT_TYPE_MAX_LENGTH:
            msg = f"event type must be 1-{_EVENT_TYPE_MAX_LENGTH} characters"
            raise ValueError(msg)
        if not 0 < days <= _INTERVAL_MAX_DAYS:
            msg = f"interval must be between 1 and {_INTERVAL_MAX_DAYS} days"
            raise ValueError(msg)
    return value


class SpeciesCreate(SQLModel):
    """Payload to create a species."""

    name: str = Field(min_length=1, max_length=200)
    scientific_name: str | None = None
    light: str | None = None
    watering_hint: str | None = None
    soil_hint: str | None = None
    deadheading: bool = False
    deadheading_hint: str | None = None
    toxicity: str | None = None
    common_issues: str | None = None
    default_intervals: dict[str, int] = Field(default_factory=dict)

    @field_validator("default_intervals")
    @classmethod
    def _validate_intervals(cls, value: dict[str, int]) -> dict[str, int]:
        return _check_intervals(value)


class SpeciesUpdate(SQLModel):
    """Partial update for a species; only provided fields are changed."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    scientific_name: str | None = None
    light: str | None = None
    watering_hint: str | None = None
    soil_hint: str | None = None
    deadheading: bool | None = None
    deadheading_hint: str | None = None
    toxicity: str | None = None
    common_issues: str | None = None
    default_intervals: dict[str, int] | None = None

    @field_validator("default_intervals")
    @classmethod
    def _validate_intervals(cls, value: dict[str, int] | None) -> dict[str, int] | None:
        return value if value is None else _check_intervals(value)


class SpeciesRead(SQLModel):
    """Full species representation."""

    id: uuid.UUID
    name: str
    scientific_name: str | None
    light: str | None
    watering_hint: str | None
    soil_hint: str | None
    deadheading: bool
    deadheading_hint: str | None
    toxicity: str | None
    common_issues: str | None
    default_intervals: dict[str, int]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class SpeciesListItem(SpeciesRead):
    """Species list entry: includes how many plants reference it."""

    plant_count: int = 0
