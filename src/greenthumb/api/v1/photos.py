"""Photo routes: metadata listing, upload, raw serving, and deletion."""

import uuid

from fastapi import APIRouter, HTTPException, Response, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlmodel import col, select, update

from greenthumb.api.v1.deps import get_plant_or_404
from greenthumb.auth import CurrentUser, SessionDep
from greenthumb.models import Plant, PlantPhoto
from greenthumb.schemas import PhotoRead
from greenthumb.services.images import UnprocessableImageError, process_upload

router = APIRouter(tags=["photos"])

# Generous for the raw upload; the stored image is downscaled well below this.
MAX_PHOTO_BYTES = 15 * 1024 * 1024
_ALLOWED_MIME_PREFIX = "image/"


@router.get("/plants/{plant_id}/photos", response_model=list[PhotoRead])
async def list_photos(plant_id: uuid.UUID, session: SessionDep, _user: CurrentUser) -> list[PlantPhoto]:
    """List photo metadata for a plant (bytes are served by GET /photos/{id})."""
    await get_plant_or_404(session, plant_id)
    statement = select(PlantPhoto).where(PlantPhoto.plant_id == plant_id).order_by(col(PlantPhoto.uploaded_at).desc())
    return list((await session.exec(statement)).all())


@router.post("/plants/{plant_id}/photos", response_model=PhotoRead, status_code=status.HTTP_201_CREATED)
async def upload_photo(plant_id: uuid.UUID, file: UploadFile, session: SessionDep, user: CurrentUser) -> PlantPhoto:
    """Upload a photo (multipart/form-data) and store it as bytea."""
    await get_plant_or_404(session, plant_id)
    mime_type = file.content_type or ""
    if not mime_type.startswith(_ALLOWED_MIME_PREFIX):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only image uploads are allowed")
    data = await file.read()
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Photo exceeds the {MAX_PHOTO_BYTES // (1024 * 1024)} MB limit",
        )
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty upload")
    # Decode + downscale + re-encode off the event loop; this is CPU-bound and the
    # backend is single-instance, so a blocking call would stall other requests.
    try:
        display, thumbnail = await run_in_threadpool(process_upload, data)
    except UnprocessableImageError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Could not process the uploaded image"
        ) from None
    photo = PlantPhoto(
        plant_id=plant_id, data=display, thumbnail=thumbnail, mime_type="image/webp", uploaded_by=user.id
    )
    session.add(photo)
    await session.commit()
    await session.refresh(photo)
    return photo


# Photos are immutable once uploaded, so browsers may cache them aggressively.
_IMMUTABLE_CACHE = {"Cache-Control": "private, max-age=86400, immutable"}


@router.get("/photos/{photo_id}")
async def serve_photo(photo_id: uuid.UUID, session: SessionDep, _user: CurrentUser) -> Response:
    """Serve the display-sized photo bytes with the stored Content-Type."""
    photo = await session.get(PlantPhoto, photo_id)
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")
    return Response(content=photo.data, media_type=photo.mime_type, headers=_IMMUTABLE_CACHE)


@router.get("/photos/{photo_id}/thumb")
async def serve_photo_thumbnail(photo_id: uuid.UUID, session: SessionDep, _user: CurrentUser) -> Response:
    """Serve the small thumbnail variant for grids and cards."""
    photo = await session.get(PlantPhoto, photo_id)
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")
    return Response(content=photo.thumbnail, media_type=photo.mime_type, headers=_IMMUTABLE_CACHE)


@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(photo_id: uuid.UUID, session: SessionDep, _user: CurrentUser) -> None:
    """Delete a photo, clearing it as cover photo where referenced."""
    photo = await session.get(PlantPhoto, photo_id)
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")
    # Explicit instead of relying on ON DELETE SET NULL so behaviour is
    # identical on the SQLite test backend.
    await session.exec(  # type: ignore[call-overload]
        update(Plant).where(col(Plant.cover_photo_id) == photo_id).values(cover_photo_id=None)
    )
    await session.delete(photo)
    await session.commit()
