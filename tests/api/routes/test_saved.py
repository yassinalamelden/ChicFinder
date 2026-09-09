"""Tests for the saved-items routes backing the mobile wishlist."""

from unittest.mock import patch


def test_saved_returns_empty_list_when_nothing_saved(saved_account_client):
    with patch("api.routes.saved.db.list_saved_item_ids", return_value=[]):
        response = saved_account_client.get("/api/v1/saved")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_saved_preserves_newest_first_ordering_from_the_database(saved_account_client):
    """The DB returns IDs newest-first; enrichment must not reshuffle them."""
    ids = ["item-c", "item-a", "item-b"]
    rds_rows = {
        "item-a": {"id": "item-a", "title": "A", "brand": "Tomato", "price": 100.0},
        "item-b": {"id": "item-b", "title": "B", "brand": "Dice", "price": 200.0},
        "item-c": {"id": "item-c", "title": "C", "brand": "Town Team", "price": 300.0},
    }

    with patch("api.routes.saved.db.list_saved_item_ids", return_value=ids), patch(
        "api.routes.saved.db.get_items_by_ids", return_value=rds_rows
    ):
        response = saved_account_client.get("/api/v1/saved")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == ids


def test_saved_keeps_items_that_enrichment_cannot_resolve(saved_account_client):
    """A catalog change must never silently drop rows from a user's wishlist."""
    with patch(
        "api.routes.saved.db.list_saved_item_ids", return_value=["gone", "here"]
    ), patch(
        "api.routes.saved.db.get_items_by_ids",
        return_value={"here": {"id": "here", "title": "Here", "price": 50.0}},
    ):
        response = saved_account_client.get("/api/v1/saved")

    body = response.json()
    assert body["total"] == 2
    assert body["items"][0] == {
        "id": "gone",
        "name": None,
        "brand": None,
        "category": None,
        "price_egp": None,
        "image_url": None,
        "product_url": None,
        "store_id": None,
        "store_location": None,
    }
    assert body["items"][1]["name"] == "Here"


def test_saved_degrades_when_rds_enrichment_fails(saved_account_client):
    """Losing metadata should not 500 the wishlist — IDs are still useful."""
    with patch("api.routes.saved.db.list_saved_item_ids", return_value=["item-a"]), patch(
        "api.routes.saved.db.get_items_by_ids", side_effect=RuntimeError("RDS down")
    ):
        response = saved_account_client.get("/api/v1/saved")

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == "item-a"


def test_saved_returns_503_when_the_saved_table_is_unreachable(saved_account_client):
    with patch(
        "api.routes.saved.db.list_saved_item_ids", side_effect=RuntimeError("no pool")
    ):
        response = saved_account_client.get("/api/v1/saved")

    assert response.status_code == 503


def test_put_saved_is_scoped_to_the_authenticated_uid(saved_account_client):
    with patch("api.routes.saved.db.save_item") as mock_save:
        response = saved_account_client.put("/api/v1/saved/item-a")

    assert response.status_code == 204
    mock_save.assert_called_once_with("dev-user", "item-a")


def test_delete_saved_is_scoped_to_the_authenticated_uid(saved_account_client):
    with patch("api.routes.saved.db.unsave_item") as mock_unsave:
        response = saved_account_client.delete("/api/v1/saved/item-a")

    assert response.status_code == 204
    mock_unsave.assert_called_once_with("dev-user", "item-a")


def test_blank_item_id_is_rejected(saved_account_client):
    with patch("api.routes.saved.db.save_item") as mock_save:
        response = saved_account_client.put("/api/v1/saved/%20")

    assert response.status_code == 400
    mock_save.assert_not_called()


def test_saved_ids_endpoint_returns_bare_ids(saved_account_client):
    with patch("api.routes.saved.db.list_saved_item_ids", return_value=["a", "b"]):
        response = saved_account_client.get("/api/v1/saved/ids")

    assert response.status_code == 200
    assert response.json() == {"ids": ["a", "b"]}
