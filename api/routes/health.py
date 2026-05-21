import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check():
    """
    Liveness probe used by Railway.
    Always returns HTTP 200 so Railway can start the container and let you
    set env vars. Diagnostic checks are included in the body for observability.
    """
    checks: dict = {}

    # Supabase connectivity (informational only — does not affect HTTP status)
    try:
        from api.db.client import get_supabase_client
        client = get_supabase_client()
        client.table("products").select("id").limit(1).execute()
        checks["supabase"] = "ok"
    except Exception as exc:
        logger.warning("Health check: Supabase unreachable — %s", exc)
        checks["supabase"] = "degraded"

    # FashionCLIP encoder singleton (informational only)
    try:
        from ai_engine.embeddings.encoder import FashionCLIPEncoder
        checks["encoder"] = "ok" if FashionCLIPEncoder._instance is not None else "not_loaded"
    except Exception:
        checks["encoder"] = "unavailable"

    return JSONResponse(
        status_code=200,
        content={"status": "ok", "service": "ChicFinder API", "checks": checks},
    )
