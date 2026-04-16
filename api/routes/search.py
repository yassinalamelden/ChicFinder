from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import base64
import time
import json
import os

from ai_engine.embeddings.vector_store import search_similar_items

router = APIRouter()

# --- LOAD METADATA GLOBALLY ---
# We load this outside the function so it stays in memory and doesn't 
# read the file from scratch on every single user request!
METADATA_PATH = os.path.join("data", "metadata.json")
try:
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)
except FileNotFoundError:
    print("Warning: metadata.json not found. API will return missing details.")
    metadata = {}

class SearchRequest(BaseModel):
    image_base64: str

class SearchResultItem(BaseModel):
    image_id: str
    similarity_score: float
    brand: Optional[str] = None
    title: Optional[str] = None # Added title to match our data
    price_egp: Optional[float] = None
    product_url: Optional[HttpUrl] = None
    store_location: Optional[str] = None
    availability_egypt: bool = True # Defaulting to True for our local brands

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
            b64_data = b64_data.split("base64,")
            
        image_bytes = base64.b64decode(b64_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid base64 encoding")

    try:
        # 2. Search FAISS index (Ask for 15 to allow for deduplication)
        search_results = search_similar_items(image_bytes, top_k=15)
        
        # 3. Map results to schema WITH Deduplication
        response_items = []
        seen_product_ids = set()
        desired_results = 5

        for item in search_results:
            if len(response_items) >= desired_results:
                break
                
            raw_id = str(item.get("image_id", ""))
            clean_id = raw_id.replace(".jpg", "")
            
            # Look up the rich data
            if clean_id in metadata:
                meta_item = metadata[clean_id]
                product_id = meta_item.get('product_id', raw_id)
                
                # --- DEDUPLICATION FILTER ---
                if product_id not in seen_product_ids:
                    seen_product_ids.add(product_id)
                    
                    # Ensure price is a float if it exists, otherwise None
                    raw_price = meta_item.get('price')
                    try:
                        price_val = float(raw_price) if raw_price else None
                    except ValueError:
                        price_val = None

                    # Append the fully populated model
                    response_items.append(
                        SearchResultItem(
                            image_id=str(product_id),
                            similarity_score=float(item.get("similarity_score", 0.0)),
                            brand=meta_item.get('brand'),
                            title=meta_item.get('title'),
                            price_egp=price_val,
                            product_url=meta_item.get('product_url'),
                            availability_egypt=True
                        )
                    )
        
        processing_time_ms = (time.time() - start_time) * 1000
        
        return SearchResponse(
            results=response_items,
            processing_time_ms=processing_time_ms
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))