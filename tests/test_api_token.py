"""Bearer-token auth: an API token authenticates like a session cookie."""

import httpx
import pytest

from greenthumb.auth.session import create_api_token
from greenthumb.models import User


async def test_bearer_token_authenticates(anon_client: httpx.AsyncClient, user: User) -> None:
    token = create_api_token(user.id)
    response = await anon_client.get("/api/v1/plants", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


@pytest.mark.parametrize("header", ["Bearer not-a-real-token", "Bearer ", "Basic abc"])
async def test_invalid_bearer_rejected(anon_client: httpx.AsyncClient, header: str) -> None:
    response = await anon_client.get("/api/v1/plants", headers={"Authorization": header})
    assert response.status_code == 401
