"""
api/routes/recommend.py
========================
Two routes:
  POST /upload   — save image, return URL           (auth required)
  POST /recommend — return SearchResponse from products.json (auth required)

The /recommend endpoint intentionally returns mock-random results.
The real RAG pipeline will be wired in by the AI team via RecommendationService.
"""

import random
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request

from api.dependencies.auth import get_current_user
from api.models.schemas import ChicFinderResult, SearchResponse

router = APIRouter()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UPLOADS_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
TOP_K = 8


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
    """
    POST /api/v1/upload

    Accepts a multipart image file (.jpg .jpeg .png .webp).
    Saves it to ./uploads/{uuid}_{original_filename}.
    Returns { success, filename, url }.
    """
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
# POST /recommend
# ---------------------------------------------------------------------------

@router.post("/recommend", response_model=SearchResponse)
async def get_recommendations(
    request: Request,
    file: UploadFile = File(...),
    _user: dict = Depends(get_current_user),
):
    """
    POST /api/v1/recommend

    Accepts a multipart image file.
    Saves the uploaded image to ./uploads/.
    Returns a SearchResponse with products randomly selected from products.json.

    NOTE: The AI team will swap this stub out for the real RAG pipeline.
    """
    start = time.time()

    suffix = Path(file.filename or "image.jpg").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type. Images only.")

    # Save the uploaded query image
    image_bytes = await file.read()
    _ensure_uploads_dir()
    saved_filename = f"{uuid.uuid4()}_{file.filename or 'image.jpg'}"
    (UPLOADS_DIR / saved_filename).write_bytes(image_bytes)

    # Load products from app state
    products = getattr(request.app.state, "products", [])
    if not products:
        raise HTTPException(
            status_code=503,
            detail="No products loaded. Check products.json exists at project root.",
        )

    # Random selection (RAG team will replace this)
    sample_size = min(TOP_K, len(products))
    selected = random.sample(products, sample_size)

    results = [
        ChicFinderResult(
            image_id=p.get("id", str(i)),
            similarity_score=round(random.uniform(0.75, 0.99), 2),
            brand=p.get("brand"),
            price_egp=p.get("price_egp"),
            product_url=p.get("product_url"),
            store_location=p.get("store_location"),
            image_url=p.get("image_url", ""),
            availability_egypt=True,
        )
        for i, p in enumerate(selected)
    ]

    elapsed_ms = (time.time() - start) * 1000

    return SearchResponse(
        results=results,
        processing_time_ms=round(elapsed_ms, 1),
    )
