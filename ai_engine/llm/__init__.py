"""
ai_engine/llm/__init__.py
Exports the three core LLM components for convenient imports.
Uses lazy imports to avoid crashing at startup if optional dependencies
(e.g. openai) are not yet installed.
"""

from __future__ import annotations


def __getattr__(name: str):
    if name == "OutfitParser":
        from ai_engine.llm.outfit_parser import OutfitParser
        return OutfitParser
    if name == "VisionReranker":
        from ai_engine.llm.reranker import VisionReranker
        return VisionReranker
    if name in ("OUTFIT_PARSE_SYSTEM", "OUTFIT_PARSE_USER", "RERANK_SYSTEM", "build_rerank_user_message"):
        from ai_engine.llm import prompt_builder
        return getattr(prompt_builder, name)
    raise AttributeError(f"module 'ai_engine.llm' has no attribute {name!r}")


__all__ = [
    "OutfitParser",
    "VisionReranker",
    "OUTFIT_PARSE_SYSTEM",
    "OUTFIT_PARSE_USER",
    "RERANK_SYSTEM",
    "build_rerank_user_message",
]
