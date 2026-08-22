"""
reranker.py — Gemini Vision-based candidate reranking, via OpenRouter.

Given a query outfit image and a list of candidate product images, uses Gemini
to produce a fine-grained ranking ordered by visual+stylistic similarity.
"""

import json
import logging
from typing import List

from openai import OpenAI
from PIL import Image

from chic_finder.config import settings
from shared.utils.image_utils import image_to_data_url
from ai_engine.llm.outfit_parser import strip_json_fences
from ai_engine.llm.prompt_builder import (
    RERANK_SYSTEM,
    build_rerank_user_message,
)

logger = logging.getLogger(__name__)

MAX_CANDIDATES_PER_CALL = 10

class VisionReranker:
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model or settings.OPENROUTER_MODEL
        self._client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=self.api_key)

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
            "VisionReranker._rerank_batch() — %d candidates, calling OpenRouter…",
            len(candidates),
        )

        # Build content array: prompt text + query image + candidate images
        content = [{"type": "text", "text": build_rerank_user_message(len(candidates))}]
        content.append({"type": "image_url", "image_url": {"url": image_to_data_url(query_image)}})
        for candidate in candidates:
            content.append({"type": "image_url", "image_url": {"url": image_to_data_url(candidate)}})

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": RERANK_SYSTEM},
                    {"role": "user", "content": content},
                ],
                temperature=0.0,
                max_tokens=8000,
                response_format={"type": "json_object"},
            )
            raw_text = strip_json_fences(response.choices[0].message.content)
            logger.debug("OpenRouter raw rerank response: %s", raw_text)

            parsed = json.loads(raw_text)
            ranking = parsed.get("ranking", [])

            # Validate: must be a permutation of [0..n-1]
            if sorted(ranking) != list(range(len(candidates))):
                logger.warning(f"Invalid ranking permutation: {ranking}")
                return list(range(len(candidates)))

            return [int(i) for i in ranking]

        except Exception as exc:
            logger.error("VisionReranker OpenRouter API call failed: %s", exc)
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
