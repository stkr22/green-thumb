"""Reminder API tests."""

import httpx

from greenthumb.models import Plant


async def test_reminder_crud_roundtrip(client: httpx.AsyncClient, plant: Plant):
    created = await client.post(
        f"/api/v1/plants/{plant.id}/reminders", json={"event_type": "watering", "interval_days": 7}
    )
    assert created.status_code == 201
    reminder = created.json()
    assert reminder["enabled"] is True
    assert reminder["last_notified_at"] is None

    listed = await client.get(f"/api/v1/plants/{plant.id}/reminders")
    assert len(listed.json()) == 1

    patched = await client.patch(f"/api/v1/reminders/{reminder['id']}", json={"interval_days": 14, "enabled": False})
    assert patched.status_code == 200
    assert patched.json()["interval_days"] == 14
    assert patched.json()["enabled"] is False

    assert (await client.delete(f"/api/v1/reminders/{reminder['id']}")).status_code == 204
    assert (await client.get(f"/api/v1/plants/{plant.id}/reminders")).json() == []


async def test_reminder_rejects_nonpositive_interval(client: httpx.AsyncClient, plant: Plant):
    response = await client.post(
        f"/api/v1/plants/{plant.id}/reminders", json={"event_type": "watering", "interval_days": 0}
    )
    assert response.status_code == 422
