"""Plant photo table model.

Photos are stored as BLOBs directly in the database, so a single backup of the
SQLite file (or a Litestream stream) covers them. Large collections grow the
file; revisit object storage if that becomes a problem.

Uploads are downscaled and re-encoded to WebP on the way in (see
services.images): ``data`` holds the display-sized image and ``thumbnail`` a
small variant for grids and cards. The original is not retained, which keeps the
file small enough that full-file backups stay cheap.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, LargeBinary
from sqlmodel import Field, SQLModel

from greenthumb.models.base import utc_datetime_type, utcnow


class PlantPhoto(SQLModel, table=True):
    """A photo of a plant, stored inline in the database."""

    __tablename__ = "plant_photos"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    plant_id: uuid.UUID = Field(foreign_key="plants.id", ondelete="CASCADE", index=True)
    data: bytes = Field(sa_column=Column(LargeBinary(), nullable=False))
    thumbnail: bytes = Field(sa_column=Column(LargeBinary(), nullable=False))
    mime_type: str
    uploaded_by: uuid.UUID = Field(foreign_key="users.id")
    uploaded_at: datetime = Field(default_factory=utcnow, sa_column=Column(utc_datetime_type(), nullable=False))
