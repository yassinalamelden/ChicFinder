"""
retriever.py — Typed KNN retrieval wrapper over VectorStore.

Converts raw FAISS hits into structured ClothingItem objects,
providing a clean typed interface for the RAG pipeline.

Implements Step 4b of the OutfitAI architecture (retrieval layer).
"""

import logging
from typing import List, Optional

import numpy as np
import torch

from ai_engine.embeddings.vector_store import VectorStore
from shared.schemas.item import ClothingItem

logger = logging.getLogger(__name__)


class Retriever:
    """
    Retriever: typed KNN lookup over the fashion VectorStore.

    Wraps VectorStore.search() and maps raw hit dicts to ClothingItem objects.

    Usage:
        retriever = Retriever(vector_store)
        items = retriever.retrieve_candidates(query_embedding, top_k=25)

    Referencing: OutfitAI architecture Step 4b.
    """

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve_candidates(
        self,
        query_vector: "np.ndarray | torch.Tensor",
        top_k: int = 25,
    ) -> List[ClothingItem]:
        """
        Retrieves the top-K most similar clothing items for a given query vector.

        Args:
            query_vector: L2-normalized embedding of shape (256,).
            top_k:        Number of candidates to retrieve.

        Returns:
            List of ClothingItem, ordered from most to least similar.
            Returns empty list if the index is empty.
        """
        if self.vector_store.size == 0:
            logger.warning("Retriever.retrieve_candidates(): vector store is empty.")
            return []

        hits = self.vector_store.search(query_vector, top_k=top_k)
        logger.debug(
            "Retriever: retrieved %d candidates (requested %d).", len(hits), top_k
        )

        return [self._hit_to_item(hit) for hit in hits]

    def retrieve_by_text(
        self,
        query_vector: "np.ndarray | torch.Tensor",
        top_k: int = 25,
    ) -> List[ClothingItem]:
        """
        Alias for retrieve_candidates — provided for semantic clarity when
        the calling code passes a text-derived query embedding.
        """
        return self.retrieve_candidates(query_vector, top_k=top_k)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hit_to_item(hit: dict) -> ClothingItem:
        """
        Maps a raw VectorStore hit dict to a typed ClothingItem.

        Any missing metadata fields are substituted with sensible defaults
        so that downstream code can always rely on the full schema.
        """
        return ClothingItem(
            id=hit.get("_id", "unknown"),
            category=hit.get("category", "N/A"),
            sub_category=hit.get("sub_category", "N/A"),
            color=hit.get("color", "N/A"),
            style=hit.get("style", "N/A"),
            image_url=hit.get("image_url", ""),
            brand=hit.get("brand"),
            price=hit.get("price"),
        )
