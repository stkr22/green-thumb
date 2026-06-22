"""Application configuration loaded from environment variables.

All deployment-specific values come from the environment (Kubernetes Secret in
production, .env.local via docker-compose for local development) so the same
image runs everywhere.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Green Thumb backend."""

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    # SQLite via aiosqlite. The four leading slashes denote an absolute path
    # (sqlite+aiosqlite:////data/greenthumb.db -> /data/greenthumb.db); use a relative
    # path for local dev. WAL mode and a busy timeout are set on connect (db.py).
    DATABASE_URL: str = "sqlite+aiosqlite:///./greenthumb.db"

    OIDC_ISSUER_URL: str = ""
    OIDC_CLIENT_ID: str = ""
    OIDC_CLIENT_SECRET: str = ""
    OIDC_REDIRECT_URI: str = ""

    SESSION_SECRET_KEY: str = ""
    # Lifetime of the signed session cookie; users re-authenticate via Zitadel afterwards.
    SESSION_MAX_AGE_SECONDS: int = 60 * 60 * 24 * 7
    # Disable only for plain-http local development; cookies must be Secure behind TLS.
    SESSION_COOKIE_SECURE: bool = True

    # Local-only escape hatch: when true, GET /auth/dev-login provisions a demo
    # user and sets a session cookie without OIDC. MUST stay false in any
    # internet-reachable deployment; the endpoint 404s while disabled.
    DEV_AUTH_BYPASS: bool = False
    DEV_AUTH_EMAIL: str = "demo@example.com"
    DEV_AUTH_DISPLAY_NAME: str = "Demo Gardener"

    NTFY_URL: str = ""
    NTFY_TOPIC: str = "greenthumb"
    NTFY_TOKEN: str | None = None

    FRONTEND_URL: str = "http://localhost:5173"

    # How often the background loop evaluates reminders. One hour is plenty for
    # day-granularity intervals while keeping ntfy traffic low.
    REMINDER_CHECK_INTERVAL_SECONDS: int = Field(default=3600, ge=60)

    LOG_LEVEL: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings instance (env is read once per process)."""
    return Settings()
