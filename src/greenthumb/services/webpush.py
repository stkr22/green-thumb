"""Web Push sender (VAPID).

Like the ntfy client, failures are logged but never raised: an unreachable
push service must not break care logging or the reminder loop. The one
signal callers must act on is a permanently-gone subscription (the user
revoked permission or cleared site data), reported as GONE so the caller
can delete the row.
"""

import base64
import json
import logging
from enum import Enum
from functools import lru_cache

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid
from pywebpush import WebPushException, webpush
from starlette.concurrency import run_in_threadpool

from greenthumb.config import get_settings
from greenthumb.models import PushSubscription

logger = logging.getLogger(__name__)


class PushResult(Enum):
    """Outcome of a single push delivery attempt."""

    SENT = "sent"
    FAILED = "failed"
    GONE = "gone"


def is_configured() -> bool:
    """Web Push is on iff a VAPID private key is configured."""
    return bool(get_settings().VAPID_PRIVATE_KEY)


@lru_cache(maxsize=1)
def public_key() -> str | None:
    """Return the applicationServerKey for PushManager.subscribe().

    Derived from the private key so the pair can never drift apart in config.
    """
    settings = get_settings()
    if not settings.VAPID_PRIVATE_KEY:
        return None
    vapid = Vapid.from_string(settings.VAPID_PRIVATE_KEY)
    raw = vapid.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _send_sync(subscription: PushSubscription, payload: str) -> PushResult:
    settings = get_settings()
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.VAPID_SUBJECT},
        )
    except WebPushException as e:
        if e.response is not None and e.response.status_code in (404, 410):
            return PushResult.GONE
        logger.warning("web push delivery failed: %s", e)
        return PushResult.FAILED
    return PushResult.SENT


async def send_notification(subscription: PushSubscription, *, title: str, message: str) -> PushResult:
    """Deliver one notification to one subscription.

    pywebpush is sync HTTP, so it runs in the threadpool.
    """
    if not is_configured():
        return PushResult.FAILED
    payload = json.dumps({"title": title, "body": message})
    return await run_in_threadpool(_send_sync, subscription, payload)
