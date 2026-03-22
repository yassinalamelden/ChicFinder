"""
api/routes/recommend.py
========================
Two routes:
  POST /upload   — save image, return URL
  POST /recommend — FAISS similarity search, return 5 ranked results
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

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
    # Validate extension
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
async def get_recommendations(file: UploadFile = File(...)):
    """
    POST /api/v1/recommend

    Accepts a multipart image file.
    Runs it through FAISSVectorStore (singleton, loaded at startup).
    Returns the top-5 similar items wrapped in the shape the frontend expects:
      [{ query_item, recommendations: [{ id, category, sub_category,
                                         color, style, image_url,
                                         brand, price, rank, score }] }]
    """
    # Validate extension
    suffix = Path(file.filename or "image.jpg").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Images only.",
        )

    image_bytes = await file.read()

    # Save upload so user can see their query image
    _ensure_uploads_dir()
    saved_filename = f"{uuid.uuid4()}_{file.filename or 'image.jpg'}"
    (UPLOADS_DIR / saved_filename).write_bytes(image_bytes)
    query_url = f"/uploads/{saved_filename}"

    # FAISS search — use the singleton loaded at app startup
    try:
        from ai_engine.embeddings.vector_store import FAISSVectorStore
        store = FAISSVectorStore.get_instance()
        hits = store.search(image_bytes, top_k=5)
    except FileNotFoundError as exc:
        # Index not built yet — return empty results with a clear message
        raise HTTPException(
            status_code=503,
            detail=f"FAISS index not available: {exc}. "
                   "Run scripts/02_build_faiss_index.py first.",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Map hits → frontend-compatible RecommendedItem dicts
    recommendations = []
    for rank, hit in enumerate(hits, start=1):
        filename = hit.get("filename", "")
        recommendations.append({
            "rank":         rank,
            "id":           hit.get("id", str(rank)),
            "filename":     filename,
            # /dataset/* is mounted at ./data/images/ — see main.py
            "image_url":    f"/dataset/{filename}" if filename else hit.get("image_url", ""),
            "score":        round(hit.get("score", 0.0), 4),
            # Metadata fields — may be absent if index was built without them
            "category":     hit.get("category", "Fashion"),
            "sub_category": hit.get("sub_category", "N/A"),
            "color":        hit.get("color", "N/A"),
            "style":        hit.get("style", "N/A"),
            "brand":        hit.get("brand"),
            "price":        hit.get("price"),
        })

    # Wrap in the shape results_page.py expects:
    #   for rec in recommendations:
    #       rec["query_item"], rec["recommendations"]
    return [
        {
            "query_item": {
                "type":  "uploaded_outfit",
                "color": "N/A",
                "style": "N/A",
            },
            "query_url":      query_url,
            "recommendations": recommendations,
        }
    ]
