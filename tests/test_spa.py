"""SPA serving: real assets win, client-side routes fall back to index.html,
and API routes registered before the catch-all mount take precedence."""

from collections.abc import AsyncGenerator

import httpx
import pytest
from fastapi import FastAPI

from greenthumb.main import _SPAStaticFiles


@pytest.fixture
async def client(tmp_path) -> AsyncGenerator[httpx.AsyncClient]:
    (tmp_path / "index.html").write_text("<!doctype html><title>SPA</title>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log('hi')")

    app = FastAPI()

    @app.get("/api/ping")
    async def ping() -> dict[str, str]:
        return {"pong": "ok"}

    app.mount("/", _SPAStaticFiles(directory=str(tmp_path), html=True), name="spa")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_real_asset_is_served(client: httpx.AsyncClient):
    response = await client.get("/assets/app.js")
    assert response.status_code == 200
    assert "console.log" in response.text


async def test_deep_link_falls_back_to_index(client: httpx.AsyncClient):
    response = await client.get("/plants/123")
    assert response.status_code == 200
    assert "SPA" in response.text


async def test_api_route_takes_precedence_over_mount(client: httpx.AsyncClient):
    response = await client.get("/api/ping")
    assert response.status_code == 200
    assert response.json() == {"pong": "ok"}
