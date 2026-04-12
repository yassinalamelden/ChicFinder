from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import base64
import time

from ai_engine.embeddings.vector_store import search_similar_items

router = APIRouter()

class SearchRequest(BaseModel):
    image_base64: str

class SearchResultItem(BaseModel):
    image_id: str
    similarity_score: float
    brand: Optional[str] = None
    price_egp: Optional[float] = None
    product_url: Optional[HttpUrl] = None
    store_location: Optional[str] = None
    availability_egypt: bool = False

class SearchResponse(BaseModel):
    results: List[SearchResultItem]
    processing_time_ms: float

@router.post("/search", response_model=SearchResponse)
def search_endpoint(request: SearchRequest):
    start_time = time.time()
    try:
        # 1. Decode Base64
        b64_data = request.image_base64
        if "base64," in b64_data:
            b64_data = b64_data.split("base64,")[1]
            
        image_bytes = base64.b64decode(b64_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid base64 encoding")

    try:
        # 2. Search FAISS index directly (Under 500ms requirement)
        search_results = search_similar_items(image_bytes, top_k=5)
        
        # 3. Map results to schema
        response_items = []
        for item in search_results:
            response_items.append(
                SearchResultItem(
                    image_id=str(item["image_id"]),
                    similarity_score=float(item["similarity_score"])
                )
            )
            
        processing_time_ms = (time.time() - start_time) * 1000
        
        return SearchResponse(
            results=response_items,
            processing_time_ms=processing_time_ms
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

