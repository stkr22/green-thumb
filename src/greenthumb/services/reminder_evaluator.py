"""Reminder evaluation: compute due state and send ntfy notifications.

The same status computation backs the dashboard endpoint and the hourly
background loop, so both always agree on what counts as overdue.
"""

import logging
from datetime import datetime, timedelta

from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from greenthumb.models import CareLog, Plant, Reminder, User
from greenthumb.models.base import ensure_utc, utcnow
from greenthumb.schemas import ReminderStatus
from greenthumb.services import ntfy

logger = logging.getLogger(__name__)

# Friendly imperative verbs for the notification title; custom event types fall
# back to a generic phrasing.
_EVENT_VERBS = {"watering": "water", "fertilising": "fertilise", "repotting": "repot"}


async def _reminder_rows(
    session: AsyncSession, *, enabled_only: bool = True
) -> list[tuple[Reminder, str, datetime | None]]:
    """Fetch reminders with plant name and the latest matching care log timestamp."""
    last_log = (
        select(
            col(CareLog.plant_id).label("plant_id"),
            col(CareLog.event_type).label("event_type"),
            func.max(CareLog.logged_at).label("last_at"),
        )
        .group_by(col(CareLog.plant_id), col(CareLog.event_type))
        .subquery()
    )
    statement = (
        select(Reminder, Plant.name, last_log.c.last_at)
        .join(Plant, col(Reminder.plant_id) == col(Plant.id))
        .outerjoin(
            last_log,
            (last_log.c.plant_id == col(Reminder.plant_id)) & (last_log.c.event_type == col(Reminder.event_type)),
        )
    )
    if enabled_only:
        statement = statement.where(col(Reminder.enabled).is_(True))
    return list((await session.exec(statement)).all())


def _status_for(reminder: Reminder, plant_name: str, last_at: datetime | None) -> ReminderStatus:
    """Derive the due state for one reminder."""
    now = utcnow()
    last_event_at = ensure_utc(last_at) if last_at is not None else None
    due_at = last_event_at + timedelta(days=reminder.interval_days) if last_event_at else None
    return ReminderStatus(
        reminder_id=reminder.id,
        plant_id=reminder.plant_id,
        plant_name=plant_name,
        event_type=reminder.event_type,
        interval_days=reminder.interval_days,
        last_event_at=last_event_at,
        due_at=due_at,
        overdue=due_at is None or due_at <= now,
    )


async def compute_reminder_statuses(session: AsyncSession) -> list[ReminderStatus]:
    """Return due state for all enabled reminders (dashboard/calendar input)."""
    return [
        _status_for(reminder, plant_name, last_at) for reminder, plant_name, last_at in await _reminder_rows(session)
    ]


def _build_message(status: ReminderStatus) -> tuple[str, str]:
    """Build the ntfy title/message pair for an overdue reminder."""
    verb = _EVENT_VERBS.get(status.event_type)
    title = f"Time to {verb} your {status.plant_name}" if verb else f"{status.plant_name}: {status.event_type} is due"
    if status.last_event_at:
        days_ago = (utcnow() - status.last_event_at).days
        message = f"Last {status.event_type} {days_ago} days ago. Reminder set for every {status.interval_days} days."
    else:
        message = f"No {status.event_type} recorded yet. Reminder set for every {status.interval_days} days."
    return title, message


async def evaluate_and_notify(session: AsyncSession) -> int:
    """Notify subscribed users about overdue reminders; returns notifications sent.

    Re-notification is throttled to interval_days / 2 since the last successful
    notification so an ignored reminder doesn't fire every hour.
    """
    now = utcnow()
    recipients = list((await session.exec(select(User).where(col(User.ntfy_enabled).is_(True)))).all())
    if not recipients:
        return 0

    sent = 0
    for reminder, plant_name, last_at in await _reminder_rows(session):
        status = _status_for(reminder, plant_name, last_at)
        if not status.overdue:
            continue
        if reminder.last_notified_at is not None:
            renotify_after = ensure_utc(reminder.last_notified_at) + timedelta(days=reminder.interval_days / 2)
            if now < renotify_after:
                continue
        title, message = _build_message(status)
        delivered = False
        for user in recipients:
            delivered = (
                await ntfy.send_notification(title=title, message=message, topic=user.ntfy_topic_override) or delivered
            )
        if delivered:
            reminder.last_notified_at = now
            session.add(reminder)
            sent += 1
    await session.commit()
    if sent:
        logger.info("Sent %d reminder notification(s)", sent)
    return sent


async def overdue_and_upcoming(
    session: AsyncSession, *, upcoming_days: int = 7
) -> tuple[list[ReminderStatus], list[ReminderStatus]]:
    """Split enabled reminders into overdue and due-within-N-days (dashboard shape)."""
    horizon = utcnow() + timedelta(days=upcoming_days)
    statuses = await compute_reminder_statuses(session)
    overdue = [s for s in statuses if s.overdue]
    upcoming = [s for s in statuses if not s.overdue and s.due_at is not None and s.due_at <= horizon]
    overdue.sort(key=lambda s: s.due_at or utcnow() - timedelta(days=36500))
    upcoming.sort(key=lambda s: s.due_at or horizon)
    return overdue, upcoming


__all__ = ["compute_reminder_statuses", "evaluate_and_notify", "overdue_and_upcoming"]
