# tests/test_health.py
import pytest


@pytest.mark.integration
def test_health_returns_200(test_client):
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200


@pytest.mark.unit
def test_health_schema(test_client):
    response = test_client.get("/api/v1/health")
    assert response.json() == {"status": "ok", "service": "ChicFinder API"}


@pytest.mark.edge
def test_health_post_method_not_allowed(test_client):
    response = test_client.post("/api/v1/health")
    assert response.status_code == 405
