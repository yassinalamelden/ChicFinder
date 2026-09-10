"""
api/routes/stores.py
=====================
Routes:
  GET /api/v1/stores                    → list all stores
  GET /api/v1/stores/{store_id}         → store detail + all items
  GET /api/v1/stores/{store_id}/items   → items with optional filters

Backed by the RDS catalog (the `items` table), same source of truth as
/search. These routes previously read products.json/stores.json from the repo
root; those files stopped being tracked in git (commit bea05a5), so they were
absent from the Docker image and every one of these endpoints silently
returned an empty list in production.
"""

import logging

from fastapi import APIRouter, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from api.models.schemas import Store, StoreDetailResponse, StoreItem
from chic_finder.db import get_items_by_store, get_stores
from shared.utils.s3_urls import public_image_url

logger = logging.getLogger(__name__)

router = APIRouter()


def _item_to_store_item(item: dict) -> StoreItem:
    """Maps an RDS `items` row to the StoreItem response shape.

    `sizes` and `description` have no column in the catalog schema, so they
    come back empty/None rather than being invented.
    """
    price = item.get("price")
    return StoreItem(
        id=str(item.get("id", "")),
        name=item.get("title") or "",
        brand=item.get("brand"),
        category=item.get("category"),
        type=item.get("sub_category"),
        color=item.get("color"),
        price_egp=float(price) if price is not None else 0.0,
        sizes=[],
        image_url=public_image_url(item.get("image_key")),
        product_url=item.get("product_url"),
        description=None,
        store_id=str(item.get("store_id") or ""),
        store_location=None,
    )


async def _load_stores() -> list[dict]:
    """Fetches the store list, degrading to empty rather than 500ing when RDS
    is unavailable (mirrors how /search handles enrichment failures)."""
    try:
        return await run_in_threadpool(get_stores)
    except Exception as exc:
        logger.warning("Store listing unavailable — RDS query failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# GET /stores
# ---------------------------------------------------------------------------

@router.get("/stores", response_model=list[Store])
async def list_stores():
    """Return all stores present in the catalog."""
    return [Store(**s) for s in await _load_stores()]


# ---------------------------------------------------------------------------
# GET /stores/{store_id}
# ---------------------------------------------------------------------------

@router.get("/stores/{store_id}", response_model=StoreDetailResponse)
async def get_store(store_id: str):
    """Return store metadata plus all its products."""
    store_data = next(
        (s for s in await _load_stores() if s["id"] == store_id), None
    )
    if not store_data:
        raise HTTPException(status_code=404, detail=f"Store '{store_id}' not found.")

    items = await run_in_threadpool(get_items_by_store, store_id)
    store_items = [_item_to_store_item(item) for item in items]

    return StoreDetailResponse(
        store=Store(**store_data),
        items=store_items,
        total_items=len(store_items),
    )


# ---------------------------------------------------------------------------
# GET /stores/{store_id}/items
# ---------------------------------------------------------------------------

@router.get("/stores/{store_id}/items", response_model=list[StoreItem])
async def get_store_items(
    store_id: str,
    category: str = Query(default="", description="Filter by category (tops/bottoms/shoes)"),
    search: str = Query(default="", description="Text search on name and type"),
):
    """Return items for a store with optional category and text filters."""
    if not any(s["id"] == store_id for s in await _load_stores()):
        raise HTTPException(status_code=404, detail=f"Store '{store_id}' not found.")

    items = [_item_to_store_item(item) for item in await run_in_threadpool(get_items_by_store, store_id)]

    if category:
        items = [i for i in items if (i.category or "").lower() == category.lower()]

    if search:
        q = search.lower()
        items = [
            i for i in items
            if q in (i.name or "").lower() or q in (i.type or "").lower()
        ]

    return items
