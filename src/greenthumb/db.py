"""Async SQLModel engine and session management.

The engine is created lazily so importing the app (e.g. for OpenAPI generation
or tests) does not require a reachable database.

The app runs on SQLite (aiosqlite). On every connection we enable WAL so the
hourly reminder loop can write while user requests read, set a busy timeout to
absorb the single-writer lock under brief contention, and turn on foreign-key
enforcement (off by default in SQLite) so ON DELETE cascades fire.
"""

from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from greenthumb.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _apply_sqlite_pragmas(engine: AsyncEngine) -> None:
    """Set per-connection SQLite pragmas via a sync-engine connect listener."""

    @event.listens_for(engine.sync_engine, "connect")
    def _set_pragmas(dbapi_connection, _record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


def get_engine() -> AsyncEngine:
    """Return the process-wide async engine, creating it on first use."""
    global _engine  # noqa: PLW0603 - intentional lazy singleton
    if _engine is None:
        _engine = create_async_engine(get_settings().DATABASE_URL)
        if _engine.dialect.name == "sqlite":
            _apply_sqlite_pragmas(_engine)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the session factory bound to the lazy engine."""
    global _session_factory  # noqa: PLW0603 - intentional lazy singleton
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped database session."""
    async with get_session_factory()() as session:
        yield session


async def dispose_engine() -> None:
    """Dispose the engine on shutdown and reset the lazy singletons (used by tests)."""
    global _engine, _session_factory  # noqa: PLW0603 - intentional lazy singleton
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
