"""Care log routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import col, select

from greenthumb.api.v1.deps import get_plant_or_404
from greenthumb.auth import CurrentUser, SessionDep
from greenthumb.models import CareLog
from greenthumb.models.base import utcnow
from greenthumb.schemas import CareLogCreate, CareLogRead

router = APIRouter(tags=["care-logs"])


@router.get("/plants/{plant_id}/logs", response_model=list[CareLogRead])
async def list_logs(
    plant_id: uuid.UUID,
    session: SessionDep,
    _user: CurrentUser,
    event_type: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CareLog]:
    """List care logs for a plant, newest first."""
    await get_plant_or_404(session, plant_id)
    statement = select(CareLog).where(CareLog.plant_id == plant_id)
    if event_type:
        statement = statement.where(CareLog.event_type == event_type)
    statement = statement.order_by(col(CareLog.logged_at).desc()).offset(offset).limit(limit)
    return list((await session.exec(statement)).all())


@router.post("/plants/{plant_id}/logs", response_model=CareLogRead, status_code=status.HTTP_201_CREATED)
async def create_log(plant_id: uuid.UUID, payload: CareLogCreate, session: SessionDep, user: CurrentUser) -> CareLog:
    """Record a care event; logged_at defaults to now and may be backdated."""
    await get_plant_or_404(session, plant_id)
    log = CareLog(
        plant_id=plant_id,
        event_type=payload.event_type,
        notes=payload.notes,
        logged_at=payload.logged_at or utcnow(),
        logged_by=user.id,
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log


@router.delete("/logs/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_log(log_id: uuid.UUID, session: SessionDep, _user: CurrentUser) -> None:
    """Delete a care log entry."""
    log = await session.get(CareLog, log_id)
    if log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Care log not found")
    await session.delete(log)
    await session.commit()
