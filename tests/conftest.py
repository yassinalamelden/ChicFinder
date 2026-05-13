# tests/conftest.py
"""
Shared fixtures and module stubs for the ChicFinder test suite.

Stubs are installed before any app module is imported so that tests run
offline without real Firebase, Google GenAI, Supabase, or PyTorch dependencies.
"""

import base64
import io
import sys
import types
from unittest.mock import MagicMock

import numpy as np
import pytest
from PIL import Image


# ---------------------------------------------------------------------------
# Module stubs — installed at collection time (before any app import)
# ---------------------------------------------------------------------------

def _install_supabase_stub():
    if "supabase" in sys.modules and hasattr(sys.modules["supabase"], "create_client"):
        return
    stub = types.ModuleType("supabase")
    stub.Client = object
    stub.create_client = lambda url, key: MagicMock()
    sys.modules["supabase"] = stub


def _install_firebase_stub():
    if "firebase_admin" in sys.modules:
        return

    class InvalidIdTokenError(Exception):
        pass

    class ExpiredIdTokenError(InvalidIdTokenError):
        pass

    auth_mod = types.ModuleType("firebase_admin.auth")
    auth_mod.InvalidIdTokenError = InvalidIdTokenError
    auth_mod.ExpiredIdTokenError = ExpiredIdTokenError
    auth_mod.verify_id_token = lambda token, check_revoked=False: {"uid": "stub-uid"}

    cred_mod = types.ModuleType("firebase_admin.credentials")

    class Certificate:
        def __init__(self, path):
            pass

    class ApplicationDefault:
        pass

    cred_mod.Certificate = Certificate
    cred_mod.ApplicationDefault = ApplicationDefault

    fa_mod = types.ModuleType("firebase_admin")
    fa_mod._apps = {}
    fa_mod.get_app = lambda: object()
    fa_mod.initialize_app = lambda *a, **kw: object()
    fa_mod.delete_app = lambda app: None
    fa_mod.auth = auth_mod
    fa_mod.credentials = cred_mod

    sys.modules["firebase_admin"] = fa_mod
    sys.modules["firebase_admin.auth"] = auth_mod
    sys.modules["firebase_admin.credentials"] = cred_mod


def _install_genai_stub():
    if "google.genai" in sys.modules:
        return

    class GenerateContentConfig:
        def __init__(self, **kwargs):
            pass

    types_mod = types.ModuleType("google.genai.types")
    types_mod.GenerateContentConfig = GenerateContentConfig

    class _Models:
        def generate_content(self, *args, **kwargs):
            m = MagicMock()
            m.text = "[]"
            return m

    class Client:
        def __init__(self, **kwargs):
            pass
        models = _Models()

    genai_mod = types.ModuleType("google.genai")
    genai_mod.Client = Client
    genai_mod.types = types_mod

    # Only create the google stub if it doesn't already exist
    if "google" not in sys.modules:
        google_mod = types.ModuleType("google")
        sys.modules["google"] = google_mod
    sys.modules["google"].genai = genai_mod  # type: ignore[attr-defined]
    sys.modules["google.genai"] = genai_mod
    sys.modules["google.genai.types"] = types_mod


# Install all stubs before app import
_install_supabase_stub()
_install_firebase_stub()
_install_genai_stub()

# ---------------------------------------------------------------------------
# App imports (safe after stubs are in place)
# ---------------------------------------------------------------------------

from api.main import app  # noqa: E402
from api.dependencies.auth import require_auth  # noqa: E402
from chic_finder.config import settings  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_png_bytes():
    """1×1 red PNG as raw bytes — usable everywhere an image is expected."""
    img = Image.new("RGB", (1, 1), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def minimal_png_b64(minimal_png_bytes):
    """Base64-encoded 1×1 PNG string."""
    return base64.b64encode(minimal_png_bytes).decode()


@pytest.fixture(autouse=True)
def patch_supabase_url(monkeypatch):
    """Ensure settings.SUPABASE_URL is always set so get_image_url() doesn't raise."""
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://test.supabase.co")


@pytest.fixture
def sample_search_rows():
    """Realistic rows in the shape returned by search_similar_items()."""
    return [
        {
            "id": f"zara_{i:03d}_0",
            "filename": f"zara_{i:03d}_0.jpg",
            "score": round(0.95 - i * 0.05, 2),
            "product_id": f"prod-{i:03d}",
            "title": f"Test Item {i}",
            "brand": "Zara" if i < 2 else "H&M",
            "category": "Tops",
            "price": float((i + 1) * 100),
            "product_url": f"https://example.com/item/{i}",
        }
        for i in range(5)
    ]


@pytest.fixture
def sample_product_rows():
    """Realistic rows in the shape returned by a Supabase products query."""
    return [
        {
            "id": i + 1,
            "product_id": f"prod-{i:03d}",
            "title": f"Zara Item {i}",
            "brand": "Zara",
            "category": "Tops",
            "price": float((i + 1) * 150),
            "product_url": f"https://example.com/item/{i}",
            "description": "A nice fashion item",
            "availability": "InStock",
        }
        for i in range(3)
    ]


@pytest.fixture
def test_client():
    """TestClient with Firebase auth bypassed via dependency override."""
    from fastapi.testclient import TestClient

    app.dependency_overrides[require_auth] = lambda: {"uid": "test-user-123"}
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def test_client_real_auth():
    """TestClient WITHOUT auth bypass — for auth-specific tests."""
    from fastapi.testclient import TestClient
    import api.dependencies.auth as auth_mod

    app.dependency_overrides.pop(require_auth, None)
    # Reset Firebase singleton so _init_firebase() runs fresh each test
    auth_mod._firebase_app = None
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    app.dependency_overrides.clear()
    auth_mod._firebase_app = None


@pytest.fixture
def reset_encoder_singleton():
    """Reset FashionCLIPEncoder singleton around a test."""
    from ai_engine.embeddings.encoder import FashionCLIPEncoder

    original = FashionCLIPEncoder._instance
    FashionCLIPEncoder._instance = None
    yield
    FashionCLIPEncoder._instance = original


@pytest.fixture
def reset_db_client():
    """Reset Supabase _client singleton around a test."""
    from api.db import client as db_mod

    original = db_mod._client
    db_mod._client = None
    yield
    db_mod._client = original
