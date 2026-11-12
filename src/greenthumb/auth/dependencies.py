"""FastAPI dependencies for authentication."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlmodel.ext.asyncio.session import AsyncSession

from greenthumb.auth.session import SESSION_COOKIE_NAME, verify_session_token
from greenthumb.db import get_db
from greenthumb.models import User

SessionDep = Annotated[AsyncSession, Depends(get_db)]


# CSRF defence for cookie sessions. SameSite=Lax stops cross-site form posts,
# but not requests from sibling subdomains, and the body-less or multipart
# POSTs here would not trip a JSON content-type check either. Browsers only
# attach a custom header to a credentialed cross-origin request after a CORS
# preflight, which this app never approves, so its presence proves the request
# came from our own pages. Bearer-token clients are exempt: no browser sends
# those automatically.
CSRF_HEADER = "X-Requested-With"
_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _bearer_token(request: Request) -> str | None:
    """Extract the token from an `Authorization: Bearer <token>` header, if present."""
    header = request.headers.get("Authorization", "")
    return header.removeprefix("Bearer ") if header.startswith("Bearer ") else None


async def get_current_user(request: Request, session: SessionDep) -> User:
    """Resolve the current user from the session cookie or a Bearer token; 401 when absent or invalid."""
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    token = cookie or _bearer_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if cookie and request.method in _UNSAFE_METHODS and CSRF_HEADER not in request.headers:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing {CSRF_HEADER} header")
    user_id = verify_session_token(token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or invalid")
    user = await session.get(User, user_id)
    if user is None:
        # The cookie outlived the user record (e.g. database reset).
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
