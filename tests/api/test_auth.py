import pytest
from fastapi import HTTPException

from api.dependencies.auth import get_current_user
from chic_finder.config import settings


async def test_get_current_user_fails_closed_in_production_without_credentials(monkeypatch):
    """In production, a missing/invalid token must raise 401 even when
    FIREBASE_CREDENTIALS_PATH isn't configured — auth must fail closed,
    not silently fall back to the dev stub.
    """
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "FIREBASE_CREDENTIALS_PATH", "")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(authorization=None)

    assert exc_info.value.status_code == 401


async def test_get_current_user_fails_closed_in_production_even_with_credentials_configured(monkeypatch):
    """Sanity check: production still fails closed when credentials ARE
    configured but the token itself is missing/invalid.
    """
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "FIREBASE_CREDENTIALS_PATH", "/some/path/creds.json")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(authorization=None)

    assert exc_info.value.status_code == 401


async def test_get_current_user_dev_stub_in_development(monkeypatch):
    """Local development is unaffected: no token still returns the dev stub."""
    monkeypatch.setattr(settings, "APP_ENV", "development")

    user = await get_current_user(authorization=None)

    assert user == {"uid": "dev-user", "email": "dev@chicfinder.local"}
