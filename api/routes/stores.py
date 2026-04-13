"""
api/routes/stores.py
=====================
Routes:
  GET /api/v1/stores                    → list all stores
  GET /api/v1/stores/{store_id}         → store detail + all items
  GET /api/v1/stores/{store_id}/items   → items with optional filters
"""

from fastapi import APIRouter, HTTPException, Query, Request

from api.models.schemas import Store, StoreDetailResponse, StoreItem

router = APIRouter()


def _product_to_store_item(p: dict) -> StoreItem:
    return StoreItem(
        id=p.get("id", ""),
        name=p.get("name", ""),
        brand=p.get("brand", ""),
        category=p.get("category", ""),
        type=p.get("type", ""),
        color=p.get("color", ""),
        price_egp=float(p.get("price_egp", 0)),
        sizes=p.get("sizes", []),
        image_url=p.get("image_url"),
        product_url=p.get("product_url"),
        description=p.get("description"),
        store_id=p.get("store_id", ""),
        store_location=p.get("store_location"),
    )


# ---------------------------------------------------------------------------
# GET /stores
# ---------------------------------------------------------------------------

@router.get("/stores", response_model=list[Store])
async def list_stores(
    request: Request,
):
    """Return all collaborating stores."""
    stores = getattr(request.app.state, "stores", [])
    return [Store(**s) for s in stores]


# ---------------------------------------------------------------------------
# GET /stores/{store_id}
# ---------------------------------------------------------------------------

@router.get("/stores/{store_id}", response_model=StoreDetailResponse)
async def get_store(
    store_id: str,
    request: Request,
):
    """Return store metadata plus all its products."""
    stores_lookup = getattr(request.app.state, "stores_lookup", {})
    store_data = stores_lookup.get(store_id)
    if not store_data:
        raise HTTPException(status_code=404, detail=f"Store '{store_id}' not found.")

    products = getattr(request.app.state, "products", [])
    store_products = [p for p in products if p.get("store_id") == store_id]

    return StoreDetailResponse(
        store=Store(**store_data),
        items=[_product_to_store_item(p) for p in store_products],
        total_items=len(store_products),
    )


# ---------------------------------------------------------------------------
# GET /stores/{store_id}/items
# ---------------------------------------------------------------------------

@router.get("/stores/{store_id}/items", response_model=list[StoreItem])
async def get_store_items(
    store_id: str,
    request: Request,
    category: str = Query(default="", description="Filter by category (tops/bottoms/shoes)"),
    search: str = Query(default="", description="Text search on name and type"),
):
    """Return items for a store with optional category and text filters."""
    stores_lookup = getattr(request.app.state, "stores_lookup", {})
    if store_id not in stores_lookup:
        raise HTTPException(status_code=404, detail=f"Store '{store_id}' not found.")

    products = getattr(request.app.state, "products", [])
    items = [p for p in products if p.get("store_id") == store_id]

    if category:
        items = [p for p in items if p.get("category", "").lower() == category.lower()]

    if search:
        q = search.lower()
        items = [
            p for p in items
            if q in p.get("name", "").lower() or q in p.get("type", "").lower()
        ]

    return [_product_to_store_item(p) for p in items]
