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


def get_stores() -> list[dict]:
    """Derives the store list from the catalog itself.

    There is no `stores` table — RDS only has `items`, which carries a
    `store_id` and a `brand` (see scripts/seed_catalog.py). So a store is
    whatever distinct store_id appears in the catalog, named by its brand,
    with the set of categories it actually stocks. Richer store metadata
    (logo, description, location, website) has no source of truth yet and
    comes back as None — the Store schema marks those Optional, so they can
    be filled in later by adding a real stores table without changing the
    API contract.
    """
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT store_id,
                       MIN(brand) AS name,
                       ARRAY_AGG(DISTINCT category) FILTER (WHERE category IS NOT NULL) AS categories
                FROM items
                WHERE store_id IS NOT NULL
                GROUP BY store_id
                ORDER BY store_id;
                """
            )
            return [
                {"id": row[0], "name": row[1] or row[0], "categories": row[2] or []}
                for row in cursor.fetchall()
            ]
    finally:
        conn.rollback()
        pool.putconn(conn)


def get_items_by_store(store_id: str) -> list[dict]:
    """Fetches every catalog item belonging to one store."""
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT {ITEM_COLUMNS} FROM items WHERE store_id = %s ORDER BY id;",
                (store_id,),
            )
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.rollback()
        pool.putconn(conn)


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
