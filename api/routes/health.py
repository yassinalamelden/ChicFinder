import logging
from fastapi import APIRouter

from api.db.client import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check():
    """Probe Supabase connectivity and return product count."""
    try:
        client = get_supabase_client()
        result = client.table("products").select("id", count="exact").limit(1).execute()
        raw_count = result.count
        product_count = int(raw_count) if raw_count is not None else 0
        return {
            "status": "ok",
            "service": "ChicFinder API",
            "supabase": "connected",
            "products": product_count,
        }
    except Exception as exc:
        logger.error("Health check failed: %s", exc)
        return {
            "status": "degraded",
            "service": "ChicFinder API",
            "supabase": "unreachable",
            "error": str(exc),
        }
