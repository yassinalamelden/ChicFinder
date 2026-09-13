"""
chic_finder/db.py
==================
Shared Postgres (RDS) connection pool + query helpers.

Used by:
  - api/routes/search.py (per-request item metadata enrichment)
  - scripts/seed_catalog.py (catalog loading/replacement)
  - ai_engine/embeddings/remote_database_builder.py (index building from RDS)
"""

from __future__ import annotations

import json
import os

import boto3
import psycopg2.pool

_pool = None

ITEM_COLUMNS = (
    "id, category, sub_category, color, style, brand, price, "
    "product_url, availability, image_key, store_id, title, product_id"
)


def connection_kwargs_from_env() -> dict:
    """Resolves Postgres connection kwargs from DB_SECRET_ARN (Secrets Manager,
    used in AWS) or discrete DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD env
    vars (used for local development)."""
    secret_arn = os.getenv("DB_SECRET_ARN")
    if secret_arn:
        secretsmanager = boto3.client("secretsmanager")
        secret = json.loads(
            secretsmanager.get_secret_value(SecretId=secret_arn)["SecretString"]
        )
        return dict(
            host=secret["host"],
            port=secret["port"],
            dbname=secret.get("dbname", "chicfinder"),
            user=secret["username"],
            password=secret["password"],
        )
    return dict(
        host=os.environ["DB_HOST"],
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "chicfinder"),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


def init_pool(minconn: int = 2, maxconn: int = 20) -> None:
    """Creates the module-level connection pool. Call once at app startup.

    Uses ThreadedConnectionPool (not SimpleConnectionPool) because
    get_items_by_ids() is invoked via run_in_threadpool from api/routes/search.py
    — i.e. from real concurrent OS threads. SimpleConnectionPool's getconn/putconn
    aren't guarded by a lock and aren't safe to share across threads.
    """
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(minconn, maxconn, **connection_kwargs_from_env())


def get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    if _pool is None:
        raise RuntimeError(
            "DB pool not initialized — call init_pool() first (see api/main.py's lifespan)."
        )
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


def get_items_by_ids(ids: list[str]) -> dict[str, dict]:
    """Fetches item records for exactly the given IDs — used to enrich FAISS
    search results without loading the full catalog into memory."""
    if not ids:
        return {}

    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT {ITEM_COLUMNS} FROM items WHERE id = ANY(%s);", (ids,))
            columns = [desc[0] for desc in cursor.description]
            return {row[0]: dict(zip(columns, row)) for row in cursor.fetchall()}
    finally:
        conn.rollback()
        pool.putconn(conn)


# Searched in this order, which is also the ranking: a query matching an
# item's own title should outrank one that only matches its brand.
SEARCH_FIELDS = ("title", "sub_category", "category", "color", "brand")


def search_catalog(
    query: str = "",
    category: str = "",
    store_id: str = "",
    limit: int = 60,
) -> list[dict]:
    """Text search across the whole catalog.

    Ranked and paged in SQL rather than in Python. The mobile app's text
    search and its cross-store item search both run through here, and pulling
    the full `items` table into the API process on every keystroke would not
    survive a real catalog.

    Postgres ILIKE is used rather than full-text search: the catalog's
    searchable columns are short labels, not prose, so a substring match is
    both what users expect ("den" finding "Denim") and cheaper to reason about
    than a tsvector with no dictionary tuned for brand names.
    """
    pattern = f"%{query.strip()}%" if query.strip() else None

    where = []
    params: list = []

    if pattern is not None:
        where.append(
            "(" + " OR ".join(f"{field} ILIKE %s" for field in SEARCH_FIELDS) + ")"
        )
        params.extend([pattern] * len(SEARCH_FIELDS))

    if category:
        where.append("LOWER(category) = LOWER(%s)")
        params.append(category)

    if store_id:
        where.append("store_id = %s")
        params.append(store_id)

    clause = f"WHERE {' AND '.join(where)}" if where else ""

    if pattern is not None:
        # CASE arms in SEARCH_FIELDS order, so a title hit sorts before a brand
        # hit. `id` breaks ties so an unchanged catalog gives an unchanged order.
        arms = " ".join(
            f"WHEN {field} ILIKE %s THEN {position}"
            for position, field in enumerate(SEARCH_FIELDS)
        )
        order = f"ORDER BY CASE {arms} ELSE {len(SEARCH_FIELDS)} END, id"
        params.extend([pattern] * len(SEARCH_FIELDS))
    else:
        order = "ORDER BY id"

    params.append(limit)

    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT {ITEM_COLUMNS} FROM items {clause} {order} LIMIT %s;",
                tuple(params),
            )
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.rollback()
        pool.putconn(conn)


# ---------------------------------------------------------------------------
# Saved items (wishlist)
#
# Backs the mobile app's save/unsave feature. Schema lives in
# scripts/migrations/001_saved_items.sql. Every function here is keyed by the
# Firebase uid, so a user can only ever touch their own rows.
# ---------------------------------------------------------------------------


def _run(query: str, params: tuple, *, fetch: bool = False, commit: bool = False):
    """Runs one statement on a pooled connection, always returning it cleanly."""
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall() if fetch else None
            columns = [d[0] for d in cursor.description] if fetch else None
        if commit:
            conn.commit()
        else:
            conn.rollback()
        if fetch:
            return [dict(zip(columns, row)) for row in rows]
        return None
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def list_saved_item_ids(uid: str) -> list[str]:
    """Returns the user's saved item IDs, most recently saved first."""
    rows = _run(
        "SELECT item_id FROM saved_items WHERE uid = %s ORDER BY created_at DESC;",
        (uid,),
        fetch=True,
    )
    return [row["item_id"] for row in rows]


def save_item(uid: str, item_id: str) -> None:
    """Saves an item. Idempotent, so re-saving is not an error."""
    _run(
        "INSERT INTO saved_items (uid, item_id) VALUES (%s, %s) "
        "ON CONFLICT (uid, item_id) DO NOTHING;",
        (uid, item_id),
        commit=True,
    )


def unsave_item(uid: str, item_id: str) -> None:
    """Removes an item from the user's saved list. Idempotent."""
    _run(
        "DELETE FROM saved_items WHERE uid = %s AND item_id = %s;",
        (uid, item_id),
        commit=True,
    )


def delete_all_user_data(uid: str) -> int:
    """Deletes every row this service holds for a user, returning the row count.

    Called by the account-deletion endpoint. Keep this function in sync with any
    future table that stores a uid, since App Store Guideline 5.1.1(v) requires
    in-app deletion to remove the account's data, not just the login.
    """
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM saved_items WHERE uid = %s;", (uid,))
            deleted = cursor.rowcount
        conn.commit()
        return deleted
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)
