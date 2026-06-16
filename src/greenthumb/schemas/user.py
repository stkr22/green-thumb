"""Request/response schemas for users and the /auth/me endpoints."""

import uuid
from datetime import datetime

from sqlmodel import SQLModel


class UserRead(SQLModel):
    """Public profile of the current user, including notification preferences."""

    id: uuid.UUID
    email: str
    display_name: str
    ntfy_enabled: bool
    ntfy_topic_override: str | None
    created_at: datetime


class UserUpdate(SQLModel):
    """Mutable user preferences; identity fields come from OIDC and are read-only."""

    ntfy_enabled: bool | None = None
    ntfy_topic_override: str | None = None
