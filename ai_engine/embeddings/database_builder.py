"""
database_builder.py — Offline FAISS index construction from a clothing dataset.

Iterates over a directory of clothing images (or a pre-build manifest JSON),
encodes each image via FashionEncoder (VGG-16 256-dim), and adds the
resulting vectors + metadata to VectorStore (FAISS).

Intended to be run once offline before serving:
  python -m scripts.build_database --data_dir ./data/images

Implements Step 4 (offline) of the OutfitAI architecture.
"""

import io
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from PIL import Image

from chic_finder.config import settings
from ai_engine.embeddings.encoder import FashionEncoder
from ai_engine.embeddings.vector_store import VectorStore

logger = logging.getLogger(__name__)


class DatabaseBuilder:
    """
    DatabaseBuilder: encodes clothing images and indexes them into FAISS.

    Two main workflows:

    1. build_from_documents(documents):
       Accepts a pre-built list of dicts, each with "image_url" pointing to
       a local path or HTTP URL (image will be fetched + encoded on the fly).

    2. build_from_directory(image_dir):
       Scans a directory of images and indexes them with minimal metadata
       derived from directory structure and filename.

    Referencing: OutfitAI architecture Step 4 (offline, refactored).
    """

    def __init__(self, index_path: Optional[str] = None, batch_size: int = 32):
        self.encoder = FashionEncoder()
        self.vector_store = VectorStore(index_path=index_path)
        self.batch_size = batch_size

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_from_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Encodes and indexes a list of clothing item documents.

        Each dict should contain at minimum:
          - "image_url": str — local path OR remote HTTP(S) URL
          - Optional metadata: category, sub_category, color, style, brand, price

        The "embedding" key will be added automatically by this function.
        """
        if not documents:
            logger.warning("DatabaseBuilder: no documents provided.")
            return

        logger.info("DatabaseBuilder: indexing %d documents in batches of %d…",
                    len(documents), self.batch_size)

        success_count = 0
        for batch_start in range(0, len(documents), self.batch_size):
            batch = documents[batch_start : batch_start + self.batch_size]
            encoded_batch = []

            for doc in batch:
                image_url = doc.get("image_url", "")
                try:
                    image = self._load_image(image_url)
                    embedding = self.encoder.encode(image)
                    doc_with_embedding = dict(doc)
                    doc_with_embedding["embedding"] = embedding
                    encoded_batch.append(doc_with_embedding)
                    success_count += 1
                except Exception as exc:
                    logger.warning("DatabaseBuilder: skipping '%s' (%s).", image_url, exc)

            if encoded_batch:
                self.vector_store.add_documents(encoded_batch)

            logger.info(
                "DatabaseBuilder: processed batch %d-%d (%d ok so far).",
                batch_start + 1,
                min(batch_start + self.batch_size, len(documents)),
                success_count,
            )

        logger.info(
            "DatabaseBuilder: completed. %d/%d documents indexed successfully.",
            success_count,
            len(documents),
        )

    def build_from_directory(
        self,
        image_dir: str,
        extensions: tuple = (".jpg", ".jpeg", ".png", ".webp"),
    ) -> None:
        """
        Scans an image directory, encodes all images, and builds the FAISS index.

        Directory layout convention (optional):
          <image_dir>/
            ├── tops/
            │   ├── casual/
            │   │   ├── item_001.jpg
            │   ...
            ├── bottoms/
            ...

        If a two-level hierarchy (category/sub_category) is detected, metadata
        is inferred from the directory names. Otherwise defaults are used.

        Args:
            image_dir:  Path to root image directory.
            extensions: Tuple of allowed image extensions.
        """
        root = Path(image_dir)
        if not root.exists():
            raise FileNotFoundError(f"Image directory not found: {image_dir}")

        image_paths = [
            p for p in root.rglob("*") if p.suffix.lower() in extensions
        ]

        if not image_paths:
            logger.warning("DatabaseBuilder: no images found in '%s'.", image_dir)
            return

        logger.info(
            "DatabaseBuilder: found %d images in '%s'.", len(image_paths), image_dir
        )

        documents = []
        for path in image_paths:
            # Infer metadata from directory structure
            parts = path.relative_to(root).parts
            category = parts[0] if len(parts) >= 2 else "unknown"
            sub_category = parts[1] if len(parts) >= 3 else "unknown"

            documents.append(
                {
                    "image_url": str(path),
                    "category": category,
                    "sub_category": sub_category,
                    "color": "unknown",
                    "style": "unknown",
                    "brand": None,
                    "price": None,
                }
            )

        self.build_from_documents(documents)

    def build_from_manifest(self, manifest_path: str) -> None:
        """
        Builds the index from a JSON manifest file.

        The manifest is a JSON array of document dicts (same format as
        build_from_documents). Useful for reproducible offline indexing.

        Args:
            manifest_path: Path to a JSON file containing the document list.
        """
        path = Path(manifest_path)
        if not path.exists():
            raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

        with open(path, "r", encoding="utf-8") as f:
            documents = json.load(f)

        logger.info(
            "DatabaseBuilder: loaded %d documents from manifest '%s'.",
            len(documents),
            manifest_path,
        )
        self.build_from_documents(documents)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_image(source: str) -> Image.Image:
        """
        Loads a PIL Image from a local path or HTTP(S) URL.

        Raises:
            ValueError if the source is empty or the image fails to load.
        """
        if not source:
            raise ValueError("Empty image source.")

        if source.startswith("http://") or source.startswith("https://"):
            response = requests.get(source, timeout=10)
            response.raise_for_status()
            return Image.open(io.BytesIO(response.content)).convert("RGB")

        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Local image not found: {source}")

        return Image.open(path).convert("RGB")


# ------------------------------------------------------------------
# Convenience functional wrapper
# ------------------------------------------------------------------

def build_database(
    documents: Optional[List[Dict[str, Any]]] = None,
    image_dir: Optional[str] = None,
    manifest_path: Optional[str] = None,
    index_path: Optional[str] = None,
    batch_size: int = 32,
) -> None:
    """
    Convenience function to build the fashion database from various sources.

    Provide exactly one of: documents, image_dir, or manifest_path.

    Args:
        documents:     Pre-built list of document dicts.
        image_dir:     Path to image directory.
        manifest_path: Path to JSON manifest.
        index_path:    Override for FAISS index output path.
        batch_size:    Encoding batch size.
    """
    builder = DatabaseBuilder(index_path=index_path, batch_size=batch_size)

    if documents is not None:
        builder.build_from_documents(documents)
    elif image_dir is not None:
        builder.build_from_directory(image_dir)
    elif manifest_path is not None:
        builder.build_from_manifest(manifest_path)
    else:
        raise ValueError(
            "build_database() requires one of: documents, image_dir, or manifest_path."
        )
