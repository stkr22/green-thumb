"""OIDC client for the Zitadel authorization-code flow.

Endpoints come from OIDC discovery rather than hardcoded Zitadel paths so the
issuer can move (or be swapped for another provider) without code changes.
Discovery and JWKS responses are cached for an hour, mirroring the reference
project's JWKS client.
"""

import base64
import hashlib
import logging
import secrets
from datetime import timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import KeySet

from greenthumb.config import get_settings
from greenthumb.models.base import utcnow

logger = logging.getLogger(__name__)

_CACHE_TTL = timedelta(hours=1)
# Tolerated clock skew between us and the identity provider when validating exp/iat.
_CLOCK_SKEW_LEEWAY_SECONDS = 120


class OIDCError(Exception):
    """Raised when any step of the OIDC flow fails."""


class OIDCClient:
    """Performs discovery, the code exchange, and ID token validation."""

    def __init__(self) -> None:
        """Initialize with empty caches; nothing is fetched until first use."""
        self._discovery: dict[str, Any] | None = None
        self._discovery_fetched_at = None
        self._jwks: KeySet | None = None
        self._jwks_fetched_at = None

    async def _get_discovery(self) -> dict[str, Any]:
        """Fetch and cache the OIDC discovery document."""
        now = utcnow()
        if self._discovery and self._discovery_fetched_at and now - self._discovery_fetched_at < _CACHE_TTL:
            return self._discovery
        issuer = get_settings().OIDC_ISSUER_URL.rstrip("/")
        if not issuer:
            raise OIDCError("OIDC_ISSUER_URL is not configured")
        url = f"{issuer}/.well-known/openid-configuration"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise OIDCError(f"OIDC discovery failed: {e}") from e
        self._discovery = response.json()
        self._discovery_fetched_at = now
        return self._discovery

    async def _get_jwks(self) -> KeySet:
        """Fetch and cache the provider's signing keys."""
        now = utcnow()
        if self._jwks and self._jwks_fetched_at and now - self._jwks_fetched_at < _CACHE_TTL:
            return self._jwks
        discovery = await self._get_discovery()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(discovery["jwks_uri"], timeout=10.0)
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise OIDCError(f"JWKS fetch failed: {e}") from e
        self._jwks = KeySet.import_key_set(response.json())
        self._jwks_fetched_at = now
        return self._jwks

    async def build_authorization_url(self, state: str, nonce: str, code_challenge: str) -> str:
        """Build the Zitadel authorization URL for the code flow with PKCE."""
        settings = get_settings()
        discovery = await self._get_discovery()
        params = {
            "client_id": settings.OIDC_CLIENT_ID,
            "redirect_uri": settings.OIDC_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid profile email",
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{discovery['authorization_endpoint']}?{urlencode(params)}"

    async def exchange_code(self, code: str, code_verifier: str) -> dict[str, Any]:
        """Exchange the authorization code for tokens at the token endpoint."""
        settings = get_settings()
        discovery = await self._get_discovery()
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.OIDC_REDIRECT_URI,
            "client_id": settings.OIDC_CLIENT_ID,
            "client_secret": settings.OIDC_CLIENT_SECRET,
            "code_verifier": code_verifier,
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(discovery["token_endpoint"], data=data, timeout=10.0)
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise OIDCError(f"Token exchange failed: {e}") from e
        return response.json()

    async def validate_id_token(self, id_token: str, nonce: str) -> dict[str, Any]:
        """Verify the ID token signature and claims; return the validated claims."""
        settings = get_settings()
        keys = await self._get_jwks()
        try:
            decoded = jwt.decode(id_token, keys)
            registry = jwt.JWTClaimsRegistry(
                iss={"essential": True, "value": settings.OIDC_ISSUER_URL.rstrip("/")},
                sub={"essential": True},
                leeway=_CLOCK_SKEW_LEEWAY_SECONDS,
            )
            registry.validate(decoded.claims)
        except JoseError as e:
            raise OIDCError(f"ID token validation failed: {e}") from e
        claims = dict(decoded.claims)
        aud = claims.get("aud", [])
        aud_list = aud if isinstance(aud, list) else [aud]
        if settings.OIDC_CLIENT_ID not in aud_list:
            raise OIDCError("ID token audience does not include our client_id")
        if claims.get("nonce") != nonce:
            raise OIDCError("ID token nonce mismatch")
        return claims

    async def fetch_userinfo(self, access_token: str) -> dict[str, Any]:
        """Fetch userinfo claims; used when the ID token lacks email/name."""
        discovery = await self._get_discovery()
        userinfo_endpoint = discovery.get("userinfo_endpoint")
        if not userinfo_endpoint:
            return {}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    userinfo_endpoint, headers={"Authorization": f"Bearer {access_token}"}, timeout=10.0
                )
                response.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("userinfo fetch failed: %s", e)
            return {}
        return response.json()

    async def build_end_session_url(self) -> str:
        """Build the Zitadel logout URL, falling back to the frontend when unavailable."""
        settings = get_settings()
        try:
            discovery = await self._get_discovery()
        except OIDCError:
            return settings.FRONTEND_URL
        end_session = discovery.get("end_session_endpoint")
        if not end_session:
            return settings.FRONTEND_URL
        params = {"client_id": settings.OIDC_CLIENT_ID, "post_logout_redirect_uri": settings.FRONTEND_URL}
        return f"{end_session}?{urlencode(params)}"


def generate_pkce_pair() -> tuple[str, str]:
    """Return a (code_verifier, code_challenge) pair for PKCE S256."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


_client: OIDCClient | None = None


def get_oidc_client() -> OIDCClient:
    """Return the process-wide OIDC client (caches discovery/JWKS across requests)."""
    global _client  # noqa: PLW0603 - intentional lazy singleton
    if _client is None:
        _client = OIDCClient()
    return _client


def reset_oidc_client() -> None:
    """Drop the cached client (used by tests)."""
    global _client  # noqa: PLW0603 - intentional lazy singleton
    _client = None
