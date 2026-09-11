"""
api/main.py
============
FastAPI application entry point.
"""

from contextlib import asynccontextmanager
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

    # NOTE: /stores used to be served from products.json/stores.json loaded
    # here. Those files stopped being tracked in git (bea05a5), so they never
    # reached the Docker image and every /stores response was silently empty
    # in production. The routes now read the RDS catalog directly, same source
    # of truth as /search — nothing to load at startup.

    yield  # application runs here

    from chic_finder.db import close_pool

    close_pool()

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

_IS_PRODUCTION = settings.APP_ENV == "production"

# Swagger/ReDoc are served publicly by default, which publishes the whole API
# surface to anyone who finds the load balancer. Keep them in development,
# switch them off in production.
app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    docs_url=None if _IS_PRODUCTION else "/docs",
    redoc_url=None if _IS_PRODUCTION else "/redoc",
    openapi_url=None if _IS_PRODUCTION else "/openapi.json",
)

# CORS — origins come from settings.CORS_ORIGINS (env var CORS_ORIGINS), a
# comma-separated list. Defaults to local dev only; production sets this to
# include the real Framer frontend origin (see compute.py).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
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
    """Service banner. Paths are relative — this is served from a load balancer
    in production, so absolute localhost URLs would be wrong for every caller."""
    endpoints = {"api_v1": settings.API_V1_STR, "health": f"{settings.API_V1_STR}/health"}
    if not _IS_PRODUCTION:
        endpoints["docs"] = "/docs"
        endpoints["redoc"] = "/redoc"

    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "description": "Egyptian Fashion Recommendation Engine",
        "environment": settings.APP_ENV,
        "endpoints": endpoints,
    }
