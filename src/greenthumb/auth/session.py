"""Signed-cookie session tokens.

Sessions are stateless HS256 JWTs signed with SESSION_SECRET_KEY, so no session
table or cache is needed. Two token kinds exist: the long-lived login session
and a short-lived token that carries OIDC flow state (state/nonce/PKCE verifier)
across the redirect to Zitadel.
"""

import logging
import uuid
from datetime import timedelta
from functools import lru_cache
from typing import Any

from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import OctKey

from greenthumb.config import get_settings
from greenthumb.models.base import utcnow

logger = logging.getLogger(__name__)

SESSION_COOKIE_NAME = "greenthumb_session"
FLOW_COOKIE_NAME = "greenthumb_oidc_flow"
# The OIDC round trip to Zitadel should complete well within this window.
FLOW_TOKEN_MAX_AGE_SECONDS = 600

_ALGORITHM = "HS256"
_PURPOSE_SESSION = "session"
_PURPOSE_FLOW = "oidc-flow"

# API tokens are ordinary session tokens with a long life, sent via the
# Authorization header instead of a cookie. They are stateless, so individual
# tokens cannot be revoked — rotate SESSION_SECRET_KEY to invalidate all of them.
API_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 90


@lru_cache(maxsize=1)
def _signing_key() -> OctKey:
    """Return the symmetric signing key derived from SESSION_SECRET_KEY."""
    secret = get_settings().SESSION_SECRET_KEY
    if not secret:
        raise RuntimeError("SESSION_SECRET_KEY is not configured")
    return OctKey.import_key(secret)


def _encode(claims: dict[str, Any], max_age_seconds: int) -> str:
    """Sign claims with an expiry relative to now."""
    now = utcnow()
    claims = {**claims, "iat": int(now.timestamp()), "exp": int((now + timedelta(seconds=max_age_seconds)).timestamp())}
    return jwt.encode({"alg": _ALGORITHM}, claims, _signing_key())


def _decode(token: str, expected_purpose: str) -> dict[str, Any] | None:
    """Verify signature, expiry and purpose; return claims or None when invalid."""
    try:
        decoded = jwt.decode(token, _signing_key(), algorithms=[_ALGORITHM])
        jwt.JWTClaimsRegistry(exp={"essential": True}).validate(decoded.claims)
    except JoseError:
        logger.debug("Rejected invalid or expired %s token", expected_purpose)
        return None
    claims = dict(decoded.claims)
    if claims.get("purpose") != expected_purpose:
        return None
    return claims


def create_session_token(user_id: uuid.UUID) -> str:
    """Create the login session token stored in the session cookie."""
    return _encode({"sub": str(user_id), "purpose": _PURPOSE_SESSION}, get_settings().SESSION_MAX_AGE_SECONDS)


def create_api_token(user_id: uuid.UUID) -> str:
    """Mint a long-lived token for headless API access; verified like a session token."""
    return _encode({"sub": str(user_id), "purpose": _PURPOSE_SESSION}, API_TOKEN_MAX_AGE_SECONDS)


def verify_session_token(token: str) -> uuid.UUID | None:
    """Return the user id from a valid session token, or None."""
    claims = _decode(token, _PURPOSE_SESSION)
    if claims is None:
        return None
    try:
        return uuid.UUID(str(claims.get("sub")))
    except ValueError:
        return None


def create_flow_token(state: str, nonce: str, code_verifier: str) -> str:
    """Create the short-lived token carrying CSRF state and the PKCE verifier."""
    claims = {"purpose": _PURPOSE_FLOW, "state": state, "nonce": nonce, "code_verifier": code_verifier}
    return _encode(claims, FLOW_TOKEN_MAX_AGE_SECONDS)


def verify_flow_token(token: str) -> dict[str, str] | None:
    """Return the OIDC flow state from a valid flow token, or None."""
    claims = _decode(token, _PURPOSE_FLOW)
    if claims is None:
        return None
    return {k: str(claims[k]) for k in ("state", "nonce", "code_verifier") if k in claims}
