"""
scripts/seed_catalog.py

Loads (or fully replaces) the ChicFinder product catalog: uploads images to
S3, inserts item records into RDS. This is the same tool for the first load
and for any later full catalog swap — pass --wipe to clear existing data
first.

Usage:
  python scripts/seed_catalog.py --images ./catalog/images --metadata ./catalog/metadata.json
  python scripts/seed_catalog.py --images ./new_catalog/images --metadata ./new_catalog/metadata.json --wipe
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import boto3
import psycopg2

from chic_finder.db import connection_kwargs_from_env

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
logger = logging.getLogger("seed_catalog")

CREATE_ITEMS_TABLE = """
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    category TEXT,
    sub_category TEXT,
    color TEXT,
    style TEXT,
    brand TEXT,
    price NUMERIC,
    product_url TEXT,
    availability BOOLEAN DEFAULT TRUE,
    image_key TEXT,
    store_id TEXT
);
"""

INSERT_ITEM = """
INSERT INTO items (id, category, sub_category, color, brand, style, price,
                    product_url, availability, image_key, store_id)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (id) DO UPDATE SET
    category = EXCLUDED.category,
    sub_category = EXCLUDED.sub_category,
    color = EXCLUDED.color,
    brand = EXCLUDED.brand,
    style = EXCLUDED.style,
    price = EXCLUDED.price,
    product_url = EXCLUDED.product_url,
    availability = EXCLUDED.availability,
    image_key = EXCLUDED.image_key,
    store_id = EXCLUDED.store_id;
"""


def seed_catalog(images_dir: Path, metadata_path: Path, bucket_name: str, db_connection, wipe: bool) -> None:
    s3 = boto3.client("s3")

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    with db_connection.cursor() as cursor:
        cursor.execute(CREATE_ITEMS_TABLE)

        if wipe:
            logger.info("Wiping existing catalog (S3 bucket contents + items table)...")
            paginator = s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket_name):
                for obj in page.get("Contents", []):
                    s3.delete_object(Bucket=bucket_name, Key=obj["Key"])
            cursor.execute("TRUNCATE items;")

        for item_id, record in metadata.items():
            image_filename = f"{item_id}.jpg"
            image_path = images_dir / image_filename
            if not image_path.exists():
                logger.warning("No image found for item '%s' at %s, skipping upload.", item_id, image_path)
                continue

            s3.upload_file(str(image_path), bucket_name, image_filename)
            logger.info("Uploaded %s -> s3://%s/%s", image_path, bucket_name, image_filename)

            cursor.execute(
                INSERT_ITEM,
                (
                    item_id,
                    record.get("category"),
                    record.get("sub_category"),
                    record.get("color"),
                    record.get("brand"),
                    record.get("style"),
                    record.get("price"),
                    record.get("product_url"),
                    record.get("availability", True),
                    image_filename,
                    record.get("store_id"),
                ),
            )

    db_connection.commit()
    logger.info("Seed complete: %d item(s) processed.", len(metadata))


def _connect_from_env():
    """Builds a psycopg2 connection using the shared connection-kwargs resolver."""
    return psycopg2.connect(**connection_kwargs_from_env())


def main() -> None:
    parser = argparse.ArgumentParser(description="Load or replace the ChicFinder catalog in S3 + RDS.")
    parser.add_argument("--images", type=str, required=True, help="Directory of catalog images.")
    parser.add_argument("--metadata", type=str, required=True, help="Path to the catalog metadata JSON.")
    parser.add_argument("--wipe", action="store_true", help="Wipe existing S3/RDS data before seeding.")
    args = parser.parse_args()

    bucket_name = os.environ["S3_BUCKET_NAME"]
    connection = _connect_from_env()
    try:
        seed_catalog(
            images_dir=Path(args.images),
            metadata_path=Path(args.metadata),
            bucket_name=bucket_name,
            db_connection=connection,
            wipe=args.wipe,
        )
    finally:
        connection.close()


if __name__ == "__main__":
    main()
