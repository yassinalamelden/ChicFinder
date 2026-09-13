"""Tests for /api/v1/items, the catalog search behind the mobile app.

Two paths are covered deliberately. Production reads RDS; local development,
which has no Postgres at all, falls back to the in-memory catalog. The bug that
made /stores serve `200 []` in production was exactly this distinction going
unnoticed, so both paths are pinned here.

Mounted on a bare app rather than importing api.main, which would pull in torch
and faiss for routes that never touch them.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import items as items_route
from chic_finder import db

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

# The shape chic_finder.db returns: RDS column names, not the JSON ones.
ROWS = [
    {
        "id": 41,
        "title": "Linen Shirt",
        "brand": "Kaftan Co",
        "category": "tops",
        "sub_category": "shirt",
        "color": "white",
        "price": 950,
        "product_url": "https://example.test/p/41",
        "image_key": "catalog/41.jpg",
        "store_id": "s1",
    }
]


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    app.include_router(items_route.router, prefix="/api/v1")
    app.state.products = PRODUCTS
    app.state.products_lookup = {p["id"]: p for p in PRODUCTS}
    return app


@pytest.fixture
def client(app: FastAPI, monkeypatch) -> TestClient:
    """No pool, so every request takes the local fallback path."""
    monkeypatch.setattr(db, "get_pool", lambda: (_ for _ in ()).throw(RuntimeError()))
    return TestClient(app)


@pytest.fixture
def rds_client(app: FastAPI, monkeypatch) -> TestClient:
    """A pool exists, so every request must go to RDS and never to app.state."""
    monkeypatch.setattr(db, "get_pool", lambda: object())
    monkeypatch.setattr(
        db, "search_catalog", lambda *args, **kwargs: list(ROWS)
    )
    monkeypatch.setattr(
        db, "get_items_by_ids", lambda ids: {"41": ROWS[0]} if "41" in ids else {}
    )
    return TestClient(app)


# ---------------------------------------------------------------------------
# Local fallback path
# ---------------------------------------------------------------------------


def test_search_spans_every_store(client: TestClient):
    res = client.get("/api/v1/items", params={"search": "linen"})
    assert res.status_code == 200
    assert {item["id"] for item in res.json()} == {"p1", "p2"}


def test_name_match_outranks_brand_match(client: TestClient):
    """`Linen Shirt` should beat the item that only has Linen in its brand."""
    res = client.get("/api/v1/items", params={"search": "linen"})
    assert [item["id"] for item in res.json()] == ["p1", "p2"]


def test_search_is_case_insensitive_and_trimmed(client: TestClient):
    res = client.get("/api/v1/items", params={"search": "  LOAFER "})
    assert [item["id"] for item in res.json()] == ["p3"]


def test_store_id_narrows_to_one_brand(client: TestClient):
    res = client.get("/api/v1/items", params={"search": "linen", "store_id": "s1"})
    assert [item["id"] for item in res.json()] == ["p1"]


def test_category_filter(client: TestClient):
    res = client.get("/api/v1/items", params={"category": "SHOES"})
    assert [item["id"] for item in res.json()] == ["p3"]


def test_no_search_returns_the_catalog(client: TestClient):
    assert len(client.get("/api/v1/items").json()) == len(PRODUCTS)


def test_limit_caps_the_response(client: TestClient):
    assert len(client.get("/api/v1/items", params={"limit": 2}).json()) == 2


def test_no_match_is_an_empty_list_not_an_error(client: TestClient):
    res = client.get("/api/v1/items", params={"search": "snowboard"})
    assert res.status_code == 200
    assert res.json() == []


def test_get_one_item(client: TestClient):
    body = client.get("/api/v1/items/p2").json()
    assert body["id"] == "p2"
    assert body["sizes"] == ["30", "32"]


def test_unknown_item_is_404(client: TestClient):
    assert client.get("/api/v1/items/nope").status_code == 404


def test_collection_route_still_wins_over_the_detail_route(client: TestClient):
    """`/items` must list, not fall into `/items/{item_id}` with an empty id."""
    res = client.get("/api/v1/items")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# ---------------------------------------------------------------------------
# RDS path
# ---------------------------------------------------------------------------


def test_rds_is_preferred_over_the_local_catalog(rds_client: TestClient):
    """With a pool present the local products must be ignored entirely."""
    body = rds_client.get("/api/v1/items", params={"search": "linen"}).json()
    assert [item["id"] for item in body] == ["41"]


def test_rds_row_maps_onto_the_response_shape(rds_client: TestClient):
    item = rds_client.get("/api/v1/items", params={"search": "linen"}).json()[0]
    assert item["name"] == "Linen Shirt"       # from `title`
    assert item["type"] == "shirt"             # from `sub_category`
    assert item["price_egp"] == 950.0          # from `price`
    assert item["store_id"] == "s1"
    # No column for either in the catalog schema, so they are empty, not invented.
    assert item["sizes"] == []
    assert item["description"] is None


def test_rds_detail_lookup(rds_client: TestClient):
    assert rds_client.get("/api/v1/items/41").json()["id"] == "41"


def test_rds_detail_missing_is_404(rds_client: TestClient):
    assert rds_client.get("/api/v1/items/999").status_code == 404
