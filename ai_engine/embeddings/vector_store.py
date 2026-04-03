"""
vector_store.py — FAISS-backed vector store for fashion item retrieval.

Replaces the original Marqo-based implementation with a lightweight,
fully offline FAISS index. This removes the requirement for an external
Marqo server and makes the system deployable anywhere.

Architecture:
  - Inner-product FAISS index (works as cosine similarity since all vectors
    are L2-normalized by FashionEncoder).
  - Metadata (category, color, style, image_url, etc.) stored as a parallel
    list keyed by FAISS internal ID (== list index).
  - Persisted to disk as:
      *.faiss   — the FAISS index binary
      *.meta    — JSON-serialized metadata list

Implements Step 4b of the OutfitAI architecture (retrieval).
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import faiss
import numpy as np
import torch

from chic_finder.config import settings

logger = logging.getLogger(__name__)

_DIM = 256  # Must match FashionEncoder output dimension


class VectorStore:
    """
    VectorStore: FAISS Inner-Product index for L2-normalized 256-dim vectors.

    Usage:
        store = VectorStore()
        store.add_documents(documents)        # offline indexing
        hits = store.search(query_vec, top_k) # online retrieval

    Documents must have at minimum:
        {"image_url": str, "embedding": np.ndarray | torch.Tensor, ...metadata}
    """

    def __init__(
        self,
        index_path: Optional[str] = None,
        dim: int = _DIM,
    ):
        self.dim = dim
        self.index_path = Path(index_path or settings.VECTOR_DB_PATH)
        self.meta_path = self.index_path.with_suffix(".meta")

        self._index: faiss.IndexFlatIP = faiss.IndexFlatIP(self.dim)
        self._metadata: List[Dict[str, Any]] = []

        # Try to load existing index from disk
        self._try_load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Adds a list of clothing item documents to the index.

        Each document dict must contain:
          - "embedding": np.ndarray or torch.Tensor of shape (256,)  [required]
          - "image_url": str                                          [required]
          - Any additional metadata keys (category, color, style, brand, price…)

        The embedding is L2-normalized before insertion (no-op if already normalized).
        """
        if not documents:
            logger.warning("VectorStore.add_documents() called with empty list.")
            return

        vectors = []
        for doc in documents:
            emb = doc.get("embedding")
            if emb is None:
                logger.warning("Document missing 'embedding', skipping: %s", doc.get("image_url"))
                continue

            vec = self._to_numpy(emb)
            vec = vec / (np.linalg.norm(vec) + 1e-9)  # Ensure unit norm
            vectors.append(vec)

            # Store metadata (everything except the raw embedding tensor)
            meta = {k: v for k, v in doc.items() if k != "embedding"}
            self._metadata.append(meta)

        if not vectors:
            return

        matrix = np.stack(vectors, axis=0).astype(np.float32)
        self._index.add(matrix)
        logger.info(
            "VectorStore: added %d vectors. Total index size: %d.",
            len(vectors),
            self._index.ntotal,
        )
        self._save()

    def search(
        self,
        query: Any,
        top_k: int = 25,
    ) -> List[Dict[str, Any]]:
        """
        Searches the FAISS index for the nearest neighbours of `query`.

        Args:
            query: One of:
                   - np.ndarray of shape (256,)
                   - torch.Tensor of shape (256,)
            top_k: Number of results to return.

        Returns:
            List of metadata dicts for the top-K results, each enriched with
            "_score" (inner product ≈ cosine similarity) and "_id" (index position).

        Returns an empty list if the index has no documents.
        """
        if self._index.ntotal == 0:
            logger.warning("VectorStore.search() called on empty index.")
            return []

        actual_k = min(top_k, self._index.ntotal)
        vec = self._to_numpy(query).astype(np.float32)
        vec = vec / (np.linalg.norm(vec) + 1e-9)

        query_matrix = vec.reshape(1, -1)
        scores, indices = self._index.search(query_matrix, actual_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._metadata):
                continue
            hit = dict(self._metadata[idx])
            hit["_id"] = str(idx)
            hit["_score"] = float(score)
            results.append(hit)

        return results

    @property
    def size(self) -> int:
        """Number of vectors currently in the index."""
        return self._index.ntotal

    def reset(self) -> None:
        """Clears the index and metadata. Use with caution."""
        self._index.reset()
        self._metadata = []
        logger.warning("VectorStore: index reset.")

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _save(self) -> None:
        """Persists the FAISS index and metadata to disk."""
        try:
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self._index, str(self.index_path))
            with open(self.meta_path, "w", encoding="utf-8") as f:
                json.dump(self._metadata, f, ensure_ascii=False)
            logger.debug("VectorStore: saved index to '%s'.", self.index_path)
        except Exception as exc:
            logger.error("VectorStore: failed to save index: %s", exc)

    def _try_load(self) -> None:
        """Loads a previously saved FAISS index and metadata from disk."""
        if not self.index_path.exists():
            logger.info(
                "VectorStore: no existing index at '%s'. Starting fresh.",
                self.index_path,
            )
            return
        try:
            self._index = faiss.read_index(str(self.index_path))
            if self.meta_path.exists():
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    self._metadata = json.load(f)
            logger.info(
                "VectorStore: loaded %d vectors from '%s'.",
                self._index.ntotal,
                self.index_path,
            )
        except Exception as exc:
            logger.error("VectorStore: failed to load index: %s. Starting fresh.", exc)
            self._index = faiss.IndexFlatIP(self.dim)
            self._metadata = []

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _to_numpy(vec: Any) -> np.ndarray:
        """Converts torch.Tensor or np.ndarray to a flat numpy array."""
        if isinstance(vec, torch.Tensor):
            return vec.detach().cpu().numpy().flatten()
        return np.array(vec).flatten()
