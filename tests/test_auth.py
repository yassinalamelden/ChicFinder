# tests/test_auth.py
"""
Tests for Firebase JWT authentication on POST /api/v1/search.
Uses test_client_real_auth so require_auth is NOT bypassed.
"""
import sys
import pytest
from unittest.mock import patch, MagicMock


def _fb_auth():
    return sys.modules["firebase_admin.auth"]


@pytest.mark.auth
def test_search_no_auth_header(test_client_real_auth):
    """HTTPBearer rejects missing Authorization header (401 in Starlette >=0.40)."""
    response = test_client_real_auth.post("/api/v1/search", json={"image_base64": "x"})
    assert response.status_code in (401, 403)


@pytest.mark.auth
def test_search_wrong_scheme(test_client_real_auth):
    """HTTPBearer rejects non-Bearer schemes (401 in Starlette >=0.40)."""
    response = test_client_real_auth.post(
        "/api/v1/search",
        json={"image_base64": "x"},
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )
    assert response.status_code in (401, 403)


@pytest.mark.auth
def test_search_invalid_token(test_client_real_auth):
    """verify_id_token raises InvalidIdTokenError → 401 with 'Invalid token' detail."""
    auth_mod = _fb_auth()
    with patch("api.dependencies.auth._init_firebase"):
        with patch.object(
            auth_mod,
            "verify_id_token",
            side_effect=auth_mod.InvalidIdTokenError("bad token"),
        ):
            response = test_client_real_auth.post(
                "/api/v1/search",
                json={"image_base64": "x"},
                headers={"Authorization": "Bearer bad.jwt.token"},
            )
    assert response.status_code == 401
    assert "Invalid token" in response.json()["detail"]


@pytest.mark.auth
def test_search_expired_token(test_client_real_auth):
    """verify_id_token raises ExpiredIdTokenError → 401 with 'expired' in detail."""
    auth_mod = _fb_auth()
    with patch("api.dependencies.auth._init_firebase"):
        with patch.object(
            auth_mod,
            "verify_id_token",
            side_effect=auth_mod.ExpiredIdTokenError("token expired"),
        ):
            response = test_client_real_auth.post(
                "/api/v1/search",
                json={"image_base64": "x"},
                headers={"Authorization": "Bearer expired.jwt"},
            )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.auth
@pytest.mark.integration
def test_search_valid_token_reaches_handler(test_client_real_auth, minimal_png_b64):
    """Valid token passes auth and handler runs successfully."""
    auth_mod = _fb_auth()
    with patch("api.dependencies.auth._init_firebase"):
        with patch.object(
            auth_mod,
            "verify_id_token",
            return_value={"uid": "real-user-123"},
        ):
            with patch("api.routes.search.search_similar_items", return_value=[]):
                response = test_client_real_auth.post(
                    "/api/v1/search",
                    json={"image_base64": minimal_png_b64},
                    headers={"Authorization": "Bearer valid.jwt.token"},
                )
    assert response.status_code == 200
    assert response.json()["results"] == []
