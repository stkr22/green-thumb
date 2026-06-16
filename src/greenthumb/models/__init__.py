"""Table models. Importing this package registers all tables on SQLModel.metadata."""

from greenthumb.models.care_log import CareLog
from greenthumb.models.location import Location
from greenthumb.models.photo import PlantPhoto
from greenthumb.models.plant import Plant
from greenthumb.models.reminder import Reminder
from greenthumb.models.user import User

__all__ = ["CareLog", "Location", "Plant", "PlantPhoto", "Reminder", "User"]
