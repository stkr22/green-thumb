"""Tests for the local-only dev-login bypass.

The endpoint must be inert (404) unless DEV_AUTH_BYPASS is explicitly enabled,
and when enabled must provision a user and set a working session cookie.
"""

import httpx

from greenthumb.config import get_settings


async def test_dev_login_disabled_returns_404(anon_client: httpx.AsyncClient):
    response = await anon_client.get("/auth/dev-login", follow_redirects=False)
    assert response.status_code == 404


async def test_dev_login_enabled_sets_working_session(anon_client: httpx.AsyncClient, monkeypatch):
    # Flip the cached settings flag for the duration of this test only.
    monkeypatch.setattr(get_settings(), "DEV_AUTH_BYPASS", True)

    response = await anon_client.get("/auth/dev-login", follow_redirects=False)
    assert response.status_code == 302
    assert "greenthumb_session" in response.cookies

    # The cookie httpx stored from the redirect authenticates a real request.
    me = await anon_client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["display_name"]


async def test_dev_login_is_idempotent(anon_client: httpx.AsyncClient, monkeypatch):
    # Hitting it twice reuses the same demo user rather than failing on the
    # unique oidc_sub constraint.
    monkeypatch.setattr(get_settings(), "DEV_AUTH_BYPASS", True)

    first = await anon_client.get("/auth/dev-login", follow_redirects=False)
    second = await anon_client.get("/auth/dev-login", follow_redirects=False)
    assert first.status_code == 302
    assert second.status_code == 302
    assert (await anon_client.get("/auth/me")).status_code == 200
