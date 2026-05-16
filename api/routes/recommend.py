import asyncio
import io
import logging
import os
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel

from ai_engine.embeddings.encoder import get_encoder
from ai_engine.embeddings.supabase_vector_store import search_by_vector
from chic_finder.config import settings

logger = logging.getLogger(__name__)

# Force CPU mode to avoid VRAM crashes on Railway
os.environ["CUDA_VISIBLE_DEVICES"] = ""

router = APIRouter()

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_SIDE = 512


class RecommendedItem(BaseModel):
    id: str
    name: Optional[str] = ""
    category: str
    image_url: str
    price: Optional[Any] = "N/A"
    brand: Optional[str] = "ChicFinder"
    product_url: Optional[str] = None


class RecommendationResponse(BaseModel):
    query_item: Dict[str, Any]
    recommendations: List[RecommendedItem]


@router.post("/recommend")
async def get_recommendations(file: UploadFile = File(...)):
    suffix = Path(file.filename or "image.png").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type. Images only.")

    raw_bytes = await file.read()

    # 1. Sanitize image (in memory only — no ephemeral file write)
    try:
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        if max(img.size) > MAX_IMAGE_SIDE:
            img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.LANCZOS)
    except Exception as e:
        logger.error("Image sanitization failed: %s", str(e))
        raise HTTPException(status_code=400, detail="Invalid image format")

    # 2. Encode + Supabase pgvector search (blocking calls moved off event loop)
    try:
        loop = asyncio.get_event_loop()
        encoder = get_encoder()
        raw_vector = await loop.run_in_executor(None, encoder._encode, img)
        query_vector = encoder._normalize(raw_vector)

        results = await loop.run_in_executor(None, partial(search_by_vector, query_vector, top_k=5))

        items = []
        for meta in results:
            image_filename = meta.get("id", "")
            image_url = settings.get_image_url(image_filename)
            items.append(RecommendedItem(
                id=str(meta.get("id")),
                name=meta.get("title") or "",
                category=meta.get("category") or "Fashion Item",
                image_url=image_url,
                price=meta.get("price", "N/A"),
                brand=meta.get("brand") or "ChicFinder",
                product_url=meta.get("product_url"),
            ))

        recommendation = RecommendationResponse(
            query_item={"type": "Full Outfit", "description": "Visual Search Match"},
            recommendations=items,
        )

        return {
            "success": True,
            "engine_used": "FashionCLIP_Supabase",
            "recommendations": [recommendation],
        }

    except Exception:
        logger.error("Recommendation engine failed", exc_info=True)
        raise HTTPException(status_code=500, detail="Recommendation failed. Please try again.")
