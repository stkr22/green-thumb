"""Web Push subscription API, VAPID key derivation, and evaluator delivery tests."""

import base64
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest
from py_vapid import Vapid
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from greenthumb.api.v1 import notifications
from greenthumb.models import Plant, PushSubscription, Reminder, User
from greenthumb.services import reminder_evaluator, webpush
from tests.conftest import add_care_log

SUBSCRIPTION = {
    "endpoint": "https://push.example/send/abc",
    "keys": {"p256dh": "client-public-key", "auth": "client-auth-secret"},
}


async def test_push_subscription_upsert(client: httpx.AsyncClient, session: AsyncSession):
    first = await client.post("/api/v1/notifications/push/subscriptions", json=SUBSCRIPTION)
    assert first.status_code == 201

    rotated = {**SUBSCRIPTION, "keys": {"p256dh": "rotated", "auth": "rotated"}}
    second = await client.post("/api/v1/notifications/push/subscriptions", json=rotated)
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]

    rows = (await session.exec(select(PushSubscription))).all()
    assert len(rows) == 1
    assert rows[0].p256dh == "rotated"


async def test_push_unsubscribe_is_idempotent(client: httpx.AsyncClient, session: AsyncSession):
    await client.post("/api/v1/notifications/push/subscriptions", json=SUBSCRIPTION)
    assert (
        await client.post("/api/v1/notifications/push/unsubscribe", json={"endpoint": SUBSCRIPTION["endpoint"]})
    ).status_code == 204
    assert (
        await client.post("/api/v1/notifications/push/unsubscribe", json={"endpoint": SUBSCRIPTION["endpoint"]})
    ).status_code == 204
    assert (await session.exec(select(PushSubscription))).all() == []


async def test_public_key_null_when_unconfigured(client: httpx.AsyncClient):
    response = await client.get("/api/v1/notifications/push/public-key")
    assert response.status_code == 200
    assert response.json()["key"] is None


def test_public_key_derivation(monkeypatch: pytest.MonkeyPatch):
    vapid = Vapid()
    vapid.generate_keys()
    raw = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
    private_key = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    monkeypatch.setattr(
        webpush, "get_settings", lambda: SimpleNamespace(VAPID_PRIVATE_KEY=private_key, VAPID_SUBJECT="mailto:a@b")
    )
    webpush.public_key.cache_clear()
    key = webpush.public_key()
    webpush.public_key.cache_clear()
    # An uncompressed P-256 point is 65 bytes starting 0x04 -> base64url 'B...'.
    assert key is not None
    assert key.startswith("B")
    assert len(key) == 87


async def test_evaluator_delivers_push_and_prunes_gone_subscriptions(
    session: AsyncSession, plant: Plant, user: User, monkeypatch: pytest.MonkeyPatch
):
    user.ntfy_enabled = False
    session.add(user)
    session.add(PushSubscription(user_id=user.id, endpoint="https://push.example/alive", p256dh="k", auth="a"))
    session.add(PushSubscription(user_id=user.id, endpoint="https://push.example/dead", p256dh="k", auth="a"))
    reminder = Reminder(plant_id=plant.id, event_type="watering", interval_days=7, created_by=user.id)
    session.add(reminder)
    await add_care_log(session, plant.id, user.id, logged_at=datetime.now(UTC) - timedelta(days=10))
    await session.commit()

    async def fake_send(subscription: PushSubscription, **_kwargs) -> webpush.PushResult:
        return webpush.PushResult.GONE if subscription.endpoint.endswith("dead") else webpush.PushResult.SENT

    monkeypatch.setattr(reminder_evaluator.webpush, "send_notification", fake_send)

    assert await reminder_evaluator.evaluate_and_notify(session) == 1
    remaining = (await session.exec(select(PushSubscription))).all()
    assert [s.endpoint for s in remaining] == ["https://push.example/alive"]
    await session.refresh(reminder)
    assert reminder.last_notified_at is not None


async def test_test_notification_uses_push_channel(
    client: httpx.AsyncClient, session: AsyncSession, user: User, monkeypatch: pytest.MonkeyPatch
):
    user.ntfy_enabled = False
    session.add(user)
    await session.commit()
    await client.post("/api/v1/notifications/push/subscriptions", json=SUBSCRIPTION)

    async def fake_send(_subscription: PushSubscription, **_kwargs) -> webpush.PushResult:
        return webpush.PushResult.SENT

    monkeypatch.setattr(notifications.webpush, "send_notification", fake_send)
    response = await client.post("/api/v1/notifications/test")
    assert response.status_code == 200
    assert response.json()["detail"] == "Sent 1 notification(s)"


async def test_test_notification_fails_without_any_channel(client: httpx.AsyncClient, user: User):
    assert user.ntfy_enabled is True  # but NTFY_URL is unset in tests, so delivery fails
    response = await client.post("/api/v1/notifications/test")
    assert response.status_code == 502
