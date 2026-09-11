from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


_STORE_ROWS = [{"id": "mobaco", "name": "Mobaco", "categories": ["tops", "bottoms"]}]

_ITEM_ROWS = [
    {
        "id": "mobaco_001_0",
        "category": "tops",
        "sub_category": "t-shirt",
        "color": "blue",
        "style": "casual",
        "brand": "Mobaco",
        "price": 400,
        "product_url": "https://mobaco.com",
        "availability": True,
        "image_key": "mobaco_001_0.jpg",
        "store_id": "mobaco",
        "title": "Blue Basic T-Shirt",
        "product_id": "001",
    }
]


def test_list_stores_comes_from_rds_not_local_json():
    """Regression: /stores was served from products.json/stores.json, which
    stopped shipping in the Docker image, so production silently returned []."""
    with patch("api.routes.stores.get_stores", return_value=_STORE_ROWS):
        response = client.get("/api/v1/stores")

    assert response.status_code == 200
    body = response.json()
    assert [s["id"] for s in body] == ["mobaco"]
    assert body[0]["name"] == "Mobaco"
    assert body[0]["categories"] == ["tops", "bottoms"]
    # No stores table exists yet — these have no source of truth.
    assert body[0]["logo_url"] is None
    assert body[0]["description"] is None


def test_list_stores_degrades_to_empty_when_rds_unavailable():
    """A DB outage must not 500 the endpoint — same posture as /search."""
    with patch("api.routes.stores.get_stores", side_effect=RuntimeError("no pool")):
        response = client.get("/api/v1/stores")

    assert response.status_code == 200
    assert response.json() == []


def test_get_store_maps_item_columns_and_builds_image_url(monkeypatch):
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("AWS_REGION", "eu-central-1")

    with patch("api.routes.stores.get_stores", return_value=_STORE_ROWS), \
         patch("api.routes.stores.get_items_by_store", return_value=_ITEM_ROWS):
        response = client.get("/api/v1/stores/mobaco")

    assert response.status_code == 200
    body = response.json()
    assert body["total_items"] == 1
    item = body["items"][0]
    assert item["name"] == "Blue Basic T-Shirt"   # title -> name
    assert item["type"] == "t-shirt"              # sub_category -> type
    assert item["price_egp"] == 400.0             # price -> price_egp
    assert item["image_url"] == (
        "https://test-bucket.s3.eu-central-1.amazonaws.com/mobaco_001_0.jpg"
    )


def test_get_store_404s_for_unknown_store():
    with patch("api.routes.stores.get_stores", return_value=_STORE_ROWS):
        response = client.get("/api/v1/stores/does-not-exist")

    assert response.status_code == 404


def test_store_items_category_and_search_filters():
    with patch("api.routes.stores.get_stores", return_value=_STORE_ROWS), \
         patch("api.routes.stores.get_items_by_store", return_value=_ITEM_ROWS):
        assert len(client.get("/api/v1/stores/mobaco/items").json()) == 1
        assert len(client.get("/api/v1/stores/mobaco/items?category=tops").json()) == 1
        assert len(client.get("/api/v1/stores/mobaco/items?category=shoes").json()) == 0
        assert len(client.get("/api/v1/stores/mobaco/items?search=blue").json()) == 1
        assert len(client.get("/api/v1/stores/mobaco/items?search=nothing").json()) == 0
