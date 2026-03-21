# Embeddings package
"""
ai_engine/embeddings/__init__.py
=================================
Public exports for the embeddings package.

Usage anywhere in the project
------------------------------
from ai_engine.embeddings import get_encoder, search_similar_items, build_index
"""

from ai_engine.embeddings.encoder import (
    EMBEDDING_DIM,
    FashionCLIPEncoder,
    get_encoder,
)
from ai_engine.embeddings.vector_store import (
    FAISSVectorStore,
    search_similar_items,
)
from ai_engine.embeddings.database_builder import (
    FAISSIndexBuilder,
    build_index,
)

__all__ = [
    # encoder
    "EMBEDDING_DIM",
    "FashionCLIPEncoder",
    "get_encoder",
    # search
    "FAISSVectorStore",
    "search_similar_items",
    # index building
    "FAISSIndexBuilder",
    "build_index",
]