"""Versioned API router: one module per domain, aggregated under /api/v1."""

from fastapi import APIRouter

from greenthumb.api.v1 import dashboard, locations, logs, notifications, photos, plants, reminders, species

router = APIRouter(prefix="/api/v1")
router.include_router(locations.router)
router.include_router(plants.router)
router.include_router(photos.router)
router.include_router(logs.router)
router.include_router(reminders.router)
router.include_router(dashboard.router)
router.include_router(species.router)
router.include_router(notifications.router)

__all__ = ["router"]
