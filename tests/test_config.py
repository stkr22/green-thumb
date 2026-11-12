"""Settings validation: misconfiguration must stop startup, not surface later as 500s."""

import pytest
from pydantic import ValidationError

from greenthumb.config import ENV_FILE_VARIABLE, Settings, get_settings

KEY = "k" * 32


def test_session_secret_is_required(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SESSION_SECRET_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_short_session_secret_is_rejected():
    with pytest.raises(ValidationError):
        Settings(SESSION_SECRET_KEY="too-short")


def test_secrets_do_not_leak_through_repr():
    settings = Settings(SESSION_SECRET_KEY=KEY, OIDC_CLIENT_SECRET="oidc-secret", NTFY_TOKEN="ntfy-secret")
    for secret in (KEY, "oidc-secret", "ntfy-secret"):
        assert secret not in repr(settings)


@pytest.mark.parametrize(
    "deployment",
    [{"OIDC_ISSUER_URL": "https://idp.example", "SESSION_COOKIE_SECURE": False}, {"SESSION_COOKIE_SECURE": True}],
    ids=["oidc-configured", "secure-cookies"],
)
def test_dev_bypass_refused_in_a_real_deployment(deployment: dict):
    with pytest.raises(ValidationError, match="DEV_AUTH_BYPASS"):
        Settings(SESSION_SECRET_KEY=KEY, DEV_AUTH_BYPASS=True, **deployment)


def test_dev_bypass_allowed_locally():
    settings = Settings(SESSION_SECRET_KEY=KEY, DEV_AUTH_BYPASS=True, SESSION_COOKIE_SECURE=False, OIDC_ISSUER_URL="")
    assert settings.DEV_AUTH_BYPASS


def test_dotenv_file_can_be_disabled(tmp_path, monkeypatch: pytest.MonkeyPatch):
    # A developer's .env (here with an IdP) must not reach an isolated run.
    (tmp_path / ".env").write_text("OIDC_ISSUER_URL=https://idp.example\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OIDC_ISSUER_URL", raising=False)  # conftest sets one
    get_settings.cache_clear()
    try:
        assert get_settings().OIDC_ISSUER_URL == "https://idp.example"
        monkeypatch.setenv(ENV_FILE_VARIABLE, "")
        get_settings.cache_clear()
        assert get_settings().OIDC_ISSUER_URL == ""
    finally:
        get_settings.cache_clear()
