"""Response schemas for the dashboard summary endpoint."""

import uuid
from datetime import datetime

from sqlmodel import SQLModel


class ReminderStatus(SQLModel):
    """A reminder enriched with its computed due state for dashboard/calendar views."""

    reminder_id: uuid.UUID
    plant_id: uuid.UUID
    plant_name: str
    event_type: str
    interval_days: int
    last_event_at: datetime | None
    due_at: datetime | None
    # due_at is None when the plant has no matching care log yet - the reminder
    # is treated as immediately overdue in that case.
    overdue: bool
    # While set and in the future, due_at is at least this value, so the UI can
    # label the deferral instead of showing the reminder as overdue.
    snoozed_until: datetime | None = None
    # Current season, and the interval at that season's pace - the UI labels
    # intervals with it ("every 14 days · winter pace") so a schedule that
    # changed by itself is explained rather than surprising.
    season: str = "spring"
    # True while the season plan suspends this event type; due_at then reports
    # when it resumes and the reminder never counts as overdue.
    paused: bool = False
    effective_interval_days: int | None = None
    # "interval" or "annual_window". Window reminders keep their full interval
    # and land in the months below, so the UI labels them differently.
    schedule_kind: str = "interval"
    window_start_month: int | None = None
    window_end_month: int | None = None


class RecentCare(SQLModel):
    """A recent care event for the dashboard's 'recently watered' list."""

    plant_id: uuid.UUID
    plant_name: str
    event_type: str
    logged_at: datetime


class DashboardSummary(SQLModel):
    """Aggregate view backing the dashboard page."""

    overdue: list[ReminderStatus]
    upcoming: list[ReminderStatus]
    recently_watered: list[RecentCare]
    total_plants: int
    total_locations: int
    # Season context for the dashboard banner. The counts cover enabled
    # reminders only, and are zero for an installation that has never set a
    # season plan - which is how the banner knows to stay hidden.
    season: str
    seasonal_adjusted: int
    seasonal_paused: int
