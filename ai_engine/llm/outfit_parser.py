"""
outfit_parser.py — GPT-4o Vision outfit decomposition.

Takes a PIL Image of an outfit and returns a structured list of individual
clothing items, each with type, color, style, gender, material, and fit tags.

Implements Step 3 of the OutfitAI architecture:
  Photo → LLM Vision → [{type, color, style, gender, material, fit}, ...]
"""

import io
import json
import logging
from typing import List, Dict

from openai import OpenAI
from PIL import Image

from chic_finder.config import settings
from shared.utils.image_utils import image_to_base64
from ai_engine.llm.prompt_builder import (
    OUTFIT_PARSE_SYSTEM,
    OUTFIT_PARSE_USER,
)

logger = logging.getLogger(__name__)


class OutfitParser:
    """
    OutfitParser: photo → [{type, color, style, gender, material, fit}, ...]

    Uses GPT-4o's vision capabilities to decompose a full outfit photograph
    into individual, purchasable clothing items with rich metadata.

    Referencing: OutfitAI architecture Step 3.
    """

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.GPT_MODEL
        self._client = OpenAI(api_key=self.api_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, image: Image.Image) -> List[Dict[str, str]]:
        """
        Parses an outfit image into a structured list of clothing items.

        Args:
            image: PIL Image of the outfit (background may or may not be removed).

        Returns:
            A list of dicts, each with keys:
              "type", "color", "style", "gender", "material", "fit"

        Raises:
            ValueError: If the LLM returns unparseable JSON.
            RuntimeError: If the OpenAI API call fails entirely.
        """
        logger.info("OutfitParser.parse() — calling GPT-4o vision…")

        # Encode image as base64 PNG for the vision API
        b64_image = image_to_base64(image, format="PNG")

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.2,  # Low temperature for reproducible structured output
                messages=[
                    {
                        "role": "system",
                        "content": OUTFIT_PARSE_SYSTEM,
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{b64_image}",
                                    "detail": "high",
                                },
                            },
                            {
                                "type": "text",
                                "text": OUTFIT_PARSE_USER,
                            },
                        ],
                    },
                ],
            )
        except Exception as exc:
            logger.error("OpenAI API call failed: %s", exc)
            raise RuntimeError(f"OutfitParser OpenAI API call failed: {exc}") from exc

        raw_text = response.choices[0].message.content.strip()
        logger.debug("GPT-4o raw outfit-parse response: %s", raw_text)

        items = self._parse_response(raw_text)
        logger.info("OutfitParser found %d items.", len(items))
        return items

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_response(self, raw_text: str) -> List[Dict[str, str]]:
        """
        Safely parses the GPT-4o JSON response into a Python list.
        Strips any accidental markdown fences before parsing.
        """
        # Strip markdown code fences if the model added them despite instructions
        text = raw_text
        if text.startswith("```"):
            lines = text.splitlines()
            # Remove first and last fence lines
            text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse outfit JSON: %s\nRaw: %s", exc, raw_text)
            raise ValueError(
                f"OutfitParser could not parse GPT-4o response as JSON: {exc}\n"
                f"Raw response:\n{raw_text}"
            ) from exc

        if not isinstance(parsed, list):
            raise ValueError(
                f"OutfitParser expected a JSON array from GPT-4o, got: {type(parsed)}"
            )

        # Normalize: ensure all required keys are present with fallbacks
        required_keys = {"type", "color", "style", "gender", "material", "fit"}
        normalized = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            entry = {k: item.get(k, "unknown") for k in required_keys}
            normalized.append(entry)

        return normalized
