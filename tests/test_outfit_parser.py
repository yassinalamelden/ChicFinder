# tests/test_outfit_parser.py
"""
Unit tests for OutfitParser — Gemini Vision is fully mocked.
"""
import json
import sys
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image


def _dummy_image():
    return Image.new("RGB", (4, 4), color=(10, 20, 30))


def _make_parser(gemini_response_text="[]"):
    """Return an OutfitParser whose _client is fully mocked."""
    from ai_engine.llm.outfit_parser import OutfitParser
    parser = OutfitParser(api_key="fake-key", model="gemini-test")
    mock_response = MagicMock()
    mock_response.text = gemini_response_text
    parser._client.models.generate_content = MagicMock(return_value=mock_response)
    return parser


@pytest.mark.unit
def test_parse_returns_list_of_dicts():
    item = {"type": "t-shirt", "color": "white", "style": "casual", "gender": "unisex", "material": "cotton", "fit": "regular"}
    parser = _make_parser(json.dumps([item]))
    result = parser.parse(_dummy_image())
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["type"] == "t-shirt"
    for key in ("type", "color", "style", "gender", "material", "fit"):
        assert key in result[0]


@pytest.mark.edge
def test_parse_wraps_single_object_in_list():
    parser = _make_parser('{"type": "dress", "color": "red", "style": "formal", "gender": "female", "material": "silk", "fit": "slim"}')
    result = parser.parse(_dummy_image())
    assert isinstance(result, list)
    assert result[0]["type"] == "dress"


@pytest.mark.edge
def test_parse_invalid_json_raises_value_error():
    parser = _make_parser("not valid JSON {")
    with pytest.raises(ValueError, match="Expected JSON output from LLM"):
        parser.parse(_dummy_image())


@pytest.mark.edge
def test_parse_api_failure_raises_runtime_error():
    from ai_engine.llm.outfit_parser import OutfitParser
    parser = OutfitParser(api_key="fake-key", model="gemini-test")
    parser._client.models.generate_content = MagicMock(side_effect=Exception("API quota exceeded"))
    with pytest.raises(RuntimeError, match="OutfitParser Gemini API call failed"):
        parser.parse(_dummy_image())


@pytest.mark.unit
def test_default_model_comes_from_settings():
    from chic_finder.config import settings
    from ai_engine.llm.outfit_parser import OutfitParser
    parser = OutfitParser(api_key="fake-key")
    assert parser.model == settings.GEMINI_MODEL


@pytest.mark.unit
def test_parse_empty_list_returns_empty():
    parser = _make_parser("[]")
    result = parser.parse(_dummy_image())
    assert result == []
