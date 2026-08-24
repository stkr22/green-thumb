"""Species routes."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlmodel import col, func, select, update

from greenthumb.auth import CurrentUser, SessionDep
from greenthumb.models import Plant, Species
from greenthumb.models.base import utcnow
from greenthumb.schemas import SeasonPlanApplied, SpeciesCreate, SpeciesListItem, SpeciesRead, SpeciesUpdate
from greenthumb.services.species import apply_season_plan_to_plants

router = APIRouter(prefix="/species", tags=["species"])


async def get_species_or_404(session: SessionDep, species_id: uuid.UUID) -> Species:
    """Fetch a species or raise 404."""
    species = await session.get(Species, species_id)
    if species is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Species not found")
    return species


@router.get("", response_model=list[SpeciesListItem])
async def list_species(session: SessionDep, _user: CurrentUser, search: str | None = None) -> list[SpeciesListItem]:
    """List species with plant counts, optionally filtered by a name search term."""
    plant_counts = (
        select(col(Plant.species_id).label("species_id"), func.count().label("plant_count"))
        .group_by(col(Plant.species_id))
        .subquery()
    )
    statement = select(Species, func.coalesce(plant_counts.c.plant_count, 0)).outerjoin(
        plant_counts, plant_counts.c.species_id == col(Species.id)
    )
    if search:
        pattern = f"%{search}%"
        statement = statement.where(col(Species.name).ilike(pattern) | col(Species.scientific_name).ilike(pattern))
    rows = (await session.exec(statement.order_by(col(Species.name)))).all()
    return [SpeciesListItem(**species.model_dump(), plant_count=count) for species, count in rows]


@router.post("", response_model=SpeciesRead, status_code=status.HTTP_201_CREATED)
async def create_species(payload: SpeciesCreate, session: SessionDep, user: CurrentUser) -> Species:
    """Create a species."""
    species = Species(**payload.model_dump(), created_by=user.id)
    session.add(species)
    await session.commit()
    await session.refresh(species)
    return species


@router.get("/{species_id}", response_model=SpeciesRead)
async def get_species(species_id: uuid.UUID, session: SessionDep, _user: CurrentUser) -> Species:
    """Fetch one species."""
    return await get_species_or_404(session, species_id)


@router.patch("/{species_id}", response_model=SpeciesRead)
async def update_species(
    species_id: uuid.UUID, payload: SpeciesUpdate, session: SessionDep, _user: CurrentUser
) -> Species:
    """Apply a partial update to a species."""
    species = await get_species_or_404(session, species_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(species, field, value)
    species.updated_at = utcnow()
    session.add(species)
    await session.commit()
    await session.refresh(species)
    return species


@router.post("/{species_id}/apply-season-plan", response_model=SeasonPlanApplied)
async def apply_season_plan(species_id: uuid.UUID, session: SessionDep, _user: CurrentUser) -> SeasonPlanApplied:
    """Roll this species' season plan out to the reminders of every plant already using it.

    Plans are copied at plant creation, so this is how a collection that
    predates the plan (or an edited plan) catches up. It overwrites only the
    season multipliers; per-plant intervals are left alone.
    """
    species = await get_species_or_404(session, species_id)
    updated = await apply_season_plan_to_plants(session, species)
    await session.commit()
    return SeasonPlanApplied(reminders_updated=updated)


@router.delete("/{species_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_species(species_id: uuid.UUID, session: SessionDep, _user: CurrentUser) -> None:
    """Delete a species; plants that referenced it keep existing unlinked."""
    species = await get_species_or_404(session, species_id)
    # Explicit detach instead of relying on ON DELETE SET NULL so behaviour is
    # identical on the SQLite test backend (mirrors location deletion).
    await session.exec(update(Plant).where(col(Plant.species_id) == species_id).values(species_id=None))  # type: ignore[call-overload]
    await session.delete(species)
    await session.commit()
