# tests/test_recommend_endpoint.py
"""
Tests for POST /api/v1/recommend (multipart file upload, no auth required).
"""
import io
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from PIL import Image


ENC_PATCH = "api.routes.recommend.get_encoder"
SEARCH_PATCH = "api.routes.recommend.search_by_vector"


def _make_png_bytes():
    img = Image.new("RGB", (1, 1), color=(0, 128, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_jpeg_bytes():
    img = Image.new("RGB", (2, 2), color=(200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _mock_encoder():
    enc = MagicMock()
    enc._encode.return_value = np.ones(512, dtype=np.float32)
    enc._normalize.return_value = np.ones(512, dtype=np.float32)
    return enc


def _sample_results():
    return [
        {
            "id": "zara_001_0",
            "score": 0.92,
            "product_id": "prod-001",
            "title": "White Shirt",
            "brand": "Zara",
            "category": "Tops",
            "price": 350.0,
            "product_url": "https://example.com/1",
        }
    ]


@pytest.mark.integration
def test_valid_png_returns_200(test_client):
    with patch(ENC_PATCH, return_value=_mock_encoder()):
        with patch(SEARCH_PATCH, return_value=_sample_results()):
            r = test_client.post(
                "/api/v1/recommend",
                files={"file": ("outfit.png", _make_png_bytes(), "image/png")},
            )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["engine_used"] == "FashionCLIP_Supabase"
    assert len(body["recommendations"]) == 1


@pytest.mark.integration
def test_valid_jpeg_returns_200(test_client):
    with patch(ENC_PATCH, return_value=_mock_encoder()):
        with patch(SEARCH_PATCH, return_value=_sample_results()):
            r = test_client.post(
                "/api/v1/recommend",
                files={"file": ("outfit.jpg", _make_jpeg_bytes(), "image/jpeg")},
            )
    assert r.status_code == 200


@pytest.mark.edge
def test_invalid_extension_returns_400(test_client):
    r = test_client.post(
        "/api/v1/recommend",
        files={"file": ("document.pdf", b"pdf content", "application/pdf")},
    )
    assert r.status_code == 400
    assert "Invalid file type" in r.json()["detail"]


@pytest.mark.edge
def test_gif_extension_rejected(test_client):
    r = test_client.post(
        "/api/v1/recommend",
        files={"file": ("anim.gif", b"gif bytes", "image/gif")},
    )
    assert r.status_code == 400


@pytest.mark.edge
def test_corrupt_image_bytes_returns_400(test_client):
    r = test_client.post(
        "/api/v1/recommend",
        files={"file": ("bad.png", b"not an image at all", "image/png")},
    )
    assert r.status_code == 400
    assert "Invalid image format" in r.json()["detail"]


@pytest.mark.edge
def test_encoder_failure_returns_500(test_client):
    failing_enc = MagicMock()
    failing_enc._encode.side_effect = RuntimeError("CLIP model unavailable")
    with patch(ENC_PATCH, return_value=failing_enc):
        r = test_client.post(
            "/api/v1/recommend",
            files={"file": ("outfit.png", _make_png_bytes(), "image/png")},
        )
    assert r.status_code == 500
    assert "Recommendation failed" in r.json()["detail"]


@pytest.mark.edge
def test_supabase_failure_returns_500(test_client):
    with patch(ENC_PATCH, return_value=_mock_encoder()):
        with patch(SEARCH_PATCH, side_effect=Exception("DB down")):
            r = test_client.post(
                "/api/v1/recommend",
                files={"file": ("outfit.png", _make_png_bytes(), "image/png")},
            )
    assert r.status_code == 500
    assert "Recommendation failed" in r.json()["detail"]


@pytest.mark.edge
def test_empty_results_returns_200(test_client):
    with patch(ENC_PATCH, return_value=_mock_encoder()):
        with patch(SEARCH_PATCH, return_value=[]):
            r = test_client.post(
                "/api/v1/recommend",
                files={"file": ("outfit.png", _make_png_bytes(), "image/png")},
            )
    assert r.status_code == 200
    assert r.json()["recommendations"][0]["recommendations"] == []


@pytest.mark.edge
def test_no_file_returns_422(test_client):
    r = test_client.post("/api/v1/recommend")
    assert r.status_code == 422


@pytest.mark.integration
def test_result_item_schema(test_client):
    with patch(ENC_PATCH, return_value=_mock_encoder()):
        with patch(SEARCH_PATCH, return_value=_sample_results()):
            r = test_client.post(
                "/api/v1/recommend",
                files={"file": ("outfit.png", _make_png_bytes(), "image/png")},
            )
    assert r.status_code == 200
    rec = r.json()["recommendations"][0]["recommendations"][0]
    assert "id" in rec
    assert "category" in rec
    assert "image_url" in rec
    assert "price" in rec
    assert "brand" in rec
