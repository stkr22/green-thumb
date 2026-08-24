"""Pydantic/SQLModel request and response schemas."""

from greenthumb.schemas.care_log import CareLogCreate, CareLogRead
from greenthumb.schemas.dashboard import DashboardSummary, RecentCare, ReminderStatus
from greenthumb.schemas.location import LocationCreate, LocationRead, LocationUpdate
from greenthumb.schemas.photo import PhotoRead
from greenthumb.schemas.plant import (
    CoverPhotoUpdate,
    PlantCreate,
    PlantDetail,
    PlantListItem,
    PlantRead,
    PlantUpdate,
)
from greenthumb.schemas.push import (
    PushKeys,
    PushPublicKey,
    PushSubscriptionCreate,
    PushSubscriptionRead,
    PushUnsubscribe,
)
from greenthumb.schemas.reminder import (
    ReminderCreate,
    ReminderRead,
    ReminderSnooze,
    ReminderStatusRead,
    ReminderUpdate,
)
from greenthumb.schemas.season import SeasonInfo, SeasonPreset
from greenthumb.schemas.species import (
    SeasonPlanApplied,
    SpeciesCreate,
    SpeciesListItem,
    SpeciesRead,
    SpeciesUpdate,
)
from greenthumb.schemas.user import ApiTokenRead, UserRead, UserUpdate

__all__ = [
    "ApiTokenRead",
    "CareLogCreate",
    "CareLogRead",
    "CoverPhotoUpdate",
    "DashboardSummary",
    "LocationCreate",
    "LocationRead",
    "LocationUpdate",
    "PhotoRead",
    "PlantCreate",
    "PlantDetail",
    "PlantListItem",
    "PlantRead",
    "PlantUpdate",
    "PushKeys",
    "PushPublicKey",
    "PushSubscriptionCreate",
    "PushSubscriptionRead",
    "PushUnsubscribe",
    "RecentCare",
    "ReminderCreate",
    "ReminderRead",
    "ReminderSnooze",
    "ReminderStatus",
    "ReminderStatusRead",
    "ReminderUpdate",
    "SeasonInfo",
    "SeasonPlanApplied",
    "SeasonPreset",
    "SpeciesCreate",
    "SpeciesListItem",
    "SpeciesRead",
    "SpeciesUpdate",
    "UserRead",
    "UserUpdate",
]
