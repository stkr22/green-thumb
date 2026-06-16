"""Photo upload, serving, and deletion tests."""

import io
import uuid

import httpx
from PIL import Image
from sqlmodel.ext.asyncio.session import AsyncSession

from greenthumb.models import Plant


def _png_bytes(size: tuple[int, int] = (1200, 900)) -> bytes:
    """Render a real PNG so the upload pipeline has something to decode."""
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(34, 139, 34)).save(buffer, format="PNG")
    return buffer.getvalue()


async def _upload(client: httpx.AsyncClient, plant_id, content=None, mime="image/png"):
    content = _png_bytes() if content is None else content
    return await client.post(f"/api/v1/plants/{plant_id}/photos", files={"file": ("photo.png", content, mime)})


async def test_upload_and_serve_photo(client: httpx.AsyncClient, plant: Plant):
    uploaded = await _upload(client, plant.id)
    assert uploaded.status_code == 201
    photo_id = uploaded.json()["id"]
    # Uploads are re-encoded to WebP regardless of the source format.
    assert uploaded.json()["mime_type"] == "image/webp"

    served = await client.get(f"/api/v1/photos/{photo_id}")
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/webp"
    display = Image.open(io.BytesIO(served.content))
    assert display.format == "WEBP"

    thumb = await client.get(f"/api/v1/photos/{photo_id}/thumb")
    assert thumb.status_code == 200
    assert thumb.headers["content-type"] == "image/webp"
    # The thumbnail is downscaled, so it must be smaller than the display image.
    assert max(Image.open(io.BytesIO(thumb.content)).size) <= 400
    assert len(thumb.content) < len(served.content)

    listed = await client.get(f"/api/v1/plants/{plant.id}/photos")
    assert [item["id"] for item in listed.json()] == [photo_id]
    assert "data" not in listed.json()[0]


async def test_thumbnail_missing_photo_returns_404(client: httpx.AsyncClient, plant: Plant):
    response = await client.get(f"/api/v1/photos/{uuid.uuid4()}/thumb")
    assert response.status_code == 404


async def test_upload_rejects_non_image(client: httpx.AsyncClient, plant: Plant):
    response = await _upload(client, plant.id, content=b"%PDF-1.4", mime="application/pdf")
    assert response.status_code == 400


async def test_upload_rejects_undecodable_image(client: httpx.AsyncClient, plant: Plant):
    # Correct MIME prefix but the bytes are not a real image: must fail to decode.
    response = await _upload(client, plant.id, content=b"not-an-image", mime="image/png")
    assert response.status_code == 400


async def test_upload_rejects_empty_file(client: httpx.AsyncClient, plant: Plant):
    response = await _upload(client, plant.id, content=b"")
    assert response.status_code == 400


async def test_delete_photo_clears_cover(client: httpx.AsyncClient, session: AsyncSession, plant: Plant):
    photo_id = (await _upload(client, plant.id)).json()["id"]
    await client.post(f"/api/v1/plants/{plant.id}/cover", json={"photo_id": photo_id})

    assert (await client.delete(f"/api/v1/photos/{photo_id}")).status_code == 204
    await session.refresh(plant)
    assert plant.cover_photo_id is None
    assert (await client.get(f"/api/v1/photos/{photo_id}")).status_code == 404
