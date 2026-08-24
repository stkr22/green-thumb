"""Reminder evaluation: compute due state and send notifications (ntfy + Web Push).

The same status computation backs the dashboard endpoint and the daily
background loop, so both always agree on what counts as overdue.
"""

import logging
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from greenthumb.config import get_settings
from greenthumb.models import CareLog, Plant, PushSubscription, Reminder, ScheduleKind, User
from greenthumb.models.base import ensure_utc, utcnow
from greenthumb.schemas import ReminderStatus
from greenthumb.services import ntfy, seasons, webpush
from greenthumb.services.seasons import Hemisphere, SeasonMultipliers

logger = logging.getLogger(__name__)

# Friendly imperative verbs for the notification title; custom event types fall
# back to a generic phrasing.
_EVENT_VERBS = {"watering": "water", "fertilising": "fertilise", "repotting": "repot"}


@dataclass(frozen=True)
class Schedule:
    """The computed state of one reminder at a point in time."""

    due_at: datetime | None
    overdue: bool
    # True while the current season suspends this event type. Paused reminders
    # never count as overdue, so a dormant plant is not nagged about feeding.
    paused: bool
    # The interval at the current season's pace, for display. None while paused.
    effective_interval_days: int | None
    season: seasons.Season


def window_months(reminder: Reminder) -> tuple[int, int] | None:
    """Return the reminder's allowed months, or None when it is a plain interval reminder."""
    if reminder.schedule_kind != ScheduleKind.ANNUAL_WINDOW:
        return None
    if reminder.window_start_month is None or reminder.window_end_month is None:
        return None
    return reminder.window_start_month, reminder.window_end_month


def compute_schedule(
    reminder: Reminder,
    last_event_at: datetime | None,
    now: datetime | None = None,
    hemisphere: Hemisphere | None = None,
) -> Schedule:
    """Derive due state from the last care event, the reminder's season plan and any snooze.

    ``due_at`` of None means due immediately (nothing logged yet, no snooze, not
    paused), matching the pre-seasons contract. A snooze earlier than the
    regular schedule is a no-op rather than moving the due date forward. While
    paused, due_at reports when the event type resumes so the UI can say so
    instead of showing a stale overdue date.
    """
    now = now or utcnow()
    hemisphere = hemisphere or get_settings().HEMISPHERE
    interval_days = reminder.interval_days
    multipliers: SeasonMultipliers = reminder.season_multipliers
    snoozed_until = ensure_utc(reminder.snoozed_until) if reminder.snoozed_until is not None else None

    season = seasons.season_for(now, hemisphere)

    window = window_months(reminder)
    if window is not None:
        # The interval runs at full speed and only the due date is pushed into
        # the allowed months; suspending it the way a season plan does would
        # stretch a two-year repotting cycle to four. Season multipliers are
        # ignored here - the window already says when the job may happen.
        anchor = last_event_at + timedelta(days=interval_days) if last_event_at else now
        if snoozed_until is not None and snoozed_until > anchor:
            anchor = snoozed_until
        due = seasons.next_window_start(anchor, *window)
        return Schedule(
            due_at=due,
            overdue=due <= now,
            paused=False,
            effective_interval_days=interval_days,
            season=season,
        )

    multiplier = seasons.multiplier_for(multipliers, season)
    paused = multiplier is None
    due = None if last_event_at is None else seasons.due_at(last_event_at, interval_days, multipliers, hemisphere)

    if paused:
        resumes_at = seasons.first_active_day(now, multipliers, hemisphere)
        due = resumes_at if due is None else max(due, resumes_at)
    if snoozed_until is not None and (due is None or snoozed_until > due):
        due = snoozed_until

    return Schedule(
        due_at=due,
        overdue=not paused and (due is None or due <= now),
        paused=paused,
        effective_interval_days=seasons.effective_interval_days(interval_days, multiplier),
        season=season,
    )


async def _reminder_rows(
    session: AsyncSession, *, enabled_only: bool = True, plant_ids: Iterable[uuid.UUID] | None = None
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
    if plant_ids is not None:
        statement = statement.where(col(Reminder.plant_id).in_(list(plant_ids)))
    return list((await session.exec(statement)).all())


def _status_for(
    reminder: Reminder, plant_name: str, last_at: datetime | None, now: datetime, hemisphere: Hemisphere
) -> ReminderStatus:
    """Derive the due state for one reminder.

    ``now`` is passed in rather than read per reminder so every row in one
    evaluation pass is judged against the same instant - otherwise a pass that
    straddles midnight on 1 March could price two reminders in two seasons.
    """
    last_event_at = ensure_utc(last_at) if last_at is not None else None
    snoozed_until = ensure_utc(reminder.snoozed_until) if reminder.snoozed_until is not None else None
    schedule = compute_schedule(reminder, last_event_at, now, hemisphere)
    return ReminderStatus(
        reminder_id=reminder.id,
        plant_id=reminder.plant_id,
        plant_name=plant_name,
        event_type=reminder.event_type,
        interval_days=reminder.interval_days,
        last_event_at=last_event_at,
        due_at=schedule.due_at,
        overdue=schedule.overdue,
        snoozed_until=snoozed_until,
        season=schedule.season,
        paused=schedule.paused,
        effective_interval_days=schedule.effective_interval_days,
        schedule_kind=reminder.schedule_kind,
        window_start_month=reminder.window_start_month,
        window_end_month=reminder.window_end_month,
    )


async def compute_reminder_statuses(session: AsyncSession) -> list[ReminderStatus]:
    """Return due state for all enabled reminders (dashboard/calendar input)."""
    now, hemisphere = utcnow(), get_settings().HEMISPHERE
    return [
        _status_for(reminder, plant_name, last_at, now, hemisphere)
        for reminder, plant_name, last_at in await _reminder_rows(session)
    ]


async def due_event_types(session: AsyncSession, plant_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, list[str]]:
    """Map plant id -> event types of enabled reminders currently overdue (snooze-aware).

    Backs the due chips on plant cards with a single grouped query instead of
    per-plant status lookups.
    """
    ids = list(plant_ids)
    if not ids:
        return {}
    now, hemisphere = utcnow(), get_settings().HEMISPHERE
    due: dict[uuid.UUID, list[str]] = {}
    for reminder, plant_name, last_at in await _reminder_rows(session, plant_ids=ids):
        status = _status_for(reminder, plant_name, last_at, now, hemisphere)
        if status.overdue:
            due.setdefault(status.plant_id, []).append(status.event_type)
    return due


def _digest_line(status: ReminderStatus) -> str:
    """One bullet line describing an overdue reminder in the digest."""
    verb = _EVENT_VERBS.get(status.event_type)
    action = f"{verb.capitalize()} {status.plant_name}" if verb else f"{status.plant_name}: {status.event_type}"
    if status.last_event_at:
        days_ago = (utcnow() - status.last_event_at).days
        return f"- {action} (last {status.event_type} {days_ago} days ago)"
    return f"- {action} (no {status.event_type} recorded yet)"


def _build_digest(statuses: list[ReminderStatus]) -> tuple[str, str]:
    """Title/body for a single notification summarising all overdue reminders."""
    n = len(statuses)
    title = f"🌱 {n} plant care reminder{'s' if n != 1 else ''}"
    return title, "\n".join(_digest_line(s) for s in statuses)


async def evaluate_and_notify(session: AsyncSession) -> int:
    """Send subscribed users one digest of all overdue reminders; returns messages sent.

    Reminders are batched into a single notification so users aren't flooded when
    several plants come due at once. Each reminder is re-included only after
    interval_days / 2 has passed since its last notification, so an ignored
    reminder doesn't reappear in every digest. The digest goes out over both
    channels a user may have: ntfy (opt-in flag) and Web Push (per device).
    """
    now, hemisphere = utcnow(), get_settings().HEMISPHERE
    ntfy_recipients = list((await session.exec(select(User).where(col(User.ntfy_enabled).is_(True)))).all())
    push_subscriptions = list((await session.exec(select(PushSubscription))).all())
    if not ntfy_recipients and not push_subscriptions:
        return 0

    due: list[tuple[Reminder, ReminderStatus]] = []
    for reminder, plant_name, last_at in await _reminder_rows(session):
        status = _status_for(reminder, plant_name, last_at, now, hemisphere)
        if not status.overdue:
            continue
        if reminder.last_notified_at is not None:
            # Back off at the season's pace, not the growing-season one, so a
            # winter reminder does not reappear twice as often as it is due.
            pace = status.effective_interval_days or reminder.interval_days
            renotify_after = ensure_utc(reminder.last_notified_at) + timedelta(days=pace / 2)
            if now < renotify_after:
                continue
        due.append((reminder, status))

    if not due:
        return 0

    title, message = _build_digest([status for _, status in due])
    sent = 0
    for user in ntfy_recipients:
        sent += int(await ntfy.send_notification(title=title, message=message, topic=user.ntfy_topic_override))
    for subscription in push_subscriptions:
        result = await webpush.send_notification(subscription, title=title, message=message)
        if result is webpush.PushResult.GONE:
            # Permission revoked or site data cleared; the endpoint is dead forever.
            await session.delete(subscription)
        sent += int(result is webpush.PushResult.SENT)
    if sent:
        for reminder, _ in due:
            reminder.last_notified_at = now
            session.add(reminder)
    await session.commit()
    if sent:
        logger.info("Sent %d reminder digest(s) covering %d reminder(s)", sent, len(due))
    return sent


def split_due(
    statuses: list[ReminderStatus], *, upcoming_days: int = 7
) -> tuple[list[ReminderStatus], list[ReminderStatus]]:
    """Split computed statuses into overdue and due-within-N-days (dashboard shape)."""
    horizon = utcnow() + timedelta(days=upcoming_days)
    overdue = [s for s in statuses if s.overdue]
    upcoming = [s for s in statuses if not s.overdue and s.due_at is not None and s.due_at <= horizon]
    overdue.sort(key=lambda s: s.due_at or utcnow() - timedelta(days=36500))
    upcoming.sort(key=lambda s: s.due_at or horizon)
    return overdue, upcoming


async def overdue_and_upcoming(
    session: AsyncSession, *, upcoming_days: int = 7
) -> tuple[list[ReminderStatus], list[ReminderStatus]]:
    """Compute every enabled reminder's status and split it for the dashboard."""
    return split_due(await compute_reminder_statuses(session), upcoming_days=upcoming_days)


__all__ = [
    "Schedule",
    "compute_reminder_statuses",
    "compute_schedule",
    "due_event_types",
    "evaluate_and_notify",
    "overdue_and_upcoming",
    "split_due",
    "window_months",
]
