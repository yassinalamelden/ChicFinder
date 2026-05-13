# tests/test_supabase_vector_store_extended.py
"""
Extended unit tests for supabase_vector_store — complementing the 3 existing tests.
"""
import sys
import types
import numpy as np
import pytest
from unittest.mock import MagicMock, patch, call


def _supabase_stub():
    if "supabase" not in sys.modules or not hasattr(sys.modules["supabase"], "create_client"):
        stub = types.ModuleType("supabase")
        stub.Client = object
        stub.create_client = lambda url, key: MagicMock()
        sys.modules["supabase"] = stub


_supabase_stub()

from ai_engine.embeddings.supabase_vector_store import (
    search_similar_items,
    search_by_vector,
    _rows_to_dicts,
)


def _mock_client(data=None):
    m = MagicMock()
    m.rpc.return_value.execute.return_value.data = data if data is not None else []
    return m


def _full_row(image_filename="abc_123_0"):
    return {
        "image_filename": image_filename,
        "similarity": 0.88,
        "product_id_str": "prod-123",
        "db_product_id": 42,
        "title": "Red Blouse",
        "brand": "Mango",
        "category": "Tops",
        "price": 450.0,
        "product_url": "https://example.com/red-blouse",
    }


# ---------------------------------------------------------------------------
# _rows_to_dicts
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_rows_to_dicts_maps_all_fields():
    result = _rows_to_dicts([_full_row()])
    assert len(result) == 1
    r = result[0]
    for key in ("id", "filename", "score", "product_id", "title", "brand", "category", "price", "product_url"):
        assert key in r, f"missing key: {key}"


@pytest.mark.unit
def test_rows_to_dicts_appends_jpg_suffix():
    result = _rows_to_dicts([_full_row("abc_0")])
    assert result[0]["filename"] == "abc_0.jpg"


@pytest.mark.unit
def test_rows_to_dicts_id_equals_image_filename():
    result = _rows_to_dicts([_full_row("tomato_001_2")])
    assert result[0]["id"] == "tomato_001_2"


@pytest.mark.unit
def test_rows_to_dicts_score_is_float():
    result = _rows_to_dicts([_full_row()])
    assert isinstance(result[0]["score"], float)


# ---------------------------------------------------------------------------
# search_by_vector
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_search_by_vector_rpc_name_is_match_embeddings():
    client = _mock_client([])
    vec = np.zeros(512, dtype=np.float32)
    with patch("ai_engine.embeddings.supabase_vector_store.get_supabase_client", return_value=client):
        search_by_vector(vec, top_k=3)
    rpc_name = client.rpc.call_args[0][0]
    assert rpc_name == "match_embeddings"


@pytest.mark.unit
def test_search_by_vector_passes_correct_top_k():
    client = _mock_client([])
    vec = np.ones(512, dtype=np.float32)
    with patch("ai_engine.embeddings.supabase_vector_store.get_supabase_client", return_value=client):
        search_by_vector(vec, top_k=7)
    kwargs = client.rpc.call_args[0][1]
    assert kwargs["match_count"] == 7


@pytest.mark.edge
def test_search_by_vector_none_data_returns_empty():
    client = _mock_client(None)  # Supabase can return None
    vec = np.ones(512, dtype=np.float32)
    with patch("ai_engine.embeddings.supabase_vector_store.get_supabase_client", return_value=client):
        result = search_by_vector(vec)
    assert result == []


# ---------------------------------------------------------------------------
# search_similar_items
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_search_similar_items_passes_top_k():
    vec = np.ones(512, dtype=np.float32)
    client = _mock_client([])
    with patch("ai_engine.embeddings.supabase_vector_store.get_supabase_client", return_value=client):
        with patch("ai_engine.embeddings.supabase_vector_store.get_encoder") as mock_enc:
            mock_enc.return_value.encode.return_value = vec
            search_similar_items(b"img_bytes", top_k=10)
    kwargs = client.rpc.call_args[0][1]
    assert kwargs["match_count"] == 10


@pytest.mark.unit
def test_search_similar_items_calls_encode_then_rpc():
    vec = np.ones(512, dtype=np.float32)
    client = _mock_client([])
    with patch("ai_engine.embeddings.supabase_vector_store.get_supabase_client", return_value=client):
        with patch("ai_engine.embeddings.supabase_vector_store.get_encoder") as mock_enc:
            mock_enc.return_value.encode.return_value = vec
            search_similar_items(b"some_image_bytes")
    mock_enc.return_value.encode.assert_called_once_with(b"some_image_bytes")
    client.rpc.assert_called_once()
    payload = client.rpc.call_args[0][1]
    assert payload["query_embedding"] == vec.tolist()
