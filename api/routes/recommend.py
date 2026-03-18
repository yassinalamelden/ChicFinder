from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
from api.models.schemas import RecommendationResponse
from api.services.recommendation_service import RecommendationService

router = APIRouter()

@router.post("/recommend", response_model=List[RecommendationResponse])
async def get_recommendations(file: UploadFile = File(...)):
    """
    POST /api/v1/recommend: endpoint for image-based outfit recommendations.
    """
    try:
        image_bytes = await file.read()
        service = RecommendationService()
        results = service.process_recommendation(image_bytes)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
