"""
pipeline.py — RAGPipeline: full end-to-end outfit recommendation orchestrator.

Wires together all AI components into a single callable pipeline:
  User photo → LLM Parsing → Encoding + KNN Retrieval
             → Vision Reranking → Typed Recommendations

Implements the complete OutfitAI pipeline (all steps combined).

Note: This version uses the FashionCLIP encoder (Yassin, Slice 2) and the
FAISS vector store already integrated into ai_engine/embeddings.
"""

import io
import logging
from pathlib import Path
from typing import List, Optional

import requests
from PIL import Image

from ai_engine.embeddings.encoder import get_encoder
from ai_engine.embeddings.vector_store import FAISSVectorStore
from ai_engine.llm.outfit_parser import OutfitParser
from ai_engine.llm.reranker import VisionReranker
from ai_engine.rag.retriever import Retriever
from shared.schemas.item import ClothingItem, Recommendation

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    RAGPipeline: end-to-end outfit → recommendations orchestrator.

    Pipeline Steps:
        1. LLM outfit parsing    (OutfitParser / GPT-4o Vision)
        2. Query encoding        (FashionCLIPEncoder / CLIP ViT-B/32, 512-dim)
        3. KNN retrieval         (Retriever → FAISSVectorStore)
        4. Vision reranking      (VisionReranker / GPT-4o Vision)
        5. Result construction   (typed Recommendation objects)

    All components are lazily evaluated via properties so the class can be
    instantiated without immediately loading GPU models (important for
    FastAPI startup inside Docker).

    Referencing: OutfitAI full pipeline entry point.
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
        self._parser: Optional[OutfitParser] = None
        self._vector_store: Optional[FAISSVectorStore] = None
        self._retriever: Optional[Retriever] = None
        self._reranker: Optional[VisionReranker] = None

    # ------------------------------------------------------------------
    # Lazy component accessors
    # ------------------------------------------------------------------

    @property
    def parser(self) -> OutfitParser:
        if self._parser is None:
            logger.info("RAGPipeline: initializing OutfitParser…")
            self._parser = OutfitParser()
        return self._parser

    @property
    def vector_store(self) -> FAISSVectorStore:
        if self._vector_store is None:
            logger.info("RAGPipeline: initializing FAISSVectorStore…")
            self._vector_store = FAISSVectorStore.get_instance()
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
        # ── Step 1: LLM outfit parsing ────────────────────────────────
        logger.info("RAGPipeline Step 1: LLM outfit parsing…")
        items_meta = self.parser.parse(query_image)

        if not items_meta:
            logger.warning("RAGPipeline: no outfit items detected. Returning empty.")
            return []

        logger.info("RAGPipeline: %d item(s) detected.", len(items_meta))

        # ── Step 2: Encode the query image once (reused for all items) ─
        logger.info("RAGPipeline Step 2: Query encoding with FashionCLIP…")
        encoder = get_encoder()
        image_bytes = self._pil_to_bytes(query_image)
        query_vector = encoder.encode(image_bytes)

        recommendations: List[Recommendation] = []

        for item_meta in items_meta:
            item_type = item_meta.get("type", "clothing")
            item_color = item_meta.get("color", "")
            item_style = item_meta.get("style", "")
            logger.info(
                "RAGPipeline: processing item → %s %s %s",
                item_color, item_style, item_type,
            )

            # ── Step 3: KNN retrieval ─────────────────────────────────
            logger.info("RAGPipeline Step 3: KNN retrieval (top %d)…", self.top_k_retrieve)
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

            # ── Step 4: Vision reranking ──────────────────────────────
            if self.skip_reranking or len(candidates) <= self.top_x_rerank:
                top_items = candidates[: self.top_x_rerank]
            else:
                logger.info(
                    "RAGPipeline Step 4: Vision reranking %d → top %d…",
                    len(candidates),
                    self.top_x_rerank,
                )
                candidate_images = [
                    self._fetch_image(item.image_url) for item in candidates
                ]
                valid_pairs = [
                    (img, item)
                    for img, item in zip(candidate_images, candidates)
                    if img is not None
                ]
                if valid_pairs:
                    valid_images, valid_items = zip(*valid_pairs)
                    ranked_indices = self.reranker.rerank(
                        query_image,
                        list(valid_images),
                        top_x=self.top_x_rerank,
                    )
                    top_items = [valid_items[i] for i in ranked_indices][: self.top_x_rerank]
                else:
                    top_items = candidates[: self.top_x_rerank]

            # ── Step 5: Package result ────────────────────────────────
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
    def _pil_to_bytes(image: Image.Image, fmt: str = "PNG") -> bytes:
        """Convert a PIL Image to raw bytes for the CLIP encoder."""
        buf = io.BytesIO()
        image.save(buf, format=fmt)
        return buf.getvalue()

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

def run_pipeline(image_bytes: bytes) -> list:
    """Standalone RAG pipeline execution integrating extraction, search, and reranking."""
    from ai_engine.llm.feature_extractor import extract_features
    from ai_engine.embeddings.vector_store import search_similar_items, FAISSVectorStore
    
    # 1. Extract Features
    features = extract_features(image_bytes)
    
    # 2. Search Similar Items
    results = search_similar_items(image_bytes, top_k=5)
    
    if not results:
        return []
        
    # 3. Rerank
    store = FAISSVectorStore.get_instance()
    reranked_results = []
    
    feat_category = (features.get("category") or "").lower()
    feat_color = (features.get("color") or "").lower()
    feat_gender = (features.get("gender") or "").lower()
    
    for item in results:
        score = item["similarity_score"]
        image_id = item["image_id"]
        
        # Look up metadata from the store
        meta = None
        if store._metadata:
            for k, v in store._metadata.items():
                if str(v.get("id")) == str(image_id) or str(v.get("filename")) == str(image_id):
                    meta = v
                    break

        if meta:
            meta_category = str(meta.get("category", "")).lower()
            meta_color = str(meta.get("color", "")).lower()
            meta_gender = str(meta.get("gender", "")).lower()
            
            if feat_category and feat_category == meta_category:
                score += 0.10
            if feat_color and feat_color == meta_color:
                score += 0.05
            if feat_gender and feat_gender == meta_gender:
                score += 0.05
                
        reranked_results.append({
            "image_id": str(image_id),
            "similarity_score": round(score, 4)
        })
        
    reranked_results.sort(key=lambda x: x["similarity_score"], reverse=True)
    return reranked_results
