"""
api/services/recommendation_service.py
=======================================
Service layer: HTTP request bytes → AI pipeline → structured results.

Uses the active stack:
  FashionCLIP encoding → Supabase pgvector KNN → ranked results
"""

from __future__ import annotations

import logging
from typing import List

from ai_engine.embeddings.supabase_vector_store import search_similar_items
from chic_finder.config import settings

logger = logging.getLogger(__name__)


class RecommendationService:
    """Thin orchestration layer between route handlers and the AI pipeline."""

    def get_recommendations(self, image_bytes: bytes, top_k: int = 5) -> List[dict]:
        """
        Encode image bytes with FashionCLIP, search Supabase pgvector,
        and return the top-k results as plain dicts.

        Each dict contains:
            id, title, brand, category, price, product_url, image_url, score
        """
        logger.info("RecommendationService: searching top_k=%d", top_k)
        raw_results = search_similar_items(image_bytes, top_k=top_k * 10)

        seen: set = set()
        output: list[dict] = []
        for item in raw_results:
            pid = item.get("product_id") or item.get("id", "")
            if pid in seen or len(output) >= top_k:
                continue
            seen.add(pid)
            image_filename = str(item.get("id", ""))
            output.append({
                "id": image_filename,
                "title": item.get("title"),
                "brand": item.get("brand"),
                "category": item.get("category"),
                "price": item.get("price"),
                "product_url": item.get("product_url"),
                "image_url": settings.get_image_url(image_filename),
                "score": float(item.get("score", 0.0)),
            })
        return output
