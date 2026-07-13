"""Plant routes."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlmodel import col, or_, select

from greenthumb.api.v1.deps import get_plant_or_404
from greenthumb.auth import CurrentUser, SessionDep
from greenthumb.models import Location, Plant, PlantPhoto, Species
from greenthumb.models.base import utcnow
from greenthumb.schemas import (
    CoverPhotoUpdate,
    PlantCreate,
    PlantDetail,
    PlantListItem,
    PlantRead,
    PlantUpdate,
    ReminderRead,
    SpeciesRead,
)
from greenthumb.services import care, reminder_evaluator
from greenthumb.services.species import materialize_default_reminders

router = APIRouter(prefix="/plants", tags=["plants"])


async def _validate_location(session: SessionDep, location_id: uuid.UUID | None) -> None:
    """Reject references to locations that don't exist (FK errors are opaque 500s)."""
    if location_id is not None and await session.get(Location, location_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Location does not exist")


async def _validate_species(session: SessionDep, species_id: uuid.UUID | None) -> Species | None:
    """Reject references to species that don't exist (FK errors are opaque 500s)."""
    if species_id is None:
        return None
    species = await session.get(Species, species_id)
    if species is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Species does not exist")
    return species


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
        # Outer join so the term also matches the linked species' names, not
        # just the legacy free-text fields on the plant itself.
        statement = statement.outerjoin(Species, col(Plant.species_id) == col(Species.id)).where(
            or_(
                col(Plant.name).ilike(pattern),
                col(Plant.species_name).ilike(pattern),
                col(Plant.scientific_name).ilike(pattern),
                col(Species.name).ilike(pattern),
                col(Species.scientific_name).ilike(pattern),
            )
        )
    plants = list((await session.exec(statement.order_by(col(Plant.name)))).all())
    if tag:
        # Tag filtering happens in Python: SQLite has no array-containment
        # operator and collections are homelab-sized.
        plants = [plant for plant in plants if tag in plant.tags]
    watered = await care.last_watered_map(session, (plant.id for plant in plants))
    due_map = await reminder_evaluator.due_event_types(session, (plant.id for plant in plants))
    species_ids = {plant.species_id for plant in plants if plant.species_id}
    species_names: dict[uuid.UUID, str] = {}
    if species_ids:
        rows = (await session.exec(select(Species.id, Species.name).where(col(Species.id).in_(species_ids)))).all()
        species_names = dict(rows)
    return [
        PlantListItem(
            **plant.model_dump(),
            last_watered_at=watered.get(plant.id),
            species_display_name=(species_names.get(plant.species_id) if plant.species_id else None)
            or plant.species_name,
            due_events=due_map.get(plant.id, []),
        )
        for plant in plants
    ]


@router.post("", response_model=PlantRead, status_code=status.HTTP_201_CREATED)
async def create_plant(payload: PlantCreate, session: SessionDep, user: CurrentUser) -> Plant:
    """Create a plant; a linked species seeds reminders from its default intervals."""
    await _validate_location(session, payload.location_id)
    species = await _validate_species(session, payload.species_id)
    plant = Plant(**payload.model_dump(), created_by=user.id)
    session.add(plant)
    if species is not None:
        await session.flush()  # plant.id must exist before reminders reference it
        await materialize_default_reminders(session, plant, species, user.id)
    await session.commit()
    await session.refresh(plant)
    return plant


@router.get("/{plant_id}", response_model=PlantDetail)
async def get_plant(plant_id: uuid.UUID, session: SessionDep, _user: CurrentUser) -> PlantDetail:
    """Plant detail including the last care event per event type and the linked species."""
    plant = await get_plant_or_404(session, plant_id)
    last_events = await care.last_event_per_type(session, plant_id)
    species = await session.get(Species, plant.species_id) if plant.species_id else None
    species_read = SpeciesRead(**species.model_dump()) if species else None
    return PlantDetail(**plant.model_dump(), last_events=last_events, species=species_read)


@router.patch("/{plant_id}", response_model=PlantRead)
async def update_plant(plant_id: uuid.UUID, payload: PlantUpdate, session: SessionDep, _user: CurrentUser) -> Plant:
    """Apply a partial update to a plant."""
    plant = await get_plant_or_404(session, plant_id)
    updates = payload.model_dump(exclude_unset=True)
    if "location_id" in updates:
        await _validate_location(session, updates["location_id"])
    if "species_id" in updates:
        await _validate_species(session, updates["species_id"])
    for field, value in updates.items():
        setattr(plant, field, value)
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


@router.post("/{plant_id}/apply-species-defaults", response_model=list[ReminderRead])
async def apply_species_defaults(plant_id: uuid.UUID, session: SessionDep, user: CurrentUser) -> list[ReminderRead]:
    """Materialize the linked species' default intervals as reminders.

    Existing reminders for the same event types are left untouched, so this is
    safe to call repeatedly (e.g. after linking a species to an older plant).
    """
    plant = await get_plant_or_404(session, plant_id)
    species = await session.get(Species, plant.species_id) if plant.species_id else None
    if species is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plant has no species")
    created = await materialize_default_reminders(session, plant, species, user.id)
    await session.commit()
    for reminder in created:
        await session.refresh(reminder)
    return [ReminderRead(**reminder.model_dump()) for reminder in created]


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
