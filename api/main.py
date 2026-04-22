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
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import recommend, health, search
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

    # ---------------------------------------------------------
    # FIX: Load our real Barawy metadata instead of products.json
    # ---------------------------------------------------------
    app.state.metadata = {}
    metadata_path = Path("data/metadata.json")
    if metadata_path.exists():
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                app.state.metadata = json.load(f)
                logger.info("Loaded %d products from data/metadata.json", len(app.state.metadata))
        except Exception as exc:
            logger.error("Failed to load metadata.json: %s", exc)
    else:
        logger.warning("data/metadata.json not found!")

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
app.include_router(search.router,    prefix=settings.API_V1_STR, tags=["search"])

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
