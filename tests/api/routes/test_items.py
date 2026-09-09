"""Tests for GET /api/v1/items, the cross-store catalog search.

Like the saved and account tests, this mounts the router on a bare app rather
than importing api.main, which would pull in torch and faiss for routes that
never touch them.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import stores

PRODUCTS = [
    {
        "id": "p1",
        "name": "Linen Shirt",
        "brand": "Kaftan Co",
        "category": "tops",
        "type": "shirt",
        "color": "white",
        "price_egp": 950,
        "sizes": ["M", "L"],
        "store_id": "s1",
        "description": "Breathable summer shirt",
    },
    {
        "id": "p2",
        "name": "Wide Leg Denim",
        "brand": "Linen House",
        "category": "bottoms",
        "type": "jeans",
        "color": "indigo",
        "price_egp": 1400,
        "sizes": ["30", "32"],
        "store_id": "s2",
        "description": "Relaxed through the leg",
    },
    {
        "id": "p3",
        "name": "Suede Loafer",
        "brand": "Cairo Leather",
        "category": "shoes",
        "type": "loafer",
        "color": "tan",
        "price_egp": 2200,
        "sizes": ["42"],
        "store_id": "s1",
        "description": "Hand finished",
    },
]


@pytest.fixture
def items_client() -> TestClient:
    app = FastAPI()
    app.include_router(stores.router, prefix="/api/v1")
    app.state.products = PRODUCTS
    app.state.products_lookup = {p["id"]: p for p in PRODUCTS}
    app.state.stores_lookup = {"s1": {"id": "s1"}, "s2": {"id": "s2"}}
    return TestClient(app)


def test_search_spans_every_store(items_client: TestClient):
    """The whole point of the endpoint: one query, all brands."""
    res = items_client.get("/api/v1/items", params={"search": "linen"})
    assert res.status_code == 200
    ids = [item["id"] for item in res.json()]
    assert set(ids) == {"p1", "p2"}


def test_name_match_outranks_brand_match(items_client: TestClient):
    """`Linen Shirt` should beat the item that only has Linen in its brand."""
    res = items_client.get("/api/v1/items", params={"search": "linen"})
    assert [item["id"] for item in res.json()] == ["p1", "p2"]


def test_search_is_case_insensitive_and_trimmed(items_client: TestClient):
    res = items_client.get("/api/v1/items", params={"search": "  LOAFER "})
    assert [item["id"] for item in res.json()] == ["p3"]


def test_store_id_narrows_to_one_brand(items_client: TestClient):
    res = items_client.get("/api/v1/items", params={"search": "linen", "store_id": "s1"})
    assert [item["id"] for item in res.json()] == ["p1"]


def test_unknown_store_id_is_404(items_client: TestClient):
    res = items_client.get("/api/v1/items", params={"store_id": "nope"})
    assert res.status_code == 404


def test_category_filter(items_client: TestClient):
    res = items_client.get("/api/v1/items", params={"category": "SHOES"})
    assert [item["id"] for item in res.json()] == ["p3"]


def test_no_search_returns_the_catalog(items_client: TestClient):
    res = items_client.get("/api/v1/items")
    assert len(res.json()) == len(PRODUCTS)


def test_limit_caps_the_response(items_client: TestClient):
    res = items_client.get("/api/v1/items", params={"limit": 2})
    assert len(res.json()) == 2


def test_no_match_is_an_empty_list_not_an_error(items_client: TestClient):
    res = items_client.get("/api/v1/items", params={"search": "snowboard"})
    assert res.status_code == 200
    assert res.json() == []


# ---------------------------------------------------------------------------
# GET /items/{item_id}
# ---------------------------------------------------------------------------


def test_get_one_item(items_client: TestClient):
    res = items_client.get("/api/v1/items/p2")
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == "p2"
    assert body["name"] == "Wide Leg Denim"
    assert body["sizes"] == ["30", "32"]


def test_get_one_item_falls_back_to_scanning_products(items_client: TestClient):
    """products_lookup is built at startup and may be absent in some contexts."""
    items_client.app.state.products_lookup = None
    res = items_client.get("/api/v1/items/p3")
    assert res.status_code == 200
    assert res.json()["id"] == "p3"


def test_unknown_item_is_404(items_client: TestClient):
    res = items_client.get("/api/v1/items/nope")
    assert res.status_code == 404


def test_collection_route_still_wins_over_the_detail_route(items_client: TestClient):
    """`/items` must list, not fall into `/items/{item_id}` with an empty id."""
    res = items_client.get("/api/v1/items")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
