"""
api/routes/recommend.py
========================
Two routes:
  POST /upload   — save image, return URL
  POST /recommend — pick 4 random products from products.json, return them
"""

import random
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Request

router = APIRouter()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UPLOADS_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _ensure_uploads_dir() -> None:
    """Create ./uploads/ if it doesn't exist."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# POST /upload
# ---------------------------------------------------------------------------

@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """
    POST /api/v1/upload

    Accepts a multipart image file (.jpg .jpeg .png .webp).
    Saves it to ./uploads/{uuid}_{original_filename}.
    Returns { success, filename, url }.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Images only.",
        )

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

@router.post("/recommend")
async def get_recommendations(request: Request, file: UploadFile = File(...)):
    """
    POST /api/v1/recommend

    Accepts a multipart image file.
    Saves the uploaded image to ./uploads/.
    Returns 4 random products from products.json (loaded at startup).
    """
    # Validate extension
    suffix = Path(file.filename or "image.jpg").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Images only.",
        )

    # Save upload so user can see their query image
    image_bytes = await file.read()
    _ensure_uploads_dir()
    saved_filename = f"{uuid.uuid4()}_{file.filename or 'image.jpg'}"
    (UPLOADS_DIR / saved_filename).write_bytes(image_bytes)
    query_url = f"/uploads/{saved_filename}"

    # Load products from app state (populated at startup in main.py)
    products = getattr(request.app.state, "products", [])

    if len(products) == 0:
        raise HTTPException(
            status_code=503,
            detail="No products loaded. Check products.json exists at project root.",
        )

    # Pick 4 random products
    sample_size = min(4, len(products))
    selected = random.sample(products, sample_size)

    # Build recommendations — products.json has no image field,
    # so image stays empty (frontend can show a placeholder)
    recommendations = []
    for rank, product in enumerate(selected, start=1):
        # products.json has no image/image_url/img/photo field
        image_field = (
            product.get("image") or
            product.get("image_url") or
            product.get("img") or
            product.get("photo") or
            product.get("thumbnail") or
            ""
        )
        # Make relative paths absolute
        if image_field and not image_field.startswith("http") \
                       and not image_field.startswith("/"):
            image_field = f"/images/{image_field}"

        recommendations.append({
            "rank":     rank,
            "score":    round(random.uniform(75, 99), 1),
            # products.json actual field names
            "name":     product.get("name") or f"Item {rank}",
            "image":    image_field,
            "price":    product.get("price_egp", ""),   # actual field is price_egp
            "brand":    product.get("brand", ""),
            "category": product.get("category", ""),
            "color":    product.get("color", ""),
            "type":     product.get("type", ""),
            "sizes":    product.get("sizes", []),
            "product":  product,
        })

    return {
        "success":         True,
        "query_url":       query_url,
        "recommendations": recommendations,
    }
