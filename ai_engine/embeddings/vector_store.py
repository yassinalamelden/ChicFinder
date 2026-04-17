"""
ai_engine/embeddings/vector_store.py
======================================
Slice 2 — Yassin (branch: ai/yassin)

FAISSVectorStore: loads the pre-built index + id mapping and serves
similarity search queries at runtime.

Drop-in replacement for Slice 1 dummy search service.
Agreed function signature (unchanged from Slice 1 contract):
    search_similar_items(image_bytes: bytes) -> list[ClothingItem]
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import numpy as np

from ai_engine.embeddings.database_builder import DEFAULT_IMAGES_DIR
from ai_engine.embeddings.encoder import get_encoder

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------

DEFAULT_INDEX_PATH = Path("data/embeddings.index")
DEFAULT_MAPPING_PATH = Path("data/index_to_image_id.json")
DEFAULT_TOP_K = 5


# ---------------------------------------------------------------------------
# FAISSVectorStore  (Singleton)
# ---------------------------------------------------------------------------


class FAISSVectorStore:
    """
    Singleton FAISS search service.

    Loads the pre-built index + id mapping once at startup, then serves
    fast cosine-similarity queries against the fashion image database.

    Usage
    -----
    store   = FAISSVectorStore.get_instance()
    results = store.search(image_bytes, top_k=5)
    # returns list[dict] with keys: id, image_url, filename, score
    """

    _instance: Optional["FAISSVectorStore"] = None

    def __init__(
        self,
        index_path: Path = DEFAULT_INDEX_PATH,
        metadata_path: Path = DEFAULT_MAPPING_PATH,
    ) -> None:
        import faiss

        self._encoder = get_encoder()  # singleton FashionCLIPEncoder

        index_path = Path(index_path)
        metadata_path = Path(metadata_path)

        # Validate files exist before loading
        if not index_path.exists():
            raise FileNotFoundError(
                f"FAISS index not found at {index_path}. "
                "Run scripts/02_build_faiss_index.py first."
            )
        if not metadata_path.exists():
            raise FileNotFoundError(
                f"Index mapping not found at {metadata_path}. "
                "Run scripts/02_build_faiss_index.py first."
            )

        logger.info("Loading FAISS index from %s ...", index_path)
        self._index = faiss.read_index(str(index_path))

        with open(metadata_path) as f:
            self._metadata: dict = json.load(f)

        logger.info("FAISSVectorStore ready | vectors=%d", self._index.ntotal)

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "FAISSVectorStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(
        self,
        image_bytes: bytes,
        top_k: int = DEFAULT_TOP_K,
    ) -> list[dict]:
        """
        Find the most visually similar fashion items.

        Parameters
        ----------
        image_bytes : bytes
            Raw bytes of the uploaded query image.
        top_k : int
            Number of results to return (default 5).

        Returns
        -------
        list[dict]
            Each dict has: id, image_url, filename, score (cosine similarity)
            Sorted by score descending (most similar first).
        """
        # 1. Encode query image → 512-d L2-normalized vector
        query_vector = self._encoder.encode(image_bytes)

        # 2. FAISS search — IndexFlatIP + L2 vectors = cosine similarity
        query_matrix = np.expand_dims(query_vector, axis=0)  # shape (1, 512)
        scores, indices = self._index.search(query_matrix, top_k)

        # 3. Build results from metadata
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue
            meta = self._metadata.get(str(idx), {})
            if isinstance(meta, str):
                filename = meta
                item_id = Path(filename).stem
                image_url = str(DEFAULT_IMAGES_DIR / filename)
            else:
                filename = meta.get("filename", "")
                item_id = meta.get("id", str(idx))
                image_url = meta.get("image_url", "")
            results.append(
                {
                    "id": item_id,
                    "image_url": image_url,
                    "filename": filename,
                    "score": float(score),  # cosine similarity in [-1, 1]
                }
            )

        return results

    def search_by_vector(
        self,
        query_vector: np.ndarray,
        top_k: int = DEFAULT_TOP_K,
    ) -> list[dict]:
        """
        Find the most visually similar fashion items given a pre-computed embedding.

        Parameters
        ----------
        query_vector : np.ndarray
            L2-normalized embedding of shape (D,), dtype=float32.
        top_k : int
            Number of results to return (default 5).

        Returns
        -------
        list[dict]
            Each dict has: _id, id, image_url, filename, score, and any stored
            metadata keys (category, color, style, brand, price, etc.).
            Sorted by score descending (most similar first).
        """
        query_matrix = np.expand_dims(query_vector.astype(np.float32), axis=0)
        scores, indices = self._index.search(query_matrix, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            meta = self._metadata.get(str(idx), {})
            if isinstance(meta, str):
                filename = meta
                item_id = Path(filename).stem
                payload = {
                    "_id": item_id,
                    "id": item_id,
                    "image_url": str(DEFAULT_IMAGES_DIR / filename),
                    "filename": filename,
                }
            else:
                payload = {
                    "_id": meta.get("id", str(idx)),
                    "id": meta.get("id", str(idx)),
                    "image_url": meta.get("image_url", ""),
                    "filename": meta.get("filename", ""),
                    "category": meta.get("category", "N/A"),
                    "sub_category": meta.get("sub_category", "N/A"),
                    "color": meta.get("color", "N/A"),
                    "style": meta.get("style", "N/A"),
                    "brand": meta.get("brand"),
                    "price": meta.get("price"),
                }
            results.append(
                {
                    **payload,
                    "score": float(score),
                }
            )

        return results

    @property
    def size(self) -> int:
        """Number of vectors currently stored in the index."""
        return self._index.ntotal


# ---------------------------------------------------------------------------
# Agreed contract function — drop-in for Slice 1 dummy
# (called from api/routers/search.py via services/search_service.py)
# ---------------------------------------------------------------------------


def search_similar_items(image_bytes: bytes) -> list[dict]:
    """
    Agreed Slice 1 → Slice 2 drop-in replacement.

    Parameters
    ----------
    image_bytes : bytes
        Raw bytes from the user's uploaded image.

    Returns
    -------
    list[dict]
        Top-5 similar fashion items, each with id, image_url, score.

    Example
    -------
    from ai_engine.embeddings.vector_store import search_similar_items

    results = search_similar_items(image_bytes)
    # [{"id": "42", "image_url": "...", "score": 0.91}, ...]
    """
    return FAISSVectorStore.get_instance().search(image_bytes)
