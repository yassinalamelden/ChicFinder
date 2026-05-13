from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import health
from chic_finder.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path("/tmp/uploads").mkdir(parents=True, exist_ok=True)
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


@app.get("/")
async def serve_frontend():
    return {
        "service": "ChicFinder API",
        "version": "1.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
