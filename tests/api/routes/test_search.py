from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_search_enriches_results_from_rds_not_app_state():
    fake_search_results = [{"id": "item1.jpg", "score": 0.92}]
    fake_metadata = {
        "item1": {
            "brand": "Tomato",
            "price": 350.0,
            "product_url": "https://tomato.example.com/item1",
        }
    }

    with patch(
        "api.routes.search.search_similar_items", return_value=fake_search_results
    ), patch(
        "api.routes.search.get_items_by_ids", return_value=fake_metadata
    ) as mock_get_items:
        response = client.post(
            "/api/v1/search",
            json={"image_base64": "aGVsbG8="},  # "hello" base64, decoding is mocked away
        )

    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["image_id"] == "item1"
    assert body["results"][0]["brand"] == "Tomato"
    assert body["results"][0]["price_egp"] == 350.0
    mock_get_items.assert_called_once_with(["item1"])
