"""Auth tests: session cookie validation and the /auth/me endpoints."""

import uuid

import httpx

from greenthumb.auth.session import (
    SESSION_COOKIE_NAME,
    create_flow_token,
    create_session_token,
    verify_flow_token,
    verify_session_token,
)
from greenthumb.models import User


async def test_me_requires_authentication(anon_client: httpx.AsyncClient):
    response = await anon_client.get("/auth/me")
    assert response.status_code == 401


async def test_me_rejects_garbage_cookie(anon_client: httpx.AsyncClient):
    anon_client.cookies.set(SESSION_COOKIE_NAME, "not-a-jwt")
    response = await anon_client.get("/auth/me")
    assert response.status_code == 401


async def test_me_rejects_flow_token_as_session(anon_client: httpx.AsyncClient):
    # A signed token of the wrong purpose must not grant a session.
    anon_client.cookies.set(SESSION_COOKIE_NAME, create_flow_token("s", "n", "v"))
    response = await anon_client.get("/auth/me")
    assert response.status_code == 401


async def test_me_rejects_unknown_user(anon_client: httpx.AsyncClient):
    anon_client.cookies.set(SESSION_COOKIE_NAME, create_session_token(uuid.uuid4()))
    response = await anon_client.get("/auth/me")
    assert response.status_code == 401


async def test_me_returns_profile(client: httpx.AsyncClient):
    response = await client.get("/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "gardener@example.com"
    assert body["ntfy_enabled"] is True  # notifications are on by default


async def test_patch_me_updates_ntfy_preferences(client: httpx.AsyncClient):
    response = await client.patch("/auth/me", json={"ntfy_enabled": False, "ntfy_topic_override": "my-plants"})
    assert response.status_code == 200
    body = response.json()
    assert body["ntfy_enabled"] is False
    assert body["ntfy_topic_override"] == "my-plants"


def test_flow_token_roundtrip():
    token = create_flow_token("state123", "nonce456", "verifier789")
    assert verify_flow_token(token) == {"state": "state123", "nonce": "nonce456", "code_verifier": "verifier789"}


def test_tokens_are_not_interchangeable():
    assert verify_session_token(create_flow_token("s", "n", "v")) is None
    assert verify_flow_token(create_session_token(uuid.uuid4())) is None


async def test_cookie_write_without_csrf_header_is_rejected(client: httpx.AsyncClient):
    # What a forged cross-site request looks like: the cookie rides along, the
    # custom header can't.
    del client.headers["X-Requested-With"]
    response = await client.post("/api/v1/locations", json={"name": "Forged"})
    assert response.status_code == 403
    assert (await client.get("/api/v1/locations")).status_code == 200  # reads stay open


async def test_bearer_write_needs_no_csrf_header(anon_client: httpx.AsyncClient, user: User):
    token = create_session_token(user.id)
    response = await anon_client.post(
        "/api/v1/locations", json={"name": "Scripted"}, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
