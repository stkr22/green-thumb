"""User table model. Users are provisioned automatically on first OIDC login."""

import uuid
from datetime import datetime

from sqlalchemy import Column
from sqlmodel import Field, SQLModel

from greenthumb.models.base import utc_datetime_type, utcnow


class User(SQLModel, table=True):
    """An application user, identified by the OIDC ``sub`` claim from Zitadel."""

    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    oidc_sub: str = Field(unique=True, index=True)
    email: str
    display_name: str
    ntfy_enabled: bool = Field(default=True)
    # Per-user topic override; falls back to the global NTFY_TOPIC when unset.
    ntfy_topic_override: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(utc_datetime_type(), nullable=False))
