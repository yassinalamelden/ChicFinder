from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import health, recommend, search, stores
from chic_finder.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up the CLIP encoder at startup so the first /recommend request
    # doesn't trigger a cold model load (which would spike memory and timeout).
    from ai_engine.embeddings.encoder import get_encoder
    get_encoder()
    logger.info("CLIP encoder warm-up complete")
    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(health.router, prefix=settings.API_V1_STR, tags=["health"])
app.include_router(recommend.router, prefix=settings.API_V1_STR, tags=["recommend"])
app.include_router(search.router, prefix=settings.API_V1_STR, tags=["search"])
app.include_router(stores.router, prefix=settings.API_V1_STR, tags=["stores"])


@app.get("/")
async def serve_frontend():
    return {
        "service": "ChicFinder API",
        "version": "1.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
