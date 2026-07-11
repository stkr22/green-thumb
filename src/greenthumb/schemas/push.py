"""Request/response schemas for Web Push subscriptions."""

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class PushKeys(SQLModel):
    """Client keys from PushManager.subscribe()."""

    p256dh: str = Field(min_length=1, max_length=512)
    auth: str = Field(min_length=1, max_length=512)


class PushSubscriptionCreate(SQLModel):
    """A browser PushSubscription, in the shape subscription.toJSON() emits."""

    endpoint: str = Field(min_length=1, max_length=2048)
    keys: PushKeys


class PushSubscriptionRead(SQLModel):
    """Stored subscription (keys omitted; the client never needs them back)."""

    id: uuid.UUID
    endpoint: str
    created_at: datetime


class PushUnsubscribe(SQLModel):
    """Payload to remove a subscription by its endpoint."""

    endpoint: str = Field(min_length=1, max_length=2048)


class PushPublicKey(SQLModel):
    """VAPID application server key; null when Web Push is not configured."""

    key: str | None
