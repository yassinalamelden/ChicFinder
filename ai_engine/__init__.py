"""
ai_engine/__init__.py
======================
Top-level exports for the ai_engine package.

Usage
-----
from ai_engine import get_encoder, search_similar_items
"""

from ai_engine.embeddings import (
    EMBEDDING_DIM,
    get_encoder,
    search_similar_items,
    build_index,
)

__all__ = [
    "EMBEDDING_DIM",
    "get_encoder",
    "search_similar_items",
    "build_index",
]