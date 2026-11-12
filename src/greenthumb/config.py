"""Application configuration loaded from environment variables.

All deployment-specific values come from the environment (Kubernetes Secret in
production, a .env file for local development; see .env.example) so the same
image runs everywhere.
"""

import os
from functools import lru_cache
from typing import Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from greenthumb.services.seasons import Hemisphere


class Settings(BaseSettings):
    """Runtime configuration for the Green Thumb backend."""

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    # SQLite via aiosqlite. The four leading slashes denote an absolute path
    # (sqlite+aiosqlite:////data/greenthumb.db -> /data/greenthumb.db); use a relative
    # path for local dev. WAL mode and a busy timeout are set on connect (db.py).
    DATABASE_URL: str = "sqlite+aiosqlite:///./greenthumb.db"

    OIDC_ISSUER_URL: str = ""
    OIDC_CLIENT_ID: str = ""
    # Secrets are SecretStr so they never show up in a settings repr, a
    # validation error or a log line; read them with .get_secret_value().
    OIDC_CLIENT_SECRET: SecretStr = SecretStr("")
    OIDC_REDIRECT_URI: str = ""

    # Required, and at least 32 characters: it is the HS256 key for every
    # session cookie and API token (RFC 7518 wants a key no shorter than the
    # hash). Failing at startup beats a 500 on the first login.
    SESSION_SECRET_KEY: SecretStr = Field(min_length=32)
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
    NTFY_TOKEN: SecretStr | None = None

    # Web Push (VAPID). The private key is the raw base64url-encoded EC key
    # (see docs/administration.md for how to generate one); leaving it empty
    # disables Web Push entirely. The subject identifies the operator to the
    # browser push services and must be a mailto: or https: URI. Validated here
    # because py_vapid rejects a malformed one only when signing, which would
    # make every push fail silently at send time.
    VAPID_PRIVATE_KEY: SecretStr = SecretStr("")
    VAPID_SUBJECT: str = Field(
        default="mailto:admin@example.com", pattern=r"^(mailto:[^@\s]+@[^@\s]+\.[^@\s]+|https://\S+)$"
    )

    FRONTEND_URL: str = "http://localhost:5173"

    # Directory of the built SPA to serve at /. Empty disables it (local dev runs
    # the Vite dev server instead); the production image sets it to /app/static.
    STATIC_DIR: str = ""

    # How often the background loop evaluates reminders. Care intervals are in
    # days, so a daily check is plenty and keeps ntfy traffic low.
    REMINDER_CHECK_INTERVAL_SECONDS: int = Field(default=86400, ge=60)

    # Season plans scale care intervals by time of year, so the installation
    # needs to know which half of the globe it sits in. Deployment-wide rather
    # than per-user: plants are shared between users, and a household has one
    # hemisphere.
    HEMISPHERE: Hemisphere = Hemisphere.NORTH

    LOG_LEVEL: str = "INFO"

    @model_validator(mode="after")
    def _dev_bypass_stays_local(self) -> Self:
        # A configured identity provider or Secure cookies both mean a real
        # deployment, where the bypass would hand out sessions to anyone.
        if self.DEV_AUTH_BYPASS and (self.OIDC_ISSUER_URL or self.SESSION_COOKIE_SECURE):
            raise ValueError(
                "DEV_AUTH_BYPASS is for local development only: it requires SESSION_COOKIE_SECURE=false "
                "and no OIDC_ISSUER_URL"
            )
        return self


# Which dotenv file to read; set it empty to read none. Isolated runs (the e2e
# backend) need that: started from the repo root they would otherwise pick up a
# developer's .env, with its real OIDC or ntfy settings.
ENV_FILE_VARIABLE = "GREENTHUMB_ENV_FILE"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings instance (env is read once per process)."""
    return Settings(_env_file=os.environ.get(ENV_FILE_VARIABLE, ".env") or None)
