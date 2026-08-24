"""Species helpers: turning species defaults into per-plant reminders."""

import uuid

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from greenthumb.models import Plant, Reminder, ScheduleKind, Species


def _schedule_fields(species: Species, event_type: str) -> dict:
    """Season pace or annual window for one event type, whichever the species defines.

    A window wins if both are set: the two mean different things (slow down
    versus wait for the right months) and combining them would stretch the
    interval on top of deferring it.
    """
    window = species.default_windows.get(event_type)
    if window:
        return {
            "schedule_kind": ScheduleKind.ANNUAL_WINDOW.value,
            "window_start_month": window[0],
            "window_end_month": window[1],
            "season_multipliers": {},
        }
    return {
        "schedule_kind": ScheduleKind.INTERVAL.value,
        "window_start_month": None,
        "window_end_month": None,
        # Copy so editing the species plan later cannot mutate this row's JSON
        # in place; SQLAlchemy would not see such a change anyway.
        "season_multipliers": dict(species.season_plan.get(event_type) or {}),
    }


async def materialize_default_reminders(
    session: AsyncSession, plant: Plant, species: Species, user_id: uuid.UUID
) -> list[Reminder]:
    """Create reminders from the species' default intervals, season plan and windows.

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
        reminder = Reminder(
            plant_id=plant.id,
            event_type=event_type,
            interval_days=interval_days,
            created_by=user_id,
            **_schedule_fields(species, event_type),
        )
        session.add(reminder)
        created.append(reminder)
    return created


async def apply_season_plan_to_plants(session: AsyncSession, species: Species) -> int:
    """Push the species' season pace and windows onto every reminder of its plants.

    Returns the number of rows updated. Both are copied at plant creation, so
    editing a species leaves existing plants on the old schedule. Rather than
    silently re-syncing (which would clobber per-plant tuning the copy exists to
    protect), this is an explicit opt-in the user triggers from the species page
    - the practical way to roll a plan out to a collection that predates it.
    Intervals are left alone. The caller commits.
    """
    plant_ids = select(Plant.id).where(Plant.species_id == species.id)
    reminders = (await session.exec(select(Reminder).where(col(Reminder.plant_id).in_(plant_ids)))).all()
    for reminder in reminders:
        for field, value in _schedule_fields(species, reminder.event_type).items():
            setattr(reminder, field, value)
        session.add(reminder)
    return len(reminders)
