"""
ai_engine/embeddings/remote_database_builder.py
=================================================
Production counterpart to database_builder.py's FAISSIndexBuilder: builds the
FAISS index from the RDS `items` table + S3 catalog images, instead of local
data/raw_images/ + data/metadata.json.

Output format (embeddings.index + index_to_image_id.json) is identical to
the local builder's: each mapping entry is a dict carrying the item's id,
image location, and catalog metadata (category/sub_category/color/style/
brand/price) so vector_store.py's search results are never metadata-blind.

Used automatically by scripts/02_build_faiss_index.py when S3_BUCKET_NAME is set.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import boto3
import numpy as np
from tqdm import tqdm

from ai_engine.embeddings.encoder import EMBEDDING_DIM, get_encoder
from chic_finder.db import ITEM_COLUMNS, get_pool

logger = logging.getLogger(__name__)

DEFAULT_INDEX_PATH = Path("data/embeddings.index")
DEFAULT_MAPPING_PATH = Path("data/index_to_image_id.json")

_ITEM_COLUMN_NAMES = [c.strip() for c in ITEM_COLUMNS.split(",")]


class RemoteIndexBuilder:
    """Builds a FAISS IndexFlatIP from the RDS `items` table + S3 images."""

    def __init__(
        self,
        bucket_name: str,
        index_path: Path = DEFAULT_INDEX_PATH,
        mapping_path: Path = DEFAULT_MAPPING_PATH,
    ) -> None:
        self.bucket_name = bucket_name
        self.index_path = Path(index_path)
        self.mapping_path = Path(mapping_path)
        self._encoder = get_encoder()
        self._s3 = boto3.client("s3")

    def build(self) -> None:
        import faiss

        items = self._load_items()
        if not items:
            raise ValueError(
                "No items found in the `items` table. Run scripts/seed_catalog.py first."
            )

        logger.info("Building FAISS index for %d candidate items from S3/RDS...", len(items))

        index = faiss.IndexFlatIP(EMBEDDING_DIM)
        mapping: dict[str, dict] = {}

        for item in tqdm(items, desc="Indexing items", unit="item"):
            item_id = item["id"]
            image_key = item.get("image_key")
            if not image_key:
                logger.warning("Skipping %s: no image_key in RDS.", item_id)
                continue
            try:
                vector = self._embed_s3_image(image_key)
                faiss_id = str(index.ntotal)
                index.add(np.expand_dims(vector, axis=0))
                mapping[faiss_id] = {
                    "id": str(item_id),
                    "filename": image_key,
                    "image_url": self._public_image_url(image_key),
                    "category": item.get("category"),
                    "sub_category": item.get("sub_category"),
                    "color": item.get("color"),
                    "style": item.get("style"),
                    "brand": item.get("brand"),
                    "price": item.get("price"),
                }
            except Exception as exc:
                logger.warning("Skipping %s: %s", item_id, exc)

        if index.ntotal == 0:
            raise ValueError("No valid items were indexed. Check S3 image availability.")

        self._save(index, mapping)
        logger.info("Index built successfully: %d vectors", index.ntotal)

    def _load_items(self) -> list[dict]:
        """Returns the full catalog row (all ITEM_COLUMNS) for every item in RDS
        that has an image, so the FAISS mapping can be built with real metadata
        instead of just an id/image_key pair."""
        pool = get_pool()
        conn = pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"SELECT {ITEM_COLUMNS} FROM items WHERE image_key IS NOT NULL;"
                )
                return [dict(zip(_ITEM_COLUMN_NAMES, row)) for row in cursor.fetchall()]
        finally:
            conn.rollback()
            pool.putconn(conn)

    def _embed_s3_image(self, image_key: str) -> np.ndarray:
        obj = self._s3.get_object(Bucket=self.bucket_name, Key=image_key)
        image_bytes = obj["Body"].read()
        return self._encoder.encode(image_bytes)

    def _public_image_url(self, image_key: str) -> str:
        """CatalogImages is a public-read bucket (infrastructure/cdk/chicfinder_constructs/storage.py)."""
        region = self._s3.meta.region_name
        return f"https://{self.bucket_name}.s3.{region}.amazonaws.com/{image_key}"

    def _save(self, index, mapping: dict[str, str]) -> None:
        import faiss

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.mapping_path.parent.mkdir(parents=True, exist_ok=True)

        faiss.write_index(index, str(self.index_path))
        with open(self.mapping_path, "w", encoding="utf-8") as file_obj:
            json.dump(mapping, file_obj, indent=2)

        logger.info("Saved index   -> %s", self.index_path)
        logger.info("Saved mapping -> %s", self.mapping_path)
