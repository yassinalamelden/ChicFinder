from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    GET /api/v1/health: endpoint for checking the service status.
    """
    return {"status": "ok", "service": "ChicFinder API"}
