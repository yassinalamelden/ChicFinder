"""
api/routes/recommend.py
========================
POST /upload   — save image, return URL (auth-gated)
POST /recommend — real FashionCLIP+FAISS visual similarity pipeline
"""

import uuid
import os
import io
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from PIL import Image

# ─── GEMINI RAG PIPELINE ───
from api.services.recommendation_service import get_recommendation_service

# ─── LOCAL AI PIPELINE ───
from ai_engine.embeddings.encoder import get_encoder
from ai_engine.embeddings.vector_store import FAISSVectorStore

from api.dependencies.auth import get_current_user
from api.models.schemas import RecommendedItem, RecommendationResponse

logger = logging.getLogger(__name__)

# Force CPU mode to avoid the VRAM crash during local testing
os.environ["CUDA_VISIBLE_DEVICES"] = ""

router = APIRouter()

UPLOADS_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# Initialize local vector store globally (None if index not built yet)
try:
    vector_store = FAISSVectorStore.get_instance()
except Exception as _faiss_err:
    import logging as _logging
    _logging.getLogger(__name__).warning("FAISS unavailable — /recommend will return 503 until index is built. %s", _faiss_err)
    vector_store = None

def _ensure_uploads_dir() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# POST /upload
# ---------------------------------------------------------------------------

@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    _user: dict = Depends(get_current_user),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type. Images only.")

    _ensure_uploads_dir()

    saved_filename = f"{uuid.uuid4()}_{file.filename}"
    save_path = UPLOADS_DIR / saved_filename
    contents = await file.read()
    save_path.write_bytes(contents)

    return {
        "success": True,
        "filename": saved_filename,
        "url": f"/uploads/{saved_filename}",
    }


# ---------------------------------------------------------------------------
# POST /recommend  (real FashionCLIP + FAISS pipeline)
# ---------------------------------------------------------------------------

@router.post("/recommend")
async def get_recommendations(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    suffix = Path(file.filename or "image.png").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type. Images only.")

    raw_bytes = await file.read()

    # ─── 1. BULLETPROOF IMAGE SANITIZATION ───
    try:
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        query_url = None
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Corrupted image format. Error: {e}")

    # ─── GEMINI RAG PIPELINE (OutfitParser + FashionCLIP + VisionReranker) ───
    try:
        service = get_recommendation_service()
        rag_responses = service.process_recommendation(raw_bytes)
        if rag_responses:
            return {
                "success": True,
                "query_url": query_url,
                "engine_used": "Gemini_RAG_Pipeline",
                "recommendations": rag_responses,
            }
        # Gemini parsed zero garments — fall through to the FAISS fallback below.
    except Exception as exc:
        logger.warning("RAG pipeline failed, falling back to local FAISS: %s", exc)

    # ─── 2. LOCAL FASHIONCLIP + FAISS SEARCH ───
    if vector_store is None:
        raise HTTPException(status_code=503, detail="FAISS index not built yet. Run scripts/02_build_faiss_index.py first.")

    try:
        print("Running Local FashionCLIP Pipeline...")
        encoder = get_encoder()

        raw_vector = encoder._encode(img)
        query_vector = encoder._normalize(raw_vector)

        results = vector_store.search_by_vector(query_vector, top_k=5)

        fallback_items = []
        for meta in results:
            raw_path = meta.get("image_url", "")
            normalized_path = raw_path.replace("\\", "/")
            clean_web_url = "/" + normalized_path.replace("data/", "")

            fallback_items.append(RecommendedItem(
                id=str(meta.get("id")),
                category=meta.get("category", "Local Match"),
                sub_category=None,
                color=None,
                style=None,
                image_url=meta.get("image_url", ""),
                price=meta.get("price"),
                brand=meta.get("brand", "ChicFinder Local")
            ))

        fallback_recommendation = RecommendationResponse(
            query_item={"type": "Full Outfit", "description": "Local Visual Search Match"},
            recommendations=fallback_items
        )

        return {
            "success": True,
            "query_url": query_url,
            "engine_used": "Local_FashionCLIP_FAISS",
            "recommendations": [fallback_recommendation]
        }

    except Exception as local_e:
        print(f"CRITICAL LOCAL ERROR: {local_e}")
        raise HTTPException(status_code=500, detail=f"Local Engine Crash: {local_e}")
