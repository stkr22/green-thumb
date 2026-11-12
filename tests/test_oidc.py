"""ID token validation against a fake provider (discovery + JWKS over a mock transport)."""

import time
from typing import Any

import httpx
import pytest
from joserfc import jwt
from joserfc.jwk import Key, KeySet, OctKey, RSAKey

from greenthumb.auth import oidc
from greenthumb.config import get_settings

ISSUER = "https://idp.example"
CLIENT_ID = "green-thumb"
NONCE = "nonce-123"


class FakeProvider:
    """Serves discovery and a mutable JWKS; counts JWKS fetches."""

    def __init__(self) -> None:
        self.keys: list[Key] = [RSAKey.generate_key(2048, parameters={"kid": "k1"})]
        self.jwks_fetches = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/.well-known/openid-configuration":
            return httpx.Response(
                200, json={"jwks_uri": f"{ISSUER}/keys", "id_token_signing_alg_values_supported": ["RS256"]}
            )
        self.jwks_fetches += 1
        return httpx.Response(200, json=KeySet(self.keys).as_dict(private=False))


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> FakeProvider:
    fake = FakeProvider()
    transport = httpx.MockTransport(fake.handler)
    real_client = httpx.AsyncClient
    monkeypatch.setattr(oidc.httpx, "AsyncClient", lambda **kw: real_client(transport=transport, **kw))
    settings = get_settings()
    monkeypatch.setattr(settings, "OIDC_ISSUER_URL", ISSUER)
    monkeypatch.setattr(settings, "OIDC_CLIENT_ID", CLIENT_ID)
    return fake


def _claims(**overrides: Any) -> dict[str, Any]:
    now = int(time.time())
    claims = {"iss": ISSUER, "sub": "user-1", "aud": CLIENT_ID, "nonce": NONCE, "iat": now, "exp": now + 300}
    claims.update(overrides)
    return {k: v for k, v in claims.items() if v is not None}


def _sign(key: Key, **overrides: Any) -> str:
    return jwt.encode({"alg": "RS256", "kid": key.kid}, _claims(**overrides), key)


async def test_valid_token_returns_claims(provider: FakeProvider):
    claims = await oidc.OIDCClient().validate_id_token(_sign(provider.keys[0]), NONCE)
    assert claims["sub"] == "user-1"


@pytest.mark.parametrize(
    "overrides",
    [
        {"nonce": "replayed"},
        {"aud": "someone-else"},
        {"iss": "https://evil.example"},
        {"exp": None},
        {"iat": None},
        {"exp": int(time.time()) - 3600},
    ],
    ids=["nonce", "aud", "iss", "no-exp", "no-iat", "expired"],
)
async def test_bad_claims_are_rejected(provider: FakeProvider, overrides: dict[str, Any]):
    with pytest.raises(oidc.OIDCError):
        await oidc.OIDCClient().validate_id_token(_sign(provider.keys[0], **overrides), NONCE)


async def test_hmac_token_is_rejected(provider: FakeProvider):
    # Classic confusion attack: HS256 "signed" with a key the attacker knows.
    token = jwt.encode({"alg": "HS256", "kid": "k1"}, _claims(), OctKey.generate_key(256))
    with pytest.raises(oidc.OIDCError):
        await oidc.OIDCClient().validate_id_token(token, NONCE)


async def test_rotated_signing_key_is_picked_up(provider: FakeProvider):
    client = oidc.OIDCClient()
    await client.validate_id_token(_sign(provider.keys[0]), NONCE)
    # The provider rotates; its next token uses a kid our cached JWKS lacks.
    provider.keys = [RSAKey.generate_key(2048, parameters={"kid": "k2"})]
    # Step past the rate limit, as if the last fetch was a minute ago.
    assert client._jwks_fetched_at is not None
    client._jwks_fetched_at -= oidc._JWKS_MIN_REFRESH_INTERVAL
    claims = await client.validate_id_token(_sign(provider.keys[0]), NONCE)
    assert claims["sub"] == "user-1"
    assert provider.jwks_fetches == 2


async def test_unknown_kid_refetch_is_rate_limited(provider: FakeProvider):
    client = oidc.OIDCClient()
    stranger = RSAKey.generate_key(2048, parameters={"kid": "unknown"})
    for _ in range(3):
        with pytest.raises(oidc.OIDCError):
            await client.validate_id_token(_sign(stranger), NONCE)
    assert provider.jwks_fetches == 1
