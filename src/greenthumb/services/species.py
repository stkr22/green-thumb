"""Species helpers: turning species defaults into per-plant reminders."""

import uuid

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from greenthumb.models import Plant, Reminder, Species


async def materialize_default_reminders(
    session: AsyncSession, plant: Plant, species: Species, user_id: uuid.UUID
) -> list[Reminder]:
    """Create reminders from the species' default intervals.

    Copies rather than links: real cadence varies per plant (pot size, window,
    season), so each plant gets its own tunable rows. Event types that already
    have a reminder are skipped to keep the operation idempotent and to never
    clobber per-plant tuning. The caller commits.
    """
    existing = {
        reminder.event_type
        for reminder in (await session.exec(select(Reminder).where(Reminder.plant_id == plant.id))).all()
    }
    created = []
    for event_type, interval_days in species.default_intervals.items():
        if event_type in existing:
            continue
        reminder = Reminder(plant_id=plant.id, event_type=event_type, interval_days=interval_days, created_by=user_id)
        session.add(reminder)
        created.append(reminder)
    return created
