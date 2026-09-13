"""
api/routes/items.py
====================
Routes:
  GET /api/v1/items             → text search across every store
  GET /api/v1/items/{item_id}   → one item, for the app's detail screen

Why these are not in stores.py
------------------------------
They were, briefly. stores.py is being rewritten to read RDS as part of the
AWS migration, and keeping these here means the mobile app's endpoints do not
collide with that work in the same file.

Why RDS first, with a fallback
------------------------------
Production has no products.json: it stopped being tracked in git (bea05a5), so
it is absent from the Docker image, and anything reading `app.state.products`
there silently serves an empty catalog. That is exactly the bug that made
/stores return `200 []` in production while looking healthy.

So these routes query RDS, and fall back to the in-memory catalog only when no
connection pool exists, which is the local-development case. The fallback is
deliberately narrow: a pool that exists but fails is an error worth seeing, not
something to paper over with a stale local file.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from starlette.concurrency import run_in_threadpool

from api.models.schemas import StoreItem
from chic_finder import db

logger = logging.getLogger(__name__)

router = APIRouter()


def _has_pool() -> bool:
    try:
        db.get_pool()
        return True
    except RuntimeError:
        return False


def _row_to_item(row: dict) -> StoreItem:
    """Maps an RDS `items` row onto the response shape.

    `sizes` and `description` have no column in the catalog schema, so they
    come back empty rather than invented. The app already treats both as
    optional and hides those sections when they are absent.
    """
    price = row.get("price")
    image_key = row.get("image_key")

    # Imported lazily: the helper lives in the AWS-facing shared package, and a
    # local checkout without it should still be able to serve the fallback path.
    image_url: Optional[str] = None
    if image_key:
        try:
            from shared.utils.s3_urls import public_image_url

            image_url = public_image_url(image_key)
        except Exception:
            image_url = image_key

    return StoreItem(
        id=str(row.get("id", "")),
        name=row.get("title") or "",
        brand=row.get("brand"),
        category=row.get("category"),
        type=row.get("sub_category"),
        color=row.get("color"),
        price_egp=float(price) if price is not None else 0.0,
        sizes=[],
        image_url=image_url,
        product_url=row.get("product_url"),
        description=None,
        store_id=str(row.get("store_id") or ""),
        store_location=None,
    )


def _product_to_item(product: dict) -> StoreItem:
    """Maps a local products.json entry onto the same shape."""
    return StoreItem(
        id=product.get("id", ""),
        name=product.get("name", ""),
        brand=product.get("brand", ""),
        category=product.get("category", ""),
        type=product.get("type", ""),
        color=product.get("color", ""),
        price_egp=float(product.get("price_egp", 0)),
        sizes=product.get("sizes", []),
        image_url=product.get("image_url"),
        product_url=product.get("product_url"),
        description=product.get("description"),
        store_id=product.get("store_id", ""),
        store_location=product.get("store_location"),
    )


# Ranking for the fallback path, mirroring the SQL CASE in db.search_catalog so
# local results are ordered the same way production orders them.
_FALLBACK_FIELDS = ("name", "type", "category", "color", "brand")


def _rank(product: dict, query: str) -> int:
    for position, field in enumerate(_FALLBACK_FIELDS):
        if query in str(product.get(field) or "").lower():
            return position
    return len(_FALLBACK_FIELDS)


def _search_local(
    request: Request, search: str, category: str, store_id: str, limit: int
) -> list[StoreItem]:
    products = getattr(request.app.state, "products", [])

    if store_id:
        products = [p for p in products if p.get("store_id") == store_id]
    if category:
        products = [
            p for p in products if (p.get("category") or "").lower() == category.lower()
        ]

    if search:
        q = search.strip().lower()
        ranked = [(_rank(p, q), p) for p in products]
        matches = [(rank, p) for rank, p in ranked if rank < len(_FALLBACK_FIELDS)]
        matches.sort(key=lambda pair: pair[0])
        products = [p for _, p in matches]

    return [_product_to_item(p) for p in products[:limit]]


# ---------------------------------------------------------------------------
# GET /items
# ---------------------------------------------------------------------------

@router.get("/items", response_model=list[StoreItem])
async def search_items(
    request: Request,
    search: str = Query(default="", description="Text search across every store"),
    category: str = Query(default="", description="Filter by category"),
    store_id: str = Query(default="", description="Restrict to one store"),
    limit: int = Query(default=60, ge=1, le=200),
):
    """
    Text search over the whole catalog.

    The per-store endpoint only reaches one brand, so the app had no way to
    answer "who sells a linen shirt". Public, like the rest of /stores*: a
    guest browsing the catalog is the top of the funnel, not a privilege.
    """
    if _has_pool():
        rows = await run_in_threadpool(
            db.search_catalog, search, category, store_id, limit
        )
        return [_row_to_item(row) for row in rows]

    return _search_local(request, search, category, store_id, limit)


# ---------------------------------------------------------------------------
# GET /items/{item_id}
# ---------------------------------------------------------------------------

@router.get("/items/{item_id}", response_model=StoreItem)
async def get_item(item_id: str, request: Request):
    """
    One item, for the in-app detail screen.

    Registered after `/items` so the literal path wins: Starlette matches in
    order, and a bare `/items` would otherwise be swallowed here with an empty
    item_id.
    """
    if _has_pool():
        rows = await run_in_threadpool(db.get_items_by_ids, [item_id])
        row = rows.get(item_id)
        if row is not None:
            return _row_to_item(row)
        raise HTTPException(status_code=404, detail=f"Item '{item_id}' not found.")

    lookup = getattr(request.app.state, "products_lookup", None)
    product = lookup.get(item_id) if lookup else None
    if product is None:
        products = getattr(request.app.state, "products", [])
        product = next((p for p in products if p.get("id") == item_id), None)

    if product is None:
        raise HTTPException(status_code=404, detail=f"Item '{item_id}' not found.")

    return _product_to_item(product)
