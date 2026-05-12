# tests/test_supabase_vector_store.py
import sys
import types
import numpy as np
from unittest.mock import MagicMock, patch


def _install_supabase_stub():
    if "supabase" not in sys.modules or not hasattr(sys.modules["supabase"], "create_client"):
        stub = types.ModuleType("supabase")
        stub.Client = object
        stub.create_client = lambda url, key: object()
        sys.modules["supabase"] = stub


def test_search_similar_items_calls_rpc():
    _install_supabase_stub()
    mock_client = MagicMock()
    mock_client.rpc.return_value.execute.return_value.data = [
        {
            "image_filename": "tomato_123_0",
            "product_id_str": "123",
            "db_product_id": 1,
            "title": "Test Shirt",
            "brand": "Tomato",
            "category": "Tops",
            "price": 500.0,
            "product_url": "https://example.com",
            "similarity": 0.91,
        }
    ]
    fake_vector = np.ones(512, dtype=np.float32)

    with patch("ai_engine.embeddings.supabase_vector_store.get_supabase_client", return_value=mock_client):
        with patch("ai_engine.embeddings.supabase_vector_store.get_encoder") as mock_enc:
            mock_enc.return_value.encode.return_value = fake_vector
            from ai_engine.embeddings import supabase_vector_store as svs
            results = svs.search_similar_items(b"fake_image_bytes", top_k=5)

    mock_client.rpc.assert_called_once_with(
        "match_embeddings",
        {"query_embedding": fake_vector.tolist(), "match_count": 5},
    )
    assert len(results) == 1
    assert results[0]["id"] == "tomato_123_0"
    assert results[0]["score"] == 0.91
    assert results[0]["brand"] == "Tomato"
    assert results[0]["filename"] == "tomato_123_0.jpg"


def test_search_by_vector_calls_rpc():
    _install_supabase_stub()
    mock_client = MagicMock()
    mock_client.rpc.return_value.execute.return_value.data = []

    with patch("ai_engine.embeddings.supabase_vector_store.get_supabase_client", return_value=mock_client):
        from ai_engine.embeddings import supabase_vector_store as svs
        vec = np.ones(512, dtype=np.float32)
        results = svs.search_by_vector(vec, top_k=3)

    mock_client.rpc.assert_called_once_with(
        "match_embeddings",
        {"query_embedding": vec.tolist(), "match_count": 3},
    )
    assert results == []


def test_rows_to_dicts_handles_none_fields():
    _install_supabase_stub()
    from ai_engine.embeddings.supabase_vector_store import _rows_to_dicts
    rows = [
        {
            "image_filename": "img_001",
            "similarity": 0.75,
            "product_id_str": None,
            "db_product_id": None,
            "title": None,
            "brand": None,
            "category": None,
            "price": None,
            "product_url": None,
        }
    ]
    result = _rows_to_dicts(rows)
    assert len(result) == 1
    assert result[0]["id"] == "img_001"
    assert result[0]["score"] == 0.75
    assert result[0]["brand"] is None
