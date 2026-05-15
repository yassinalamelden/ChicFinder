import base64
import time
import io
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from PIL import Image

from ai_engine.embeddings.supabase_vector_store import search_similar_items
from api.dependencies.auth import require_auth
from chic_finder.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_IMAGE_B64_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = ("JPEG", "PNG", "WEBP", "GIF")


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
    image_urls: List[str] = []
    description: Optional[str] = None
    availability: str = "InStock"
    availability_egypt: bool = True


class SearchResponse(BaseModel):
    results: List[SearchResultItem]
    processing_time_ms: float


@router.post("/search", response_model=SearchResponse)
def search_endpoint(
    request: SearchRequest,
    _user: dict = Depends(require_auth),
):
    start_time = time.time()

    # Decode and validate base64 image
    try:
        b64_data = request.image_base64.strip()
        if "base64," in b64_data:
            b64_data = b64_data.split("base64,")[1]
        missing_padding = len(b64_data) % 4
        if missing_padding:
            b64_data += "=" * (4 - missing_padding)
        image_bytes = base64.b64decode(b64_data)

        try:
            img = Image.open(io.BytesIO(image_bytes))
            if img.format not in ALLOWED_IMAGE_FORMATS:
                raise HTTPException(
                    status_code=400,
                    detail="Unsupported image format. Supported: JPEG, PNG, WEBP, GIF",
                )
            # Re-open fresh before verify() — PIL requires an unread stream;
            # accessing .format above may advance the internal file pointer.
            Image.open(io.BytesIO(image_bytes)).verify()
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

    # Vector search + filter
    try:
        search_results = search_similar_items(image_bytes, top_k=50)

        response_items: List[SearchResultItem] = []
        seen_product_ids: set = set()
        brands_filter = [b.strip().lower() for b in request.brands] if request.brands else []

        for item in search_results:
            if len(response_items) >= 5:
                break

            image_filename = str(item.get("id", ""))
            product_id = item.get("product_id") or image_filename
            similarity_score = float(item.get("score", 0.0))

            # Brand filter
            if brands_filter:
                item_brand = (item.get("brand") or "").strip().lower()
                if item_brand not in brands_filter:
                    continue

            # Price filter
            price_val: Optional[float] = None
            try:
                raw_price = item.get("price")
                price_val = float(raw_price) if raw_price is not None else None
            except (ValueError, TypeError):
                pass

            if request.min_price is not None or request.max_price is not None:
                if price_val is None:
                    continue
                if request.min_price is not None and price_val < request.min_price:
                    continue
                if request.max_price is not None and price_val > request.max_price:
                    continue

            if product_id not in seen_product_ids:
                seen_product_ids.add(product_id)
                image_url = settings.get_image_url(image_filename)
                response_items.append(
                    SearchResultItem(
                        image_id=image_filename,
                        similarity_score=similarity_score,
                        brand=item.get("brand"),
                        title=item.get("title"),
                        price_egp=price_val,
                        product_url=item.get("product_url"),
                        image_url=image_url,
                        image_urls=[image_url],
                        availability="InStock",
                        availability_egypt=True,
                    )
                )

        processing_time_ms = (time.time() - start_time) * 1000
        return SearchResponse(results=response_items, processing_time_ms=processing_time_ms)

    except HTTPException:
        raise
    except Exception:
        logger.error("Search endpoint error", exc_info=True)
        raise HTTPException(status_code=500, detail="Search failed. Please try again.")
