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
