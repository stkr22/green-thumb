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


async def test_snooze_defaults_to_interval(client: httpx.AsyncClient, plant: Plant):
    reminder = (
        await client.post(f"/api/v1/plants/{plant.id}/reminders", json={"event_type": "watering", "interval_days": 7})
    ).json()

    before = datetime.now(UTC)
    snoozed = await client.post(f"/api/v1/reminders/{reminder['id']}/snooze", json={})
    assert snoozed.status_code == 200
    snoozed_until = datetime.fromisoformat(snoozed.json()["snoozed_until"]).replace(tzinfo=UTC)
    assert before + timedelta(days=7) <= snoozed_until <= datetime.now(UTC) + timedelta(days=7)


async def test_snooze_custom_days(client: httpx.AsyncClient, plant: Plant):
    reminder = (
        await client.post(f"/api/v1/plants/{plant.id}/reminders", json={"event_type": "watering", "interval_days": 7})
    ).json()

    snoozed = await client.post(f"/api/v1/reminders/{reminder['id']}/snooze", json={"days": 2})
    snoozed_until = datetime.fromisoformat(snoozed.json()["snoozed_until"]).replace(tzinfo=UTC)
    assert snoozed_until <= datetime.now(UTC) + timedelta(days=2)
    assert snoozed_until > datetime.now(UTC) + timedelta(days=1)


async def test_snooze_unknown_reminder_404(client: httpx.AsyncClient):
    response = await client.post("/api/v1/reminders/00000000-0000-0000-0000-000000000000/snooze", json={})
    assert response.status_code == 404


async def test_unsnooze_clears(client: httpx.AsyncClient, plant: Plant):
    reminder = (
        await client.post(f"/api/v1/plants/{plant.id}/reminders", json={"event_type": "watering", "interval_days": 7})
    ).json()
    await client.post(f"/api/v1/reminders/{reminder['id']}/snooze", json={})

    cleared = await client.delete(f"/api/v1/reminders/{reminder['id']}/snooze")
    assert cleared.status_code == 200
    assert cleared.json()["snoozed_until"] is None


async def test_reminder_list_due_at_reflects_snooze(
    client: httpx.AsyncClient, session: AsyncSession, plant: Plant, user: User
):
    reminder = (
        await client.post(f"/api/v1/plants/{plant.id}/reminders", json={"event_type": "watering", "interval_days": 7})
    ).json()
    watered_at = datetime.now(UTC) - timedelta(days=1)
    await add_care_log(session, plant.id, user.id, event_type="watering", logged_at=watered_at)

    # A snooze beyond the regular schedule wins.
    await client.post(f"/api/v1/reminders/{reminder['id']}/snooze", json={"days": 30})
    listed = (await client.get(f"/api/v1/plants/{plant.id}/reminders")).json()[0]
    due_at = datetime.fromisoformat(listed["due_at"]).replace(tzinfo=UTC)
    assert due_at > watered_at + timedelta(days=7)

    # A snooze earlier than the regular schedule leaves it untouched.
    await client.post(f"/api/v1/reminders/{reminder['id']}/snooze", json={"days": 2})
    listed = (await client.get(f"/api/v1/plants/{plant.id}/reminders")).json()[0]
    due_at = datetime.fromisoformat(listed["due_at"]).replace(tzinfo=UTC)
    assert due_at == watered_at + timedelta(days=7)
