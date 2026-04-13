"""
outfit_parser.py — Gemini Vision outfit decomposition.

Takes a PIL Image of an outfit and returns a structured list of individual
clothing items, each with type, color, style, gender, material, and fit tags.
"""

import json
import logging
from typing import List, Dict

from google import genai
from google.genai import types
from PIL import Image

from chic_finder.config import settings
from ai_engine.llm.prompt_builder import (
    OUTFIT_PARSE_SYSTEM,
    OUTFIT_PARSE_USER,
)

logger = logging.getLogger(__name__)

class OutfitParser:
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self._client = genai.Client(api_key=self.api_key)

    def parse(self, image: Image.Image) -> List[Dict[str, str]]:
        logger.info("OutfitParser.parse() — calling Gemini vision…")

        try:
            # We enforce JSON output directly from Gemini
            response = self._client.models.generate_content(
                model=self.model,
                contents=[
                    OUTFIT_PARSE_USER,
                    image
                ],
                config=types.GenerateContentConfig(
                    system_instruction=OUTFIT_PARSE_SYSTEM,
                    temperature=0.2,
                    response_mime_type="application/json",
                )
            )
        except Exception as exc:
            logger.error("Gemini API call failed: %s", exc)
            raise RuntimeError(f"OutfitParser Gemini API call failed: {exc}") from exc

        raw_text = response.text.strip()
        
        try:
            items_meta = json.loads(raw_text)
            if not isinstance(items_meta, list):
                logger.warning("Gemini returned JSON that is not a list. Wrapping in list.")
                items_meta = [items_meta]
            return items_meta
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse Gemini output as JSON: %s", raw_text)
            raise ValueError("Expected JSON output from LLM.") from exc