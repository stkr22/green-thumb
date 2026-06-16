"""Server-side image processing for uploaded plant photos.

Phone cameras produce multi-megabyte 4K images, but the UI never needs that
resolution and the bytes live inline in the SQLite file (see models.photo), so
oversized originals would bloat both backups and page loads. Every upload is
therefore decoded once and re-encoded into two WebP variants:

- a *display* image bounded to a sane longest edge for the detail view, and
- a small *thumbnail* for grids and cards.

The original is intentionally discarded. WebP is chosen over JPEG for its better
ratio at equal quality and over AVIF for fast, dependency-free encoding via
Pillow; it is supported by every browser this app targets. EXIF is dropped as a
side effect of re-encoding, which both shrinks the file and strips embedded GPS.
"""

import io

from PIL import Image, ImageOps, UnidentifiedImageError

# Longest-edge caps. The display size comfortably fills the largest view while
# the thumbnail keeps list payloads tiny; both downscale only (never upscale).
DISPLAY_MAX_EDGE = 2048
THUMBNAIL_MAX_EDGE = 400

# WebP quality: 82 is visually lossless for photos; thumbnails tolerate more loss.
DISPLAY_QUALITY = 82
THUMBNAIL_QUALITY = 75

OUTPUT_MIME_TYPE = "image/webp"


class UnprocessableImageError(Exception):
    """Raised when the uploaded bytes cannot be decoded as an image."""


def _encode(image: Image.Image, max_edge: int, quality: int) -> bytes:
    """Downscale a copy of ``image`` to ``max_edge`` and encode it as WebP."""
    # thumbnail() mutates in place and never upscales, so work on a copy to keep
    # the source intact for the second variant.
    variant = image.copy()
    variant.thumbnail((max_edge, max_edge))
    buffer = io.BytesIO()
    variant.save(buffer, format="WEBP", quality=quality, method=6)
    return buffer.getvalue()


def process_upload(raw: bytes) -> tuple[bytes, bytes]:
    """Turn raw upload bytes into ``(display_webp, thumbnail_webp)``.

    Raises :class:`UnprocessableImageError` if the bytes are not a decodable
    image. CPU-bound (decode + two encodes), so callers should run it off the
    event loop.
    """
    try:
        with Image.open(io.BytesIO(raw)) as opened:
            # Bake in EXIF orientation before re-encoding strips the metadata,
            # otherwise portrait phone shots would display sideways.
            image = ImageOps.exif_transpose(opened)
            # Preserve alpha (PNG uploads) but flatten exotic modes (P, CMYK)
            # that WebP cannot encode directly.
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
            display = _encode(image, DISPLAY_MAX_EDGE, DISPLAY_QUALITY)
            thumbnail = _encode(image, THUMBNAIL_MAX_EDGE, THUMBNAIL_QUALITY)
    except (UnidentifiedImageError, OSError, ValueError) as e:
        raise UnprocessableImageError(str(e)) from e
    return display, thumbnail
