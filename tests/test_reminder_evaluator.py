"""Reminder evaluation and notification dedup tests."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from greenthumb.models import Plant, Reminder, User
from greenthumb.services import reminder_evaluator
from tests.conftest import add_care_log


@pytest.fixture
def sent_notifications(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Capture ntfy payloads instead of doing HTTP."""
    captured: list[dict] = []

    async def _fake_send(**kwargs) -> bool:
        captured.append(kwargs)
        return True

    monkeypatch.setattr(reminder_evaluator.ntfy, "send_notification", _fake_send)
    return captured


async def _make_overdue_reminder(session: AsyncSession, plant: Plant, user: User) -> Reminder:
    """Watering reminder that is 3 days overdue."""
    reminder = Reminder(plant_id=plant.id, event_type="watering", interval_days=7, created_by=user.id)
    session.add(reminder)
    await add_care_log(session, plant.id, user.id, logged_at=datetime.now(UTC) - timedelta(days=10))
    await session.commit()
    await session.refresh(reminder)
    return reminder


async def test_no_recipients_means_no_notifications(
    session: AsyncSession, plant: Plant, user: User, sent_notifications: list[dict]
):
    user.ntfy_enabled = False
    session.add(user)
    await _make_overdue_reminder(session, plant, user)
    assert await reminder_evaluator.evaluate_and_notify(session) == 0
    assert sent_notifications == []


async def test_overdue_reminder_notifies_subscribed_users(
    session: AsyncSession, plant: Plant, user: User, sent_notifications: list[dict]
):
    user.ntfy_enabled = True
    user.ntfy_topic_override = "my-topic"
    session.add(user)
    reminder = await _make_overdue_reminder(session, plant, user)

    assert await reminder_evaluator.evaluate_and_notify(session) == 1
    assert len(sent_notifications) == 1
    payload = sent_notifications[0]
    assert payload["title"] == "🌱 1 plant care reminder"
    assert "Water Monstera (last watering 10 days ago)" in payload["message"]
    assert payload["topic"] == "my-topic"

    await session.refresh(reminder)
    assert reminder.last_notified_at is not None


async def test_renotification_is_throttled(
    session: AsyncSession, plant: Plant, user: User, sent_notifications: list[dict]
):
    user.ntfy_enabled = True
    session.add(user)
    await _make_overdue_reminder(session, plant, user)

    assert await reminder_evaluator.evaluate_and_notify(session) == 1
    # Immediately re-running must not notify again (interval_days / 2 backoff).
    assert await reminder_evaluator.evaluate_and_notify(session) == 0
    assert len(sent_notifications) == 1


async def test_renotifies_after_backoff_expires(
    session: AsyncSession, plant: Plant, user: User, sent_notifications: list[dict]
):
    user.ntfy_enabled = True
    session.add(user)
    reminder = await _make_overdue_reminder(session, plant, user)
    reminder.last_notified_at = datetime.now(UTC) - timedelta(days=4)  # > 7/2 days ago
    session.add(reminder)
    await session.commit()

    assert await reminder_evaluator.evaluate_and_notify(session) == 1


async def test_not_due_reminder_does_not_notify(
    session: AsyncSession, plant: Plant, user: User, sent_notifications: list[dict]
):
    user.ntfy_enabled = True
    session.add(user)
    reminder = Reminder(plant_id=plant.id, event_type="watering", interval_days=7, created_by=user.id)
    session.add(reminder)
    await add_care_log(session, plant.id, user.id, logged_at=datetime.now(UTC) - timedelta(days=1))
    await session.commit()

    assert await reminder_evaluator.evaluate_and_notify(session) == 0
    assert sent_notifications == []


async def test_multiple_overdue_reminders_batch_into_one_message(
    session: AsyncSession, plant: Plant, user: User, sent_notifications: list[dict]
):
    user.ntfy_enabled = True
    session.add(user)
    await _make_overdue_reminder(session, plant, user)  # watering on Monstera
    other = Plant(name="Fern", created_by=user.id)
    session.add(other)
    await session.commit()
    session.add(Reminder(plant_id=other.id, event_type="repotting", interval_days=365, created_by=user.id))
    await session.commit()

    # Two overdue reminders, but only a single digest notification is sent.
    assert await reminder_evaluator.evaluate_and_notify(session) == 1
    assert len(sent_notifications) == 1
    message = sent_notifications[0]["message"]
    assert "Water Monstera" in message
    assert "Repot Fern" in message


async def test_reminder_without_any_log_notifies(
    session: AsyncSession, plant: Plant, user: User, sent_notifications: list[dict]
):
    user.ntfy_enabled = True
    session.add(user)
    session.add(Reminder(plant_id=plant.id, event_type="repotting", interval_days=365, created_by=user.id))
    await session.commit()

    assert await reminder_evaluator.evaluate_and_notify(session) == 1
    assert "Repot Monstera (no repotting recorded yet)" in sent_notifications[0]["message"]
