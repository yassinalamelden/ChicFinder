"""
pipeline.py — RAGPipeline: full end-to-end outfit recommendation orchestrator.

Wires together all AI components into a single callable pipeline:
  User photo → Background Removal → LLM Parsing → Encoding + KNN Retrieval
             → Vision Reranking → Typed Recommendations

Implements the complete OutfitAI pipeline (all steps combined).
"""

import io
import logging
from pathlib import Path
from typing import List, Optional

import requests
from PIL import Image

from ai_engine.background_removal.segmenter import FashionSegmenter
from ai_engine.embeddings.encoder import FashionEncoder
from ai_engine.embeddings.vector_store import VectorStore
from ai_engine.llm.outfit_parser import OutfitParser
from ai_engine.llm.reranker import VisionReranker
from ai_engine.rag.retriever import Retriever
from shared.schemas.item import ClothingItem, Recommendation

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    RAGPipeline: end-to-end outfit → recommendations orchestrator.

    Pipeline Steps:
        1. Background removal    (FashionSegmenter / rembg)
        2. LLM outfit parsing    (OutfitParser / GPT-4o Vision)
        3. Query encoding        (FashionEncoder / VGG-16 256-dim)
        4. KNN retrieval         (Retriever → FAISS VectorStore)
        5. Vision reranking      (VisionReranker / GPT-4o Vision)
        6. Result construction   (typed Recommendation objects)

    All components are lazily evaluated via properties so the class can be
    instantiated without immediately loading GPU models (important for
    FastAPI startup inside Docker).

    Referencing: OutfitAI full pipeline entry point (refactored).
    """

    def __init__(
        self,
        top_k_retrieve: int = 25,
        top_x_rerank: int = 5,
        skip_reranking: bool = False,
    ):
        """
        Args:
            top_k_retrieve: Number of candidates to retrieve from FAISS.
            top_x_rerank:   Final number of recommendations per item to return.
            skip_reranking: If True, skip GPT-4o reranking step (faster, cheaper).
        """
        self.top_k_retrieve = top_k_retrieve
        self.top_x_rerank = top_x_rerank
        self.skip_reranking = skip_reranking

        # Components (initialized once on first use)
        self._segmenter: Optional[FashionSegmenter] = None
        self._parser: Optional[OutfitParser] = None
        self._encoder: Optional[FashionEncoder] = None
        self._vector_store: Optional[VectorStore] = None
        self._retriever: Optional[Retriever] = None
        self._reranker: Optional[VisionReranker] = None

    # ------------------------------------------------------------------
    # Lazy component accessors
    # ------------------------------------------------------------------

    @property
    def segmenter(self) -> FashionSegmenter:
        if self._segmenter is None:
            logger.info("RAGPipeline: initializing FashionSegmenter…")
            self._segmenter = FashionSegmenter()
        return self._segmenter

    @property
    def parser(self) -> OutfitParser:
        if self._parser is None:
            logger.info("RAGPipeline: initializing OutfitParser…")
            self._parser = OutfitParser()
        return self._parser

    @property
    def encoder(self) -> FashionEncoder:
        if self._encoder is None:
            logger.info("RAGPipeline: initializing FashionEncoder…")
            self._encoder = FashionEncoder()
        return self._encoder

    @property
    def vector_store(self) -> VectorStore:
        if self._vector_store is None:
            logger.info("RAGPipeline: initializing VectorStore…")
            self._vector_store = VectorStore()
        return self._vector_store

    @property
    def retriever(self) -> Retriever:
        if self._retriever is None:
            self._retriever = Retriever(self.vector_store)
        return self._retriever

    @property
    def reranker(self) -> VisionReranker:
        if self._reranker is None:
            logger.info("RAGPipeline: initializing VisionReranker…")
            self._reranker = VisionReranker()
        return self._reranker

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, query_image: Image.Image) -> List[Recommendation]:
        """
        Executes the full RAG pipeline on the given outfit image.

        Args:
            query_image: RGB PIL Image of the user's outfit.

        Returns:
            List of Recommendation objects, one per detected outfit item.
            Each Recommendation contains:
              - query_item: dict with the parsed item metadata
              - suggestions: List[ClothingItem] ordered by relevance
        """
        # ── Step 1: Background removal ────────────────────────────────
        logger.info("RAGPipeline Step 1: Background removal…")
        clean_image = self.segmenter.segment(query_image)

        # ── Step 2: LLM outfit parsing ────────────────────────────────
        logger.info("RAGPipeline Step 2: LLM outfit parsing…")
        items_meta = self.parser.parse(clean_image)

        if not items_meta:
            logger.warning("RAGPipeline: no outfit items detected. Returning empty.")
            return []

        logger.info("RAGPipeline: %d item(s) detected.", len(items_meta))

        recommendations: List[Recommendation] = []

        for item_meta in items_meta:
            item_type = item_meta.get("type", "clothing")
            item_color = item_meta.get("color", "")
            item_style = item_meta.get("style", "")
            logger.info(
                "RAGPipeline: processing item → %s %s %s",
                item_color, item_style, item_type,
            )

            # ── Step 3: Query encoding ────────────────────────────────
            # Encode the full clean image as the query vector.
            # (In a more advanced version, each item crop would be encoded separately.)
            logger.info("RAGPipeline Step 3: Query encoding…")
            query_vector = self.encoder.encode(clean_image)

            # ── Step 4: KNN retrieval ─────────────────────────────────
            logger.info("RAGPipeline Step 4: KNN retrieval (top %d)…", self.top_k_retrieve)
            candidates: List[ClothingItem] = self.retriever.retrieve_candidates(
                query_vector, top_k=self.top_k_retrieve
            )

            if not candidates:
                logger.warning(
                    "RAGPipeline: no candidates retrieved for item '%s'. "
                    "Is the FAISS database built? Run build_database first.",
                    item_type,
                )
                recommendations.append(
                    Recommendation(query_item=item_meta, suggestions=[])
                )
                continue

            # ── Step 5: Vision reranking ──────────────────────────────
            if self.skip_reranking or len(candidates) <= self.top_x_rerank:
                top_items = candidates[: self.top_x_rerank]
            else:
                logger.info(
                    "RAGPipeline Step 5: Vision reranking %d → top %d…",
                    len(candidates),
                    self.top_x_rerank,
                )
                candidate_images = [
                    self._fetch_image(item.image_url) for item in candidates
                ]
                # Filter out None (failed fetches)
                valid_pairs = [
                    (img, item)
                    for img, item in zip(candidate_images, candidates)
                    if img is not None
                ]
                if valid_pairs:
                    valid_images, valid_items = zip(*valid_pairs)
                    ranked_indices = self.reranker.rerank(
                        clean_image,
                        list(valid_images),
                        top_x=self.top_x_rerank,
                    )
                    top_items = [valid_items[i] for i in ranked_indices][: self.top_x_rerank]
                else:
                    top_items = candidates[: self.top_x_rerank]

            # ── Step 6: Package result ────────────────────────────────
            recommendations.append(
                Recommendation(query_item=item_meta, suggestions=top_items)
            )
            logger.info(
                "RAGPipeline: %d recommendation(s) finalized for item '%s'.",
                len(top_items),
                item_type,
            )

        return recommendations

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _fetch_image(source: str) -> Optional[Image.Image]:
        """
        Loads a PIL Image from a local path or HTTP URL.
        Returns None on failure (so it can be filtered out gracefully).
        """
        if not source:
            return None
        try:
            if source.startswith("http://") or source.startswith("https://"):
                resp = requests.get(source, timeout=8)
                resp.raise_for_status()
                return Image.open(io.BytesIO(resp.content)).convert("RGB")
            path = Path(source)
            if path.exists():
                return Image.open(path).convert("RGB")
            logger.warning("RAGPipeline._fetch_image: path not found: %s", source)
            return None
        except Exception as exc:
            logger.warning("RAGPipeline._fetch_image: failed to load '%s': %s", source, exc)
            return None
