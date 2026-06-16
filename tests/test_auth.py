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
    assert body["ntfy_enabled"] is False


async def test_patch_me_updates_ntfy_preferences(client: httpx.AsyncClient):
    response = await client.patch("/auth/me", json={"ntfy_enabled": True, "ntfy_topic_override": "my-plants"})
    assert response.status_code == 200
    body = response.json()
    assert body["ntfy_enabled"] is True
    assert body["ntfy_topic_override"] == "my-plants"


def test_session_token_roundtrip():
    user_id = uuid.uuid4()
    assert verify_session_token(create_session_token(user_id)) == user_id


def test_flow_token_roundtrip():
    token = create_flow_token("state123", "nonce456", "verifier789")
    assert verify_flow_token(token) == {"state": "state123", "nonce": "nonce456", "code_verifier": "verifier789"}


def test_tokens_are_not_interchangeable():
    assert verify_session_token(create_flow_token("s", "n", "v")) is None
    assert verify_flow_token(create_session_token(uuid.uuid4())) is None
