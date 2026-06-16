"""Dashboard summary route."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlmodel import col, func, select

from greenthumb.auth import CurrentUser, SessionDep
from greenthumb.models import CareLog, Location, Plant
from greenthumb.models.base import ensure_utc
from greenthumb.schemas import DashboardSummary, RecentCare
from greenthumb.services import care
from greenthumb.services.reminder_evaluator import overdue_and_upcoming

router = APIRouter(tags=["dashboard"])

_RECENT_LIMIT = 5


async def _recently_watered(session: SessionDep) -> list[RecentCare]:
    """Latest watering per plant, most recent first."""
    last_at = func.max(CareLog.logged_at).label("last_at")
    statement = (
        select(CareLog.plant_id, Plant.name, last_at)
        .join(Plant, col(CareLog.plant_id) == col(Plant.id))
        .where(CareLog.event_type == care.WATERING)
        .group_by(col(CareLog.plant_id), col(Plant.name))
        .order_by(last_at.desc())
        .limit(_RECENT_LIMIT)
    )
    rows = (await session.exec(statement)).all()
    return [
        RecentCare(plant_id=plant_id, plant_name=name, event_type=care.WATERING, logged_at=ensure_utc(logged_at))
        for plant_id, name, logged_at in rows
    ]


@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard(
    session: SessionDep,
    _user: CurrentUser,
    upcoming_days: Annotated[int, Query(ge=1, le=366)] = 7,
) -> DashboardSummary:
    """Aggregate dashboard data; upcoming_days is raised by the calendar view."""
    overdue, upcoming = await overdue_and_upcoming(session, upcoming_days=upcoming_days)
    total_plants = (await session.exec(select(func.count()).select_from(Plant))).one()
    total_locations = (await session.exec(select(func.count()).select_from(Location))).one()
    return DashboardSummary(
        overdue=overdue,
        upcoming=upcoming,
        recently_watered=await _recently_watered(session),
        total_plants=total_plants,
        total_locations=total_locations,
    )
