"""Care log API tests."""

import httpx

from greenthumb.models import Plant


async def test_create_log_defaults_logged_at(client: httpx.AsyncClient, plant: Plant):
    created = await client.post(f"/api/v1/plants/{plant.id}/logs", json={"event_type": "watering"})
    assert created.status_code == 201
    assert created.json()["logged_at"] is not None


async def test_list_logs_filter_and_limit(client: httpx.AsyncClient, plant: Plant):
    for event_type in ("watering", "watering", "fertilising"):
        await client.post(f"/api/v1/plants/{plant.id}/logs", json={"event_type": event_type})

    watering = await client.get(f"/api/v1/plants/{plant.id}/logs", params={"event_type": "watering"})
    assert len(watering.json()) == 2

    limited = await client.get(f"/api/v1/plants/{plant.id}/logs", params={"limit": 1})
    assert len(limited.json()) == 1


async def test_logs_support_backdating_and_custom_types(client: httpx.AsyncClient, plant: Plant):
    created = await client.post(
        f"/api/v1/plants/{plant.id}/logs",
        json={"event_type": "misting", "logged_at": "2026-01-15T08:00:00Z", "notes": "morning mist"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["event_type"] == "misting"
    assert body["logged_at"].startswith("2026-01-15T08:00:00")


async def test_delete_log(client: httpx.AsyncClient, plant: Plant):
    log_id = (await client.post(f"/api/v1/plants/{plant.id}/logs", json={"event_type": "watering"})).json()["id"]
    assert (await client.delete(f"/api/v1/logs/{log_id}")).status_code == 204
    assert (await client.get(f"/api/v1/plants/{plant.id}/logs")).json() == []
