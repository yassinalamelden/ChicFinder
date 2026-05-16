# ai_engine/embeddings/supabase_vector_store.py
"""
Supabase pgvector replacement for FAISSVectorStore.
Exposes the same public API used by api/routes/search.py and recommend.py.
"""

from __future__ import annotations

import logging
import numpy as np

from ai_engine.embeddings.encoder import get_encoder
from api.db.client import get_supabase_client

logger = logging.getLogger(__name__)


def _rows_to_dicts(rows: list[dict]) -> list[dict]:
    return [
        {
            "id": row["image_filename"],
            "filename": f"{row['image_filename']}.jpg",
            "score": float(row["similarity"]),
            "product_id": row.get("product_id_str"),
            "title": row.get("title"),
            "brand": row.get("brand"),
            "category": row.get("category"),
            "price": row.get("price"),
            "product_url": row.get("product_url"),
        }
        for row in rows
    ]


def search_similar_items(image_bytes: bytes, top_k: int = 50) -> list[dict]:
    """Encode image bytes with FashionCLIP, then query pgvector via RPC."""
    encoder = get_encoder()
    query_vector: np.ndarray = encoder.encode(image_bytes)
    return search_by_vector(query_vector, top_k=top_k)


def search_by_vector(query_vector: np.ndarray, top_k: int = 50) -> list[dict]:
    """Query pgvector directly with a pre-computed 512-d embedding."""
    client = get_supabase_client()
    try:
        result = client.rpc(
            "match_embeddings",
            {"query_embedding": query_vector.tolist(), "match_count": top_k},
        ).execute()
        return _rows_to_dicts(result.data or [])
    except Exception as exc:
        logger.error("pgvector RPC failed: %s", exc, exc_info=True)
        raise
