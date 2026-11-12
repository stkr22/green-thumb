"""PATCH semantics shared by every resource: omitted keeps, null clears or is rejected."""

import httpx
import pytest

from greenthumb.models import Plant


async def _targets(client: httpx.AsyncClient, plant: Plant) -> dict[str, str]:
    location = (await client.post("/api/v1/locations", json={"name": "Hall"})).json()
    species = (await client.post("/api/v1/species", json={"name": "Fern"})).json()
    reminder = (
        await client.post(f"/api/v1/plants/{plant.id}/reminders", json={"event_type": "watering", "interval_days": 7})
    ).json()
    return {
        "plant": f"/api/v1/plants/{plant.id}",
        "location": f"/api/v1/locations/{location['id']}",
        "species": f"/api/v1/species/{species['id']}",
        "reminder": f"/api/v1/reminders/{reminder['id']}",
        "me": "/auth/me",
    }


# Every field backed by a NOT NULL column: null must be a validation error, not
# an IntegrityError (500) from the database.
NOT_NULL_FIELDS = [
    ("plant", "name"),
    ("plant", "tags"),
    ("location", "name"),
    ("species", "name"),
    ("species", "deadheading"),
    ("species", "default_intervals"),
    ("species", "season_plan"),
    ("species", "default_windows"),
    ("reminder", "event_type"),
    ("reminder", "interval_days"),
    ("reminder", "season_multipliers"),
    ("reminder", "schedule_kind"),
    ("reminder", "enabled"),
    ("me", "ntfy_enabled"),
]


@pytest.mark.parametrize(("target", "field"), NOT_NULL_FIELDS)
async def test_null_for_required_column_is_rejected(client: httpx.AsyncClient, plant: Plant, target: str, field: str):
    url = (await _targets(client, plant))[target]
    response = await client.patch(url, json={field: None})
    assert response.status_code == 422, response.text


async def test_null_clears_nullable_column(client: httpx.AsyncClient, plant: Plant):
    response = await client.patch(f"/api/v1/plants/{plant.id}", json={"species_name": None})
    assert response.status_code == 200
    assert response.json()["species_name"] is None
    assert response.json()["name"] == "Monstera"  # omitted field untouched
