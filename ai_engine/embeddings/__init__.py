# Embeddings package
"""
ai_engine/embeddings/__init__.py
=================================
Public exports for the embeddings package.

Usage anywhere in the project
------------------------------
from ai_engine.embeddings import get_encoder
"""

from ai_engine.embeddings.encoder import (
    EMBEDDING_DIM,
    FashionCLIPEncoder,
    get_encoder,
)

__all__ = [
    # encoder
    "EMBEDDING_DIM",
    "FashionCLIPEncoder",
    "get_encoder",
]