"""
ai_engine/embeddings/remote_database_builder.py
=================================================
Production counterpart to database_builder.py's FAISSIndexBuilder: builds the
FAISS index from the RDS `items` table + S3 catalog images, instead of local
data/raw_images/ + data/metadata.json.

Output format (embeddings.index + index_to_image_id.json) is identical to
the local builder's, so vector_store.py needs no changes — S3 keys and local
filenames both follow the `{item_id}.jpg` convention.

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
from chic_finder.db import get_pool

logger = logging.getLogger(__name__)

DEFAULT_INDEX_PATH = Path("data/embeddings.index")
DEFAULT_MAPPING_PATH = Path("data/index_to_image_id.json")


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
        mapping: dict[str, str] = {}

        for item_id, image_key in tqdm(items, desc="Indexing items", unit="item"):
            if not image_key:
                logger.warning("Skipping %s: no image_key in RDS.", item_id)
                continue
            try:
                vector = self._embed_s3_image(image_key)
                faiss_id = str(index.ntotal)
                index.add(np.expand_dims(vector, axis=0))
                mapping[faiss_id] = image_key
            except Exception as exc:
                logger.warning("Skipping %s: %s", item_id, exc)

        if index.ntotal == 0:
            raise ValueError("No valid items were indexed. Check S3 image availability.")

        self._save(index, mapping)
        logger.info("Index built successfully: %d vectors", index.ntotal)

    def _load_items(self) -> list[tuple[str, str]]:
        """Returns [(id, image_key), ...] for every item in RDS."""
        pool = get_pool()
        conn = pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, image_key FROM items WHERE image_key IS NOT NULL;")
                return cursor.fetchall()
        finally:
            conn.rollback()
            pool.putconn(conn)

    def _embed_s3_image(self, image_key: str) -> np.ndarray:
        obj = self._s3.get_object(Bucket=self.bucket_name, Key=image_key)
        image_bytes = obj["Body"].read()
        return self._encoder.encode(image_bytes)

    def _save(self, index, mapping: dict[str, str]) -> None:
        import faiss

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.mapping_path.parent.mkdir(parents=True, exist_ok=True)

        faiss.write_index(index, str(self.index_path))
        with open(self.mapping_path, "w", encoding="utf-8") as file_obj:
            json.dump(mapping, file_obj, indent=2)

        logger.info("Saved index   -> %s", self.index_path)
        logger.info("Saved mapping -> %s", self.mapping_path)
