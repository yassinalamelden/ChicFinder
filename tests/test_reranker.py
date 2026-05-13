# tests/test_reranker.py
"""
Unit tests for VisionReranker — Gemini Vision is fully mocked.
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image


def _dummy_image():
    return Image.new("RGB", (4, 4))


def _make_reranker():
    from ai_engine.llm.reranker import VisionReranker
    r = VisionReranker(api_key="fake-key", model="gemini-test")
    return r


def _set_batch_response(reranker, ranking_list):
    mock_response = MagicMock()
    mock_response.text = json.dumps({"ranking": ranking_list})
    reranker._client.models.generate_content = MagicMock(return_value=mock_response)


@pytest.mark.edge
def test_empty_candidates_returns_empty():
    r = _make_reranker()
    result = r.rerank(_dummy_image(), [], top_x=5)
    assert result == []


@pytest.mark.unit
def test_single_candidate_returns_one_index():
    r = _make_reranker()
    _set_batch_response(r, [0])
    result = r.rerank(_dummy_image(), [_dummy_image()], top_x=5)
    assert result == [0]


@pytest.mark.unit
def test_returns_top_x_indices():
    r = _make_reranker()
    _set_batch_response(r, [2, 0, 1, 3])
    result = r.rerank(_dummy_image(), [_dummy_image()] * 4, top_x=2)
    assert result == [2, 0]


@pytest.mark.unit
def test_valid_permutation_returned():
    r = _make_reranker()
    _set_batch_response(r, [2, 0, 1])
    result = r._rerank_batch(_dummy_image(), [_dummy_image()] * 3)
    assert result == [2, 0, 1]


@pytest.mark.edge
def test_invalid_permutation_falls_back_to_identity():
    r = _make_reranker()
    _set_batch_response(r, [0, 0, 1])  # not a valid permutation of [0,1,2]
    result = r._rerank_batch(_dummy_image(), [_dummy_image()] * 3)
    assert result == [0, 1, 2]


@pytest.mark.edge
def test_batch_exception_falls_back_to_identity():
    r = _make_reranker()
    r._client.models.generate_content = MagicMock(side_effect=Exception("timeout"))
    result = r._rerank_batch(_dummy_image(), [_dummy_image()] * 3)
    assert result == [0, 1, 2]


@pytest.mark.unit
def test_large_candidate_list_uses_multi_batch():
    """More than 10 candidates triggers _rerank_multi_batch."""
    from ai_engine.llm.reranker import VisionReranker
    r = _make_reranker()
    candidates = [_dummy_image()] * 11
    identity = list(range(11))
    # Provide identity ranking responses for each batch call
    call_count = {"n": 0}
    def generate_side_effect(*args, **kwargs):
        resp = MagicMock()
        # Each batch chunk: first chunk has 10 items, second has 1
        chunk_sizes = [10, 1]
        n = call_count["n"]
        call_count["n"] += 1
        if n < len(chunk_sizes):
            resp.text = json.dumps({"ranking": list(range(chunk_sizes[n]))})
        else:
            resp.text = json.dumps({"ranking": [0]})
        return resp
    r._client.models.generate_content = generate_side_effect
    result = r.rerank(_dummy_image(), candidates, top_x=3)
    assert len(result) <= 3
    assert all(0 <= i < 11 for i in result)
