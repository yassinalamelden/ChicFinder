"""
reranker.py — GPT-4o Vision-based candidate reranking.

Given a query outfit image and a list of candidate product images, uses GPT-4o
to produce a fine-grained ranking ordered by visual+stylistic similarity.

Implements Step 5 of the OutfitAI architecture:
  Top-K candidates → GPT-4o Vision reranking → Top-X results
"""

import json
import logging
from typing import List

from openai import OpenAI
from PIL import Image

from chic_finder.config import settings
from shared.utils.image_utils import image_to_base64
from ai_engine.llm.prompt_builder import (
    RERANK_SYSTEM,
    build_rerank_user_message,
)

logger = logging.getLogger(__name__)

# Maximum candidates to send per API call (context + cost control)
MAX_CANDIDATES_PER_CALL = 10


class VisionReranker:
    """
    VisionReranker: reranks Top-K candidates to Top-X via GPT-4o Vision.

    Sends the query image together with all candidate images in a single
    multi-image message and asks GPT-4o to rank them by visual similarity.

    Referencing: OutfitAI architecture Step 5.
    """

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.GPT_MODEL
        self._client = OpenAI(api_key=self.api_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def rerank(
        self,
        query_image: Image.Image,
        candidate_images: List[Image.Image],
        top_x: int = 5,
    ) -> List[int]:
        """
        Reranks candidate images by visual similarity to the query outfit image.

        Args:
            query_image:      PIL Image of the query outfit (post-background-removal).
            candidate_images: List of PIL Images of candidate clothing items.
            top_x:            Number of top results to return.

        Returns:
            List[int] — indices into `candidate_images` of the top_x most
            similar items, ordered from most to least similar.

        Notes:
            - If candidate_images is empty, returns [].
            - If GPT-4o response is malformed, falls back to the original order.
            - Batches automatically if more than MAX_CANDIDATES_PER_CALL images.
        """
        if not candidate_images:
            return []

        top_x = min(top_x, len(candidate_images))

        # If candidates fit in one call, rerank directly
        if len(candidate_images) <= MAX_CANDIDATES_PER_CALL:
            ranked = self._rerank_batch(query_image, candidate_images)
        else:
            ranked = self._rerank_multi_batch(query_image, candidate_images, top_x)

        return ranked[:top_x]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rerank_batch(
        self,
        query_image: Image.Image,
        candidates: List[Image.Image],
    ) -> List[int]:
        """
        Single-batch GPT-4o reranking call.

        Returns the full ranking as a list of candidate indices.
        """
        logger.info(
            "VisionReranker._rerank_batch() — %d candidates, calling GPT-4o…",
            len(candidates),
        )

        # Build the multi-image message content
        # Layout: [query_image, candidate_0, candidate_1, ..., candidate_n, text_prompt]
        content = []

        # Query image first
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_to_base64(query_image, 'PNG')}",
                    "detail": "low",  # query needs less detail; save tokens
                },
            }
        )

        # Candidate images
        for img in candidates:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_to_base64(img, 'PNG')}",
                        "detail": "low",
                    },
                }
            )

        # Text instruction
        content.append(
            {
                "type": "text",
                "text": build_rerank_user_message(len(candidates)),
            }
        )

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                max_tokens=256,
                temperature=0.0,  # Deterministic ranking
                messages=[
                    {"role": "system", "content": RERANK_SYSTEM},
                    {"role": "user", "content": content},
                ],
            )
        except Exception as exc:
            logger.error("VisionReranker OpenAI API call failed: %s", exc)
            # Graceful degradation: return original order
            return list(range(len(candidates)))

        raw_text = response.choices[0].message.content.strip()
        logger.debug("GPT-4o raw rerank response: %s", raw_text)

        return self._parse_ranking(raw_text, len(candidates))

    def _rerank_multi_batch(
        self,
        query_image: Image.Image,
        candidates: List[Image.Image],
        top_x: int,
    ) -> List[int]:
        """
        When there are more candidates than MAX_CANDIDATES_PER_CALL, run
        two-phase reranking:
          Phase 1: Batch each chunk → get top_x from each chunk.
          Phase 2: Rerank the phase-1 winners against each other.
        """
        logger.info(
            "VisionReranker multi-batch reranking — %d candidates in chunks of %d.",
            len(candidates),
            MAX_CANDIDATES_PER_CALL,
        )

        # Phase 1: reduce each chunk to top_x survivors
        survivors_global_indices: List[int] = []
        for start in range(0, len(candidates), MAX_CANDIDATES_PER_CALL):
            chunk = candidates[start : start + MAX_CANDIDATES_PER_CALL]
            local_ranking = self._rerank_batch(query_image, chunk)
            # Convert local indices back to global indices
            for local_idx in local_ranking[:top_x]:
                survivors_global_indices.append(start + local_idx)

        # Phase 2: rerank the survivors
        survivor_images = [candidates[i] for i in survivors_global_indices]
        final_local_ranking = self._rerank_batch(query_image, survivor_images)

        # Map back to original global indices
        return [survivors_global_indices[i] for i in final_local_ranking]

    def _parse_ranking(self, raw_text: str, n_candidates: int) -> List[int]:
        """
        Parses the GPT-4o ranking JSON response.

        Expected format: {"ranking": [2, 0, 3, 1]}
        Falls back to original order if parsing fails.
        """
        # Strip markdown fences if present
        text = raw_text
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

        try:
            parsed = json.loads(text)
            ranking = parsed["ranking"]

            # Validate: must be a permutation of [0..n-1]
            if sorted(ranking) != list(range(n_candidates)):
                raise ValueError(f"Invalid ranking permutation: {ranking}")

            return [int(i) for i in ranking]

        except Exception as exc:
            logger.warning(
                "VisionReranker failed to parse ranking (%s). Using original order.", exc
            )
            return list(range(n_candidates))
