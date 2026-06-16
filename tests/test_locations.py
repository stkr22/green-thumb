"""Location CRUD tests."""

import uuid

import httpx
from sqlmodel.ext.asyncio.session import AsyncSession

from greenthumb.models import Plant


async def test_location_crud_roundtrip(client: httpx.AsyncClient):
    created = await client.post("/api/v1/locations", json={"name": "Living room", "description": "South window"})
    assert created.status_code == 201
    location_id = created.json()["id"]

    listed = await client.get("/api/v1/locations")
    assert listed.status_code == 200
    assert [item["name"] for item in listed.json()] == ["Living room"]
    assert listed.json()[0]["plant_count"] == 0

    patched = await client.patch(f"/api/v1/locations/{location_id}", json={"name": "Lounge"})
    assert patched.status_code == 200
    assert patched.json()["name"] == "Lounge"

    deleted = await client.delete(f"/api/v1/locations/{location_id}")
    assert deleted.status_code == 204
    assert (await client.get("/api/v1/locations")).json() == []


async def test_location_delete_detaches_plants(client: httpx.AsyncClient, session: AsyncSession):
    location = (await client.post("/api/v1/locations", json={"name": "Kitchen"})).json()
    plant = (await client.post("/api/v1/plants", json={"name": "Basil", "location_id": location["id"]})).json()

    counted = await client.get("/api/v1/locations")
    assert counted.json()[0]["plant_count"] == 1

    assert (await client.delete(f"/api/v1/locations/{location['id']}")).status_code == 204
    refreshed = await session.get(Plant, uuid.UUID(plant["id"]))
    assert refreshed is not None
    assert refreshed.location_id is None


async def test_location_update_missing_returns_404(client: httpx.AsyncClient):
    response = await client.patch("/api/v1/locations/00000000-0000-0000-0000-000000000000", json={"name": "X"})
    assert response.status_code == 404
