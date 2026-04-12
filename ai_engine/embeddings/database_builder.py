"""
ai_engine/embeddings/database_builder.py
==========================================
Slice 2 — Yassin (branch: ai/yassin)

Offline pipeline: raw dataset images → FAISS index + metadata.json

Run once before starting the API:
    python scripts/02_build_faiss_index.py

Flow:
    data/raw_images/*.jpg
        → FashionCLIPEncoder.encode()     (512-d L2-normalized vector)
        → faiss.IndexFlatIP               (cosine similarity via dot product)
        → data/embeddings.index           (FAISS binary)
        → data/metadata.json              (id → image_url mapping)
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np

from ai_engine.embeddings.encoder import EMBEDDING_DIM, get_encoder

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default paths  (overridable via env vars or constructor args)
# ---------------------------------------------------------------------------

DEFAULT_IMAGES_DIR   = Path("data/images")
DEFAULT_INDEX_PATH   = Path("data/embeddings.index")
DEFAULT_METADATA_PATH = Path("data/metadata.json")

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


# ---------------------------------------------------------------------------
# FAISSIndexBuilder
# ---------------------------------------------------------------------------

class FAISSIndexBuilder:
    """
    Builds a FAISS IndexFlatIP from a directory of fashion images.

    Usage (called from scripts/02_build_faiss_index.py)
    -----
    builder = FAISSIndexBuilder()
    builder.build(images_dir="data/raw_images")
    # Saves:  data/embeddings.index
    #         data/metadata.json
    """

    def __init__(
        self,
        index_path:    Path = DEFAULT_INDEX_PATH,
        metadata_path: Path = DEFAULT_METADATA_PATH,
    ) -> None:
        self.index_path    = Path(index_path)
        self.metadata_path = Path(metadata_path)
        self._encoder      = get_encoder()   # singleton — loaded once

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def build(self, images_dir: Path = DEFAULT_IMAGES_DIR) -> None:
        """
        Full build pipeline.

        Parameters
        ----------
        images_dir : Path
            Directory containing raw fashion images.
        """
        import faiss

        images_dir = Path(images_dir)
        image_paths = self._collect_images(images_dir)

        if not image_paths:
            raise FileNotFoundError(
                f"No images found in {images_dir}. "
                "Run scripts/01_download_test_data.py first."
            )

        logger.info("Building FAISS index for %d images ...", len(image_paths))

        index    = faiss.IndexFlatIP(EMBEDDING_DIM)
        metadata = {}

        for idx, path in enumerate(image_paths):
            try:
                vector = self._embed_image(path)
                # FAISS expects shape (1, dim)
                index.add(np.expand_dims(vector, axis=0))
                metadata[str(idx)] = {
                    "id":        str(idx),
                    "image_url": str(path),
                    "filename":  path.name,
                }
                if (idx + 1) % 10 == 0:
                    logger.info("  Processed %d / %d", idx + 1, len(image_paths))

            except Exception as exc:
                logger.warning("Skipping %s — %s", path.name, exc)

        self._save(index, metadata)
        logger.info(
            "Index built: %d vectors saved to %s",
            index.ntotal, self.index_path,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_images(self, images_dir: Path) -> list[Path]:
        """Return sorted list of supported image paths."""
        return sorted(
            p for p in images_dir.iterdir()
            if p.suffix.lower() in SUPPORTED_EXTENSIONS
        )

    def _embed_image(self, path: Path) -> np.ndarray:
        """Read image file → L2-normalized 512-d vector."""
        with open(path, "rb") as f:
            return self._encoder.encode(f.read())

    def _save(self, index, metadata: dict) -> None:
        """Persist FAISS index and metadata JSON to disk."""
        import faiss

        # Ensure output directories exist
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)

        faiss.write_index(index, str(self.index_path))
        with open(self.metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info("Saved index     → %s", self.index_path)
        logger.info("Saved metadata  → %s", self.metadata_path)


# ---------------------------------------------------------------------------
# Convenience function (called from scripts/02_build_faiss_index.py)
# ---------------------------------------------------------------------------

def build_index(
    images_dir:    Path = DEFAULT_IMAGES_DIR,
    index_path:    Path = DEFAULT_INDEX_PATH,
    metadata_path: Path = DEFAULT_METADATA_PATH,
) -> None:
    """
    One-call entry point for scripts/02_build_faiss_index.py.

    Example
    -------
    from ai_engine.embeddings.database_builder import build_index
    build_index()
    """
    FAISSIndexBuilder(
        index_path=index_path,
        metadata_path=metadata_path,
    ).build(images_dir=images_dir)