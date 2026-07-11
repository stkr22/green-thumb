"""Web Push subscription table model."""

import uuid
from datetime import datetime

from sqlalchemy import Column
from sqlmodel import Field, SQLModel

from greenthumb.models.base import utc_datetime_type, utcnow


class PushSubscription(SQLModel, table=True):
    """One browser/device push subscription for a user.

    A user typically has several (phone, laptop); the endpoint is what the
    push service hands out and uniquely identifies the device+browser.
    """

    __tablename__ = "push_subscriptions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    endpoint: str = Field(unique=True, index=True)
    # Client keypair from PushManager.subscribe(); needed to encrypt payloads.
    p256dh: str
    auth: str
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(utc_datetime_type(), nullable=False))
