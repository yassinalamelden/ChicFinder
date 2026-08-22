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
import psycopg2
import psycopg2.pool

_pool = None

ITEM_COLUMNS = (
    "id, category, sub_category, color, style, brand, price, "
    "product_url, availability, image_key, store_id"
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


def init_pool(minconn: int = 1, maxconn: int = 10) -> None:
    """Creates the module-level connection pool. Call once at app startup."""
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.SimpleConnectionPool(minconn, maxconn, **connection_kwargs_from_env())


def get_pool():
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
        pool.putconn(conn)
