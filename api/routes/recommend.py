import uuid
import os
import io
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from PIL import Image
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from ai_engine.embeddings.encoder import get_encoder
from ai_engine.embeddings.supabase_vector_store import search_by_vector
from chic_finder.config import settings

logger = logging.getLogger(__name__)

# Force CPU mode to avoid VRAM crashes
os.environ["CUDA_VISIBLE_DEVICES"] = ""

router = APIRouter()

UPLOADS_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class RecommendedItem(BaseModel):
    id: str
    category: str
    image_url: str
    price: Optional[Any] = "N/A"
    brand: Optional[str] = "ChicFinder"


class RecommendationResponse(BaseModel):
    query_item: Dict[str, Any]
    recommendations: List[RecommendedItem]


def _ensure_uploads_dir() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/recommend")
async def get_recommendations(file: UploadFile = File(...)):
    suffix = Path(file.filename or "image.png").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type. Images only.")

    raw_bytes = await file.read()

    # 1. Sanitize image
    try:
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        _ensure_uploads_dir()
        saved_filename = f"{uuid.uuid4()}_clean.png"
        save_path = UPLOADS_DIR / saved_filename
        img.save(save_path, format="PNG")
        query_url = f"/uploads/{saved_filename}"
    except Exception as e:
        logger.error("Image sanitization failed: %s", str(e))
        raise HTTPException(status_code=400, detail="Invalid image format")

    # 2. Encode + Supabase pgvector search
    try:
        encoder = get_encoder()
        raw_vector = encoder._encode(img)
        query_vector = encoder._normalize(raw_vector)

        results = search_by_vector(query_vector, top_k=5)

        items = []
        for meta in results:
            image_filename = meta.get("id", "")
            image_url = settings.get_image_url(image_filename)
            items.append(RecommendedItem(
                id=str(meta.get("id")),
                category=meta.get("category") or "Fashion Item",
                image_url=image_url,
                price=meta.get("price", "N/A"),
                brand=meta.get("brand") or "ChicFinder",
            ))

        recommendation = RecommendationResponse(
            query_item={"type": "Full Outfit", "description": "Visual Search Match"},
            recommendations=items,
        )

        return {
            "success": True,
            "query_url": query_url,
            "engine_used": "FashionCLIP_Supabase",
            "recommendations": [recommendation],
        }

    except Exception:
        logger.error("Recommendation engine failed", exc_info=True)
        raise HTTPException(status_code=500, detail="Recommendation failed. Please try again.")
