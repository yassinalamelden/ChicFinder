"""
api/main.py
============
FastAPI application entry point.

  - `lifespan` warms up FashionCLIP encoder and verifies Supabase connection.
  - Mounted ./uploads at /uploads (writable, for query images).
  - All product data and images are served from Supabase (PostgreSQL + Storage).
"""

from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import recommend, health, search, stores
from api.middleware.logging import LoggingMiddleware
from chic_finder.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — pre-warm singletons once at startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure uploads dir exists. All data is now in Supabase."""
    Path("uploads").mkdir(parents=True, exist_ok=True)

    # Warm up the FashionCLIP encoder (downloads model on first run)
    try:
        from ai_engine.embeddings.encoder import get_encoder
        get_encoder()
        logger.info("FashionCLIP encoder ready.")
    except Exception as exc:
        logger.error("Failed to warm up encoder: %s", exc)

    # Verify Supabase connection
    try:
        from api.db.client import get_supabase_client
        client = get_supabase_client()
        client.table("products").select("id").limit(1).execute()
        logger.info("Supabase connection verified.")
    except Exception as exc:
        logger.error("Supabase connection failed: %s", exc)

    yield

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# CORS — restrict origins to configured frontend URLs
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Custom logging middleware
app.add_middleware(LoggingMiddleware)

# Routers
app.include_router(recommend.router, prefix=settings.API_V1_STR, tags=["recommendation"])
app.include_router(health.router,    prefix=settings.API_V1_STR, tags=["health"])
app.include_router(search.router,    prefix=settings.API_V1_STR, tags=["search"])
app.include_router(stores.router,    prefix=settings.API_V1_STR, tags=["stores"])

# ---------------------------------------------------------------------------
# Ensure required directories exist (must happen BEFORE app.mount calls)
# ---------------------------------------------------------------------------

_UPLOADS_DIR = Path("uploads")
_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Static file mounts
# ---------------------------------------------------------------------------

# User-uploaded query images
app.mount("/uploads", StaticFiles(directory=str(_UPLOADS_DIR)), name="uploads")


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")
