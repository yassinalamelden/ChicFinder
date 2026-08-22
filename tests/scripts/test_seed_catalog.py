import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.seed_catalog import seed_catalog


@pytest.fixture
def sample_catalog(tmp_path):
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    (images_dir / "item1.jpg").write_bytes(b"fake-image-bytes")

    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "item1": {
                    "category": "shirt",
                    "sub_category": "t-shirt",
                    "color": "white",
                    "style": "casual",
                    "brand": "Tomato",
                    "price": 350.0,
                    "product_url": "https://tomato.example.com/item1",
                    "availability": True,
                    "store_id": "tomato",
                }
            }
        )
    )
    return images_dir, metadata_path


@mock_aws
def test_seed_catalog_uploads_images_and_inserts_records(sample_catalog):
    images_dir, metadata_path = sample_catalog

    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-chicfinder-catalog")

    fake_cursor = MagicMock()
    fake_conn = MagicMock()
    fake_conn.cursor.return_value.__enter__.return_value = fake_cursor

    seed_catalog(
        images_dir=images_dir,
        metadata_path=metadata_path,
        bucket_name="test-chicfinder-catalog",
        db_connection=fake_conn,
        wipe=False,
    )

    uploaded = s3.list_objects_v2(Bucket="test-chicfinder-catalog")
    uploaded_keys = [obj["Key"] for obj in uploaded.get("Contents", [])]
    assert "item1.jpg" in uploaded_keys

    insert_calls = [
        call for call in fake_cursor.execute.call_args_list if "INSERT INTO items" in call.args[0]
    ]
    assert len(insert_calls) == 1
    assert insert_calls[0].args[1][0] == "item1"  # id
    assert insert_calls[0].args[1][4] == "Tomato"  # brand


@mock_aws
def test_seed_catalog_wipes_existing_data_first_when_requested(sample_catalog):
    images_dir, metadata_path = sample_catalog

    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-chicfinder-catalog")
    s3.put_object(Bucket="test-chicfinder-catalog", Key="old_item.jpg", Body=b"stale")

    fake_cursor = MagicMock()
    fake_conn = MagicMock()
    fake_conn.cursor.return_value.__enter__.return_value = fake_cursor

    seed_catalog(
        images_dir=images_dir,
        metadata_path=metadata_path,
        bucket_name="test-chicfinder-catalog",
        db_connection=fake_conn,
        wipe=True,
    )

    remaining = s3.list_objects_v2(Bucket="test-chicfinder-catalog")
    remaining_keys = [obj["Key"] for obj in remaining.get("Contents", [])]
    assert "old_item.jpg" not in remaining_keys
    assert "item1.jpg" in remaining_keys

    truncate_calls = [
        call for call in fake_cursor.execute.call_args_list if "TRUNCATE" in call.args[0]
    ]
    assert len(truncate_calls) == 1
