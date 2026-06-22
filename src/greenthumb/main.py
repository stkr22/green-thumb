"""FastAPI application entry point.

Run locally with: uvicorn greenthumb.main:app --reload
"""

import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, status
from fastapi.staticfiles import StaticFiles
from sqlmodel import text
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import Scope

from greenthumb import auth
from greenthumb.api import v1
from greenthumb.config import get_settings
from greenthumb.db import dispose_engine, get_engine, get_session_factory
from greenthumb.services.reminder_evaluator import evaluate_and_notify

logger = logging.getLogger(__name__)


class _SPAStaticFiles(StaticFiles):
    """Static files with an index.html fallback so client-side routes resolve."""

    async def get_response(self, path: str, scope: Scope):
        # StaticFiles raises (not returns) 404 for a missing path; a deep link
        # like /plants/123 is a client-side route, so serve the SPA shell instead.
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                return await super().get_response("index.html", scope)
            raise


async def _reminder_loop(interval_seconds: int) -> None:
    """Evaluate reminders forever; failures are logged and the loop keeps running."""
    while True:
        try:
            async with get_session_factory()() as session:
                await evaluate_and_notify(session)
        except Exception:
            logger.exception("Reminder evaluation failed; retrying next cycle")
        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Start the background reminder loop for the app's lifetime."""
    settings = get_settings()
    logging.basicConfig(level=settings.LOG_LEVEL.upper())
    task = asyncio.create_task(_reminder_loop(settings.REMINDER_CHECK_INTERVAL_SECONDS))
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        await dispose_engine()


app = FastAPI(title="Green Thumb", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(v1.router)


@app.get("/healthz", include_in_schema=False)
async def healthz() -> dict[str, str]:
    """Liveness probe: the process is up."""
    return {"status": "ok"}


@app.get("/readyz", include_in_schema=False)
async def readyz() -> dict[str, str]:
    """Readiness probe: the database answers a trivial query."""
    async with get_engine().connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"status": "ready"}


# Serve the built SPA at / in the production image; the API routers and probes
# registered above take precedence. ponytail: an unknown /api path falls through
# to index.html rather than a JSON 404 — fine for a single-household app.
_static_dir = get_settings().STATIC_DIR
if _static_dir and Path(_static_dir).is_dir():
    app.mount("/", _SPAStaticFiles(directory=_static_dir, html=True), name="spa")
