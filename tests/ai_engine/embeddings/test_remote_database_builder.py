import json
from unittest.mock import MagicMock, patch

import boto3
import numpy as np
from moto import mock_aws

from ai_engine.embeddings.remote_database_builder import RemoteIndexBuilder


@mock_aws
def test_build_indexes_items_from_s3_and_rds(tmp_path):
    bucket_name = "test-chicfinder-catalog"
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=bucket_name)
    s3.put_object(Bucket=bucket_name, Key="item1.jpg", Body=b"fake-image-bytes")

    fake_cursor = MagicMock()
    fake_cursor.fetchall.return_value = [("item1", "item1.jpg")]
    fake_conn = MagicMock()
    fake_conn.cursor.return_value.__enter__.return_value = fake_cursor
    fake_pool = MagicMock()
    fake_pool.getconn.return_value = fake_conn

    index_path = tmp_path / "embeddings.index"
    mapping_path = tmp_path / "index_to_image_id.json"

    with patch(
        "ai_engine.embeddings.remote_database_builder.get_pool", return_value=fake_pool
    ), patch(
        "ai_engine.embeddings.remote_database_builder.get_encoder"
    ) as mock_get_encoder:
        mock_get_encoder.return_value.encode.return_value = np.ones(512, dtype=np.float32)

        builder = RemoteIndexBuilder(
            bucket_name=bucket_name, index_path=index_path, mapping_path=mapping_path
        )
        builder.build()

    assert index_path.exists()
    mapping = json.loads(mapping_path.read_text())
    assert mapping == {"0": "item1.jpg"}


@mock_aws
def test_build_raises_when_no_items_in_rds(tmp_path):
    bucket_name = "test-chicfinder-catalog"
    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=bucket_name)

    fake_cursor = MagicMock()
    fake_cursor.fetchall.return_value = []
    fake_conn = MagicMock()
    fake_conn.cursor.return_value.__enter__.return_value = fake_cursor
    fake_pool = MagicMock()
    fake_pool.getconn.return_value = fake_conn

    with patch(
        "ai_engine.embeddings.remote_database_builder.get_pool", return_value=fake_pool
    ), patch("ai_engine.embeddings.remote_database_builder.get_encoder"):
        builder = RemoteIndexBuilder(
            bucket_name=bucket_name,
            index_path=tmp_path / "embeddings.index",
            mapping_path=tmp_path / "index_to_image_id.json",
        )
        try:
            builder.build()
            assert False, "expected ValueError"
        except ValueError as exc:
            assert "items" in str(exc)
