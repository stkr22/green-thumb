"""Request/response schemas for species."""

import uuid
from datetime import datetime

from pydantic import field_validator
from sqlmodel import Field, SQLModel

from greenthumb.services.seasons import validate_season_plan

# Same bounds as ReminderCreate, since these entries become reminders.
_EVENT_TYPE_MAX_LENGTH = 100
_INTERVAL_MAX_DAYS = 3650

# event_type -> season -> multiplier on the default interval (null suspends it).
SeasonPlanField = dict[str, dict[str, float | None]]
# event_type -> [start_month, end_month] for care that belongs in a fixed part
# of the year; makes the materialized reminder an annual-window one.
DefaultWindowsField = dict[str, list[int]]


def _check_season_plan(value: SeasonPlanField) -> SeasonPlanField:
    """Apply the season plan bounds before the plan reaches the scheduler."""
    validate_season_plan(value)
    return value


_WINDOW_BOUNDS = 2
_MONTHS_IN_YEAR = 12


def _check_windows(value: DefaultWindowsField) -> DefaultWindowsField:
    """Each entry must be exactly two calendar months; the pair may wrap the year."""
    for event_type, months in value.items():
        if not isinstance(months, list) or len(months) != _WINDOW_BOUNDS:
            raise ValueError(f"Window for '{event_type}' must be [start_month, end_month]")
        for month in months:
            valid = isinstance(month, int) and not isinstance(month, bool) and 1 <= month <= _MONTHS_IN_YEAR
            if not valid:
                raise ValueError(f"Window months for '{event_type}' must be between 1 and {_MONTHS_IN_YEAR}")
    return value


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
    season_plan: SeasonPlanField = Field(default_factory=dict)
    default_windows: DefaultWindowsField = Field(default_factory=dict)

    @field_validator("default_intervals")
    @classmethod
    def _validate_intervals(cls, value: dict[str, int]) -> dict[str, int]:
        return _check_intervals(value)

    @field_validator("season_plan")
    @classmethod
    def _validate_season_plan(cls, value: SeasonPlanField) -> SeasonPlanField:
        return _check_season_plan(value)

    @field_validator("default_windows")
    @classmethod
    def _validate_windows(cls, value: DefaultWindowsField) -> DefaultWindowsField:
        return _check_windows(value)


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
    season_plan: SeasonPlanField | None = None
    default_windows: DefaultWindowsField | None = None

    @field_validator("default_intervals")
    @classmethod
    def _validate_intervals(cls, value: dict[str, int] | None) -> dict[str, int] | None:
        return value if value is None else _check_intervals(value)

    @field_validator("season_plan")
    @classmethod
    def _validate_season_plan(cls, value: SeasonPlanField | None) -> SeasonPlanField | None:
        return value if value is None else _check_season_plan(value)

    @field_validator("default_windows")
    @classmethod
    def _validate_windows(cls, value: DefaultWindowsField | None) -> DefaultWindowsField | None:
        return value if value is None else _check_windows(value)


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
    season_plan: SeasonPlanField
    default_windows: DefaultWindowsField
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class SpeciesListItem(SpeciesRead):
    """Species list entry: includes how many plants reference it."""

    plant_count: int = 0


class SeasonPlanApplied(SQLModel):
    """How many existing reminders a season plan roll-out touched."""

    reminders_updated: int
