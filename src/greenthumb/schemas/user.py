"""Request/response schemas for users and the /auth/me endpoints."""

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


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

    # NOT NULL columns are typed non-optional with a None default: omitting the
    # field leaves it unchanged, while an explicit null is a 422 instead of an
    # IntegrityError. Nullable columns keep `| None` so null clears them.
    ntfy_enabled: bool = Field(default=None)
    ntfy_topic_override: str | None = None


class ApiTokenRead(SQLModel):
    """A freshly minted API token. Shown once; the server keeps no copy."""

    token: str
