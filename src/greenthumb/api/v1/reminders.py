"""Reminder routes."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from greenthumb.api.v1.deps import get_plant_or_404
from greenthumb.auth import CurrentUser, SessionDep
from greenthumb.models import Reminder
from greenthumb.schemas import ReminderCreate, ReminderRead, ReminderUpdate

router = APIRouter(tags=["reminders"])


@router.get("/plants/{plant_id}/reminders", response_model=list[ReminderRead])
async def list_reminders(plant_id: uuid.UUID, session: SessionDep, _user: CurrentUser) -> list[Reminder]:
    """List reminders configured for a plant."""
    await get_plant_or_404(session, plant_id)
    return list((await session.exec(select(Reminder).where(Reminder.plant_id == plant_id))).all())


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
