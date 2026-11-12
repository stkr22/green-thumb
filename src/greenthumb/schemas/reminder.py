"""Request/response schemas for reminders."""

import uuid
from datetime import datetime

from pydantic import field_validator, model_validator
from sqlmodel import Field, SQLModel

from greenthumb.models.reminder import ScheduleKind
from greenthumb.services.seasons import validate_season_multipliers

# season -> multiplier on interval_days; null suspends the event type for that
# season. Empty means the interval applies unchanged all year.
SeasonMultipliersField = dict[str, float | None]


def _check_multipliers(value: SeasonMultipliersField) -> SeasonMultipliersField:
    """Apply the season plan bounds; interval_days is the growing-season pace it scales."""
    validate_season_multipliers(value, "season multipliers")
    return value


def _check_window(kind: str | None, start: int | None, end: int | None) -> None:
    """Reject half-specified windows, which would silently fall back to a plain interval."""
    if kind == ScheduleKind.ANNUAL_WINDOW and (start is None or end is None):
        raise ValueError("annual_window reminders need both window_start_month and window_end_month")
    if kind == ScheduleKind.INTERVAL and (start is not None or end is not None):
        raise ValueError("window months only apply to annual_window reminders")


class ReminderCreate(SQLModel):
    """Payload to create a reminder."""

    event_type: str = Field(min_length=1, max_length=100)
    interval_days: int = Field(gt=0, le=3650)
    season_multipliers: SeasonMultipliersField = Field(default_factory=dict)
    schedule_kind: ScheduleKind = ScheduleKind.INTERVAL
    window_start_month: int | None = Field(default=None, ge=1, le=12)
    window_end_month: int | None = Field(default=None, ge=1, le=12)
    enabled: bool = True

    @field_validator("season_multipliers")
    @classmethod
    def _validate_multipliers(cls, value: SeasonMultipliersField) -> SeasonMultipliersField:
        return _check_multipliers(value)

    @model_validator(mode="after")
    def _validate_window(self) -> ReminderCreate:
        _check_window(self.schedule_kind, self.window_start_month, self.window_end_month)
        return self


class ReminderUpdate(SQLModel):
    """Partial update for a reminder."""

    # NOT NULL columns are typed non-optional with a None default: omitting the
    # field leaves it unchanged, while an explicit null is a 422 instead of an
    # IntegrityError. Nullable columns keep `| None` so null clears them.
    event_type: str = Field(default=None, min_length=1, max_length=100)
    interval_days: int = Field(default=None, gt=0, le=3650)
    season_multipliers: SeasonMultipliersField = Field(default=None)
    schedule_kind: ScheduleKind = Field(default=None)
    window_start_month: int | None = Field(default=None, ge=1, le=12)
    window_end_month: int | None = Field(default=None, ge=1, le=12)
    enabled: bool = Field(default=None)

    @field_validator("season_multipliers")
    @classmethod
    def _validate_multipliers(cls, value: SeasonMultipliersField) -> SeasonMultipliersField:
        return _check_multipliers(value)

    @model_validator(mode="after")
    def _validate_window(self) -> ReminderUpdate:
        # Only checkable when the kind is part of the same patch; switching kind
        # without months (or the reverse) is rejected here rather than silently
        # producing a window reminder with no window.
        if "schedule_kind" in self.model_fields_set:
            _check_window(self.schedule_kind, self.window_start_month, self.window_end_month)
        return self


class ReminderSnooze(SQLModel):
    """Payload to snooze a reminder; omitting days defers by the reminder's own interval."""

    days: int | None = Field(default=None, gt=0, le=3650)


class ReminderRead(SQLModel):
    """A reminder as stored."""

    id: uuid.UUID
    plant_id: uuid.UUID
    event_type: str
    interval_days: int
    season_multipliers: SeasonMultipliersField
    schedule_kind: str
    window_start_month: int | None
    window_end_month: int | None
    enabled: bool
    last_notified_at: datetime | None
    snoozed_until: datetime | None
    created_by: uuid.UUID
    created_at: datetime


class ReminderStatusRead(ReminderRead):
    """A reminder plus its computed schedule, for the plant detail page.

    due_at is None when no matching care event exists yet — the reminder is
    due immediately, matching the evaluator's overdue rule. While paused it
    instead reports when the event type resumes.
    """

    due_at: datetime | None = None
    season: str = "spring"
    paused: bool = False
    # interval_days at the current season's pace; None while paused.
    effective_interval_days: int | None = None
