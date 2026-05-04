from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


# --- SCHEMAS ---

class StoreResponse(BaseModel):
    id: str
    name: str
    description: str
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    location: Optional[str] = None
    categories: List[str]
    total_items: int


class StoreItemResponse(BaseModel):
    id: str
    name: str
    brand: str
    category: Optional[str] = None
    type: Optional[str] = None
    price_egp: float
    image_urls: List[str] = []
    product_url: Optional[str] = None
    description: Optional[str] = None
    availability: str = "InStock"
    store_id: str


class StoreDetailResponse(BaseModel):
    store: StoreResponse
    items: List[StoreItemResponse]
    total_items: int


# --- HELPERS ---

def _slug(brand: str) -> str:
    return brand.lower().replace(" ", "-").replace("_", "-")


def _brand_from_slug(slug: str, barawy_data: list) -> Optional[str]:
    for record in barawy_data:
        brand = record.get("brand", "")
        if brand and _slug(brand) == slug:
            return brand
    return None


def _item_to_response(record: dict, store_id: str) -> StoreItemResponse:
    return StoreItemResponse(
        id=record["id"],
        name=record.get("name", ""),
        brand=record.get("brand", ""),
        category=record.get("category"),
        type=record.get("subcategory") or record.get("category"),
        price_egp=float(record.get("price") or 0),
        image_urls=record.get("image_urls", []),
        product_url=record.get("product_url"),
        description=record.get("description"),
        availability=record.get("availability", "InStock"),
        store_id=store_id,
    )


def _build_store(brand: str, items: list) -> StoreResponse:
    categories = sorted({r.get("category") for r in items if r.get("category")})
    return StoreResponse(
        id=_slug(brand),
        name=brand,
        description=f"{brand} — fashion items available in Egypt",
        categories=categories,
        total_items=len(items),
    )


# --- ENDPOINTS ---

@router.get("/stores", response_model=List[StoreResponse])
def list_stores(request: Request):
    barawy_data: list = getattr(request.app.state, "barawy_data", [])
    brands: dict[str, list] = {}
    for record in barawy_data:
        brand = record.get("brand", "")
        if brand:
            brands.setdefault(brand, []).append(record)
    return [_build_store(brand, items) for brand, items in sorted(brands.items())]


@router.get("/stores/{store_id}", response_model=StoreDetailResponse)
def get_store(store_id: str, request: Request):
    barawy_data: list = getattr(request.app.state, "barawy_data", [])
    brand = _brand_from_slug(store_id, barawy_data)
    if not brand:
        raise HTTPException(status_code=404, detail=f"Store '{store_id}' not found")
    brand_items = [r for r in barawy_data if r.get("brand", "") == brand]
    store = _build_store(brand, brand_items)
    items = [_item_to_response(r, store_id) for r in brand_items]
    return StoreDetailResponse(store=store, items=items, total_items=store.total_items)


@router.get("/stores/{store_id}/items", response_model=List[StoreItemResponse])
def get_store_items(
    store_id: str,
    request: Request,
    category: Optional[str] = None,
    search: Optional[str] = None,
):
    barawy_data: list = getattr(request.app.state, "barawy_data", [])
    brand = _brand_from_slug(store_id, barawy_data)
    if not brand:
        raise HTTPException(status_code=404, detail=f"Store '{store_id}' not found")

    search_lower = search.lower() if search else None
    category_lower = category.lower() if category else None
    results = []
    for record in barawy_data:
        if record.get("brand", "") != brand:
            continue
        if category_lower and (record.get("category") or "").lower() != category_lower:
            continue
        if search_lower and search_lower not in (record.get("name") or "").lower():
            continue
        results.append(_item_to_response(record, store_id))
    return results
