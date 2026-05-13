from fastapi import APIRouter
import logging

from chic_finder.dependencies.supabase import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health")
async def health_check():
    """
    GET /api/v1/health: endpoint for checking the service status.
    Probes Supabase connectivity to detect database issues.
    """
    try:
        client = get_supabase_client()
        client.table("products").select("id").limit(1).execute()
        return {"status": "ok", "service": "ChicFinder API"}
    except Exception as e:
        logger.warning("Health check: Supabase connectivity issue: %s", str(e))
        return {"status": "degraded", "service": "ChicFinder API", "reason": "Database connectivity issue"}
