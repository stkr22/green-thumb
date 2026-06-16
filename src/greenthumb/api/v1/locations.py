"""Location routes."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlmodel import col, func, select, update

from greenthumb.auth import CurrentUser, SessionDep
from greenthumb.models import Location, Plant
from greenthumb.schemas import LocationCreate, LocationRead, LocationUpdate

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("", response_model=list[LocationRead])
async def list_locations(session: SessionDep, _user: CurrentUser) -> list[LocationRead]:
    """List all locations with their plant counts."""
    plant_counts = (
        select(col(Plant.location_id).label("location_id"), func.count().label("plant_count"))
        .group_by(col(Plant.location_id))
        .subquery()
    )
    statement = select(Location, func.coalesce(plant_counts.c.plant_count, 0)).outerjoin(
        plant_counts, plant_counts.c.location_id == col(Location.id)
    )
    rows = (await session.exec(statement)).all()
    return [LocationRead(**location.model_dump(), plant_count=count) for location, count in rows]


@router.post("", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
async def create_location(payload: LocationCreate, session: SessionDep, user: CurrentUser) -> LocationRead:
    """Create a location."""
    location = Location(**payload.model_dump(), created_by=user.id)
    session.add(location)
    await session.commit()
    await session.refresh(location)
    return LocationRead(**location.model_dump(), plant_count=0)


@router.patch("/{location_id}", response_model=LocationRead)
async def update_location(
    location_id: uuid.UUID, payload: LocationUpdate, session: SessionDep, _user: CurrentUser
) -> LocationRead:
    """Update a location's name/description."""
    location = await session.get(Location, location_id)
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(location, field, value)
    session.add(location)
    await session.commit()
    await session.refresh(location)
    count = (await session.exec(select(func.count()).select_from(Plant).where(Plant.location_id == location.id))).one()
    return LocationRead(**location.model_dump(), plant_count=count)


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(location_id: uuid.UUID, session: SessionDep, _user: CurrentUser) -> None:
    """Delete a location; plants that lived there keep existing without a location."""
    location = await session.get(Location, location_id)
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    # Explicit detach instead of relying on ON DELETE SET NULL so behaviour is
    # identical on the SQLite test backend.
    await session.exec(update(Plant).where(col(Plant.location_id) == location_id).values(location_id=None))  # type: ignore[call-overload]
    await session.delete(location)
    await session.commit()
