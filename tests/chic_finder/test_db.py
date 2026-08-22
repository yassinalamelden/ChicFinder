from unittest.mock import MagicMock, patch

from chic_finder.db import get_items_by_ids


def test_get_items_by_ids_returns_dict_keyed_by_id():
    fake_cursor = MagicMock()
    fake_cursor.description = [("id",), ("brand",), ("price",)]
    fake_cursor.fetchall.return_value = [("item1", "Tomato", 350.0)]
    fake_conn = MagicMock()
    fake_conn.cursor.return_value.__enter__.return_value = fake_cursor
    fake_pool = MagicMock()
    fake_pool.getconn.return_value = fake_conn

    with patch("chic_finder.db.get_pool", return_value=fake_pool):
        result = get_items_by_ids(["item1"])

    assert result == {"item1": {"id": "item1", "brand": "Tomato", "price": 350.0}}
    fake_pool.putconn.assert_called_once_with(fake_conn)


def test_get_items_by_ids_returns_empty_dict_without_querying_for_empty_input():
    assert get_items_by_ids([]) == {}
