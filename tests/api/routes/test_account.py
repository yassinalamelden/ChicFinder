"""Tests for account deletion, which App Store review checks directly."""

from unittest.mock import patch


def test_delete_account_removes_data_then_the_auth_record(saved_account_client):
    """Order matters: data first, so a failure never leaves orphaned rows."""
    calls = []

    def record_data_delete(uid):
        calls.append(("data", uid))
        return 3

    def record_auth_delete(uid):
        calls.append(("auth", uid))
        return True

    with patch(
        "api.routes.account.db.delete_all_user_data", side_effect=record_data_delete
    ), patch("api.routes.account._delete_firebase_user", side_effect=record_auth_delete):
        response = saved_account_client.delete("/api/v1/account")

    assert response.status_code == 200
    assert calls == [("data", "dev-user"), ("auth", "dev-user")]

    body = response.json()
    assert body["deleted"] is True
    assert body["rows_removed"] == 3
    assert body["auth_record_removed"] is True


def test_delete_account_reports_failure_when_the_auth_record_survives(saved_account_client):
    """A partial deletion must not be reported to the user as a success."""
    with patch("api.routes.account.db.delete_all_user_data", return_value=1), patch(
        "api.routes.account._delete_firebase_user", return_value=False
    ):
        response = saved_account_client.delete("/api/v1/account")

    assert response.status_code == 502
    assert "could not be removed" in response.json()["detail"]


def test_delete_account_does_not_touch_auth_when_data_deletion_fails(saved_account_client):
    with patch(
        "api.routes.account.db.delete_all_user_data", side_effect=RuntimeError("RDS down")
    ), patch("api.routes.account._delete_firebase_user") as mock_auth:
        response = saved_account_client.delete("/api/v1/account")

    assert response.status_code == 503
    mock_auth.assert_not_called()


def test_get_account_returns_the_callers_own_identity(saved_account_client):
    response = saved_account_client.get("/api/v1/account")

    assert response.status_code == 200
    assert response.json() == {"uid": "dev-user", "email": "dev@chicfinder.local"}
