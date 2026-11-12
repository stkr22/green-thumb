"""Care log query helpers shared by the plants routes and the dashboard."""

import uuid
from collections.abc import Iterable
from datetime import datetime

from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from greenthumb.models import CareLog

WATERING = "watering"


async def last_event_per_type(session: AsyncSession, plant_id: uuid.UUID) -> dict[str, datetime]:
    """Return the most recent care event timestamp per event type for one plant."""
    statement = (
        select(CareLog.event_type, func.max(CareLog.logged_at))
        .where(CareLog.plant_id == plant_id)
        .group_by(col(CareLog.event_type))
    )
    rows = (await session.exec(statement)).all()
    return dict(rows)


async def last_watered_map(session: AsyncSession, plant_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, datetime]:
    """Return plant_id -> last watering timestamp for the plant list view."""
    ids = list(plant_ids)
    if not ids:
        return {}
    statement = (
        select(CareLog.plant_id, func.max(CareLog.logged_at))
        .where(col(CareLog.plant_id).in_(ids), CareLog.event_type == WATERING)
        .group_by(col(CareLog.plant_id))
    )
    rows = (await session.exec(statement)).all()
    return dict(rows)
