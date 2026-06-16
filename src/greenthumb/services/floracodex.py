"""FloraCodex species lookup.

The API key is optional: without it every function degrades to an empty result
so the rest of the app keeps working (species fields stay user-supplied).
Responses are parsed defensively because FloraCodex's schema is not under our
control.
"""

import logging
from typing import Any

import httpx

from greenthumb.config import get_settings
from greenthumb.schemas import SpeciesSearchResult

logger = logging.getLogger(__name__)

# Keys worth persisting on the plant for care-threshold display; the full
# species payload is large and mostly irrelevant.
_DETAIL_KEYS = ("common_name", "scientific_name", "image_url", "growth", "specifications")


def _parse_search_item(item: dict[str, Any]) -> SpeciesSearchResult | None:
    """Map one FloraCodex search hit onto our schema; None when unusable."""
    pid = item.get("id") or item.get("pid") or item.get("slug")
    name = item.get("common_name") or item.get("scientific_name")
    if pid is None or not name:
        return None
    return SpeciesSearchResult(
        pid=str(pid),
        name=str(name),
        scientific_name=item.get("scientific_name"),
        image_url=item.get("image_url"),
    )


async def search_species(query: str) -> list[SpeciesSearchResult]:
    """Search FloraCodex species; empty list when no key is configured or on errors."""
    settings = get_settings()
    if not settings.FLORACODEX_API_KEY:
        return []
    url = f"{settings.FLORACODEX_BASE_URL.rstrip('/')}/v1/species/search"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params={"q": query, "key": settings.FLORACODEX_API_KEY}, timeout=10.0)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("FloraCodex search failed for %r: %s", query, e)
        return []
    items = payload.get("data", []) if isinstance(payload, dict) else []
    return [result for item in items if isinstance(item, dict) and (result := _parse_search_item(item))]


async def fetch_species_detail(pid: str) -> dict[str, Any] | None:
    """Fetch care-relevant species details for a FloraCodex id; None when unavailable."""
    settings = get_settings()
    if not settings.FLORACODEX_API_KEY:
        return None
    url = f"{settings.FLORACODEX_BASE_URL.rstrip('/')}/v1/species/{pid}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params={"key": settings.FLORACODEX_API_KEY}, timeout=10.0)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("FloraCodex detail fetch failed for %r: %s", pid, e)
        return None
    data = payload.get("data", payload) if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return None
    return {key: data[key] for key in _DETAIL_KEYS if key in data}
