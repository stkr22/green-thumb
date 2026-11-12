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
from pywebpush import WebPushException, webpush_async

from greenthumb.config import get_settings
from greenthumb.models import PushSubscription

logger = logging.getLogger(__name__)

# A stalled push service must not hold up the reminder run (or shutdown).
_TIMEOUT_SECONDS = 10
# Push services drop a TTL=0 message unless the device is online right now; a
# sleeping phone would never see the daily digest. One day matches its cadence.
_TTL_SECONDS = 24 * 60 * 60


class PushResult(Enum):
    """Outcome of a single push delivery attempt."""

    SENT = "sent"
    FAILED = "failed"
    GONE = "gone"


def is_configured() -> bool:
    """Web Push is on iff a VAPID private key is configured."""
    return bool(get_settings().VAPID_PRIVATE_KEY.get_secret_value())


@lru_cache(maxsize=1)
def _vapid() -> Vapid | None:
    """Parse the VAPID key once instead of on every delivery."""
    private_key = get_settings().VAPID_PRIVATE_KEY.get_secret_value()
    return Vapid.from_string(private_key) if private_key else None


def public_key() -> str | None:
    """Return the applicationServerKey for PushManager.subscribe().

    Derived from the private key so the pair can never drift apart in config.
    """
    vapid = _vapid()
    if vapid is None:
        return None
    raw = vapid.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


async def send_notification(subscription: PushSubscription, *, title: str, message: str) -> PushResult:
    """Deliver one notification to one subscription."""
    vapid = _vapid()
    if vapid is None:
        return PushResult.FAILED
    try:
        await webpush_async(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=json.dumps({"title": title, "body": message}),
            vapid_private_key=vapid,
            vapid_claims={"sub": get_settings().VAPID_SUBJECT},
            timeout=_TIMEOUT_SECONDS,
            ttl=_TTL_SECONDS,
        )
    except WebPushException as e:
        if e.response is not None and e.response.status in (404, 410):
            return PushResult.GONE
        logger.warning("web push delivery failed: %s", e)
        return PushResult.FAILED
    except Exception:
        # Network errors and timeouts surface as aiohttp/asyncio exceptions, not
        # WebPushException; one unreachable endpoint must not abort the digest.
        logger.warning("web push delivery failed", exc_info=True)
        return PushResult.FAILED
    return PushResult.SENT
