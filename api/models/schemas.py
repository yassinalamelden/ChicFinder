from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class RecommendedItem(BaseModel):
    id: str
    category: str
    sub_category: Optional[str] = None
    color: Optional[str] = None
    style: Optional[str] = None
    image_url: str
    brand: Optional[str] = None
    price: Optional[float] = None


class RecommendationResponse(BaseModel):
    query_item: Dict[str, Any]
    recommendations: List[RecommendedItem]


class ChicFinderResult(BaseModel):
    image_id: str
    similarity_score: float
    brand: Optional[str] = None
    price_egp: Optional[float] = None
    product_url: Optional[str] = None
    store_location: Optional[str] = None
    image_url: str
    availability_egypt: bool = True


class SearchResponse(BaseModel):
    results: List[ChicFinderResult]
    processing_time_ms: float


class Store(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    location: Optional[str] = None
    categories: List[str] = []


class StoreItem(BaseModel):
    id: str
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    type: Optional[str] = None
    color: Optional[str] = None
    price_egp: float = 0.0
    sizes: List[str] = []
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    description: Optional[str] = None
    store_id: str
    store_location: Optional[str] = None


class StoreDetailResponse(BaseModel):
    store: Store
    items: List[StoreItem]
    total_items: int
