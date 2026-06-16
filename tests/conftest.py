"""Shared test fixtures.

Tests run against in-memory SQLite (with the foreign_keys pragma enabled so
ON DELETE behaviour matches PostgreSQL) and authenticate by minting a real
session cookie, so the whole auth dependency chain is exercised.
"""

import os
import uuid
from collections.abc import AsyncGenerator

# Configuration must exist before greenthumb modules read it.
os.environ.setdefault("SESSION_SECRET_KEY", "test-secret-key-for-sessions")
os.environ.setdefault("SESSION_COOKIE_SECURE", "false")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("OIDC_ISSUER_URL", "https://auth.test")
os.environ.setdefault("OIDC_CLIENT_ID", "test-client")
os.environ.setdefault("FRONTEND_URL", "http://frontend.test")

import httpx
import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from greenthumb.auth.session import SESSION_COOKIE_NAME, create_session_token
from greenthumb.db import get_db
from greenthumb.main import app
from greenthumb.models import CareLog, Plant, User


@pytest.fixture
async def engine() -> AsyncGenerator[AsyncEngine]:
    """Fresh in-memory database per test."""
    test_engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(test_engine.sync_engine, "connect")
    def _enable_fk(dbapi_connection, _record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield test_engine
    await test_engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    """Database session bound to the test engine."""
    async with AsyncSession(engine, expire_on_commit=False) as db_session:
        yield db_session


@pytest.fixture
async def user(session: AsyncSession) -> User:
    """A provisioned user, as the OIDC callback would create one."""
    test_user = User(oidc_sub="oidc|test-sub", email="gardener@example.com", display_name="Test Gardener")
    session.add(test_user)
    await session.commit()
    await session.refresh(test_user)
    return test_user


@pytest.fixture
async def client(session: AsyncSession, user: User) -> AsyncGenerator[httpx.AsyncClient]:
    """Authenticated API client; the app uses the test database session."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession]:
        yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as api_client:
        api_client.cookies.set(SESSION_COOKIE_NAME, create_session_token(user.id))
        yield api_client
    app.dependency_overrides.clear()


@pytest.fixture
async def anon_client(session: AsyncSession) -> AsyncGenerator[httpx.AsyncClient]:
    """Unauthenticated API client for 401 tests."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession]:
        yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as api_client:
        yield api_client
    app.dependency_overrides.clear()


@pytest.fixture
async def plant(session: AsyncSession, user: User) -> Plant:
    """A basic plant owned by the test user."""
    test_plant = Plant(name="Monstera", species_name="Monstera deliciosa", tags=["tropical"], created_by=user.id)
    session.add(test_plant)
    await session.commit()
    await session.refresh(test_plant)
    return test_plant


async def add_care_log(session: AsyncSession, plant_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> CareLog:
    """Insert a care log directly, bypassing the API."""
    log = CareLog(plant_id=plant_id, logged_by=user_id, event_type=kwargs.pop("event_type", "watering"), **kwargs)
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log
