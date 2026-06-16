"""Plant CRUD, filtering, and cover photo tests."""

from datetime import UTC, datetime

import httpx
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from greenthumb.models import CareLog, Plant, PlantPhoto, Reminder, User
from tests.conftest import add_care_log


async def test_create_and_get_plant(client: httpx.AsyncClient):
    created = await client.post(
        "/api/v1/plants",
        json={"name": "Ficus", "scientific_name": "Ficus lyrata", "tags": ["indoor", "big"], "notes": "Window spot"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["tags"] == ["indoor", "big"]

    detail = await client.get(f"/api/v1/plants/{body['id']}")
    assert detail.status_code == 200
    assert detail.json()["last_events"] == {}


async def test_create_plant_with_unknown_location_fails(client: httpx.AsyncClient):
    response = await client.post(
        "/api/v1/plants", json={"name": "X", "location_id": "00000000-0000-0000-0000-000000000000"}
    )
    assert response.status_code == 400


async def test_list_plants_filters(client: httpx.AsyncClient, plant: Plant):
    await client.post("/api/v1/plants", json={"name": "Cactus", "species_name": "Echinopsis", "tags": ["desert"]})

    by_search = await client.get("/api/v1/plants", params={"search": "deliciosa"})
    assert [p["name"] for p in by_search.json()] == ["Monstera"]

    by_tag = await client.get("/api/v1/plants", params={"tag": "desert"})
    assert [p["name"] for p in by_tag.json()] == ["Cactus"]

    everything = await client.get("/api/v1/plants")
    assert len(everything.json()) == 2


async def test_list_plants_includes_last_watered(
    client: httpx.AsyncClient, session: AsyncSession, plant: Plant, user: User
):
    logged_at = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    await add_care_log(session, plant.id, user.id, logged_at=logged_at)

    listed = await client.get("/api/v1/plants")
    item = listed.json()[0]
    assert item["last_watered_at"].startswith("2026-06-01T12:00:00")


async def test_plant_detail_last_events(client: httpx.AsyncClient, session: AsyncSession, plant: Plant, user: User):
    await add_care_log(session, plant.id, user.id, event_type="watering")
    await add_care_log(session, plant.id, user.id, event_type="fertilising")

    detail = await client.get(f"/api/v1/plants/{plant.id}")
    assert set(detail.json()["last_events"]) == {"watering", "fertilising"}


async def test_patch_plant_updates_fields_and_timestamp(client: httpx.AsyncClient, plant: Plant):
    before = plant.updated_at
    patched = await client.patch(f"/api/v1/plants/{plant.id}", json={"name": "Monstera XXL", "tags": []})
    assert patched.status_code == 200
    body = patched.json()
    assert body["name"] == "Monstera XXL"
    assert body["tags"] == []
    assert datetime.fromisoformat(body["updated_at"]) >= before


async def test_delete_plant_cascades(client: httpx.AsyncClient, session: AsyncSession, plant: Plant, user: User):
    await add_care_log(session, plant.id, user.id)
    session.add(Reminder(plant_id=plant.id, event_type="watering", interval_days=7, created_by=user.id))
    session.add(
        PlantPhoto(plant_id=plant.id, data=b"img", thumbnail=b"thumb", mime_type="image/webp", uploaded_by=user.id)
    )
    await session.commit()

    assert (await client.delete(f"/api/v1/plants/{plant.id}")).status_code == 204
    for model in (CareLog, Reminder, PlantPhoto):
        assert (await session.exec(select(model))).all() == []


async def test_cover_photo_must_belong_to_plant(
    client: httpx.AsyncClient, session: AsyncSession, plant: Plant, user: User
):
    other = Plant(name="Other", created_by=user.id)
    session.add(other)
    await session.commit()
    photo = PlantPhoto(plant_id=other.id, data=b"img", thumbnail=b"thumb", mime_type="image/webp", uploaded_by=user.id)
    session.add(photo)
    await session.commit()

    rejected = await client.post(f"/api/v1/plants/{plant.id}/cover", json={"photo_id": str(photo.id)})
    assert rejected.status_code == 400

    accepted = await client.post(f"/api/v1/plants/{other.id}/cover", json={"photo_id": str(photo.id)})
    assert accepted.status_code == 200
    assert accepted.json()["cover_photo_id"] == str(photo.id)
