"""Table models. Importing this package registers all tables on SQLModel.metadata."""

from greenthumb.models.care_log import CareLog
from greenthumb.models.location import Location
from greenthumb.models.photo import PlantPhoto
from greenthumb.models.plant import Plant
from greenthumb.models.push_subscription import PushSubscription
from greenthumb.models.reminder import Reminder, ScheduleKind
from greenthumb.models.species import Species
from greenthumb.models.user import User

__all__ = [
    "CareLog",
    "Location",
    "Plant",
    "PlantPhoto",
    "PushSubscription",
    "Reminder",
    "ScheduleKind",
    "Species",
    "User",
]
