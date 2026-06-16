"""Health, species search, and notification trigger tests."""

import httpx
import pytest

from greenthumb.api.v1 import notifications as notifications_module


async def test_healthz(anon_client: httpx.AsyncClient):
    response = await anon_client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_species_search_without_api_key_returns_empty(client: httpx.AsyncClient):
    # FLORACODEX_API_KEY is unset in tests: graceful degradation per spec.
    response = await client.get("/api/v1/species/search", params={"q": "monstera"})
    assert response.status_code == 200
    assert response.json() == []


async def test_species_search_requires_auth(anon_client: httpx.AsyncClient):
    response = await anon_client.get("/api/v1/species/search", params={"q": "monstera"})
    assert response.status_code == 401


async def test_notification_test_endpoint_success(client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch):
    async def _ok(**_kwargs) -> bool:
        return True

    monkeypatch.setattr(notifications_module.ntfy, "send_notification", _ok)
    response = await client.post("/api/v1/notifications/test")
    assert response.status_code == 200


async def test_notification_test_endpoint_failure_returns_502(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    async def _fail(**_kwargs) -> bool:
        return False

    monkeypatch.setattr(notifications_module.ntfy, "send_notification", _fail)
    response = await client.post("/api/v1/notifications/test")
    assert response.status_code == 502
