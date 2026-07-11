"""Notification endpoints.

Web Push subscription management plus a manual test trigger that exercises
every channel the user has set up.
"""

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from greenthumb.auth import CurrentUser, SessionDep
from greenthumb.models import PushSubscription
from greenthumb.schemas import PushPublicKey, PushSubscriptionCreate, PushSubscriptionRead, PushUnsubscribe
from greenthumb.services import ntfy, webpush

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/push/public-key", response_model=PushPublicKey)
async def get_push_public_key(_user: CurrentUser) -> PushPublicKey:
    """VAPID public key for PushManager.subscribe(); null hides the push UI."""
    return PushPublicKey(key=webpush.public_key())


@router.post("/push/subscriptions", response_model=PushSubscriptionRead, status_code=status.HTTP_201_CREATED)
async def create_push_subscription(
    payload: PushSubscriptionCreate, session: SessionDep, user: CurrentUser
) -> PushSubscription:
    """Register (or re-register) this device's push subscription.

    Upserts on the endpoint: browsers rotate subscription details and a
    re-subscribe after clearing site data must not create duplicates.
    """
    subscription = (
        await session.exec(select(PushSubscription).where(PushSubscription.endpoint == payload.endpoint))
    ).first()
    if subscription is None:
        subscription = PushSubscription(
            user_id=user.id, endpoint=payload.endpoint, p256dh=payload.keys.p256dh, auth=payload.keys.auth
        )
    else:
        subscription.user_id = user.id
        subscription.p256dh = payload.keys.p256dh
        subscription.auth = payload.keys.auth
    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)
    return subscription


@router.post("/push/unsubscribe", status_code=status.HTTP_204_NO_CONTENT)
async def delete_push_subscription(payload: PushUnsubscribe, session: SessionDep, _user: CurrentUser) -> None:
    """Remove a subscription by endpoint (idempotent: unknown endpoints 204)."""
    subscription = (
        await session.exec(select(PushSubscription).where(PushSubscription.endpoint == payload.endpoint))
    ).first()
    if subscription is not None:
        await session.delete(subscription)
        await session.commit()


@router.post("/test")
async def send_test_notification(session: SessionDep, user: CurrentUser) -> dict[str, str]:
    """Send a test notification over every channel the user has configured."""
    delivered = 0
    if user.ntfy_enabled:
        delivered += int(
            await ntfy.send_notification(
                title="Green Thumb test notification",
                message=f"Hello {user.display_name}, your ntfy setup works!",
                topic=user.ntfy_topic_override,
            )
        )
    subscriptions = (await session.exec(select(PushSubscription).where(PushSubscription.user_id == user.id))).all()
    for subscription in subscriptions:
        result = await webpush.send_notification(
            subscription,
            title="Green Thumb test notification",
            message=f"Hello {user.display_name}, push notifications on this device work!",
        )
        if result is webpush.PushResult.GONE:
            await session.delete(subscription)
        delivered += int(result is webpush.PushResult.SENT)
    await session.commit()
    if not delivered:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No notification could be delivered; enable ntfy or subscribe this device to push first",
        )
    return {"detail": f"Sent {delivered} notification(s)"}
