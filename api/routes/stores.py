import functools
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.db.client import get_supabase_client
from chic_finder.config import settings

router = APIRouter()


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


def _slug(brand: str) -> str:
    return brand.lower().replace(" ", "-").replace("_", "-")


def _build_store(brand: str, entries: list) -> StoreResponse:
    categories = sorted({e.get("category") for e in entries if e.get("category")})
    return StoreResponse(
        id=_slug(brand),
        name=brand,
        description=f"{brand} — fashion items available in Egypt",
        categories=categories,
        total_items=len(entries),
    )


@functools.lru_cache(maxsize=256)
def _resolve_brand(store_id: str) -> Optional[str]:
    """Fetch distinct brand names and match by slug. Result is cached for the process lifetime."""
    client = get_supabase_client()
    rows = client.table("products").select("brand").execute().data or []
    seen: set[str] = set()
    for row in rows:
        brand = row.get("brand") or ""
        if brand and brand not in seen:
            seen.add(brand)
            if _slug(brand) == store_id:
                return brand
    return None


def _get_product_images(db_ids: list[int]) -> dict[int, list[str]]:
    if not db_ids:
        return {}
    client = get_supabase_client()
    rows = (
        client.table("embeddings")
        .select("product_id, image_filename")
        .in_("product_id", db_ids)
        .execute()
        .data or []
    )
    result: dict[int, list[str]] = {}
    for row in rows:
        result.setdefault(row["product_id"], []).append(row["image_filename"])
    return result


def _build_item(row: dict, product_images: dict[int, list[str]], store_id: str) -> StoreItemResponse:
    img_filenames = sorted(product_images.get(row["id"], []))
    image_urls = [settings.get_image_url(f) for f in img_filenames]
    return StoreItemResponse(
        id=row["product_id"],
        name=row.get("title") or "",
        brand=row.get("brand") or "",
        category=row.get("category"),
        type=row.get("category"),
        price_egp=float(row.get("price") or 0),
        image_urls=image_urls,
        product_url=row.get("product_url"),
        description=row.get("description"),
        availability=row.get("availability") or "InStock",
        store_id=store_id,
    )


@router.get("/stores", response_model=List[StoreResponse])
def list_stores():
    client = get_supabase_client()
    rows = client.table("products").select("brand, category, product_id").execute().data or []

    brands: dict[str, list] = {}
    seen: set = set()
    for row in rows:
        pid = row.get("product_id", "")
        if pid in seen:
            continue
        seen.add(pid)
        brand = row.get("brand") or ""
        if brand:
            brands.setdefault(brand, []).append(row)

    return [_build_store(brand, entries) for brand, entries in sorted(brands.items())]


@router.get("/stores/{store_id}", response_model=StoreDetailResponse)
def get_store(store_id: str):
    brand = _resolve_brand(store_id)
    if not brand:
        raise HTTPException(status_code=404, detail=f"Store '{store_id}' not found")

    client = get_supabase_client()
    product_rows = (
        client.table("products")
        .select("id, product_id, title, brand, category, price, product_url, description, availability")
        .eq("brand", brand)
        .execute()
        .data or []
    )

    db_ids = [r["id"] for r in product_rows]
    product_images = _get_product_images(db_ids)

    seen_pids: set = set()
    items = []
    for row in product_rows:
        pid = row["product_id"]
        if pid in seen_pids:
            continue
        seen_pids.add(pid)
        items.append(_build_item(row, product_images, store_id))

    store_entries = [{"brand": r["brand"], "category": r["category"]} for r in product_rows]
    store = _build_store(brand, store_entries)
    return StoreDetailResponse(store=store, items=items, total_items=len(items))


@router.get("/stores/{store_id}/items", response_model=List[StoreItemResponse])
def get_store_items(
    store_id: str,
    category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    brand = _resolve_brand(store_id)
    if not brand:
        raise HTTPException(status_code=404, detail=f"Store '{store_id}' not found")

    client = get_supabase_client()
    query = (
        client.table("products")
        .select("id, product_id, title, brand, category, price, product_url, description, availability")
        .eq("brand", brand)
    )
    if category:
        query = query.ilike("category", category)
    if search:
        query = query.ilike("title", f"%{search}%")

    product_rows = query.execute().data or []
    db_ids = [r["id"] for r in product_rows]
    product_images = _get_product_images(db_ids)

    seen_pids: set = set()
    all_items = []
    for row in product_rows:
        pid = row["product_id"]
        if pid in seen_pids:
            continue
        seen_pids.add(pid)
        all_items.append(_build_item(row, product_images, store_id))
    return all_items[offset : offset + limit]
