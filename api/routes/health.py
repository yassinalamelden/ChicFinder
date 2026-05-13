import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check():
    """
    Readiness probe used by Railway and load balancers.
    Returns HTTP 200 when the service is ready to handle traffic.
    """
    checks: dict = {}

    # Supabase connectivity
    try:
        from api.db.client import get_supabase_client
        client = get_supabase_client()
        client.table("products").select("id").limit(1).execute()
        checks["supabase"] = "ok"
    except Exception as exc:
        logger.warning("Health check: Supabase unreachable — %s", exc)
        checks["supabase"] = "degraded"

    # FashionCLIP encoder (just check singleton exists, no re-load)
    try:
        from ai_engine.embeddings.encoder import FashionCLIPEncoder
        checks["encoder"] = "ok" if FashionCLIPEncoder._instance is not None else "not_loaded"
    except Exception:
        checks["encoder"] = "unavailable"

    overall = "ok" if all(v in ("ok", "not_loaded") for v in checks.values()) else "degraded"
    status_code = 200 if overall == "ok" else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "service": "ChicFinder API", "checks": checks},
    )
