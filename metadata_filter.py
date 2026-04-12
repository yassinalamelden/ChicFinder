"""
ai_engine/retrieval/metadata_filter.py

Bridges FAISS vector search results with the product metadata JSON database.
Enriches raw image_id results with real-world product details.
"""

import json
import os
from functools import lru_cache
from typing import List, Optional, Dict, Any

# ---------------------------------------------------------------------------
# Path to the shared metadata file (relative to the project root).
# Override via the METADATA_PATH environment variable if needed.
# ---------------------------------------------------------------------------
_DEFAULT_METADATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "metadata.json"
)
METADATA_PATH: str = os.environ.get("METADATA_PATH", _DEFAULT_METADATA_PATH)


# ---------------------------------------------------------------------------
# Cached loader — reads from disk exactly once per process lifetime.
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _load_metadata(path: str) -> Dict[str, Any]:
    """
    Load the product metadata JSON file into memory.

    The result is cached by `lru_cache` so subsequent calls return the
    in-memory dictionary without any further disk I/O.

    Args:
        path: Absolute or relative path to ``metadata.json``.

    Returns:
        A dictionary keyed by ``image_id`` (str).

    Raises:
        FileNotFoundError: If the metadata file does not exist at *path*.
        json.JSONDecodeError: If the file content is not valid JSON.
    """
    with open(path, "r", encoding="utf-8") as fh:
        raw: list = json.load(fh)

    # Build a lookup dict keyed by image_id for O(1) access.
    # Supports both formats:
    #   - a JSON array of objects that each contain "image_id"
    #   - a JSON object already keyed by image_id
    if isinstance(raw, list):
        return {str(item["image_id"]): item for item in raw}
    if isinstance(raw, dict):
        return {str(k): v for k, v in raw.items()}

    raise ValueError(
        f"Unexpected metadata format in '{path}': "
        "expected a JSON array or object."
    )


def _get_metadata_db() -> Dict[str, Any]:
    """Thin public wrapper so tests can call this without knowing the path."""
    return _load_metadata(METADATA_PATH)


# ---------------------------------------------------------------------------
# Main enrichment function
# ---------------------------------------------------------------------------
def enrich_search_results(faiss_results: List[dict]) -> List[dict]:
    """
    Enrich FAISS search results with product metadata from the JSON database.

    For every item returned by the FAISS similarity search, this function
    looks up the corresponding product record and appends:
        - ``brand``
        - ``price_egp``
        - ``product_url``
        - ``store_location``

    Missing products (image_id not found in the database) are handled
    gracefully: all four metadata fields are set to ``None`` rather than
    raising a ``KeyError``.

    Args:
        faiss_results: A list of dicts produced by the FAISS search layer.
            Each dict **must** contain at minimum an ``"image_id"`` key.
            Example element::

                {
                    "image_id": "prod_00123",
                    "similarity_score": 0.94
                }

    Returns:
        The same list with four metadata fields injected into each dict.
        Shape matches the ``SearchResultItem`` Pydantic schema (Issue #9)::

            {
                "image_id":        str,
                "similarity_score": float,
                "brand":           str | None,
                "price_egp":       float | None,
                "product_url":     str | None,
                "store_location":  str | None,
            }
    """
    metadata_db: Dict[str, Any] = _get_metadata_db()

    enriched: List[dict] = []

    for result in faiss_results:
        # Work on a shallow copy so we never mutate the caller's objects.
        item = dict(result)

        image_id: str = str(item.get("image_id", ""))
        product_record: Optional[Dict[str, Any]] = metadata_db.get(image_id)

        # Safe .get() calls — returns None for any missing key instead of
        # raising KeyError and causing a 500 Server Error.
        item["brand"]          = product_record.get("brand")          if product_record else None
        item["price_egp"]      = product_record.get("price_egp")      if product_record else None
        item["product_url"]    = product_record.get("product_url")    if product_record else None
        item["store_location"] = product_record.get("store_location") if product_record else None

        enriched.append(item)

    return enriched
