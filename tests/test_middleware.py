# tests/test_middleware.py
"""Unit tests for LoggingMiddleware."""
import logging
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.middleware.logging import LoggingMiddleware


def _app_with_middleware():
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get("/ping")
    def ping():
        return {"pong": True}

    return app


@pytest.mark.unit
def test_middleware_calls_next():
    client = TestClient(_app_with_middleware())
    r = client.get("/ping")
    assert r.status_code == 200
    assert r.json() == {"pong": True}


@pytest.mark.unit
def test_middleware_logs_path_and_time(caplog):
    app = _app_with_middleware()
    client = TestClient(app)
    with caplog.at_level(logging.INFO):
        client.get("/ping")
    log_text = " ".join(caplog.messages)
    assert "/ping" in log_text
    assert "processed in" in log_text
