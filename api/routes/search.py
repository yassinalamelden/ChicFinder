import base64
import time
import os
import io
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, HttpUrl, Field
from PIL import Image

# Import the standalone function from your vector store
from ai_engine.embeddings.vector_store import search_similar_items
from api.dependencies.auth import require_auth

logger = logging.getLogger(__name__)
router = APIRouter()

# --- CONSTANTS ---
MAX_IMAGE_B64_BYTES = 10 * 1024 * 1024  # 10 MB decoded limit
ALLOWED_IMAGE_FORMATS = ("JPEG", "PNG", "WEBP", "GIF")

# --- SCHEMAS ---

class SearchRequest(BaseModel):
    image_base64: str = Field(..., max_length=MAX_IMAGE_B64_BYTES * 4 // 3 + 100)
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    brands: Optional[List[str]] = None

class SearchResultItem(BaseModel):
    image_id: str
    similarity_score: float
    brand: Optional[str] = None
    title: Optional[str] = None
    price_egp: Optional[float] = None
    product_url: Optional[str] = None
    image_url: Optional[str] = None
    availability_egypt: bool = True

class SearchResponse(BaseModel):
    results: List[SearchResultItem]
    processing_time_ms: float

# --- ENDPOINT ---

@router.post("/search", response_model=SearchResponse)
def search_endpoint(
    request: SearchRequest,
    fastapi_req: Request,
    _user: dict = Depends(require_auth),
):
    start_time = time.time()
    metadata = getattr(fastapi_req.app.state, "metadata", {})

    try:
        # 1. Clean the string (removes hidden newlines or spaces from copy-pasting)
        b64_data = request.image_base64.strip()

        # 2. Remove the header if it exists ("data:image/jpeg;base64,")
        if "base64," in b64_data:
            b64_data = b64_data.split("base64,")[1]

        # 3. Fix missing padding (Python requires the length to be a multiple of 4)
        missing_padding = len(b64_data) % 4
        if missing_padding:
            b64_data += '=' * (4 - missing_padding)

        # 4. Decode
        image_bytes = base64.b64decode(b64_data)

        # 5. Validate image format before passing to FAISS
        try:
            img = Image.open(io.BytesIO(image_bytes))
            if img.format not in ALLOWED_IMAGE_FORMATS:
                raise HTTPException(status_code=400, detail="Unsupported image format. Supported: JPEG, PNG, WEBP, GIF")
            img.verify()
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("Image validation failed: %s", str(e))
            raise HTTPException(status_code=400, detail="Invalid image data")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Base64 decode failed: %s", str(e))
        raise HTTPException(status_code=400, detail="Invalid image format")

    try:
        # Increase top_k to allow enough items after filtering
        search_results = search_similar_items(image_bytes, top_k=50)
        
        response_items = []
        seen_product_ids = set()
        desired_results = 5
        
        # Prepare filters
        brands_filter = [b.strip().lower() for b in request.brands] if request.brands else []

        for item in search_results:
            if len(response_items) >= desired_results:
                break
                
            raw_id = str(item.get("id", ""))
            clean_id = raw_id.replace(".jpg", "")
            similarity_score = float(item.get("score", 0.0))
            
            if clean_id in metadata:
                meta_item = metadata[clean_id]
                
                # Filter by brand
                if brands_filter:
                    item_brand = meta_item.get('brand', '')
                    if not item_brand or item_brand.strip().lower() not in brands_filter:
                        continue
                        
                # Filter by price
                try:
                    raw_price = meta_item.get('price')
                    price_val = float(raw_price) if raw_price else None
                except (ValueError, TypeError):
                    price_val = None
                    
                if request.min_price is not None or request.max_price is not None:
                    if price_val is None:
                        continue
                    if request.min_price is not None and price_val < request.min_price:
                        continue
                    if request.max_price is not None and price_val > request.max_price:
                        continue
                        
                product_id = meta_item.get('product_id', clean_id)
                
                if product_id not in seen_product_ids:
                    seen_product_ids.add(product_id)

                    image_urls = meta_item.get('image_urls', [])
                    image_url = image_urls[0] if image_urls else f"/images/{clean_id}.jpg"

                    response_items.append(
                        SearchResultItem(
                            image_id=clean_id,
                            similarity_score=similarity_score,
                            brand=meta_item.get('brand'),
                            title=meta_item.get('title'),
                            price_egp=price_val,
                            product_url=meta_item.get('product_url'),
                            image_url=image_url,
                            availability_egypt=True
                        )
                    )
            else:
                # If no metadata exists, we drop it from search results if filters are applied
                if brands_filter or request.min_price is not None or request.max_price is not None:
                    continue
                    
                if clean_id not in seen_product_ids:
                    seen_product_ids.add(clean_id)
                    response_items.append(
                        SearchResultItem(
                            image_id=clean_id,
                            similarity_score=similarity_score
                        )
                    )
        
        processing_time_ms = (time.time() - start_time) * 1000

        return SearchResponse(
            results=response_items,
            processing_time_ms=processing_time_ms
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Search endpoint error", exc_info=True)
        raise HTTPException(status_code=500, detail="Search failed. Please try again.")