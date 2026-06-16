"""Plant routes."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlmodel import col, or_, select

from greenthumb.api.v1.deps import get_plant_or_404
from greenthumb.auth import CurrentUser, SessionDep
from greenthumb.models import Location, Plant, PlantPhoto
from greenthumb.models.base import utcnow
from greenthumb.schemas import CoverPhotoUpdate, PlantCreate, PlantDetail, PlantListItem, PlantRead, PlantUpdate
from greenthumb.services import care, floracodex

router = APIRouter(prefix="/plants", tags=["plants"])


async def _validate_location(session: SessionDep, location_id: uuid.UUID | None) -> None:
    """Reject references to locations that don't exist (FK errors are opaque 500s)."""
    if location_id is not None and await session.get(Location, location_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Location does not exist")


@router.get("", response_model=list[PlantListItem])
async def list_plants(
    session: SessionDep,
    _user: CurrentUser,
    location_id: uuid.UUID | None = None,
    tag: str | None = None,
    search: str | None = None,
) -> list[PlantListItem]:
    """List plants, filterable by location, tag, and a name/species search term."""
    statement = select(Plant)
    if location_id is not None:
        statement = statement.where(Plant.location_id == location_id)
    if search:
        pattern = f"%{search}%"
        statement = statement.where(
            or_(
                col(Plant.name).ilike(pattern),
                col(Plant.species_name).ilike(pattern),
                col(Plant.scientific_name).ilike(pattern),
            )
        )
    plants = list((await session.exec(statement.order_by(col(Plant.name)))).all())
    if tag:
        # Tag filtering happens in Python: SQLite has no array-containment
        # operator and collections are homelab-sized.
        plants = [plant for plant in plants if tag in plant.tags]
    watered = await care.last_watered_map(session, (plant.id for plant in plants))
    return [PlantListItem(**plant.model_dump(), last_watered_at=watered.get(plant.id)) for plant in plants]


@router.post("", response_model=PlantRead, status_code=status.HTTP_201_CREATED)
async def create_plant(payload: PlantCreate, session: SessionDep, user: CurrentUser) -> Plant:
    """Create a plant; species thresholds are fetched from FloraCodex when a pid is given."""
    await _validate_location(session, payload.location_id)
    plant = Plant(**payload.model_dump(), created_by=user.id)
    if plant.floracodex_pid:
        plant.floracodex_data = await floracodex.fetch_species_detail(plant.floracodex_pid)
    session.add(plant)
    await session.commit()
    await session.refresh(plant)
    return plant


@router.get("/{plant_id}", response_model=PlantDetail)
async def get_plant(plant_id: uuid.UUID, session: SessionDep, _user: CurrentUser) -> PlantDetail:
    """Plant detail including the last care event per event type."""
    plant = await get_plant_or_404(session, plant_id)
    last_events = await care.last_event_per_type(session, plant_id)
    return PlantDetail(**plant.model_dump(), last_events=last_events)


@router.patch("/{plant_id}", response_model=PlantRead)
async def update_plant(plant_id: uuid.UUID, payload: PlantUpdate, session: SessionDep, _user: CurrentUser) -> Plant:
    """Apply a partial update to a plant."""
    plant = await get_plant_or_404(session, plant_id)
    updates = payload.model_dump(exclude_unset=True)
    if "location_id" in updates:
        await _validate_location(session, updates["location_id"])
    pid_changed = "floracodex_pid" in updates and updates["floracodex_pid"] != plant.floracodex_pid
    for field, value in updates.items():
        setattr(plant, field, value)
    if pid_changed and plant.floracodex_pid and "floracodex_data" not in updates:
        plant.floracodex_data = await floracodex.fetch_species_detail(plant.floracodex_pid)
    plant.updated_at = utcnow()
    session.add(plant)
    await session.commit()
    await session.refresh(plant)
    return plant


@router.delete("/{plant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plant(plant_id: uuid.UUID, session: SessionDep, _user: CurrentUser) -> None:
    """Delete a plant; photos, logs and reminders cascade at the database level."""
    plant = await get_plant_or_404(session, plant_id)
    # Clear the self-referential cover FK before deleting so the row's own
    # cover_photo_id can't block removal; child rows cascade via ON DELETE.
    plant.cover_photo_id = None
    await session.delete(plant)
    await session.commit()


@router.post("/{plant_id}/cover", response_model=PlantRead)
async def set_cover_photo(
    plant_id: uuid.UUID, payload: CoverPhotoUpdate, session: SessionDep, _user: CurrentUser
) -> Plant:
    """Set the cover photo; it must be an existing photo of this plant."""
    plant = await get_plant_or_404(session, plant_id)
    photo = (
        await session.exec(select(PlantPhoto).where(PlantPhoto.id == payload.photo_id, PlantPhoto.plant_id == plant_id))
    ).first()
    if photo is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Photo does not belong to this plant")
    plant.cover_photo_id = photo.id
    plant.updated_at = utcnow()
    session.add(plant)
    await session.commit()
    await session.refresh(plant)
    return plant
