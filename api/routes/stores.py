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
    category: str
    type: str
    color: str
    price_egp: float
    sizes: List[str]
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    description: Optional[str] = None
    store_id: str
    store_location: Optional[str] = None


class StoreDetailResponse(BaseModel):
    store: StoreResponse
    items: List[StoreItemResponse]
    total_items: int


# --- HELPERS ---

def _slug(brand: str) -> str:
    return brand.lower().replace(" ", "-")


def _brand_from_slug(slug: str, metadata: dict) -> Optional[str]:
    for item in metadata.values():
        brand = item.get("brand", "")
        if brand and _slug(brand) == slug:
            return brand
    return None


def _item_to_response(key: str, meta: dict, store_id: str) -> StoreItemResponse:
    image_urls = meta.get("image_urls", [])
    return StoreItemResponse(
        id=meta.get("product_id", key),
        name=meta.get("title", ""),
        brand=meta.get("brand", ""),
        category=meta.get("category", ""),
        type=meta.get("subcategory") or meta.get("category", ""),
        color="",
        price_egp=float(meta.get("price") or 0),
        sizes=[],
        image_url=image_urls[0] if image_urls else None,
        product_url=meta.get("product_url"),
        description=meta.get("description"),
        store_id=store_id,
    )


def _build_store(brand: str, items: list[dict]) -> StoreResponse:
    categories = sorted({i.get("category", "") for i in items if i.get("category")})
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
    metadata: dict = getattr(request.app.state, "metadata", {})

    brands: dict[str, list] = {}
    for meta in metadata.values():
        brand = meta.get("brand", "")
        if brand:
            brands.setdefault(brand, []).append(meta)

    return [_build_store(brand, items) for brand, items in sorted(brands.items())]


@router.get("/stores/{store_id}", response_model=StoreDetailResponse)
def get_store(store_id: str, request: Request):
    metadata: dict = getattr(request.app.state, "metadata", {})

    brand = _brand_from_slug(store_id, metadata)
    if not brand:
        raise HTTPException(status_code=404, detail=f"Store '{store_id}' not found")

    brand_items = {k: v for k, v in metadata.items() if v.get("brand", "") == brand}
    store = _build_store(brand, list(brand_items.values()))
    items = [_item_to_response(k, v, store_id) for k, v in list(brand_items.items())[:20]]

    return StoreDetailResponse(store=store, items=items, total_items=store.total_items)


@router.get("/stores/{store_id}/items", response_model=List[StoreItemResponse])
def get_store_items(
    store_id: str,
    request: Request,
    category: Optional[str] = None,
    search: Optional[str] = None,
):
    metadata: dict = getattr(request.app.state, "metadata", {})

    brand = _brand_from_slug(store_id, metadata)
    if not brand:
        raise HTTPException(status_code=404, detail=f"Store '{store_id}' not found")

    results = []
    search_lower = search.lower() if search else None
    category_lower = category.lower() if category else None

    for key, meta in metadata.items():
        if meta.get("brand", "") != brand:
            continue
        if category_lower and meta.get("category", "").lower() != category_lower:
            continue
        if search_lower and search_lower not in meta.get("title", "").lower():
            continue
        results.append(_item_to_response(key, meta, store_id))

    return results
