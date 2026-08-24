"""Reminder table model."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from greenthumb.models.base import utc_datetime_type, utcnow


class ScheduleKind(StrEnum):
    """How a reminder's due date is derived."""

    # Due one interval after the last care event, scaled by season_multipliers.
    INTERVAL = "interval"
    # Due one interval after the last care event, then deferred into the months
    # between window_start_month and window_end_month. For jobs that belong in
    # a fixed part of the year (repot in spring, prune in late winter, move
    # plants indoors before the frost) rather than ones that merely slow down.
    ANNUAL_WINDOW = "annual_window"


class Reminder(SQLModel, table=True):
    """A recurring care reminder: notify when no matching care log exists within the interval."""

    __tablename__ = "reminders"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    plant_id: uuid.UUID = Field(foreign_key="plants.id", ondelete="CASCADE", index=True)
    event_type: str
    interval_days: int = Field(gt=0)
    # season -> multiplier on interval_days, null to suspend this event type for
    # the season. Copied from the species' season_plan at creation, like
    # interval_days itself, so per-plant tuning never leaks to siblings. Empty
    # means no seasonal change, which is how every pre-seasons reminder reads.
    season_multipliers: dict[str, float | None] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    # Stored as a plain string (like event_type) rather than a SQL enum: SQLite
    # cannot ALTER TABLE ADD COLUMN with the CHECK constraint sa.Enum emits.
    schedule_kind: str = Field(default=ScheduleKind.INTERVAL.value)
    # Inclusive month bounds for ANNUAL_WINDOW, and may wrap the year
    # (11 -> 2 is November to February). Both null for INTERVAL.
    window_start_month: int | None = Field(default=None, ge=1, le=12)
    window_end_month: int | None = Field(default=None, ge=1, le=12)
    enabled: bool = Field(default=True)
    # Dedup marker: re-notify only after interval_days / 2 has passed since the
    # last notification, so an ignored reminder doesn't spam every hour.
    last_notified_at: datetime | None = Field(default=None, sa_column=Column(utc_datetime_type(), nullable=True))
    # User-initiated deferral ("due but not needed, e.g. soil still wet"). While
    # set, the effective due date is max(last log + interval, snoozed_until), so
    # the reminder neither shows as overdue nor notifies. Cleared when a care
    # log of this event_type is created, since the snooze must not outlive an
    # actual care event.
    snoozed_until: datetime | None = Field(default=None, sa_column=Column(utc_datetime_type(), nullable=True))
    created_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(utc_datetime_type(), nullable=False))
