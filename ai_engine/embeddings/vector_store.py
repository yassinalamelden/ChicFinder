"""
ai_engine/embeddings/vector_store.py
======================================
Slice 2 — Yassin (branch: ai/yassin)

FAISSVectorStore: loads the pre-built index + metadata and serves
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

from ai_engine.embeddings.encoder import get_encoder

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------

DEFAULT_INDEX_PATH    = Path("data/embeddings.index")
DEFAULT_METADATA_PATH = Path("data/metadata.json")
DEFAULT_TOP_K         = 5


# ---------------------------------------------------------------------------
# FAISSVectorStore  (Singleton)
# ---------------------------------------------------------------------------

class FAISSVectorStore:
    """
    Singleton FAISS search service.

    Loads the pre-built index + metadata once at startup, then serves
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
        index_path:    Path = DEFAULT_INDEX_PATH,
        metadata_path: Path = DEFAULT_METADATA_PATH,
    ) -> None:
        import faiss

        self._encoder  = get_encoder()   # singleton FashionCLIPEncoder

        index_path    = Path(index_path)
        metadata_path = Path(metadata_path)

        self._index = None
        self._metadata = None

        # Handle missing files gracefully
        if not index_path.exists() or not metadata_path.exists():
            logger.warning(
                "FAISS index or metadata not found. VectorStore initialized empty."
            )
            return

        try:
            logger.info("Loading FAISS index from %s ...", index_path)
            self._index = faiss.read_index(str(index_path))

            with open(metadata_path) as f:
                self._metadata: dict = json.load(f)

            logger.info(
                "FAISSVectorStore ready | vectors=%d", self._index.ntotal
            )
        except Exception as exc:
            logger.error("Failed to load index or metadata: %s", exc)

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
            Each dict has: image_id, similarity_score
            Sorted by score descending (most similar first).
        """
        if not image_bytes:
            return []

        if self._index is None or self._metadata is None:
            logger.error("Search failed: Index or metadata not loaded.")
            return []

        try:
            # 1. Encode query image → 512-d L2-normalized vector
            query_vector = self._encoder.encode(image_bytes)
        except Exception as exc:
            logger.error("Image encoding failed: %s", exc)
            return []

        # 2. FAISS search — IndexFlatIP + L2 vectors = cosine similarity
        query_matrix = np.expand_dims(query_vector, axis=0)  # shape (1, 512)
        try:
            scores, indices = self._index.search(query_matrix, top_k)
        except Exception as exc:
            logger.error("FAISS search failed: %s", exc)
            return []

        # 3. Build results from metadata
        results = []
        if len(indices) == 0 or len(indices[0]) == 0:
            return results

        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:           # FAISS returns -1 for empty slots
                continue
            meta = self._metadata.get(str(idx), {})
            image_id = meta.get("filename", meta.get("id", str(idx)))
            if image_id == "":
                image_id = str(idx)

            results.append({
                "image_id": str(image_id),
                "similarity_score": float(score),
            })

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
            results.append({
                "_id":       meta.get("id", str(idx)),
                "id":        meta.get("id", str(idx)),
                "image_url": meta.get("image_url", ""),
                "filename":  meta.get("filename", ""),
                "category":  meta.get("category", "N/A"),
                "sub_category": meta.get("sub_category", "N/A"),
                "color":     meta.get("color", "N/A"),
                "style":     meta.get("style", "N/A"),
                "brand":     meta.get("brand"),
                "price":     meta.get("price"),
                "score":     float(score),
            })

        return results

    @property
    def size(self) -> int:
        """Number of vectors currently stored in the index."""
        if self._index is None:
            return 0
        return self._index.ntotal


# ---------------------------------------------------------------------------
# Agreed contract function — drop-in for Slice 1 dummy
# (called from api/routers/search.py via services/search_service.py)
# ---------------------------------------------------------------------------

def search_similar_items(image_bytes: bytes, top_k: int = 5) -> list[dict]:
    """
    Agreed Slice 1 → Slice 2 drop-in replacement.

    Parameters
    ----------
    image_bytes : bytes
        Raw bytes from the user's uploaded image.
    top_k : int
        Number of items to retrieve.

    Returns
    -------
    list[dict]
        Top-K similar fashion items.

    Example
    -------
    from ai_engine.embeddings.vector_store import search_similar_items

    results = search_similar_items(image_bytes, top_k=5)
    # [{"image_id": "12345.jpg", "similarity_score": 0.91}, ...]
    """
    return FAISSVectorStore.get_instance().search(image_bytes, top_k=top_k)