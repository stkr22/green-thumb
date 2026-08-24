"""SPA serving: real assets win, browser deep links fall back to index.html,
non-HTML requests get real 404s, and API routes take precedence."""

from collections.abc import AsyncGenerator

import httpx
import pytest
from fastapi import FastAPI

BROWSER_ACCEPT = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}


@pytest.fixture
async def client(tmp_path) -> AsyncGenerator[httpx.AsyncClient]:
    (tmp_path / "index.html").write_text("<!doctype html><title>SPA</title>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log('hi')")

    app = FastAPI()

    @app.get("/api/ping")
    async def ping() -> dict[str, str]:
        return {"pong": "ok"}

    app.frontend("/", directory=str(tmp_path), fallback="index.html")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_real_asset_is_served(client: httpx.AsyncClient):
    response = await client.get("/assets/app.js")
    assert response.status_code == 200
    assert "console.log" in response.text


async def test_deep_link_falls_back_to_index(client: httpx.AsyncClient):
    response = await client.get("/plants/123", headers=BROWSER_ACCEPT)
    assert response.status_code == 200
    assert "SPA" in response.text


async def test_missing_asset_is_not_masked_by_the_shell(client: httpx.AsyncClient):
    # A stale precache entry must fail loudly instead of receiving index.html,
    # which the browser would then try to parse as JavaScript.
    response = await client.get("/assets/gone.js")
    assert response.status_code == 404


async def test_unknown_api_path_returns_json_404(client: httpx.AsyncClient):
    response = await client.get("/api/nope", headers={"Accept": "application/json"})
    assert response.status_code == 404


async def test_api_route_takes_precedence_over_frontend(client: httpx.AsyncClient):
    response = await client.get("/api/ping")
    assert response.status_code == 200
    assert response.json() == {"pong": "ok"}
