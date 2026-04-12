"""
ai_engine/rag/__init__.py
Exports the RAG pipeline and retriever components.
Uses lazy imports so openai is not required at startup.
"""

from __future__ import annotations


def __getattr__(name: str):
    if name == "RAGPipeline":
        from ai_engine.rag.pipeline import RAGPipeline
        return RAGPipeline
    if name == "Retriever":
        from ai_engine.rag.retriever import Retriever
        return Retriever
    raise AttributeError(f"module 'ai_engine.rag' has no attribute {name!r}")


__all__ = [
    "RAGPipeline",
    "Retriever",
]
