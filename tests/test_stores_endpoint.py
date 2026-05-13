# tests/test_stores_endpoint.py
"""
Tests for GET /api/v1/stores, GET /api/v1/stores/{id}, GET /api/v1/stores/{id}/items.
Supabase client is fully mocked per test.
"""
import pytest
from unittest.mock import MagicMock, patch

from api.routes.stores import _slug, _build_store, _build_item

PATCH_CLIENT = "api.routes.stores.get_supabase_client"


def _brand_rows(brands_and_cats):
    """Return rows shaped like products SELECT brand, category, product_id."""
    return [
        {"brand": b, "category": c, "product_id": f"prod-{i:03d}"}
        for i, (b, c) in enumerate(brands_and_cats)
    ]


def _product_rows(brand="Zara", n=3):
    return [
        {
            "id": i + 1,
            "product_id": f"prod-{i:03d}",
            "title": f"{brand} Item {i}",
            "brand": brand,
            "category": "Tops",
            "price": float((i + 1) * 150),
            "product_url": f"https://example.com/{i}",
            "description": "Nice item",
            "availability": "InStock",
        }
        for i in range(n)
    ]


def _mock_client_for_list_stores(rows):
    """Mock: client.table(...).select(...).execute().data = rows"""
    m = MagicMock()
    m.table.return_value.select.return_value.execute.return_value.data = rows
    return m


def _mock_client_for_get_store(brand, product_rows, embedding_rows=None):
    """Mock client for get_store and get_store_items."""
    embedding_rows = embedding_rows or []
    m = MagicMock()

    # First call: _resolve_brand  → SELECT brand
    # Second call: product rows   → SELECT id, product_id, ...
    # Third call: embeddings       → SELECT product_id, image_filename
    all_brand_rows = [{"brand": brand}]

    call_count = {"n": 0}

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "products":
            def select_side_effect(fields):
                call_count["n"] += 1
                sel = MagicMock()
                if "brand" in fields and "category" not in fields and call_count["n"] == 1:
                    sel.execute.return_value.data = all_brand_rows
                else:
                    sel.execute.return_value.data = product_rows
                    sel.eq.return_value = sel
                    sel.ilike.return_value = sel
                return sel
            tbl.select.side_effect = select_side_effect
        elif name == "embeddings":
            sel = MagicMock()
            sel.in_.return_value.execute.return_value.data = embedding_rows
            tbl.select.return_value = sel
        return tbl

    m.table.side_effect = table_side_effect
    return m


# ── Unit tests for pure helper functions ──────────────────────────────────────

@pytest.mark.unit
def test_slug_spaces_become_dashes():
    assert _slug("Louis Vuitton") == "louis-vuitton"


@pytest.mark.unit
def test_slug_underscores_become_dashes():
    assert _slug("under_score") == "under-score"


@pytest.mark.unit
def test_slug_lowercases():
    assert _slug("ZARA") == "zara"


@pytest.mark.unit
def test_build_store_categories_sorted():
    entries = [
        {"brand": "Zara", "category": "Shoes"},
        {"brand": "Zara", "category": "Accessories"},
        {"brand": "Zara", "category": "Tops"},
    ]
    store = _build_store("Zara", entries)
    assert store.categories == ["Accessories", "Shoes", "Tops"]


@pytest.mark.unit
def test_build_store_filters_none_categories():
    entries = [
        {"brand": "Zara", "category": "Tops"},
        {"brand": "Zara", "category": None},
    ]
    store = _build_store("Zara", entries)
    assert None not in store.categories
    assert "Tops" in store.categories


@pytest.mark.unit
def test_build_store_total_items_is_entry_count():
    entries = [{"brand": "Zara", "category": "Tops"}] * 7
    store = _build_store("Zara", entries)
    assert store.total_items == 7


@pytest.mark.unit
def test_build_item_none_price_becomes_zero():
    row = {
        "id": 1,
        "product_id": "prod-001",
        "title": "Test Shirt",
        "brand": "Zara",
        "category": "Tops",
        "price": None,
        "product_url": "https://example.com",
        "description": "Desc",
        "availability": "InStock",
    }
    item = _build_item(row, {}, "zara")
    assert item.price_egp == 0.0


@pytest.mark.unit
def test_build_item_store_id_attached():
    row = {
        "id": 1,
        "product_id": "prod-001",
        "title": "Shirt",
        "brand": "Zara",
        "category": "Tops",
        "price": 200.0,
        "product_url": "https://example.com",
        "description": "",
        "availability": "InStock",
    }
    item = _build_item(row, {}, "zara")
    assert item.store_id == "zara"


# ── Integration tests for list_stores ─────────────────────────────────────────

@pytest.mark.integration
def test_list_stores_returns_200(test_client, sample_product_rows):
    rows = _brand_rows([("Zara", "Tops"), ("Zara", "Bottoms"), ("H&M", "Tops")])
    with patch(PATCH_CLIENT, return_value=_mock_client_for_list_stores(rows)):
        r = test_client.get("/api/v1/stores")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    names = [s["name"] for s in body]
    assert "Zara" in names
    assert "H&M" in names


@pytest.mark.integration
def test_list_stores_deduplicates_product_ids(test_client):
    rows = [
        {"brand": "Zara", "category": "Tops", "product_id": "prod-001"},
        {"brand": "Zara", "category": "Tops", "product_id": "prod-001"},  # duplicate
        {"brand": "Zara", "category": "Tops", "product_id": "prod-002"},
    ]
    with patch(PATCH_CLIENT, return_value=_mock_client_for_list_stores(rows)):
        r = test_client.get("/api/v1/stores")
    assert r.status_code == 200
    zara = next(s for s in r.json() if s["name"] == "Zara")
    assert zara["total_items"] == 2


@pytest.mark.edge
def test_list_stores_empty_database(test_client):
    with patch(PATCH_CLIENT, return_value=_mock_client_for_list_stores([])):
        r = test_client.get("/api/v1/stores")
    assert r.status_code == 200
    assert r.json() == []


# ── Integration tests for get_store ───────────────────────────────────────────

@pytest.mark.integration
def test_get_store_known_id_returns_200(test_client):
    prod_rows = _product_rows("Zara", 2)
    mock_client = _mock_client_for_get_store("Zara", prod_rows)
    with patch(PATCH_CLIENT, return_value=mock_client):
        r = test_client.get("/api/v1/stores/zara")
    assert r.status_code == 200
    body = r.json()
    assert body["store"]["name"] == "Zara"
    assert body["store"]["id"] == "zara"
    assert "items" in body
    assert "total_items" in body


@pytest.mark.edge
def test_get_store_unknown_id_returns_404(test_client):
    m = MagicMock()
    m.table.return_value.select.return_value.execute.return_value.data = []
    with patch(PATCH_CLIENT, return_value=m):
        r = test_client.get("/api/v1/stores/ghost-brand")
    assert r.status_code == 404
    assert "ghost-brand" in r.json()["detail"]


# ── Integration tests for get_store_items ─────────────────────────────────────

@pytest.mark.integration
def test_get_store_items_no_filters(test_client):
    prod_rows = _product_rows("Zara", 3)
    mock_client = _mock_client_for_get_store("Zara", prod_rows)
    with patch(PATCH_CLIENT, return_value=mock_client):
        r = test_client.get("/api/v1/stores/zara/items")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert all(item["brand"] == "Zara" for item in body)
    assert all(item["store_id"] == "zara" for item in body)


@pytest.mark.integration
def test_get_store_items_category_filter_applied(test_client):
    """The query chain should include .ilike('category', 'tops')."""
    prod_rows = _product_rows("Zara", 1)
    # Build a mock that tracks ilike calls
    m = MagicMock()
    # _resolve_brand call
    brand_sel = MagicMock()
    brand_sel.execute.return_value.data = [{"brand": "Zara"}]
    # products query chain
    prod_sel = MagicMock()
    prod_sel.eq.return_value = prod_sel
    prod_sel.ilike.return_value = prod_sel
    prod_sel.execute.return_value.data = prod_rows
    # embeddings
    emb_sel = MagicMock()
    emb_sel.in_.return_value.execute.return_value.data = []

    call_n = {"n": 0}
    def tbl(name):
        t = MagicMock()
        if name == "products":
            def sel(fields):
                call_n["n"] += 1
                if call_n["n"] == 1:
                    return brand_sel
                return prod_sel
            t.select.side_effect = sel
        else:
            t.select.return_value = emb_sel
        return t
    m.table.side_effect = tbl

    with patch(PATCH_CLIENT, return_value=m):
        r = test_client.get("/api/v1/stores/zara/items?category=tops")
    assert r.status_code == 200
    prod_sel.ilike.assert_called_with("category", "tops")


@pytest.mark.integration
def test_get_store_items_search_filter_applied(test_client):
    """The query chain should include .ilike('title', '%shirt%')."""
    prod_rows = _product_rows("Zara", 1)
    m = MagicMock()
    brand_sel = MagicMock()
    brand_sel.execute.return_value.data = [{"brand": "Zara"}]
    prod_sel = MagicMock()
    prod_sel.eq.return_value = prod_sel
    prod_sel.ilike.return_value = prod_sel
    prod_sel.execute.return_value.data = prod_rows
    emb_sel = MagicMock()
    emb_sel.in_.return_value.execute.return_value.data = []

    call_n = {"n": 0}
    def tbl(name):
        t = MagicMock()
        if name == "products":
            def sel(fields):
                call_n["n"] += 1
                return brand_sel if call_n["n"] == 1 else prod_sel
            t.select.side_effect = sel
        else:
            t.select.return_value = emb_sel
        return t
    m.table.side_effect = tbl

    with patch(PATCH_CLIENT, return_value=m):
        r = test_client.get("/api/v1/stores/zara/items?search=shirt")
    assert r.status_code == 200
    prod_sel.ilike.assert_called_with("title", "%shirt%")


@pytest.mark.edge
def test_get_store_items_unknown_store_404(test_client):
    m = MagicMock()
    m.table.return_value.select.return_value.execute.return_value.data = []
    with patch(PATCH_CLIENT, return_value=m):
        r = test_client.get("/api/v1/stores/ghost-brand/items")
    assert r.status_code == 404
