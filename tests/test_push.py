"""Web Push subscription API, VAPID key derivation, and evaluator delivery tests."""

import base64
import os
import uuid
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest
from aiohttp import web
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from py_vapid import Vapid
from pydantic import SecretStr, ValidationError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from greenthumb.api.v1 import notifications
from greenthumb.config import Settings
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


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


@pytest.fixture
def vapid_configured(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    vapid = Vapid()
    vapid.generate_keys()
    private_key = _b64url(vapid.private_key.private_numbers().private_value.to_bytes(32, "big"))
    monkeypatch.setattr(
        webpush,
        "get_settings",
        lambda: SimpleNamespace(VAPID_PRIVATE_KEY=SecretStr(private_key), VAPID_SUBJECT="mailto:admin@example.com"),
    )
    webpush._vapid.cache_clear()
    yield
    webpush._vapid.cache_clear()


def test_public_key_derivation(vapid_configured: None):
    key = webpush.public_key()
    # An uncompressed P-256 point is 65 bytes starting 0x04 -> base64url 'B...'.
    assert key is not None
    assert key.startswith("B")
    assert len(key) == 87


def _browser_subscription(endpoint: str) -> PushSubscription:
    """A subscription with real browser-style keys, so payload encryption runs."""
    client_key = ec.generate_private_key(ec.SECP256R1()).public_key()
    p256dh = client_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return PushSubscription(
        user_id=uuid.uuid4(), endpoint=endpoint, p256dh=_b64url(p256dh), auth=_b64url(os.urandom(16))
    )


async def test_send_notification_maps_push_service_responses(
    vapid_configured: None, aiohttp_push_service: tuple[str, list[web.Request]]
):
    base_url, requests = aiohttp_push_service

    async def send(path: str) -> webpush.PushResult:
        return await webpush.send_notification(_browser_subscription(base_url + path), title="t", message="m")

    assert await send("/ok") is webpush.PushResult.SENT
    assert await send("/gone") is webpush.PushResult.GONE
    assert await send("/error") is webpush.PushResult.FAILED
    # A non-zero TTL lets the push service hold the digest for a sleeping phone.
    assert int(requests[0].headers["TTL"]) > 0
    assert requests[0].headers["Authorization"].startswith("vapid ")


async def test_send_notification_survives_unreachable_endpoint(vapid_configured: None):
    # Port 9 (discard) is closed locally: a connection error, not a WebPushException.
    subscription = _browser_subscription("http://127.0.0.1:9/push")
    assert await webpush.send_notification(subscription, title="t", message="m") is webpush.PushResult.FAILED


@pytest.fixture
async def aiohttp_push_service() -> AsyncIterator[tuple[str, list[web.Request]]]:
    """A local stand-in for a browser push service."""
    requests: list[web.Request] = []
    statuses = {"/ok": 201, "/gone": 410, "/error": 500}

    async def handle(request: web.Request) -> web.Response:
        requests.append(request)
        await request.read()
        return web.Response(status=statuses[request.path])

    app = web.Application()
    app.router.add_post("/{tail:.*}", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", 0).start()
    host, port = runner.addresses[0][:2]
    yield f"http://{host}:{port}", requests
    await runner.cleanup()


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


@pytest.mark.parametrize("subject", ["mailto:a@b", "admin@example.com", "http://plants.example"])
def test_malformed_vapid_subject_fails_at_startup(subject: str):
    # py_vapid would only reject these when signing, failing every push silently.
    with pytest.raises(ValidationError):
        Settings(VAPID_SUBJECT=subject)
