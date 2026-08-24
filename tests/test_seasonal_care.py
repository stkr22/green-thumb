"""Season plans end to end: materialization, evaluation, notification and the API surface.

These tests use plans whose four seasons carry the same value, so they assert
the same thing whatever today's real date is. The date-dependent maths (season
boundaries, accumulation across a boundary, hemispheres) is covered by
tests/test_seasons.py against fixed dates.
"""

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from greenthumb.models import Plant, Reminder, ScheduleKind, Species, User
from greenthumb.services import reminder_evaluator
from greenthumb.services.species import materialize_default_reminders
from tests.conftest import add_care_log

ALWAYS_DOUBLE: dict[str, float | None] = {"spring": 2.0, "summer": 2.0, "autumn": 2.0, "winter": 2.0}
ALWAYS_PAUSED: dict[str, float | None] = dict.fromkeys(("spring", "summer", "autumn", "winter"))


@pytest.fixture
async def species(session: AsyncSession, user: User) -> Species:
    """A species that waters every 7 days and pauses feeding all year."""
    entry = Species(
        name="Test Fern",
        default_intervals={"watering": 7, "fertilising": 30},
        season_plan={"watering": ALWAYS_DOUBLE, "fertilising": ALWAYS_PAUSED},
        created_by=user.id,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def _reminder(
    session: AsyncSession, plant: Plant, *, multipliers: dict, days_ago: float, event: str = "watering"
) -> Reminder:
    """A reminder with the given season plan and a care log this many days ago."""
    owner = plant.created_by
    reminder = Reminder(
        plant_id=plant.id, event_type=event, interval_days=7, season_multipliers=multipliers, created_by=owner
    )
    session.add(reminder)
    await add_care_log(
        session, plant.id, owner, event_type=event, logged_at=datetime.now(UTC) - timedelta(days=days_ago)
    )
    await session.commit()
    await session.refresh(reminder)
    return reminder


async def test_materialization_copies_the_season_plan(
    session: AsyncSession, plant: Plant, user: User, species: Species
):
    created = await materialize_default_reminders(session, plant, species, user.id)
    await session.commit()
    by_type = {reminder.event_type: reminder for reminder in created}
    assert by_type["watering"].season_multipliers == ALWAYS_DOUBLE
    assert by_type["fertilising"].season_multipliers == ALWAYS_PAUSED


async def test_materialized_plan_is_a_copy_not_a_reference(
    session: AsyncSession, plant: Plant, user: User, species: Species
):
    """Editing a species plan must not silently retune plants already created from it."""
    created = await materialize_default_reminders(session, plant, species, user.id)
    await session.commit()
    species.season_plan["watering"]["winter"] = 9.0
    assert created[0].season_multipliers["winter"] == 2.0


async def test_event_type_without_a_plan_entry_gets_no_multipliers(
    session: AsyncSession, plant: Plant, user: User, species: Species
):
    species.season_plan = {"watering": ALWAYS_DOUBLE}
    created = await materialize_default_reminders(session, plant, species, user.id)
    await session.commit()
    assert {r.event_type: r.season_multipliers for r in created}["fertilising"] == {}


async def test_plan_stretches_the_due_date(session: AsyncSession, plant: Plant, user: User):
    """A 7-day reminder at a 2.0 multiplier is not yet due 10 days after watering."""
    await _reminder(session, plant, multipliers=ALWAYS_DOUBLE, days_ago=10)
    statuses = await reminder_evaluator.compute_reminder_statuses(session)
    assert statuses[0].overdue is False
    assert statuses[0].effective_interval_days == 14


async def test_stretched_reminder_still_comes_due(session: AsyncSession, plant: Plant, user: User):
    await _reminder(session, plant, multipliers=ALWAYS_DOUBLE, days_ago=15)
    statuses = await reminder_evaluator.compute_reminder_statuses(session)
    assert statuses[0].overdue is True


async def test_unplanned_reminder_matches_the_plain_interval(session: AsyncSession, plant: Plant, user: User):
    """No season plan must behave exactly as before seasons existed."""
    await _reminder(session, plant, multipliers={}, days_ago=10)
    statuses = await reminder_evaluator.compute_reminder_statuses(session)
    assert statuses[0].overdue is True
    assert statuses[0].effective_interval_days == 7
    assert statuses[0].paused is False


async def test_paused_reminder_is_never_overdue(session: AsyncSession, plant: Plant, user: User):
    await _reminder(session, plant, multipliers=ALWAYS_PAUSED, days_ago=90, event="fertilising")
    statuses = await reminder_evaluator.compute_reminder_statuses(session)
    assert statuses[0].paused is True
    assert statuses[0].overdue is False
    assert statuses[0].effective_interval_days is None


async def test_paused_reminder_is_not_notified(
    session: AsyncSession, plant: Plant, user: User, monkeypatch: pytest.MonkeyPatch
):
    sent: list[dict] = []

    async def _fake_send(**kwargs) -> bool:
        sent.append(kwargs)
        return True

    monkeypatch.setattr(reminder_evaluator.ntfy, "send_notification", _fake_send)
    await _reminder(session, plant, multipliers=ALWAYS_PAUSED, days_ago=90, event="fertilising")
    assert await reminder_evaluator.evaluate_and_notify(session) == 0
    assert sent == []


async def test_paused_reminder_without_any_care_log_is_not_due(session: AsyncSession, plant: Plant, user: User):
    """A plant added mid-dormancy should not immediately ask to be fed."""
    reminder = Reminder(
        plant_id=plant.id,
        event_type="fertilising",
        interval_days=30,
        season_multipliers=ALWAYS_PAUSED,
        created_by=user.id,
    )
    session.add(reminder)
    await session.commit()
    statuses = await reminder_evaluator.compute_reminder_statuses(session)
    assert statuses[0].overdue is False
    assert statuses[0].paused is True


async def test_reminder_list_reports_pace_and_pause(client: httpx.AsyncClient, plant: Plant):
    created = await client.post(
        f"/api/v1/plants/{plant.id}/reminders",
        json={"event_type": "watering", "interval_days": 7, "season_multipliers": ALWAYS_DOUBLE},
    )
    assert created.status_code == 201
    assert created.json()["season_multipliers"] == ALWAYS_DOUBLE

    listed = (await client.get(f"/api/v1/plants/{plant.id}/reminders")).json()
    assert listed[0]["effective_interval_days"] == 14
    assert listed[0]["paused"] is False
    assert listed[0]["season"] in {"spring", "summer", "autumn", "winter"}


async def test_snooze_defers_by_the_seasonal_pace(client: httpx.AsyncClient, plant: Plant):
    """Snoozing a winter-slowed reminder defers by the slowed interval, not the base one."""
    reminder = (
        await client.post(
            f"/api/v1/plants/{plant.id}/reminders",
            json={"event_type": "watering", "interval_days": 7, "season_multipliers": ALWAYS_DOUBLE},
        )
    ).json()
    snoozed = (await client.post(f"/api/v1/reminders/{reminder['id']}/snooze", json={})).json()
    # SQLite hands timestamps back naive; compare in naive UTC as the API serves them.
    deferred_by = datetime.fromisoformat(snoozed["snoozed_until"]) - datetime.now(UTC).replace(tzinfo=None)
    assert timedelta(days=13) < deferred_by <= timedelta(days=14)


@pytest.mark.parametrize(
    "multipliers",
    [
        {"sprung": 1.0},
        {"winter": 0},
        {"winter": -2},
        {"winter": 50},
        {"winter": "slow"},
    ],
)
async def test_malformed_multipliers_are_rejected(client: httpx.AsyncClient, plant: Plant, multipliers: dict):
    response = await client.post(
        f"/api/v1/plants/{plant.id}/reminders",
        json={"event_type": "watering", "interval_days": 7, "season_multipliers": multipliers},
    )
    assert response.status_code == 422


async def test_species_round_trips_a_season_plan(client: httpx.AsyncClient):
    created = await client.post(
        "/api/v1/species",
        json={
            "name": "Echeveria",
            "default_intervals": {"watering": 10},
            "season_plan": {"watering": {"winter": 3.5}},
        },
    )
    assert created.status_code == 201
    assert created.json()["season_plan"] == {"watering": {"winter": 3.5}}


async def test_species_rejects_a_malformed_season_plan(client: httpx.AsyncClient):
    response = await client.post(
        "/api/v1/species",
        json={"name": "Broken", "season_plan": {"watering": {"january": 2.0}}},
    )
    assert response.status_code == 422


async def test_apply_season_plan_updates_existing_plants(
    client: httpx.AsyncClient, session: AsyncSession, user: User, species: Species
):
    """Plans are copied at creation, so an edited plan needs this explicit roll-out."""
    plant = Plant(name="Older Fern", species_id=species.id, created_by=user.id)
    session.add(plant)
    reminder = Reminder(plant_id=plant.id, event_type="watering", interval_days=7, created_by=user.id)
    session.add(reminder)
    await session.commit()

    response = await client.post(f"/api/v1/species/{species.id}/apply-season-plan")
    assert response.status_code == 200
    assert response.json()["reminders_updated"] == 1
    await session.refresh(reminder)
    assert reminder.season_multipliers == ALWAYS_DOUBLE


async def test_apply_season_plan_leaves_intervals_alone(
    client: httpx.AsyncClient, session: AsyncSession, user: User, species: Species
):
    plant = Plant(name="Tuned Fern", species_id=species.id, created_by=user.id)
    session.add(plant)
    reminder = Reminder(plant_id=plant.id, event_type="watering", interval_days=21, created_by=user.id)
    session.add(reminder)
    await session.commit()

    await client.post(f"/api/v1/species/{species.id}/apply-season-plan")
    await session.refresh(reminder)
    assert reminder.interval_days == 21


async def test_apply_season_plan_on_missing_species_is_404(client: httpx.AsyncClient):
    response = await client.post(f"/api/v1/species/{'0' * 8}-0000-0000-0000-000000000000/apply-season-plan")
    assert response.status_code == 404


async def test_season_endpoint_serves_presets_and_current_season(client: httpx.AsyncClient):
    body = (await client.get("/api/v1/seasons")).json()
    assert body["hemisphere"] in {"north", "south"}
    assert body["current_season"] in {"spring", "summer", "autumn", "winter"}
    keys = {preset["key"] for preset in body["presets"]}
    assert {"tropical", "standard", "succulent", "winter_grower"} == keys
    standard = next(p for p in body["presets"] if p["key"] == "standard")
    assert standard["plan"]["watering"]["winter"] == 2.0
    assert standard["plan"]["fertilising"]["winter"] is None


async def test_season_endpoint_serves_hemisphere_correct_window_months(client: httpx.AsyncClient):
    """The window editor offers "spring" as months, which differ by hemisphere."""
    body = (await client.get("/api/v1/seasons")).json()
    months = body["season_months"]
    assert set(months) == {"spring", "summer", "autumn", "winter"}
    expected_spring = [3, 5] if body["hemisphere"] == "north" else [9, 11]
    assert months["spring"] == expected_spring


async def test_season_endpoint_requires_auth(anon_client: httpx.AsyncClient):
    assert (await anon_client.get("/api/v1/seasons")).status_code == 401


# --- annual-window reminders -------------------------------------------------
#
# Whether a window is open depends on today's date, so these derive their months
# from the current one: ALL_YEAR is always open, and _closed_window() is always
# shut. The calendar maths itself is pinned to fixed dates in test_seasons.py.

ALL_YEAR = (1, 12)


def _closed_window() -> tuple[int, int]:
    """A two-month window starting next month, so it is always currently shut."""
    start = datetime.now(UTC).month % 12 + 1
    return start, start % 12 + 1


async def _window_reminder(
    session: AsyncSession, plant: Plant, *, window: tuple[int, int], interval_days: int, days_ago: float | None
) -> Reminder:
    owner = plant.created_by
    reminder = Reminder(
        plant_id=plant.id,
        event_type="repotting",
        interval_days=interval_days,
        schedule_kind=ScheduleKind.ANNUAL_WINDOW.value,
        window_start_month=window[0],
        window_end_month=window[1],
        created_by=owner,
    )
    session.add(reminder)
    if days_ago is not None:
        await add_care_log(
            session, plant.id, owner, event_type="repotting", logged_at=datetime.now(UTC) - timedelta(days=days_ago)
        )
    await session.commit()
    await session.refresh(reminder)
    return reminder


async def test_window_reminder_is_not_due_while_its_window_is_shut(session: AsyncSession, plant: Plant):
    start, _end = _closed_window()
    await _window_reminder(session, plant, window=(start, _end), interval_days=730, days_ago=800)
    statuses = await reminder_evaluator.compute_reminder_statuses(session)
    assert statuses[0].overdue is False
    assert statuses[0].due_at is not None
    assert statuses[0].due_at.month == start
    assert statuses[0].paused is False


async def test_window_reminder_is_due_once_its_window_is_open(session: AsyncSession, plant: Plant):
    await _window_reminder(session, plant, window=ALL_YEAR, interval_days=730, days_ago=800)
    statuses = await reminder_evaluator.compute_reminder_statuses(session)
    assert statuses[0].overdue is True


async def test_window_reminder_keeps_its_full_interval(session: AsyncSession, plant: Plant):
    """The window defers the due date; it must not stretch the interval the way a pause does."""
    await _window_reminder(session, plant, window=ALL_YEAR, interval_days=730, days_ago=100)
    statuses = await reminder_evaluator.compute_reminder_statuses(session)
    assert statuses[0].overdue is False
    assert statuses[0].effective_interval_days == 730


async def test_never_logged_window_reminder_waits_for_the_window(session: AsyncSession, plant: Plant):
    """A plant added out of season should not ask to be repotted straight away."""
    start, end = _closed_window()
    await _window_reminder(session, plant, window=(start, end), interval_days=730, days_ago=None)
    statuses = await reminder_evaluator.compute_reminder_statuses(session)
    assert statuses[0].overdue is False
    assert statuses[0].due_at is not None
    assert statuses[0].due_at.month == start


async def test_species_window_materializes_an_annual_window_reminder(
    session: AsyncSession, plant: Plant, user: User, species: Species
):
    species.default_intervals = {"repotting": 730}
    species.default_windows = {"repotting": [3, 5]}
    created = await materialize_default_reminders(session, plant, species, user.id)
    await session.commit()
    reminder = created[0]
    assert reminder.schedule_kind == ScheduleKind.ANNUAL_WINDOW
    assert (reminder.window_start_month, reminder.window_end_month) == (3, 5)
    # A window and a season pace mean different things; the window wins.
    assert reminder.season_multipliers == {}


async def test_apply_season_plan_also_rolls_out_windows(
    client: httpx.AsyncClient, session: AsyncSession, user: User, species: Species
):
    species.default_windows = {"repotting": [3, 5]}
    session.add(species)
    repot_plant = Plant(name="Repot me", species_id=species.id, created_by=user.id)
    session.add(repot_plant)
    reminder = Reminder(plant_id=repot_plant.id, event_type="repotting", interval_days=730, created_by=user.id)
    session.add(reminder)
    await session.commit()

    await client.post(f"/api/v1/species/{species.id}/apply-season-plan")
    await session.refresh(reminder)
    assert reminder.schedule_kind == ScheduleKind.ANNUAL_WINDOW
    assert (reminder.window_start_month, reminder.window_end_month) == (3, 5)


async def test_window_reminder_round_trips_through_the_api(client: httpx.AsyncClient, plant: Plant):
    created = await client.post(
        f"/api/v1/plants/{plant.id}/reminders",
        json={
            "event_type": "repotting",
            "interval_days": 730,
            "schedule_kind": "annual_window",
            "window_start_month": 3,
            "window_end_month": 5,
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["schedule_kind"] == "annual_window"
    assert (body["window_start_month"], body["window_end_month"]) == (3, 5)


@pytest.mark.parametrize(
    "payload",
    [
        # A window kind with no months would silently behave as a plain interval.
        {"schedule_kind": "annual_window"},
        {"schedule_kind": "annual_window", "window_start_month": 3},
        # Months without the window kind would be stored and ignored.
        {"window_start_month": 3, "window_end_month": 5},
        {"schedule_kind": "annual_window", "window_start_month": 0, "window_end_month": 5},
        {"schedule_kind": "annual_window", "window_start_month": 3, "window_end_month": 13},
        {"schedule_kind": "quarterly"},
    ],
)
async def test_malformed_window_payloads_are_rejected(client: httpx.AsyncClient, plant: Plant, payload: dict):
    response = await client.post(
        f"/api/v1/plants/{plant.id}/reminders",
        json={"event_type": "repotting", "interval_days": 730, **payload},
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "windows",
    [
        {"repotting": [3]},
        {"repotting": [3, 5, 7]},
        {"repotting": [0, 5]},
        {"repotting": [3, 13]},
        {"repotting": "spring"},
    ],
)
async def test_species_rejects_malformed_windows(client: httpx.AsyncClient, windows: dict):
    response = await client.post("/api/v1/species", json={"name": "Broken window", "default_windows": windows})
    assert response.status_code == 422
