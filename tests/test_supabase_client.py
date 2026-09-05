# tests/test_supabase_client.py
import os
import sys
import types
import pytest


def _install_supabase_stub():
    """Install a minimal supabase stub so client.py can be imported without the real package."""
    if "supabase" not in sys.modules or not hasattr(sys.modules["supabase"], "create_client"):
        stub = types.ModuleType("supabase")
        stub.Client = object

        def create_client(url, key):
            return object()  # return a non-None sentinel

        stub.create_client = create_client
        sys.modules["supabase"] = stub


def _reset_client_module():
    """Reset the module-level singleton so tests start clean."""
    sys.modules.pop("api.db.client", None)


def test_get_supabase_client_raises_without_env(monkeypatch):
    _install_supabase_stub()
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    _reset_client_module()
    from api.db import client as db_mod
    db_mod._client = None  # reset singleton
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        db_mod.get_supabase_client()


def test_get_supabase_client_returns_client_with_env(monkeypatch):
    _install_supabase_stub()
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service_key")
    _reset_client_module()
    from api.db import client as db_mod
    db_mod._client = None  # reset singleton
    result = db_mod.get_supabase_client()
    assert result is not None
