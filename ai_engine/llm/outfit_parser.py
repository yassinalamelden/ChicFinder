"""
outfit_parser.py — Vision outfit decomposition via OpenRouter (Gemini).

Takes a PIL Image of an outfit and returns a structured list of individual
clothing items, each with type, color, style, gender, material, and fit tags.
"""

import json
import logging
from typing import List, Dict

from openai import OpenAI
from PIL import Image

from chic_finder.config import settings
from shared.utils.image_utils import image_to_data_url
from ai_engine.llm.prompt_builder import (
    OUTFIT_PARSE_SYSTEM,
    OUTFIT_PARSE_USER,
)

logger = logging.getLogger(__name__)


def strip_json_fences(text: str) -> str:
    """Strips a leading/trailing ```json ... ``` markdown fence, if present."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rstrip()
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


class OutfitParser:
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model or settings.OPENROUTER_MODEL
        self._client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=self.api_key)

    def parse(self, image: Image.Image) -> List[Dict[str, str]]:
        logger.info("OutfitParser.parse() — calling Gemini via OpenRouter…")

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": OUTFIT_PARSE_SYSTEM},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": OUTFIT_PARSE_USER},
                            {"type": "image_url", "image_url": {"url": image_to_data_url(image)}},
                        ],
                    },
                ],
                temperature=0.0,
                max_tokens=8000,
            )
        except Exception as exc:
            logger.error("OpenRouter API call failed: %s", exc)
            raise RuntimeError(f"OutfitParser OpenRouter API call failed: {exc}") from exc

        raw_text = strip_json_fences(response.choices[0].message.content)

        try:
            items_meta = json.loads(raw_text)
            if not isinstance(items_meta, list):
                logger.warning("Gemini returned JSON that is not a list. Wrapping in list.")
                items_meta = [items_meta]
            return items_meta
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse Gemini output as JSON: %s", raw_text)
            raise ValueError("Expected JSON output from LLM.") from exc