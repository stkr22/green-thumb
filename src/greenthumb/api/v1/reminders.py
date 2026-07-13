"""Reminder routes."""

import uuid
from datetime import timedelta

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from greenthumb.api.v1.deps import get_plant_or_404
from greenthumb.auth import CurrentUser, SessionDep
from greenthumb.models import Reminder
from greenthumb.models.base import ensure_utc, utcnow
from greenthumb.schemas import ReminderCreate, ReminderRead, ReminderSnooze, ReminderStatusRead, ReminderUpdate
from greenthumb.services import care
from greenthumb.services.reminder_evaluator import effective_due_at

router = APIRouter(tags=["reminders"])


@router.get("/plants/{plant_id}/reminders", response_model=list[ReminderStatusRead])
async def list_reminders(plant_id: uuid.UUID, session: SessionDep, _user: CurrentUser) -> list[ReminderStatusRead]:
    """List reminders for a plant with their computed next-due timestamps."""
    await get_plant_or_404(session, plant_id)
    reminders = (await session.exec(select(Reminder).where(Reminder.plant_id == plant_id))).all()
    last_events = await care.last_event_per_type(session, plant_id)
    result = []
    for reminder in reminders:
        last = last_events.get(reminder.event_type)
        snoozed = ensure_utc(reminder.snoozed_until) if reminder.snoozed_until is not None else None
        due_at = effective_due_at(last, reminder.interval_days, snoozed)
        result.append(ReminderStatusRead(**reminder.model_dump(), due_at=due_at))
    return result


@router.post("/plants/{plant_id}/reminders", response_model=ReminderRead, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    plant_id: uuid.UUID, payload: ReminderCreate, session: SessionDep, user: CurrentUser
) -> Reminder:
    """Create a reminder for a plant."""
    await get_plant_or_404(session, plant_id)
    reminder = Reminder(plant_id=plant_id, **payload.model_dump(), created_by=user.id)
    session.add(reminder)
    await session.commit()
    await session.refresh(reminder)
    return reminder


@router.patch("/reminders/{reminder_id}", response_model=ReminderRead)
async def update_reminder(
    reminder_id: uuid.UUID, payload: ReminderUpdate, session: SessionDep, _user: CurrentUser
) -> Reminder:
    """Update a reminder's interval, event type, or enabled flag."""
    reminder = await session.get(Reminder, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(reminder, field, value)
    session.add(reminder)
    await session.commit()
    await session.refresh(reminder)
    return reminder


@router.delete("/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(reminder_id: uuid.UUID, session: SessionDep, _user: CurrentUser) -> None:
    """Delete a reminder."""
    reminder = await session.get(Reminder, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    await session.delete(reminder)
    await session.commit()


@router.post("/reminders/{reminder_id}/snooze", response_model=ReminderRead)
async def snooze_reminder(
    reminder_id: uuid.UUID, payload: ReminderSnooze, session: SessionDep, _user: CurrentUser
) -> Reminder:
    """Defer a reminder ("due but not needed"); defaults to one full interval from now."""
    reminder = await session.get(Reminder, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    reminder.snoozed_until = utcnow() + timedelta(days=payload.days or reminder.interval_days)
    session.add(reminder)
    await session.commit()
    await session.refresh(reminder)
    return reminder


@router.delete("/reminders/{reminder_id}/snooze", response_model=ReminderRead)
async def unsnooze_reminder(reminder_id: uuid.UUID, session: SessionDep, _user: CurrentUser) -> Reminder:
    """Cancel an active snooze, restoring the regular schedule."""
    reminder = await session.get(Reminder, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    reminder.snoozed_until = None
    session.add(reminder)
    await session.commit()
    await session.refresh(reminder)
    return reminder
