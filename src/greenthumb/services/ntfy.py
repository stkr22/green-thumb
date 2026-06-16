"""ntfy push notification client.

Failures are logged but never raised to callers: a down ntfy instance must not
break care logging or the reminder loop.
"""

import logging

import httpx

from greenthumb.config import get_settings

logger = logging.getLogger(__name__)


async def send_notification(
    *,
    title: str,
    message: str,
    topic: str | None = None,
    priority: int = 3,
    tags: list[str] | None = None,
) -> bool:
    """Publish a notification; returns True when ntfy accepted it."""
    settings = get_settings()
    if not settings.NTFY_URL:
        logger.info("NTFY_URL not configured; dropping notification %r", title)
        return False
    payload = {
        "topic": topic or settings.NTFY_TOPIC,
        "title": title,
        "message": message,
        "priority": priority,
        "tags": tags or ["seedling"],
    }
    headers = {}
    if settings.NTFY_TOKEN:
        headers["Authorization"] = f"Bearer {settings.NTFY_TOKEN}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(settings.NTFY_URL, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("ntfy publish failed for %r: %s", title, e)
        return False
    return True
