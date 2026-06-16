"""Manual notification trigger for testing the ntfy pipeline end to end."""

from fastapi import APIRouter, HTTPException, status

from greenthumb.auth import CurrentUser
from greenthumb.services import ntfy

router = APIRouter(tags=["notifications"])


@router.post("/notifications/test")
async def send_test_notification(user: CurrentUser) -> dict[str, str]:
    """Send a test notification to the current user's effective topic."""
    delivered = await ntfy.send_notification(
        title="Green Thumb test notification",
        message=f"Hello {user.display_name}, your ntfy setup works!",
        topic=user.ntfy_topic_override,
    )
    if not delivered:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="ntfy did not accept the notification; check NTFY_URL and credentials",
        )
    return {"detail": "Notification sent"}
