"""
api/routes/saved.py
====================
Saved items (wishlist) for the mobile app.

Routes:
  GET    /api/v1/saved            → the caller's saved items, enriched
  GET    /api/v1/saved/ids        → just the IDs, for cheap heart-icon state
  PUT    /api/v1/saved/{item_id}  → save an item (idempotent)
  DELETE /api/v1/saved/{item_id}  → unsave an item (idempotent)

Every route is scoped to the Firebase uid from the bearer token, so a user can
only read or write their own rows.

Enrichment reads the RDS `items` table first (that is where search results come
from) and falls back to the in-memory products.json catalog that the /stores
routes serve. An ID that resolves in neither is still returned, with nulls, so a
catalog change never makes a user's wishlist disappear.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependencies.auth import get_current_user
from chic_finder import db

logger = logging.getLogger(__name__)

router = APIRouter()

# An item_id longer than this is not a real catalog ID, it is someone probing.
_MAX_ITEM_ID_LEN = 128


class SavedItem(BaseModel):
    id: str
    name: str | None = None
    brand: str | None = None
    category: str | None = None
    price_egp: float | None = None
    image_url: str | None = None
    product_url: str | None = None
    store_id: str | None = None
    store_location: str | None = None


class SavedItemsResponse(BaseModel):
    items: list[SavedItem]
    total: int


class SavedIdsResponse(BaseModel):
    ids: list[str]


def _from_rds_row(row: dict) -> SavedItem:
    """Maps a row of the RDS `items` table onto the response shape."""
    image_key = row.get("image_key")
    return SavedItem(
        id=row["id"],
        name=row.get("title"),
        brand=row.get("brand"),
        category=row.get("category"),
        price_egp=float(row["price"]) if row.get("price") is not None else None,
        image_url=f"/images/{image_key}" if image_key else None,
        product_url=row.get("product_url"),
        store_id=row.get("store_id"),
    )


def _from_catalog(product: dict) -> SavedItem:
    """Maps a products.json entry onto the response shape."""
    price = product.get("price_egp", product.get("price"))
    return SavedItem(
        id=product.get("id", ""),
        name=product.get("name"),
        brand=product.get("brand"),
        category=product.get("category"),
        price_egp=float(price) if price is not None else None,
        image_url=product.get("image_url"),
        product_url=product.get("product_url"),
        store_id=product.get("store_id"),
        store_location=product.get("store_location"),
    )


def _validate_item_id(item_id: str) -> str:
    item_id = item_id.strip()
    if not item_id or len(item_id) > _MAX_ITEM_ID_LEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item id.",
        )
    return item_id


# ---------------------------------------------------------------------------
# GET /saved
# ---------------------------------------------------------------------------

@router.get("/saved", response_model=SavedItemsResponse)
async def list_saved(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Returns the caller's saved items, newest first, with catalog metadata."""
    uid = user["uid"]

    try:
        item_ids = await run_in_threadpool(db.list_saved_item_ids, uid)
    except Exception as exc:
        logger.error("Failed to list saved items for uid=%s: %s", uid, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Saved items are temporarily unavailable.",
        )

    if not item_ids:
        return SavedItemsResponse(items=[], total=0)

    # Enrich from RDS, then fill the gaps from the JSON catalog.
    rds_rows: dict[str, dict] = {}
    try:
        rds_rows = await run_in_threadpool(db.get_items_by_ids, item_ids)
    except Exception as exc:
        # Degrade rather than 500: the wishlist is still usable from the catalog.
        logger.warning("RDS enrichment failed for saved items: %s", exc)

    catalog = getattr(request.app.state, "products_lookup", {})

    items: list[SavedItem] = []
    for item_id in item_ids:  # preserves newest-first ordering
        if item_id in rds_rows:
            items.append(_from_rds_row(rds_rows[item_id]))
        elif item_id in catalog:
            items.append(_from_catalog(catalog[item_id]))
        else:
            items.append(SavedItem(id=item_id))

    return SavedItemsResponse(items=items, total=len(items))


# ---------------------------------------------------------------------------
# GET /saved/ids
# ---------------------------------------------------------------------------

@router.get("/saved/ids", response_model=SavedIdsResponse)
async def list_saved_ids(user: dict = Depends(get_current_user)):
    """Returns saved IDs only. The app calls this on launch to render hearts."""
    try:
        ids = await run_in_threadpool(db.list_saved_item_ids, user["uid"])
    except Exception as exc:
        logger.error("Failed to list saved ids for uid=%s: %s", user["uid"], exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Saved items are temporarily unavailable.",
        )
    return SavedIdsResponse(ids=ids)


# ---------------------------------------------------------------------------
# PUT /saved/{item_id}
# ---------------------------------------------------------------------------

@router.put("/saved/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def save(item_id: str, user: dict = Depends(get_current_user)):
    """Saves an item for the caller. Safe to call repeatedly."""
    item_id = _validate_item_id(item_id)
    try:
        await run_in_threadpool(db.save_item, user["uid"], item_id)
    except Exception as exc:
        logger.error("Failed to save item %s for uid=%s: %s", item_id, user["uid"], exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not save this item right now.",
        )


# ---------------------------------------------------------------------------
# DELETE /saved/{item_id}
# ---------------------------------------------------------------------------

@router.delete("/saved/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsave(item_id: str, user: dict = Depends(get_current_user)):
    """Removes an item from the caller's saved list. Safe to call repeatedly."""
    item_id = _validate_item_id(item_id)
    try:
        await run_in_threadpool(db.unsave_item, user["uid"], item_id)
    except Exception as exc:
        logger.error("Failed to unsave item %s for uid=%s: %s", item_id, user["uid"], exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not remove this item right now.",
        )
