# Backend AWS Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the deployed AWS infrastructure (from the AWS Infrastructure and Data Layer plan) actually power the live API — the index builder reads the catalog from RDS/S3 instead of local files, and `/search`'s metadata enrichment queries RDS per-request instead of a local-JSON cache loaded once at startup.

**Architecture:** A new shared `chic_finder/db.py` module (a Postgres connection pool + query helpers) is the single place both the index builder and the API talk to RDS from. `ai_engine/embeddings/remote_database_builder.py` is a new S3/RDS-sourced counterpart to the existing local-file-based `FAISSIndexBuilder`, chosen automatically by `scripts/02_build_faiss_index.py` based on whether `S3_BUCKET_NAME` is set — so the existing local dev workflow (no AWS required) keeps working unchanged.

**Tech Stack:** `psycopg2` (connection pooling), `boto3` (S3), `pytest` + `moto` (mocking AWS in tests), GitHub Actions + CDK for deployment.

**Spec:** `docs/superpowers/specs/2026-08-22-aws-backend-migration-design.md`

## Global Constraints

- The existing local-file dev workflow (`FAISSIndexBuilder`, local `data/raw_images/`/`data/metadata.json`) must keep working unchanged for anyone without AWS access configured — nothing in this plan removes that path.
- `FAISSVectorStore`/`vector_store.py` requires **no changes** — the remote index builder produces the exact same output format (`embeddings.index` + a plain id→filename-string `index_to_image_id.json` mapping) as the existing local builder, because `seed_catalog.py`'s S3 keys already follow the same `{item_id}.jpg` naming convention as local files.
- `/recommend`'s FAISS-fallback path (`api/routes/recommend.py`) is unaffected by this plan — it doesn't read `app.state.metadata` today and isn't touched here; only `/search`'s enrichment source changes.
- DB pool initialization at API startup must be non-fatal on failure (matching the existing FAISS-prewarm pattern in `main.py`) — a machine without `DB_*`/`DB_SECRET_ARN` configured should still boot and serve `/health`/`/stores`; only `/search` degrades.

---

### Task 1: Shared DB connection module

**Files:**
- Create: `chic_finder/db.py`
- Modify: `scripts/seed_catalog.py`
- Test: `tests/chic_finder/test_db.py`

**Interfaces:**
- Produces: `connection_kwargs_from_env() -> dict` — resolves Postgres connection kwargs from `DB_SECRET_ARN` (AWS) or discrete `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASSWORD` env vars (local dev).
- Produces: `init_pool(minconn=1, maxconn=10) -> None`, `get_pool() -> psycopg2.pool.SimpleConnectionPool`, `close_pool() -> None`.
- Produces: `get_items_by_ids(ids: list[str]) -> dict[str, dict]` — the per-request enrichment query, keyed by item id.

- [ ] **Step 1: Write the failing test**

Create `tests/chic_finder/test_db.py`:

```python
from unittest.mock import MagicMock, patch

from chic_finder.db import get_items_by_ids


def test_get_items_by_ids_returns_dict_keyed_by_id():
    fake_cursor = MagicMock()
    fake_cursor.description = [("id",), ("brand",), ("price",)]
    fake_cursor.fetchall.return_value = [("item1", "Tomato", 350.0)]
    fake_conn = MagicMock()
    fake_conn.cursor.return_value.__enter__.return_value = fake_cursor
    fake_pool = MagicMock()
    fake_pool.getconn.return_value = fake_conn

    with patch("chic_finder.db.get_pool", return_value=fake_pool):
        result = get_items_by_ids(["item1"])

    assert result == {"item1": {"id": "item1", "brand": "Tomato", "price": 350.0}}
    fake_pool.putconn.assert_called_once_with(fake_conn)


def test_get_items_by_ids_returns_empty_dict_without_querying_for_empty_input():
    assert get_items_by_ids([]) == {}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/chic_finder/test_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'chic_finder.db'`

- [ ] **Step 3: Implement `chic_finder/db.py`**

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/chic_finder/test_db.py -v`
Expected: 2 passed.

- [ ] **Step 5: Refactor `scripts/seed_catalog.py` to reuse the shared connection helper**

In `scripts/seed_catalog.py`, replace the existing `_connect_from_env()` function body with a call to the new shared helper (remove the duplicated Secrets-Manager-vs-env-vars branching logic):

```python
from chic_finder.db import connection_kwargs_from_env


def _connect_from_env():
    """Builds a psycopg2 connection using the shared connection-kwargs resolver."""
    return psycopg2.connect(**connection_kwargs_from_env())
```

(This replaces the entire previous `_connect_from_env()` body from the AWS Infrastructure and Data Layer plan's Task 8 — the function name and its callers in `main()` don't change, only its internals.)

- [ ] **Step 6: Run the full seed_catalog test suite to confirm the refactor didn't break anything**

Run: `pytest tests/scripts/test_seed_catalog.py -v`
Expected: 2 passed (unchanged from before the refactor).

- [ ] **Step 7: Commit**

```bash
git add chic_finder/db.py tests/chic_finder/test_db.py scripts/seed_catalog.py
git commit -m "feat: add shared RDS connection pool module, refactor seed_catalog to use it"
```

---

### Task 2: Remote (S3/RDS) FAISS index builder

**Files:**
- Create: `ai_engine/embeddings/remote_database_builder.py`
- Modify: `scripts/02_build_faiss_index.py`
- Test: `tests/ai_engine/embeddings/test_remote_database_builder.py`

**Interfaces:**
- Consumes: `chic_finder.db.get_pool()`, `ai_engine.embeddings.encoder.get_encoder()` (existing).
- Produces: `RemoteIndexBuilder(bucket_name, index_path=..., mapping_path=...).build() -> None` — same output contract as the existing `FAISSIndexBuilder.build()`: writes a FAISS `IndexFlatIP` to `index_path` and a `{faiss_id: image_filename}` JSON mapping to `mapping_path`.

- [ ] **Step 1: Write the failing test**

Create `tests/ai_engine/embeddings/test_remote_database_builder.py`:

```python
import json
from unittest.mock import MagicMock, patch

import boto3
import numpy as np
from moto import mock_aws

from ai_engine.embeddings.remote_database_builder import RemoteIndexBuilder


@mock_aws
def test_build_indexes_items_from_s3_and_rds(tmp_path):
    bucket_name = "test-chicfinder-catalog"
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=bucket_name)
    s3.put_object(Bucket=bucket_name, Key="item1.jpg", Body=b"fake-image-bytes")

    fake_cursor = MagicMock()
    fake_cursor.fetchall.return_value = [("item1", "item1.jpg")]
    fake_conn = MagicMock()
    fake_conn.cursor.return_value.__enter__.return_value = fake_cursor
    fake_pool = MagicMock()
    fake_pool.getconn.return_value = fake_conn

    index_path = tmp_path / "embeddings.index"
    mapping_path = tmp_path / "index_to_image_id.json"

    with patch(
        "ai_engine.embeddings.remote_database_builder.get_pool", return_value=fake_pool
    ), patch(
        "ai_engine.embeddings.remote_database_builder.get_encoder"
    ) as mock_get_encoder:
        mock_get_encoder.return_value.encode.return_value = np.ones(512, dtype=np.float32)

        builder = RemoteIndexBuilder(
            bucket_name=bucket_name, index_path=index_path, mapping_path=mapping_path
        )
        builder.build()

    assert index_path.exists()
    mapping = json.loads(mapping_path.read_text())
    assert mapping == {"0": "item1.jpg"}


@mock_aws
def test_build_raises_when_no_items_in_rds(tmp_path):
    bucket_name = "test-chicfinder-catalog"
    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=bucket_name)

    fake_cursor = MagicMock()
    fake_cursor.fetchall.return_value = []
    fake_conn = MagicMock()
    fake_conn.cursor.return_value.__enter__.return_value = fake_cursor
    fake_pool = MagicMock()
    fake_pool.getconn.return_value = fake_conn

    with patch(
        "ai_engine.embeddings.remote_database_builder.get_pool", return_value=fake_pool
    ), patch("ai_engine.embeddings.remote_database_builder.get_encoder"):
        builder = RemoteIndexBuilder(
            bucket_name=bucket_name,
            index_path=tmp_path / "embeddings.index",
            mapping_path=tmp_path / "index_to_image_id.json",
        )
        try:
            builder.build()
            assert False, "expected ValueError"
        except ValueError as exc:
            assert "items" in str(exc)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/ai_engine/embeddings/test_remote_database_builder.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ai_engine.embeddings.remote_database_builder'`

- [ ] **Step 3: Implement `RemoteIndexBuilder`**

Create `ai_engine/embeddings/remote_database_builder.py`:

```python
"""
ai_engine/embeddings/remote_database_builder.py
=================================================
Production counterpart to database_builder.py's FAISSIndexBuilder: builds the
FAISS index from the RDS `items` table + S3 catalog images, instead of local
data/raw_images/ + data/metadata.json.

Output format (embeddings.index + index_to_image_id.json) is identical to
the local builder's, so vector_store.py needs no changes — S3 keys and local
filenames both follow the `{item_id}.jpg` convention.

Used automatically by scripts/02_build_faiss_index.py when S3_BUCKET_NAME is set.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import boto3
import numpy as np
from tqdm import tqdm

from ai_engine.embeddings.encoder import EMBEDDING_DIM, get_encoder
from chic_finder.db import get_pool

logger = logging.getLogger(__name__)

DEFAULT_INDEX_PATH = Path("data/embeddings.index")
DEFAULT_MAPPING_PATH = Path("data/index_to_image_id.json")


class RemoteIndexBuilder:
    """Builds a FAISS IndexFlatIP from the RDS `items` table + S3 images."""

    def __init__(
        self,
        bucket_name: str,
        index_path: Path = DEFAULT_INDEX_PATH,
        mapping_path: Path = DEFAULT_MAPPING_PATH,
    ) -> None:
        self.bucket_name = bucket_name
        self.index_path = Path(index_path)
        self.mapping_path = Path(mapping_path)
        self._encoder = get_encoder()
        self._s3 = boto3.client("s3")

    def build(self) -> None:
        import faiss

        items = self._load_items()
        if not items:
            raise ValueError(
                "No items found in the `items` table. Run scripts/seed_catalog.py first."
            )

        logger.info("Building FAISS index for %d candidate items from S3/RDS...", len(items))

        index = faiss.IndexFlatIP(EMBEDDING_DIM)
        mapping: dict[str, str] = {}

        for item_id, image_key in tqdm(items, desc="Indexing items", unit="item"):
            if not image_key:
                logger.warning("Skipping %s: no image_key in RDS.", item_id)
                continue
            try:
                vector = self._embed_s3_image(image_key)
                faiss_id = str(index.ntotal)
                index.add(np.expand_dims(vector, axis=0))
                mapping[faiss_id] = image_key
            except Exception as exc:
                logger.warning("Skipping %s: %s", item_id, exc)

        if index.ntotal == 0:
            raise ValueError("No valid items were indexed. Check S3 image availability.")

        self._save(index, mapping)
        logger.info("Index built successfully: %d vectors", index.ntotal)

    def _load_items(self) -> list[tuple[str, str]]:
        """Returns [(id, image_key), ...] for every item in RDS."""
        pool = get_pool()
        conn = pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, image_key FROM items WHERE image_key IS NOT NULL;")
                return cursor.fetchall()
        finally:
            pool.putconn(conn)

    def _embed_s3_image(self, image_key: str) -> np.ndarray:
        obj = self._s3.get_object(Bucket=self.bucket_name, Key=image_key)
        image_bytes = obj["Body"].read()
        return self._encoder.encode(image_bytes)

    def _save(self, index, mapping: dict[str, str]) -> None:
        import faiss

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.mapping_path.parent.mkdir(parents=True, exist_ok=True)

        faiss.write_index(index, str(self.index_path))
        with open(self.mapping_path, "w", encoding="utf-8") as file_obj:
            json.dump(mapping, file_obj, indent=2)

        logger.info("Saved index   -> %s", self.index_path)
        logger.info("Saved mapping -> %s", self.mapping_path)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/ai_engine/embeddings/test_remote_database_builder.py -v`
Expected: 2 passed.

- [ ] **Step 5: Wire into `scripts/02_build_faiss_index.py`**

Add to the imports:

```python
import os

from ai_engine.embeddings.remote_database_builder import RemoteIndexBuilder
```

Replace the body of `main()` (everything from `args = parser.parse_args()` to the final `logger.info("Done. Offline FAISS artifacts are ready.")`) with:

```python
    args = parser.parse_args()

    bucket_name = os.getenv("S3_BUCKET_NAME")
    if bucket_name:
        logger.info("S3_BUCKET_NAME is set — building from S3 + RDS...")
        from chic_finder.db import init_pool

        init_pool()
        builder = RemoteIndexBuilder(
            bucket_name=bucket_name,
            index_path=Path(args.index),
            mapping_path=Path(args.mapping),
        )
        builder.build()
    else:
        images_dir = Path(args.images)
        images_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Initializing local FAISS index builder...")
        builder = FAISSIndexBuilder(
            index_path=Path(args.index),
            mapping_path=Path(args.mapping),
            metadata_source_path=Path(args.metadata),
        )
        builder.build(images_dir=images_dir)

    logger.info("Done. Offline FAISS artifacts are ready.")
```

- [ ] **Step 6: Manual smoke test of the local path (regression check)**

Run: `python scripts/02_build_faiss_index.py`
Expected: same output as always — builds from `data/raw_images/`, since `S3_BUCKET_NAME` isn't set locally. Confirms the local dev workflow is unaffected.

- [ ] **Step 7: Commit**

```bash
git add ai_engine/embeddings/remote_database_builder.py tests/ai_engine/embeddings/test_remote_database_builder.py scripts/02_build_faiss_index.py
git commit -m "feat: build FAISS index from S3+RDS when deployed, local files otherwise"
```

---

### Task 3: Switch `/search` metadata enrichment from local-JSON cache to per-request RDS query

**Files:**
- Modify: `api/routes/search.py`
- Modify: `api/main.py`
- Test: `tests/api/routes/test_search.py`

**Interfaces:**
- Consumes: `chic_finder.db.get_items_by_ids(ids: list[str]) -> dict[str, dict]` (Task 1), `chic_finder.db.init_pool()` / `close_pool()` (Task 1).

- [ ] **Step 1: Write the failing test**

Create `tests/api/routes/test_search.py`:

```python
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_search_enriches_results_from_rds_not_app_state():
    fake_search_results = [{"id": "item1.jpg", "score": 0.92}]
    fake_metadata = {
        "item1": {
            "brand": "Tomato",
            "price": 350.0,
            "product_url": "https://tomato.example.com/item1",
        }
    }

    with patch(
        "api.routes.search.search_similar_items", return_value=fake_search_results
    ), patch(
        "api.routes.search.get_items_by_ids", return_value=fake_metadata
    ) as mock_get_items:
        response = client.post(
            "/api/v1/search",
            json={"image_base64": "aGVsbG8="},  # "hello" base64, decoding is mocked away
        )

    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["image_id"] == "item1"
    assert body["results"][0]["brand"] == "Tomato"
    assert body["results"][0]["price_egp"] == 350.0
    mock_get_items.assert_called_once_with(["item1"])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/api/routes/test_search.py -v`
Expected: FAIL — `AttributeError` or import error, since `get_items_by_ids` isn't imported/used in `search.py` yet, and `app.state.metadata` (empty, since nothing populates it in this test) means `metadata[clean_id]` lookups miss and brand/price come back `None`.

- [ ] **Step 3: Update `api/routes/search.py`**

Add to the imports:

```python
from chic_finder.db import get_items_by_ids
```

Remove this line from `search_endpoint`:

```python
    metadata = getattr(fastapi_req.app.state, "metadata", {})
```

In the `try` block, immediately after `search_results = await run_in_threadpool(search_similar_items, image_bytes, top_k=50)`, add:

```python
        candidate_ids = [str(item.get("id", "")).replace(".jpg", "") for item in search_results]
        metadata = await run_in_threadpool(get_items_by_ids, candidate_ids)
```

Everything below this (the `response_items = []` loop and onward) is unchanged — it already reads from a local variable named `metadata`, which now comes from RDS instead of `app.state`.

- [ ] **Step 4: Update `api/main.py`'s lifespan**

Remove the entire "Load data/metadata.json (used by /search route)" block (the `app.state.metadata = {}` line through the `else: logger.warning(...)` for it).

Add, right after the "Ensure uploads dir exists" block and before the FAISS pre-warm comment block:

```python
    # Initialize the RDS connection pool (item metadata enrichment for /search).
    # Non-fatal: a machine without DB_* / DB_SECRET_ARN configured still boots;
    # only /search's enrichment will fail until it's set.
    try:
        from chic_finder.db import init_pool

        init_pool()
        logger.info("RDS connection pool initialized.")
    except Exception as exc:
        logger.warning(
            "RDS connection pool not initialized — /search enrichment will fail "
            "until DB_* env vars or DB_SECRET_ARN are set. %s", exc
        )
```

Add, right after the `yield` line (so it runs on shutdown):

```python
    from chic_finder.db import close_pool

    close_pool()
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `pytest tests/api/routes/test_search.py -v`
Expected: PASS.

- [ ] **Step 6: Run the full test suite to check for regressions**

Run: `pytest tests/ -v`
Expected: all tests pass (this plan's new tests plus Task 1/2's).

- [ ] **Step 7: Commit**

```bash
git add api/routes/search.py api/main.py tests/api/routes/test_search.py
git commit -m "feat: enrich /search results from RDS per-request instead of a local-JSON cache"
```

---

### Task 4: CI/CD — deploy on push

**Files:**
- Create: `.github/workflows/deploy-api.yml`

**One manual, one-time prerequisite before this task's first real run:** create an IAM role trusted for GitHub Actions OIDC (so the workflow authenticates without long-lived AWS access keys), then add its ARN as a repository secret named `AWS_DEPLOY_ROLE_ARN`. This is an AWS Console/CLI step, not something committed to the repo — follow AWS's standard "GitHub Actions OIDC" setup guide for the exact trust policy.

- [ ] **Step 1: Create the workflow**

There is no existing `.github/workflows/` directory on this branch (a stale assumption in the spec — verified directly, corrected). Create `.github/workflows/deploy-api.yml`:

```yaml
name: Deploy API

on:
  push:
    branches: [main]
    paths:
      - 'api/**'
      - 'ai_engine/**'
      - 'chic_finder/**'
      - 'shared/**'
      - 'scripts/**'
      - 'requirements.txt'
      - 'requirements.lock'
      - 'infrastructure/docker/Dockerfile.api'
      - 'infrastructure/cdk/**'
      - '.github/workflows/deploy-api.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: us-east-1

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install CDK app dependencies
        working-directory: infrastructure/cdk
        run: pip install -r requirements.txt

      - name: Install AWS CDK CLI
        run: npm install -g aws-cdk

      - name: Deploy
        working-directory: infrastructure/cdk
        run: cdk deploy --require-approval never
```

`cdk deploy` handles the whole deployment lifecycle here — it rebuilds the API Docker image asset (since the code changed), pushes it to CDK's managed ECR repo, and rolls the ECS service, all in one step. This deliberately does not duplicate that logic with a separate hand-rolled `docker build && aws ecs update-service` pipeline — the CDK stack from the AWS Infrastructure and Data Layer plan is the single source of truth for how this app gets deployed, in CI exactly as it is when run by hand.

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/deploy-api.yml
git commit -m "ci: deploy the API stack on push via CDK"
```

- [ ] **Step 3: Verify on the next push to `main`**

Once merged, push a small no-op change (or merge this branch) and confirm in the GitHub Actions tab that the workflow runs and completes successfully, then confirm `curl http://<LoadBalancerDNS>/api/v1/health` still responds after the deploy.

## Self-Review Notes

- **Spec coverage:** index builder reading from RDS/S3 (Task 2), per-request metadata enrichment (Task 3), CI/CD (Task 4) — every remaining "Components" bullet from the spec not covered by the AWS Infrastructure and Data Layer plan is covered here.
- **Type consistency:** `get_items_by_ids`'s signature (Task 1) matches its call site in `search.py` (Task 3) and its test mock (both tasks). `RemoteIndexBuilder`'s constructor args match how `scripts/02_build_faiss_index.py` calls it.
- **No placeholders:** every step has complete, runnable code, including the CI workflow YAML in full.
- **Regression safety:** Task 2 Step 6 and Task 1 Step 6 are explicit manual/automated checks that the existing local-file dev workflow still works unchanged after these changes — this plan adds a new path, it doesn't replace the old one.
