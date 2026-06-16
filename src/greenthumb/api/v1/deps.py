"""Shared helpers for v1 route handlers."""

import uuid

from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from greenthumb.models import Plant


async def get_plant_or_404(session: AsyncSession, plant_id: uuid.UUID) -> Plant:
    """Load a plant or raise the standard 404."""
    plant = await session.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plant not found")
    return plant
