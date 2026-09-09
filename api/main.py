"""
api/main.py
============
FastAPI application entry point.
"""

from contextlib import asynccontextmanager
import json
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes import recommend, health, stores, search, saved, account
from api.middleware.logging import LoggingMiddleware
from chic_finder.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — pre-warm singletons once at startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load data and pre-warm AI artifacts at startup."""

    # Ensure uploads dir exists
    Path("uploads").mkdir(parents=True, exist_ok=True)

    # Initialize the RDS connection pool (item metadata enrichment for /search).
    # Non-fatal: a machine without DB_* / DB_SECRET_ARN configured still boots;
    # only /search's enrichment will fail until it's set.
    try:
        from chic_finder.db import init_pool

        init_pool()
        logger.info("RDS connection pool initialized.")
    except Exception as exc:
        logger.warning(
            "RDS connection pool not initialized — /search enrichment will fail "
            "until DB_* env vars or DB_SECRET_ARN are set. %s", exc
        )

    # Pre-warm the FAISSVectorStore (skipped gracefully if not built yet)
    # DEV: Disabled for local development
    # try:
    #     from ai_engine.embeddings.vector_store import FAISSVectorStore
    #     FAISSVectorStore.get_instance()
    #     logger.info("FAISSVectorStore pre-warmed successfully.")
    # except FileNotFoundError as exc:
    #     logger.warning("FAISS index not found at startup — AI search disabled. %s", exc)
    # except Exception as exc:
    #     logger.error("Unexpected error pre-warming FAISSVectorStore: %s", exc)

    # Load products.json (used by /stores routes)
    app.state.products = []
    app.state.products_lookup = {}
    products_path = Path(__file__).parent.parent / "products.json"
    if products_path.exists():
        try:
            with open(products_path) as f:
                products = json.load(f)
                app.state.products = products
                app.state.products_lookup = {p.get("id"): p for p in products if p.get("id")}
                logger.info("Loaded %d products from products.json", len(products))
        except Exception as exc:
            logger.error("Failed to load products.json: %s", exc)
    else:
        logger.warning("products.json not found at project root")

    # Load stores.json
    app.state.stores = []
    app.state.stores_lookup = {}
    stores_path = Path(__file__).parent.parent / "stores.json"
    if stores_path.exists():
        try:
            with open(stores_path) as f:
                store_list = json.load(f)
                app.state.stores = store_list
                app.state.stores_lookup = {s.get("id"): s for s in store_list if s.get("id")}
                logger.info("Loaded %d stores from stores.json", len(store_list))
        except Exception as exc:
            logger.error("Failed to load stores.json: %s", exc)
    else:
        logger.warning("stores.json not found at project root")

    yield  # application runs here

    from chic_finder.db import close_pool

    close_pool()

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# CORS — the Next.js dev server, the Expo web dev server, and any origins added
# via CORS_ORIGINS (comma-separated) for deployed frontends.
#
# The native iOS and Android builds send no Origin header, so CORS never applies
# to them. This list only matters for browser-based clients.
_DEFAULT_ORIGINS = [
    "http://localhost:3000",   # Next.js dev
    "http://127.0.0.1:3000",
    "http://localhost:8081",   # Expo web / Metro dev
    "http://127.0.0.1:8081",
]
_extra_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_DEFAULT_ORIGINS + _extra_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)

# Routers
app.include_router(recommend.router, prefix=settings.API_V1_STR, tags=["recommendation"])
app.include_router(health.router,    prefix=settings.API_V1_STR, tags=["health"])
app.include_router(stores.router,    prefix=settings.API_V1_STR, tags=["stores"])
app.include_router(search.router,    prefix=settings.API_V1_STR, tags=["search"])
app.include_router(saved.router,     prefix=settings.API_V1_STR, tags=["saved"])
app.include_router(account.router,   prefix=settings.API_V1_STR, tags=["account"])

# ---------------------------------------------------------------------------
# Static file mounts (directories must exist before mounting)
# ---------------------------------------------------------------------------

_UPLOADS_DIR = Path("uploads")
_DATA_DIR    = Path("data/raw_images")
_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
_DATA_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(_UPLOADS_DIR)), name="uploads")
app.mount("/images",  StaticFiles(directory=str(_DATA_DIR)),    name="images")


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "description": "Egyptian Fashion Recommendation Engine",
        "endpoints": {
            "docs":    "http://localhost:8000/docs",
            "redoc":   "http://localhost:8000/redoc",
            "api_v1":  "/api/v1/",
        },
        "frontend": "http://localhost:3000",
    }
