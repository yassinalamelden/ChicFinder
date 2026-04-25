"""
api/main.py
============
FastAPI application entry point.
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
from fastapi.staticfiles import StaticFiles

from api.routes import recommend, health, stores, search
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

    # Load data/metadata.json (used by /search route)
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
        logger.warning("data/metadata.json not found — /search will return empty results until built.")

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

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# CORS — allow the Next.js dev server and any future deployed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
