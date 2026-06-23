"""Mint a long-lived API token for a user, identified by email.

Usage: uv run python scripts/mint_api_token.py user@example.com

Prints a bearer token to stdout. Send it as `Authorization: Bearer <token>` to
call the API without a browser/OIDC round trip. Tokens are stateless and cannot
be revoked individually — rotate SESSION_SECRET_KEY to invalidate all of them.
"""

import asyncio
import sys

from sqlmodel import select

from greenthumb.auth.session import create_api_token
from greenthumb.db import dispose_engine, get_session_factory
from greenthumb.models import User


async def main(email: str) -> int:
    async with get_session_factory()() as session:
        user = (await session.exec(select(User).where(User.email == email))).first()
    await dispose_engine()
    if user is None:
        print(f"No user with email {email!r}", file=sys.stderr)
        return 1
    print(create_api_token(user.id))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(asyncio.run(main(sys.argv[1])))
