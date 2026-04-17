"""
reranker.py — Gemini Vision-based candidate reranking.

Given a query outfit image and a list of candidate product images, uses Gemini
to produce a fine-grained ranking ordered by visual+stylistic similarity.
"""

import json
import logging
from typing import List

from google import genai
from google.genai import types
from PIL import Image

from chic_finder.config import settings
from ai_engine.llm.prompt_builder import (
    RERANK_SYSTEM,
    build_rerank_user_message,
)

logger = logging.getLogger(__name__)

MAX_CANDIDATES_PER_CALL = 10

class VisionReranker:
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self._client = genai.Client(api_key=self.api_key)

    def rerank(
        self,
        query_image: Image.Image,
        candidate_images: List[Image.Image],
        top_x: int = 5,
    ) -> List[int]:
        if not candidate_images:
            return []

        top_x = min(top_x, len(candidate_images))

        if len(candidate_images) <= MAX_CANDIDATES_PER_CALL:
            ranked = self._rerank_batch(query_image, candidate_images)
        else:
            ranked = self._rerank_multi_batch(query_image, candidate_images, top_x)

        return ranked[:top_x]

    def _rerank_batch(
        self,
        query_image: Image.Image,
        candidates: List[Image.Image],
    ) -> List[int]:
        logger.info(
            "VisionReranker._rerank_batch() — %d candidates, calling Gemini…",
            len(candidates),
        )

        # Build contents array for Gemini: prompt + query image + candidates
        contents = [build_rerank_user_message(len(candidates)), query_image]
        contents.extend(candidates)

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=RERANK_SYSTEM,
                    temperature=0.0,
                    response_mime_type="application/json",
                )
            )
            raw_text = response.text.strip()
            logger.debug("Gemini raw rerank response: %s", raw_text)
            
            parsed = json.loads(raw_text)
            ranking = parsed.get("ranking", [])

            # Validate: must be a permutation of [0..n-1]
            if sorted(ranking) != list(range(len(candidates))):
                logger.warning(f"Invalid ranking permutation: {ranking}")
                return list(range(len(candidates)))

            return [int(i) for i in ranking]

        except Exception as exc:
            logger.error("VisionReranker Gemini API call failed: %s", exc)
            return list(range(len(candidates)))

    def _rerank_multi_batch(
        self,
        query_image: Image.Image,
        candidates: List[Image.Image],
        top_x: int,
    ) -> List[int]:
        survivors_global_indices: List[int] = []
        for start in range(0, len(candidates), MAX_CANDIDATES_PER_CALL):
            chunk = candidates[start : start + MAX_CANDIDATES_PER_CALL]
            local_ranking = self._rerank_batch(query_image, chunk)
            for local_idx in local_ranking[:top_x]:
                survivors_global_indices.append(start + local_idx)

        survivor_images = [candidates[i] for i in survivors_global_indices]
        final_local_ranking = self._rerank_batch(query_image, survivor_images)

        return [survivors_global_indices[i] for i in final_local_ranking]
