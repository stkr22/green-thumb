"""Species CRUD and default-care materialization tests."""

import uuid

import httpx
from sqlmodel.ext.asyncio.session import AsyncSession

from greenthumb.models import Plant

MONSTERA = {
    "name": "Monstera",
    "scientific_name": "Monstera deliciosa",
    "light": "Bright indirect",
    "watering_hint": "Let the top few centimetres dry out",
    "deadheading": False,
    "toxicity": "Toxic to cats and dogs",
    "common_issues": "Spider mites: fine webbing under leaves",
    "default_intervals": {"watering": 7, "fertilising": 30},
}


async def test_species_crud_roundtrip(client: httpx.AsyncClient):
    created = await client.post("/api/v1/species", json=MONSTERA)
    assert created.status_code == 201
    species_id = created.json()["id"]
    assert created.json()["default_intervals"] == {"watering": 7, "fertilising": 30}

    listed = await client.get("/api/v1/species")
    assert listed.status_code == 200
    assert [item["name"] for item in listed.json()] == ["Monstera"]
    assert listed.json()[0]["plant_count"] == 0

    fetched = await client.get(f"/api/v1/species/{species_id}")
    assert fetched.status_code == 200
    assert fetched.json()["toxicity"] == "Toxic to cats and dogs"

    patched = await client.patch(f"/api/v1/species/{species_id}", json={"deadheading": True, "deadheading_hint": "X"})
    assert patched.status_code == 200
    assert patched.json()["deadheading"] is True

    deleted = await client.delete(f"/api/v1/species/{species_id}")
    assert deleted.status_code == 204
    assert (await client.get("/api/v1/species")).json() == []


async def test_species_search(client: httpx.AsyncClient):
    await client.post("/api/v1/species", json=MONSTERA)
    await client.post("/api/v1/species", json={"name": "Basil", "scientific_name": "Ocimum basilicum"})

    hits = await client.get("/api/v1/species", params={"search": "basilic"})
    assert [item["name"] for item in hits.json()] == ["Basil"]


async def test_species_rejects_bad_intervals(client: httpx.AsyncClient):
    response = await client.post("/api/v1/species", json={"name": "X", "default_intervals": {"watering": 0}})
    assert response.status_code == 422
    response = await client.post("/api/v1/species", json={"name": "X", "default_intervals": {"": 7}})
    assert response.status_code == 422


async def test_plant_create_with_species_materializes_reminders(client: httpx.AsyncClient):
    species = (await client.post("/api/v1/species", json=MONSTERA)).json()
    plant = (await client.post("/api/v1/plants", json={"name": "Kitchen Monstera", "species_id": species["id"]})).json()

    reminders = (await client.get(f"/api/v1/plants/{plant['id']}/reminders")).json()
    assert {(r["event_type"], r["interval_days"]) for r in reminders} == {("watering", 7), ("fertilising", 30)}

    counted = await client.get("/api/v1/species")
    assert counted.json()[0]["plant_count"] == 1


async def test_plant_create_rejects_unknown_species(client: httpx.AsyncClient):
    response = await client.post(
        "/api/v1/plants", json={"name": "X", "species_id": "00000000-0000-0000-0000-000000000000"}
    )
    assert response.status_code == 400


async def test_plant_detail_embeds_species(client: httpx.AsyncClient):
    species = (await client.post("/api/v1/species", json=MONSTERA)).json()
    plant = (await client.post("/api/v1/plants", json={"name": "Monsti", "species_id": species["id"]})).json()

    detail = (await client.get(f"/api/v1/plants/{plant['id']}")).json()
    assert detail["species"]["name"] == "Monstera"
    assert detail["species"]["watering_hint"] == MONSTERA["watering_hint"]


async def test_plant_list_resolves_species_display_name(client: httpx.AsyncClient):
    species = (await client.post("/api/v1/species", json=MONSTERA)).json()
    await client.post("/api/v1/plants", json={"name": "Linked", "species_id": species["id"]})
    await client.post("/api/v1/plants", json={"name": "Legacy", "species_name": "Basil"})

    by_name = {item["name"]: item for item in (await client.get("/api/v1/plants")).json()}
    assert by_name["Linked"]["species_display_name"] == "Monstera"
    assert by_name["Legacy"]["species_display_name"] == "Basil"


async def test_plant_search_matches_linked_species(client: httpx.AsyncClient):
    species = (await client.post("/api/v1/species", json=MONSTERA)).json()
    await client.post("/api/v1/plants", json={"name": "Fensterblatt", "species_id": species["id"]})
    await client.post("/api/v1/plants", json={"name": "Basil"})

    hits = await client.get("/api/v1/plants", params={"search": "deliciosa"})
    assert [item["name"] for item in hits.json()] == ["Fensterblatt"]


async def test_apply_species_defaults_skips_existing(client: httpx.AsyncClient):
    species = (await client.post("/api/v1/species", json=MONSTERA)).json()
    plant = (await client.post("/api/v1/plants", json={"name": "Old Monstera"})).json()
    # Tuned reminder created before the species is linked; must survive untouched.
    await client.post(f"/api/v1/plants/{plant['id']}/reminders", json={"event_type": "watering", "interval_days": 3})

    linked = await client.patch(f"/api/v1/plants/{plant['id']}", json={"species_id": species["id"]})
    assert linked.status_code == 200

    applied = await client.post(f"/api/v1/plants/{plant['id']}/apply-species-defaults")
    assert applied.status_code == 200
    assert [(r["event_type"], r["interval_days"]) for r in applied.json()] == [("fertilising", 30)]

    # Idempotent: a second call creates nothing.
    assert (await client.post(f"/api/v1/plants/{plant['id']}/apply-species-defaults")).json() == []

    reminders = (await client.get(f"/api/v1/plants/{plant['id']}/reminders")).json()
    assert {(r["event_type"], r["interval_days"]) for r in reminders} == {("watering", 3), ("fertilising", 30)}


async def test_apply_species_defaults_requires_species(client: httpx.AsyncClient):
    plant = (await client.post("/api/v1/plants", json={"name": "No species"})).json()
    response = await client.post(f"/api/v1/plants/{plant['id']}/apply-species-defaults")
    assert response.status_code == 400


async def test_species_delete_detaches_plants(client: httpx.AsyncClient, session: AsyncSession):
    species = (await client.post("/api/v1/species", json=MONSTERA)).json()
    plant = (await client.post("/api/v1/plants", json={"name": "Monsti", "species_id": species["id"]})).json()

    assert (await client.delete(f"/api/v1/species/{species['id']}")).status_code == 204
    refreshed = await session.get(Plant, uuid.UUID(plant["id"]))
    assert refreshed is not None
    assert refreshed.species_id is None
