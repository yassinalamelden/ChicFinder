# tests/test_search_endpoint.py
"""
Integration tests for POST /api/v1/search.
Auth is bypassed via the test_client fixture; only search_similar_items is mocked.
"""
import base64
import pytest
from unittest.mock import patch


PATCH = "api.routes.search.search_similar_items"


def _make_rows(prices, brands=None, product_ids=None):
    brands = brands or ["Zara"] * len(prices)
    ids = product_ids or [f"prod-{i:03d}" for i in range(len(prices))]
    return [
        {
            "id": f"item_{i}_0",
            "filename": f"item_{i}_0.jpg",
            "score": 0.9,
            "product_id": ids[i],
            "title": f"Item {i}",
            "brand": brands[i],
            "category": "Tops",
            "price": prices[i],
            "product_url": f"https://example.com/{i}",
        }
        for i in range(len(prices))
    ]


@pytest.mark.integration
def test_valid_request_returns_200(test_client, minimal_png_b64, sample_search_rows):
    with patch(PATCH, return_value=sample_search_rows):
        r = test_client.post("/api/v1/search", json={"image_base64": minimal_png_b64})
    assert r.status_code == 200
    body = r.json()
    assert "results" in body
    assert "processing_time_ms" in body
    assert len(body["results"]) == 5


@pytest.mark.integration
def test_cap_at_5_results(test_client, minimal_png_b64):
    rows = _make_rows([100.0] * 20, product_ids=[f"prod-{i:03d}" for i in range(20)])
    with patch(PATCH, return_value=rows):
        r = test_client.post("/api/v1/search", json={"image_base64": minimal_png_b64})
    assert r.status_code == 200
    assert len(r.json()["results"]) == 5


@pytest.mark.integration
def test_deduplicate_product_ids(test_client, minimal_png_b64):
    # items 0 and 2 share the same product_id
    rows = _make_rows([100.0, 200.0, 300.0], product_ids=["prod-A", "prod-B", "prod-A"])
    with patch(PATCH, return_value=rows):
        r = test_client.post("/api/v1/search", json={"image_base64": minimal_png_b64})
    assert r.status_code == 200
    assert len(r.json()["results"]) == 2


@pytest.mark.integration
def test_brand_filter(test_client, minimal_png_b64):
    rows = _make_rows([100.0] * 5, brands=["Zara", "Zara", "H&M", "H&M", "H&M"])
    with patch(PATCH, return_value=rows):
        r = test_client.post(
            "/api/v1/search",
            json={"image_base64": minimal_png_b64, "brands": ["Zara"]},
        )
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 2
    assert all(item["brand"] == "Zara" for item in results)


@pytest.mark.edge
def test_brand_filter_case_insensitive(test_client, minimal_png_b64):
    rows = _make_rows([100.0, 200.0], brands=["ZARA", "H&M"])
    with patch(PATCH, return_value=rows):
        r = test_client.post(
            "/api/v1/search",
            json={"image_base64": minimal_png_b64, "brands": ["zara"]},
        )
    assert r.status_code == 200
    assert len(r.json()["results"]) == 1


@pytest.mark.integration
def test_min_price_filter(test_client, minimal_png_b64):
    rows = _make_rows([100.0, 200.0, 300.0, 400.0, 500.0])
    with patch(PATCH, return_value=rows):
        r = test_client.post(
            "/api/v1/search",
            json={"image_base64": minimal_png_b64, "min_price": 250.0},
        )
    results = r.json()["results"]
    assert all(item["price_egp"] >= 250.0 for item in results)
    assert len(results) == 3


@pytest.mark.integration
def test_max_price_filter(test_client, minimal_png_b64):
    rows = _make_rows([100.0, 200.0, 300.0, 400.0, 500.0])
    with patch(PATCH, return_value=rows):
        r = test_client.post(
            "/api/v1/search",
            json={"image_base64": minimal_png_b64, "max_price": 350.0},
        )
    results = r.json()["results"]
    assert all(item["price_egp"] <= 350.0 for item in results)
    assert len(results) == 3


@pytest.mark.integration
def test_price_range_filter(test_client, minimal_png_b64):
    rows = _make_rows([100.0, 200.0, 300.0, 400.0, 500.0])
    with patch(PATCH, return_value=rows):
        r = test_client.post(
            "/api/v1/search",
            json={"image_base64": minimal_png_b64, "min_price": 150.0, "max_price": 350.0},
        )
    results = r.json()["results"]
    assert len(results) == 2
    assert all(150.0 <= item["price_egp"] <= 350.0 for item in results)


@pytest.mark.edge
def test_price_filter_skips_none_price(test_client, minimal_png_b64):
    rows = _make_rows([200.0, None, 300.0])
    with patch(PATCH, return_value=rows):
        r = test_client.post(
            "/api/v1/search",
            json={"image_base64": minimal_png_b64, "min_price": 100.0},
        )
    # None-price item is excluded when a price filter is active
    assert r.status_code == 200
    assert len(r.json()["results"]) == 2


@pytest.mark.edge
def test_malformed_b64_returns_400(test_client):
    r = test_client.post("/api/v1/search", json={"image_base64": "not-valid-base64!!!"})
    assert r.status_code == 400
    assert "Invalid image format" in r.json()["detail"]


@pytest.mark.edge
def test_valid_b64_non_image_returns_400(test_client):
    b64 = base64.b64encode(b"this is just text, not an image").decode()
    r = test_client.post("/api/v1/search", json={"image_base64": b64})
    assert r.status_code == 400
    assert "Invalid image data" in r.json()["detail"]


@pytest.mark.edge
def test_data_uri_prefix_stripped(test_client, minimal_png_b64):
    with patch(PATCH, return_value=[]):
        r = test_client.post(
            "/api/v1/search",
            json={"image_base64": f"data:image/png;base64,{minimal_png_b64}"},
        )
    assert r.status_code == 200


@pytest.mark.edge
def test_missing_b64_padding_handled(test_client, minimal_png_b64):
    # Strip trailing '=' to simulate missing padding
    stripped = minimal_png_b64.rstrip("=")
    with patch(PATCH, return_value=[]):
        r = test_client.post("/api/v1/search", json={"image_base64": stripped})
    assert r.status_code == 200


@pytest.mark.edge
def test_supabase_failure_returns_500(test_client, minimal_png_b64):
    with patch(PATCH, side_effect=Exception("Supabase RPC failed")):
        r = test_client.post("/api/v1/search", json={"image_base64": minimal_png_b64})
    assert r.status_code == 500
    assert r.json()["detail"] == "Search failed. Please try again."


@pytest.mark.integration
def test_response_schema(test_client, minimal_png_b64, sample_search_rows):
    with patch(PATCH, return_value=sample_search_rows[:1]):
        r = test_client.post("/api/v1/search", json={"image_base64": minimal_png_b64})
    assert r.status_code == 200
    item = r.json()["results"][0]
    assert "image_id" in item
    assert "similarity_score" in item
    assert item["availability"] == "InStock"
    assert item["availability_egypt"] is True
    assert isinstance(item["image_urls"], list)
