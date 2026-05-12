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

        def create_client(url, key):  # pragma: no cover
            pass

        stub.create_client = create_client
        sys.modules["supabase"] = stub


def test_get_supabase_client_raises_without_env(monkeypatch):
    _install_supabase_stub()
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    # Remove cached module so the import picks up the stub
    sys.modules.pop("api.db.client", None)
    from api.db import client as db_mod
    db_mod.get_supabase_client.cache_clear()
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        db_mod.get_supabase_client()
