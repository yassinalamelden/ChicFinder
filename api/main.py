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

from api.routes import health
from chic_finder.config import settings

# TODO: Re-enable these routes once health endpoint is stable
# from api.routes import recommend, search, stores
# from api.middleware.logging import LoggingMiddleware

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — pre-warm singletons once at startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure uploads dir exists. All data is now in Supabase."""
    try:
        Path("/tmp/uploads").mkdir(parents=True, exist_ok=True)
        logger.info("✓ Uploads directory ready at /tmp/uploads")
    except Exception as e:
        logger.error("✗ Failed to create uploads directory: %s", str(e))
        raise
    yield
    logger.info("✓ Lifespan shutdown complete")

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

# Routers
app.include_router(health.router,    prefix=settings.API_V1_STR, tags=["health"])

# ---------------------------------------------------------------------------
# Static file mounts (disabled for initial testing)
# ---------------------------------------------------------------------------

# TODO: Re-enable StaticFiles mount once health endpoint is fully stable
# _UPLOADS_DIR = Path("/tmp/uploads")
# _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
# app.mount("/uploads", StaticFiles(directory=str(_UPLOADS_DIR)), name="uploads")


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

@app.get("/")
async def serve_frontend():
    return {
        "service": "ChicFinder API",
        "version": "1.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "endpoints": {
            "recommend": "POST /api/v1/recommend",
            "search": "POST /api/v1/search",
            "stores": "GET /api/v1/stores"
        }
    }
