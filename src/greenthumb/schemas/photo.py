"""Response schemas for plant photos (metadata only; bytes are streamed separately)."""

import uuid
from datetime import datetime

from sqlmodel import SQLModel


class PhotoRead(SQLModel):
    """Photo metadata; the image itself is served by GET /photos/{photo_id}."""

    id: uuid.UUID
    plant_id: uuid.UUID
    mime_type: str
    uploaded_by: uuid.UUID
    uploaded_at: datetime
