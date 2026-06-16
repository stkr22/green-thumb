"""Dashboard summary tests."""

from datetime import UTC, datetime, timedelta

import httpx
from sqlmodel.ext.asyncio.session import AsyncSession

from greenthumb.models import Plant, Reminder, User
from tests.conftest import add_care_log


async def test_dashboard_empty(client: httpx.AsyncClient):
    response = await client.get("/api/v1/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "overdue": [],
        "upcoming": [],
        "recently_watered": [],
        "total_plants": 0,
        "total_locations": 0,
    }


async def test_dashboard_overdue_and_upcoming(
    client: httpx.AsyncClient, session: AsyncSession, plant: Plant, user: User
):
    now = datetime.now(UTC)
    other = Plant(name="Fern", created_by=user.id)
    session.add(other)
    await session.commit()

    # Monstera: watered 10 days ago with a 7-day interval -> overdue.
    session.add(Reminder(plant_id=plant.id, event_type="watering", interval_days=7, created_by=user.id))
    await add_care_log(session, plant.id, user.id, logged_at=now - timedelta(days=10))
    # Fern: watered yesterday with a 7-day interval -> due in 6 days (upcoming).
    session.add(Reminder(plant_id=other.id, event_type="watering", interval_days=7, created_by=user.id))
    await add_care_log(session, other.id, user.id, logged_at=now - timedelta(days=1))
    await session.commit()

    body = (await client.get("/api/v1/dashboard")).json()
    assert [item["plant_name"] for item in body["overdue"]] == ["Monstera"]
    assert [item["plant_name"] for item in body["upcoming"]] == ["Fern"]
    assert body["total_plants"] == 2
    # Latest watering per plant, newest first.
    assert [item["plant_name"] for item in body["recently_watered"]] == ["Fern", "Monstera"]


async def test_dashboard_reminder_without_log_is_overdue(
    client: httpx.AsyncClient, session: AsyncSession, plant: Plant, user: User
):
    session.add(Reminder(plant_id=plant.id, event_type="fertilising", interval_days=30, created_by=user.id))
    await session.commit()

    body = (await client.get("/api/v1/dashboard")).json()
    assert len(body["overdue"]) == 1
    assert body["overdue"][0]["last_event_at"] is None
    assert body["overdue"][0]["due_at"] is None


async def test_dashboard_disabled_reminders_are_ignored(
    client: httpx.AsyncClient, session: AsyncSession, plant: Plant, user: User
):
    session.add(Reminder(plant_id=plant.id, event_type="watering", interval_days=7, enabled=False, created_by=user.id))
    await session.commit()

    body = (await client.get("/api/v1/dashboard")).json()
    assert body["overdue"] == []
    assert body["upcoming"] == []


async def test_dashboard_upcoming_days_widens_horizon(
    client: httpx.AsyncClient, session: AsyncSession, plant: Plant, user: User
):
    now = datetime.now(UTC)
    # Due in 20 days: outside the default week, inside a 30-day calendar window.
    session.add(Reminder(plant_id=plant.id, event_type="watering", interval_days=21, created_by=user.id))
    await add_care_log(session, plant.id, user.id, logged_at=now - timedelta(days=1))
    await session.commit()

    default_window = (await client.get("/api/v1/dashboard")).json()
    assert default_window["upcoming"] == []
    month_window = (await client.get("/api/v1/dashboard", params={"upcoming_days": 30})).json()
    assert len(month_window["upcoming"]) == 1
