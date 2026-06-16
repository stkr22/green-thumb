"""Auth routes: OIDC login/callback/logout plus the current-user profile endpoints.

Mounted at /auth (not /api/v1) because Traefik routes /auth/* to the backend and
the OIDC redirect URI points here.
"""

import logging
import secrets

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlmodel import select

from greenthumb.auth.dependencies import CurrentUser, SessionDep
from greenthumb.auth.oidc import OIDCError, generate_pkce_pair, get_oidc_client
from greenthumb.auth.session import (
    FLOW_COOKIE_NAME,
    FLOW_TOKEN_MAX_AGE_SECONDS,
    SESSION_COOKIE_NAME,
    create_flow_token,
    create_session_token,
    verify_flow_token,
)
from greenthumb.config import get_settings
from greenthumb.models import User
from greenthumb.schemas import UserRead, UserUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login() -> RedirectResponse:
    """Start the OIDC flow: stash state/nonce/PKCE in a signed cookie, redirect to Zitadel."""
    settings = get_settings()
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    code_verifier, code_challenge = generate_pkce_pair()
    try:
        authorization_url = await get_oidc_client().build_authorization_url(state, nonce, code_challenge)
    except OIDCError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    response = RedirectResponse(authorization_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        FLOW_COOKIE_NAME,
        create_flow_token(state, nonce, code_verifier),
        max_age=FLOW_TOKEN_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/auth",
    )
    return response


DEV_AUTH_SUB = "demo|local"


@router.get("/dev-login")
async def dev_login(session: SessionDep) -> RedirectResponse:
    """Local-only: provision a demo user and set a session cookie, bypassing OIDC.

    Guarded by DEV_AUTH_BYPASS; returns 404 when disabled so the route is inert
    in any real deployment. Reuses a fixed oidc_sub so seeded demo data attaches
    to this user.
    """
    settings = get_settings()
    if not settings.DEV_AUTH_BYPASS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    user = (await session.exec(select(User).where(User.oidc_sub == DEV_AUTH_SUB))).first()
    if user is None:
        user = User(oidc_sub=DEV_AUTH_SUB, email=settings.DEV_AUTH_EMAIL, display_name=settings.DEV_AUTH_DISPLAY_NAME)
        session.add(user)
        await session.commit()
        await session.refresh(user)

    response = RedirectResponse(settings.FRONTEND_URL, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        create_session_token(user.id),
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/callback")
async def callback(request: Request, session: SessionDep) -> RedirectResponse:
    """Finish the OIDC flow: validate state, exchange the code, upsert the user, set the session."""
    settings = get_settings()
    if error := request.query_params.get("error"):
        description = request.query_params.get("error_description", "")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"OIDC error: {error} {description}")

    code = request.query_params.get("code")
    state = request.query_params.get("state")
    flow_cookie = request.cookies.get(FLOW_COOKIE_NAME)
    flow = verify_flow_token(flow_cookie) if flow_cookie else None
    if not code or not state or flow is None or flow.get("state") != state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired login attempt")

    client = get_oidc_client()
    try:
        tokens = await client.exchange_code(code, flow["code_verifier"])
        id_token = tokens.get("id_token")
        if not id_token:
            raise OIDCError("Token response did not include an id_token")
        claims = await client.validate_id_token(id_token, flow["nonce"])
    except OIDCError as e:
        logger.warning("OIDC callback failed: %s", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed") from e

    email = claims.get("email")
    display_name = claims.get("name") or claims.get("preferred_username")
    if (not email or not display_name) and tokens.get("access_token"):
        # Zitadel only embeds profile claims in the ID token when configured to;
        # fall back to the userinfo endpoint like the reference project does.
        userinfo = await client.fetch_userinfo(tokens["access_token"])
        email = email or userinfo.get("email")
        display_name = display_name or userinfo.get("name") or userinfo.get("preferred_username")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not determine email; ensure the 'email' scope is granted",
        )

    oidc_sub = str(claims["sub"])
    user = (await session.exec(select(User).where(User.oidc_sub == oidc_sub))).first()
    if user is None:
        user = User(oidc_sub=oidc_sub, email=email, display_name=display_name or email)
        session.add(user)
        logger.info("Provisioned new user for sub=%s", oidc_sub)
    else:
        # Keep identity fields in sync with the IdP on every login.
        user.email = email
        user.display_name = display_name or email
    await session.commit()
    await session.refresh(user)

    response = RedirectResponse(settings.FRONTEND_URL, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        create_session_token(user.id),
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    response.delete_cookie(FLOW_COOKIE_NAME, path="/auth")
    return response


@router.get("/logout")
async def logout() -> RedirectResponse:
    """Clear the session cookie and send the browser to Zitadel's end-session endpoint."""
    response = RedirectResponse(await get_oidc_client().build_end_session_url(), status_code=status.HTTP_302_FOUND)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return response


@router.get("/me", response_model=UserRead)
async def read_me(current_user: CurrentUser) -> User:
    """Return the current user's profile and notification preferences."""
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_me(payload: UserUpdate, current_user: CurrentUser, session: SessionDep) -> User:
    """Update notification preferences (the only user-editable fields)."""
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(current_user, field, value)
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    return current_user
