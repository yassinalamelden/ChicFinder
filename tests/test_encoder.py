# tests/test_encoder.py
"""
Unit tests for FashionCLIPEncoder.
All torch/transformers calls are mocked so these run without GPU or model files.
"""
import io
import math
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from PIL import Image

from ai_engine.embeddings.encoder import FashionCLIPEncoder, get_encoder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_encoder_instance(model=None, processor=None):
    """Build a FashionCLIPEncoder without loading real weights."""
    enc = object.__new__(FashionCLIPEncoder)
    enc._model = model or MagicMock()
    enc._processor = processor or MagicMock()
    enc._device = "cpu"
    return enc


# ---------------------------------------------------------------------------
# Tests for _normalize
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_normalize_unit_vector():
    v = np.array([3.0, 4.0], dtype=np.float32)
    result = FashionCLIPEncoder._normalize(v)
    np.testing.assert_allclose(result, [0.6, 0.8], atol=1e-6)
    assert abs(np.linalg.norm(result) - 1.0) < 1e-6


@pytest.mark.unit
def test_normalize_already_unit():
    v = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    result = FashionCLIPEncoder._normalize(v)
    np.testing.assert_allclose(result, v, atol=1e-6)


@pytest.mark.edge
def test_normalize_near_zero_vector_returns_as_is():
    v = np.zeros(512, dtype=np.float32)
    result = FashionCLIPEncoder._normalize(v)
    # Should not raise; norm remains 0 (guard path returns as-is)
    assert np.linalg.norm(result) == pytest.approx(0.0)


@pytest.mark.unit
def test_normalize_512d_vector():
    v = np.full(512, 2.0, dtype=np.float32)
    result = FashionCLIPEncoder._normalize(v)
    assert result.shape == (512,)
    assert abs(np.linalg.norm(result) - 1.0) < 1e-5


# ---------------------------------------------------------------------------
# Tests for _decode
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_decode_valid_png_returns_rgb_image(minimal_png_bytes):
    enc = _make_encoder_instance()
    result = enc._decode(minimal_png_bytes)
    assert isinstance(result, Image.Image)
    assert result.mode == "RGB"


@pytest.mark.edge
def test_decode_invalid_bytes_raises_value_error():
    enc = _make_encoder_instance()
    with pytest.raises(ValueError, match="Cannot decode image"):
        enc._decode(b"garbage bytes here that cannot be decoded as an image")


# ---------------------------------------------------------------------------
# Tests for encode (end-to-end, with _encode mocked)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_encode_normalizes_output(minimal_png_bytes):
    enc = _make_encoder_instance()
    # _encode returns a raw un-normalized vector
    raw = np.full(512, 2.0, dtype=np.float32)
    with patch.object(enc, "_encode", return_value=raw):
        result = enc.encode(minimal_png_bytes)
    assert result.shape == (512,)
    assert abs(np.linalg.norm(result) - 1.0) < 1e-5


@pytest.mark.unit
def test_encode_calls_decode_then_encode_then_normalize(minimal_png_bytes):
    enc = _make_encoder_instance()
    raw = np.ones(512, dtype=np.float32)
    with patch.object(enc, "_decode", wraps=enc._decode) as mock_decode, \
         patch.object(enc, "_encode", return_value=raw) as mock_enc, \
         patch.object(enc, "_normalize", wraps=FashionCLIPEncoder._normalize) as mock_norm:
        enc.encode(minimal_png_bytes)
    mock_decode.assert_called_once()
    mock_enc.assert_called_once()
    mock_norm.assert_called_once()


# ---------------------------------------------------------------------------
# Tests for singleton
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_singleton_returns_same_instance(reset_encoder_singleton):
    mock_init = MagicMock(return_value=None)
    with patch.object(FashionCLIPEncoder, "__init__", mock_init):
        FashionCLIPEncoder._instance = None
        inst1 = FashionCLIPEncoder.get_instance()
        inst2 = FashionCLIPEncoder.get_instance()
    assert inst1 is inst2
    # __init__ called exactly once
    assert mock_init.call_count == 1


@pytest.mark.unit
def test_get_encoder_returns_singleton(reset_encoder_singleton):
    sentinel = _make_encoder_instance()
    FashionCLIPEncoder._instance = sentinel
    result = get_encoder()
    assert result is sentinel
    FashionCLIPEncoder._instance = None  # cleanup


# ---------------------------------------------------------------------------
# Test: CLIP_MODEL_PATH used as HF model ID when local path is missing
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_encoder_uses_clip_model_path_as_hf_id_when_local_missing(monkeypatch):
    """If CLIP_MODEL_PATH is set but not a valid local path, use it as HF model ID."""
    monkeypatch.setenv("CLIP_MODEL_PATH", "nonexistent/chicfinder-clip")

    captured_source = {}

    def fake_from_pretrained(source, *args, **kwargs):
        captured_source["source"] = source
        return MagicMock()

    with patch("transformers.CLIPProcessor.from_pretrained", side_effect=fake_from_pretrained), \
         patch("transformers.CLIPModel.from_pretrained", return_value=MagicMock()), \
         patch("torch.cuda.is_available", return_value=False):
        FashionCLIPEncoder._instance = None  # reset singleton
        enc = FashionCLIPEncoder()
        FashionCLIPEncoder._instance = None  # cleanup

    assert captured_source["source"] == "nonexistent/chicfinder-clip"
