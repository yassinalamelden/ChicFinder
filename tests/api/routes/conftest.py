"""Shared fixtures for route tests.

`saved_account_client` mounts only the saved and account routers on a bare
FastAPI app. Importing api.main would drag in the whole AI stack (torch, faiss,
FashionCLIP), which these routes never touch, so keeping them isolated makes the
tests fast and lets them run in an environment without the model dependencies.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import account, saved


@pytest.fixture
def saved_account_app() -> FastAPI:
    app = FastAPI()
    app.include_router(saved.router, prefix="/api/v1")
    app.include_router(account.router, prefix="/api/v1")
    # The /stores routes populate these at startup; the saved routes read them
    # as an enrichment fallback.
    app.state.products = []
    app.state.products_lookup = {}
    return app


@pytest.fixture
def saved_account_client(saved_account_app: FastAPI) -> TestClient:
    return TestClient(saved_account_app)
