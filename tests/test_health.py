# tests/test_health.py
from unittest.mock import MagicMock, patch
import pytest


@pytest.mark.integration
def test_health_returns_200(test_client):
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200


@pytest.mark.unit
def test_health_schema_when_supabase_connected(test_client):
    mock_result = MagicMock()
    mock_result.count = 42
    with patch("api.routes.health.get_supabase_client") as mock_client:
        mock_client.return_value.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_result
        response = test_client.get("/api/v1/health")
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "ChicFinder API"
    assert data["supabase"] == "connected"
    assert data["products"] == 42


@pytest.mark.unit
def test_health_schema_when_supabase_unreachable(test_client):
    with patch("api.routes.health.get_supabase_client") as mock_client:
        mock_client.return_value.table.side_effect = Exception("connection refused")
        response = test_client.get("/api/v1/health")
    data = response.json()
    assert data["status"] == "degraded"
    assert data["supabase"] == "unreachable"
    assert "error" in data


@pytest.mark.edge
def test_health_post_method_not_allowed(test_client):
    response = test_client.post("/api/v1/health")
    assert response.status_code == 405
