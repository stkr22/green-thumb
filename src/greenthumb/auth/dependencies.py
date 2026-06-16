"""FastAPI dependencies for authentication."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlmodel.ext.asyncio.session import AsyncSession

from greenthumb.auth.session import SESSION_COOKIE_NAME, verify_session_token
from greenthumb.db import get_db
from greenthumb.models import User

SessionDep = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(request: Request, session: SessionDep) -> User:
    """Resolve the current user from the session cookie; 401 when absent or invalid."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user_id = verify_session_token(token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or invalid")
    user = await session.get(User, user_id)
    if user is None:
        # The cookie outlived the user record (e.g. database reset).
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
