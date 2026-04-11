"""
api/main.py
============
FastAPI application entry point.

Changes vs original:
  - Added `lifespan` context manager to pre-warm FAISSVectorStore once at startup.
  - Mounted ./uploads at /uploads (writable, for query images).
  - Mounted ./data/images at /dataset (read-only, for dataset images).
  - Registered the new /upload route (same router file as /recommend).
"""

from contextlib import asynccontextmanager
import json
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import recommend, health
from api.middleware.logging import LoggingMiddleware
from chic_finder.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — pre-warm singletons once at startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Load heavy AI artifacts once when the server starts.
    Gracefully skips if the FAISS index hasn't been built yet.
    """
    # Ensure ./uploads/ exists so StaticFiles mount doesn't fail
    Path("uploads").mkdir(parents=True, exist_ok=True)

    # Pre-warm the FAISSVectorStore (+ FashionCLIPEncoder inside it)
    try:
        from ai_engine.embeddings.vector_store import FAISSVectorStore
        FAISSVectorStore.get_instance()
        logger.info("FAISSVectorStore pre-warmed successfully.")
    except FileNotFoundError as exc:
        logger.warning(
            "FAISS index not found at startup — searches will fail until built. %s", exc
        )
    except Exception as exc:
        logger.error("Unexpected error pre-warming FAISSVectorStore: %s", exc)

    # Load products.json
    app.state.products = []
    app.state.products_lookup = {}
    products_path = Path("products.json")
    if products_path.exists():
        try:
            with open(products_path) as f:
                products = json.load(f)
                app.state.products = products
                # Build lookup by ID (padded to match FAISS index logic if needed)
                # Strategy B: key by id or filename. products.json has id: "001"
                app.state.products_lookup = {
                    p.get("id"): p for p in products if p.get("id")
                }
                logger.info("Loaded %d products from products.json", len(products))
        except Exception as exc:
            logger.error("Failed to load products.json: %s", exc)
    else:
        logger.warning("products.json not found at project root")

    yield  # application runs here


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom logging middleware
app.add_middleware(LoggingMiddleware)

# Routers
app.include_router(recommend.router, prefix=settings.API_V1_STR, tags=["recommendation"])
app.include_router(health.router,    prefix=settings.API_V1_STR, tags=["health"])

# ---------------------------------------------------------------------------
# Ensure required directories exist (must happen BEFORE app.mount calls)
# ---------------------------------------------------------------------------

_UPLOADS_DIR = Path("uploads")
_DATA_DIR    = Path("data/raw_images")
_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
_DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Static file mounts
# ---------------------------------------------------------------------------

# User-uploaded query images
app.mount("/uploads", StaticFiles(directory=str(_UPLOADS_DIR)), name="uploads")

# Dataset images — served read-only so frontend can display results by URL
app.mount("/images", StaticFiles(directory=str(_DATA_DIR)), name="images")


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")
