"""Reminder API tests."""

from datetime import UTC, datetime, timedelta

import httpx
from sqlmodel.ext.asyncio.session import AsyncSession

from greenthumb.models import Plant, User
from tests.conftest import add_care_log


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


async def test_reminder_list_computes_due_at(
    client: httpx.AsyncClient, session: AsyncSession, plant: Plant, user: User
):
    await client.post(f"/api/v1/plants/{plant.id}/reminders", json={"event_type": "watering", "interval_days": 7})
    await client.post(f"/api/v1/plants/{plant.id}/reminders", json={"event_type": "fertilising", "interval_days": 30})
    watered_at = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    await add_care_log(session, plant.id, user.id, event_type="watering", logged_at=watered_at)

    listed = {item["event_type"]: item for item in (await client.get(f"/api/v1/plants/{plant.id}/reminders")).json()}
    assert datetime.fromisoformat(listed["watering"]["due_at"]).replace(tzinfo=UTC) == watered_at + timedelta(days=7)
    # No fertilising event yet: due immediately, signalled by a null due_at.
    assert listed["fertilising"]["due_at"] is None


async def test_reminder_rejects_nonpositive_interval(client: httpx.AsyncClient, plant: Plant):
    response = await client.post(
        f"/api/v1/plants/{plant.id}/reminders", json={"event_type": "watering", "interval_days": 0}
    )
    assert response.status_code == 422
