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
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

# Longest-edge caps. The display size comfortably fills the largest view while
# the thumbnail keeps list payloads tiny; both downscale only (never upscale).
DISPLAY_MAX_EDGE = 2048
THUMBNAIL_MAX_EDGE = 400

# WebP quality: 82 is visually lossless for photos; thumbnails tolerate more loss.
DISPLAY_QUALITY = 82
THUMBNAIL_QUALITY = 75

OUTPUT_MIME_TYPE = "image/webp"

# Phone photos are ~12-50 MP. Pillow's default ceiling (~89 MP warns, ~179 MP
# errors) would let a crafted file decode to ~700 MB of RGBA on a small pod.
_MAX_PIXELS = 64_000_000
# Only what cameras and browsers produce; keeps exotic decoders off the attack surface.
_ACCEPTED_FORMATS = ("JPEG", "PNG", "WEBP", "GIF", "AVIF")


class UnprocessableImageError(Exception):
    """Raised when the uploaded bytes cannot be decoded as an image."""


def _encode(image: Image.Image, quality: int) -> bytes:
    buffer = io.BytesIO()
    # method=4 (the default speed/size tradeoff) is several times faster than 6
    # for a few percent larger files, which matters on a CPU-limited pod.
    image.save(buffer, format="WEBP", quality=quality, method=4)
    return buffer.getvalue()


def process_upload(raw: bytes) -> tuple[bytes, bytes]:
    """Turn raw upload bytes into ``(display_webp, thumbnail_webp)``.

    Raises :class:`UnprocessableImageError` if the bytes are not a decodable
    image. CPU-bound (decode + two encodes), so callers should run it off the
    event loop.
    """
    try:
        with warnings.catch_warnings():
            # Promote Pillow's "suspiciously large" warning to an error.
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw), formats=_ACCEPTED_FORMATS) as opened:
                if opened.width * opened.height > _MAX_PIXELS:
                    raise UnprocessableImageError("image has too many pixels")
                # JPEG can decode at 1/2, 1/4 or 1/8 scale for free; skip
                # decoding pixels the downscale would throw away anyway.
                opened.draft("RGB", (DISPLAY_MAX_EDGE, DISPLAY_MAX_EDGE))
                # Bake in EXIF orientation before re-encoding strips the metadata,
                # otherwise portrait phone shots would display sideways.
                image = ImageOps.exif_transpose(opened)
                # Preserve alpha (PNG uploads) but flatten exotic modes (P, CMYK)
                # that WebP cannot encode directly.
                if image.mode not in ("RGB", "RGBA"):
                    image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
                # thumbnail() downscales in place and never upscales; deriving the
                # small variant from the display one avoids a second full-size pass.
                image.thumbnail((DISPLAY_MAX_EDGE, DISPLAY_MAX_EDGE))
                display = _encode(image, DISPLAY_QUALITY)
                image.thumbnail((THUMBNAIL_MAX_EDGE, THUMBNAIL_MAX_EDGE))
                thumbnail = _encode(image, THUMBNAIL_QUALITY)
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as e:
        raise UnprocessableImageError(str(e)) from e
    return display, thumbnail
