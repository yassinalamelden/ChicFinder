# Nour Atef — ChicFinder Contributions

**Project:** ChicFinder — Egyptian Fashion Recommendation Engine  
**Live URL:** https://chicfinder.framer.website  
**Backend:** https://chicfinder-production.up.railway.app  
**Role:** Full-Stack Engineer (Backend, Database, Infrastructure, Frontend)  
**Stack:** FastAPI · Supabase · pgvector · Firebase Auth · Docker · Railway · Framer · React · TypeScript

---

## Project Overview

ChicFinder is an AI-powered fashion recommendation engine for the Egyptian market. Users upload a photo of an outfit and the system returns visually similar products from Egyptian fashion brands. The engine uses FashionCLIP (a fine-tuned CLIP model) to encode images into 512-dimensional vectors, stores them in Supabase's pgvector extension, and performs approximate cosine similarity search to surface the top 5 matching products.

The project was built collaboratively: teammates handled the AI model training pipeline and data scraping/ingestion. My responsibility was everything else — designing the system architecture, building the full backend API, designing the database schema, deploying to production, and building the entire Framer frontend from scratch.

---

## My Role in the Team

| Area | Owner |
|------|-------|
| FastAPI backend system (all routes) | **Nour** |
| Database design (Supabase + pgvector) | **Nour** |
| Containerization (Docker) | **Nour** |
| Railway deployment & configuration | **Nour** |
| Framer frontend (all pages + components) | **Nour** |
| AI pipeline integration (CLIP → backend) | **Nour** |
| FashionCLIP model training & fine-tuning | Teammates |
| Product data scraping & ingestion | Teammates |

---

## 1. Backend System (FastAPI)

### Architecture Decisions

I designed the backend as a production-grade FastAPI application with clear separation of concerns: routes handle HTTP I/O, AI engine modules handle inference, and a singleton Supabase client manages database access. The app uses FastAPI's `lifespan` context manager to warm up the CLIP encoder at startup — a deliberate choice to prevent the first recommendation request from triggering a cold model load that would spike memory and cause a Railway health-check timeout.

**Entry point:** [api/main.py](api/main.py)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    from ai_engine.embeddings.encoder import get_encoder
    get_encoder()   # warm-up: load CLIP into memory before first request
    logger.info("CLIP encoder warm-up complete")
    yield
```

CORS is configured to accept requests from the Framer frontend domain, with `ALLOWED_ORIGINS` injected as a comma-separated environment variable so it can be overridden per environment without code changes.

### Route-by-Route Breakdown

#### `GET /api/v1/health` — [api/routes/health.py](api/routes/health.py)

Probes Supabase connectivity and reports live product count. Returns `degraded` instead of crashing if the DB is unreachable, so Railway's health check gets a `200` even if there's a transient Supabase hiccup.

```json
{ "status": "ok", "service": "ChicFinder API", "supabase": "connected", "products": 4821 }
```

---

#### `POST /api/v1/recommend` — [api/routes/recommend.py](api/routes/recommend.py)

The core recommendation endpoint. Accepts `.jpg`, `.jpeg`, `.png`, or `.webp` file uploads.

**Pipeline:**
1. Validates file extension before reading bytes
2. Opens the image with Pillow in memory (no disk write) and resizes to max 512×512 (LANCZOS) to bound memory usage
3. Encodes the image with FashionCLIP and L2-normalizes the resulting 512-d vector
4. Queries Supabase pgvector for the top 5 most similar products
5. Constructs Supabase Storage URLs for each result image and returns structured JSON

**Key engineering choice:** Both the CLIP encode and the pgvector RPC call are blocking operations. I moved them off FastAPI's async event loop using `loop.run_in_executor(None, ...)` to prevent them from blocking other concurrent requests:

```python
loop = asyncio.get_event_loop()
encoder = get_encoder()
raw_vector = await loop.run_in_executor(None, encoder._encode, img)
query_vector = encoder._normalize(raw_vector)
results = await loop.run_in_executor(None, partial(search_by_vector, query_vector, top_k=5))
```

I also forced CPU mode (`CUDA_VISIBLE_DEVICES=""`) to prevent VRAM crashes on Railway's CPU-only compute.

---

#### `POST /api/v1/search` — [api/routes/search.py](api/routes/search.py)

An authenticated search endpoint that accepts base64-encoded images with optional filters. Protected by Firebase JWT via the `require_auth` FastAPI dependency.

**Features:**
- Accepts base64 strings with or without data URI prefix (`data:image/jpeg;base64,...`)
- Validates image format (JPEG, PNG, WEBP, GIF) and rejects corrupt data
- Fetches top 50 pgvector candidates, then applies brand and price range filters in Python
- Deduplicates by `product_id` before returning the top 5 results
- Measures and returns `processing_time_ms` for observability

**Deduplication + filter loop:**
```python
for item in search_results:           # 50 candidates
    if len(response_items) >= 5:
        break
    if brands_filter and item_brand not in brands_filter:
        continue
    if price out of range:
        continue
    if product_id not in seen_product_ids:
        seen_product_ids.add(product_id)
        response_items.append(...)     # collect until 5 unique results
```

---

#### `GET /api/v1/stores` and `GET /api/v1/stores/{store_id}` and `GET /api/v1/stores/{store_id}/items` — [api/routes/stores.py](api/routes/stores.py)

Three endpoints that implement the store browsing experience. The data model doesn't have a `stores` table — brands exist only as a field on products — so I built a virtual store abstraction on top of the products table.

**`/stores`** — Fetches up to 5000 product rows (see the PostgREST fix below), groups them by brand with a `seen` set for deduplication, and returns one `StoreResponse` per unique brand with derived `categories` and `total_items`.

**`/stores/{store_id}`** — Resolves the URL slug to a brand name via the `get_brand_by_slug` SQL RPC, then fetches all products for that brand. Images are fetched in a separate batch query on the `embeddings` table (indexed by `product_id`) and joined in Python to avoid a complex SQL join.

**`/stores/{store_id}/items`** — Same brand resolution, but supports `category` and `search` query params mapped to `ilike` filters for case-insensitive pattern matching.

**Brand slug utility:**
```python
def _slug(brand: str) -> str:
    return brand.lower().replace(" ", "-").replace("_", "-")
```

---

#### Supabase Client — [api/db/client.py](api/db/client.py)

Thread-safe singleton using the double-checked locking pattern. The first call acquires the lock and creates the client; subsequent calls skip the lock entirely for zero-overhead access.

```python
def get_supabase_client() -> Client:
    global _client
    if _client is None:          # fast path — no lock
        with _lock:
            if _client is None:  # re-check inside lock
                _client = create_client(url, key)
    return _client
```

---

#### Firebase JWT Authentication — [api/dependencies/auth.py](api/dependencies/auth.py)

A FastAPI `Depends`-compatible async function that verifies Firebase ID tokens on the `/search` endpoint. Implemented with three initialization strategies to support different deployment environments without code changes:

| Strategy | Condition | Use Case |
|----------|-----------|----------|
| Service account JSON | `FIREBASE_SERVICE_ACCOUNT_PATH` exists | Full admin access |
| Project ID only | `FIREBASE_PROJECT_ID` set | Railway production (no file access) |
| Application Default Credentials | GCP environment | Local dev or GCP-hosted |

The `project_id` strategy is the one used in production — it's sufficient for `verify_id_token` because token verification is done against Google's public JWKS endpoint, not the Firebase Admin API, so no service account privileges are needed.

Error handling distinguishes between expired tokens and invalid tokens, returning descriptive 401 messages for each case.

---

## 2. AI Pipeline Integration

My teammates built and fine-tuned the FashionCLIP model (`NourAtef112/chicfinder-clip` on HuggingFace) and the vector store wrapper. My job was to integrate those components into the backend system in a way that's production-safe.

**What I built around the AI model:**

- **Singleton management:** The encoder loads once on startup via `get_encoder()` and is held in module-level state. Every request reuses the same loaded weights — no per-request model load.
- **Startup warm-up:** Wired `get_encoder()` into the FastAPI `lifespan` context so the model is in memory before the health check passes and Railway starts routing traffic.
- **Executor offloading:** Moved `encoder._encode()` and `search_by_vector()` to `run_in_executor` so the async event loop is never blocked during inference or DB round-trips.
- **Model cache in Docker:** The Dockerfile pre-downloads the model from HuggingFace at build time using a `RUN python -c ...` layer. At runtime the model loads from the Docker image layer cache — no network call, no auth needed, no latency spike.

```dockerfile
RUN python -c "\
from transformers import CLIPModel, CLIPProcessor; \
CLIPModel.from_pretrained('NourAtef112/chicfinder-clip'); \
CLIPProcessor.from_pretrained('NourAtef112/chicfinder-clip'); \
print('Fine-tuned ChicFinder model cached OK')"
```

---

## 3. Database Design (Supabase + pgvector)

I designed the full database schema from scratch, including the pgvector index configuration and both SQL RPC functions.

**Migration file:** [supabase/migrations/001_initial_schema.sql](supabase/migrations/001_initial_schema.sql)

### `products` Table

Stores product metadata for all Egyptian fashion brands. `product_id` is a unique external SKU string (from the scraper); `id` is the internal auto-increment PK.

```sql
CREATE TABLE IF NOT EXISTS products (
    id          BIGSERIAL PRIMARY KEY,
    product_id  TEXT UNIQUE NOT NULL,  -- external SKU
    title       TEXT,
    brand       TEXT,
    category    TEXT,
    price       DECIMAL(10,2),
    product_url TEXT,
    description TEXT,
    availability TEXT DEFAULT 'InStock',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_brand    ON products(brand);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
```

### `embeddings` Table

One row per product image. Stores the FashionCLIP 512-d vector alongside a reference to the Supabase Storage filename. The `(product_id, image_filename)` uniqueness constraint prevents duplicate embeddings from re-runs of the ingestion script.

```sql
CREATE TABLE IF NOT EXISTS embeddings (
    id              BIGSERIAL PRIMARY KEY,
    product_id      BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    image_filename  TEXT NOT NULL,        -- Storage key, e.g. "tomato_9215097798909_0"
    embedding       vector(512),
    UNIQUE(product_id, image_filename)
);
```

### pgvector Index (IVFFlat)

Configured for approximate cosine similarity. `lists=100` is appropriate for the current dataset size (~1,000–5,000 vectors) and provides fast approximate search with good recall.

```sql
CREATE INDEX IF NOT EXISTS idx_embeddings_vector
    ON embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

### `match_embeddings` RPC Function

A SQL function called by the Python backend to perform similarity search and join product metadata in one DB round-trip. Uses pgvector's `<=>` cosine distance operator.

```sql
CREATE OR REPLACE FUNCTION match_embeddings(
    query_embedding vector(512),
    match_count int DEFAULT 50
)
RETURNS TABLE (image_filename text, product_id_str text, db_product_id bigint,
               title text, brand text, category text, price decimal, product_url text, similarity float)
LANGUAGE sql STABLE AS $$
    SELECT
        e.image_filename,
        p.product_id   AS product_id_str,
        p.id           AS db_product_id,
        p.title, p.brand, p.category, p.price, p.product_url,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM embeddings e
    JOIN products p ON e.product_id = p.id
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
$$;
```

### `get_brand_by_slug` RPC Function

Resolves a URL slug back to the exact brand name stored in `products.brand`. Written to bypass PostgREST's 1000-row default ceiling — see the bug fix section below.

### Supabase Storage

Set up the `product-images` public bucket and built the URL construction utility in `config.py`:

```python
def get_image_url(self, image_filename: str) -> str:
    stem = image_filename.rsplit(".", 1)[0] if "." in image_filename else image_filename
    return f"{self.SUPABASE_URL}/storage/v1/object/public/product-images/{stem}.jpg"
```

---

## 4. Containerization & Deployment (Railway)

### Docker Setup

**File:** [infrastructure/docker/Dockerfile.api](infrastructure/docker/Dockerfile.api)

I built a Python 3.10-slim image that bakes the fine-tuned FashionCLIP model into the image layer at build time. This was a deliberate optimization: model download at container startup would exceed Railway's health check timeout and cause the deploy to fail.

The build process:
1. Install system dependencies (`build-essential`) and Python packages from `requirements.txt`
2. Pre-download and cache `NourAtef112/chicfinder-clip` via a `RUN python -c ...` layer — this commits the model weights to the image
3. Copy application code
4. Expose port 8000

### Railway Configuration

**File:** [railway.toml](railway.toml)

```toml
[build]
dockerfilePath = "infrastructure/docker/Dockerfile.api"

[deploy]
startCommand = "bash start.sh"
healthcheckPath = "/api/v1/health"
healthcheckTimeout = 600        # 10 minutes — accounts for CLIP warmup on slow cold starts
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

The 600-second health check timeout was a calculated choice: loading the CLIP model on Railway's CPU hardware takes 2–4 minutes on a cold start. Setting the timeout below that would cause Railway to kill the container before it finishes warming up.

---

## 5. Production Bug Fixes

### Bug 1 — Railway Container Running Out of Memory

**Symptom:** The Railway container was crashing with OOM errors before the app finished loading.

**Root cause:** The initial `requirements.txt` included `rembg` (background removal) and `opencv-python`, both of which have large native library dependencies. These inflated the container's footprint even though neither was used in production code.

**Fix:**
- Removed `rembg` and `opencv-python` from `requirements.txt`
- Added `low_cpu_mem_usage=True` to the CLIP model load — this loads model weights in chunks rather than allocating the full parameter tensor in one allocation, significantly reducing peak RAM during the model load phase

**Commits:** part of the `2c394a8` clean-up commit

---

### Bug 2 — Store Pages Showing Incomplete Product Lists (PostgREST 1000-Row Cap)

**Symptom:** Stores with more than 1000 products were silently truncated. The `/stores` endpoint only returned partial brand lists, and store detail pages were missing items.

**Root cause:** PostgREST (the REST API layer Supabase exposes) applies a server-side default limit of 1000 rows to all queries. This cap is silent — no error is raised, results are just truncated.

**Fix 1 — `.limit(5000)` on all queries in `stores.py`:**
```python
rows = client.table("products").select("brand, category, product_id").limit(5000).execute().data
```
Setting an explicit `.limit()` larger than the PostgREST default bypasses the implicit cap.

**Fix 2 — `get_brand_by_slug` SQL RPC for brand resolution:**

The `/stores/{store_id}` route needed to resolve a URL slug (e.g., `tomato-fashion`) to the exact brand name stored in the DB (e.g., `Tomato Fashion`). The original approach — querying all products and scanning brand names — would silently miss brands when the product list was truncated. I moved this to a SQL RPC that does the slug resolution in the database itself, bypassing PostgREST's row limit entirely:

```python
result = client.rpc("get_brand_by_slug", {"p_slug": store_id}).execute()
```

**Commits:** `b034431` (limit fix), `7a71a5f` (brand RPC fix)

---

## 6. Framer Frontend

I built the entire Framer frontend from scratch — from creating the initial Framer project to publishing the live site at `https://chicfinder.framer.website`.

### Pages

| Page | Description |
|------|-------------|
| Home / Landing | Marketing page with brand overview and entry points |
| Stores (`/stores`) | Grid of all available Egyptian fashion brands |
| Store Detail (`/store?id={slug}`) | Brand page with product grid, category filters, and search |
| Recommend (`/recommend`) | AI image upload and results page |

### Framer Code Components

Framer is a visual design tool that supports custom React code components embedded directly in the visual canvas. I built the following:

---

#### `StoreGrid`

Fetches the `/api/v1/stores` endpoint and renders a grid of store cards. Each card shows the store name, total product count, and category tags. Clicking a card navigates to the store detail page via Framer's routing.

---

#### `StoreProducts`

Store detail page component. Features:
- Fetches store metadata + items from `/api/v1/stores/{store_id}`
- Category filter tabs (derived dynamically from the store's available categories)
- Product search via `?search=` query param passed to `/api/v1/stores/{store_id}/items`
- Product cards with image, name, brand, price, and link to the brand's website

---

#### `RecommendPage` — [framer-components/RecommendPage.tsx](framer-components/RecommendPage.tsx)

The most complex component (624 lines). Manages a complete upload-to-results flow with multiple UI phases.

**State machine:**
```typescript
type Phase = "choose" | "camera" | "loading" | "results" | "error"
```

**User flow:**
1. **`choose`** — Upload button with camera/gallery selector
2. **`camera`** — Native camera or file picker input
3. **`loading`** — Animated spinner while the backend processes the image
4. **`results`** — 5 product cards with staggered entrance animation
5. **`error`** — Error state with retry option

**API integration:**
```typescript
async function callRecommend(blob: Blob): Promise<Item[]> {
    const formData = new FormData()
    formData.append("file", blob, "photo.jpg")
    const res = await fetch(`${API_URL}/api/v1/recommend`, { method: "POST", body: formData })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return data.recommendations?.[0]?.recommendations ?? []
}
```

**Animations:** Built with Framer Motion. Product cards enter with a staggered spring animation (`delay: index * 0.08`), with `whileHover` scale and shadow effects. The product modal enters with a spring scale transition.

**Product Modal:** Clicking any result card opens a full-screen modal with the product image, name, brand, price (formatted as `LE {amount}` for Egyptian pounds), and a direct link to the brand's website.

**Query-param routing:** Store detail pages use `/store?id={slug}` so each brand has a shareable URL. The `StoreProducts` component reads `window.location.search` on mount to extract the store ID.

---

## Key Technical Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Vector search backend | Supabase pgvector | Eliminates FAISS index as a separate stateful artifact; enables multi-instance Railway deployment without shared filesystem |
| CLIP model loading | Baked into Docker layer at build time | Avoids cold-start network download; model is always available, even without HuggingFace connectivity |
| Singleton encoder | Module-level `_encoder` with `threading.Lock` | CLIP model weights are ~300MB — one load per process, shared across all requests |
| Blocking calls | `run_in_executor` for encode + DB | Keeps FastAPI's async event loop unblocked; critical for concurrent request handling |
| PostgREST workaround | SQL RPC + explicit `.limit(5000)` | PostgREST's 1000-row default cap silently truncates large result sets; RPC functions bypass the cap |
| Firebase auth strategy | 3-strategy fallback | No service account JSON file in Railway; project-ID-only strategy handles production with no file I/O |
| Frontend platform | Framer | No build/deploy pipeline needed; Framer's code components allow full React with direct API access |
| Store abstraction | Virtual (derived from products table) | Avoids a separate `stores` table that would need to stay in sync; brands are the source of truth |

---

## Skills Demonstrated

**Backend:**
- FastAPI async routing, lifespan management, dependency injection
- Thread-safe singleton patterns (double-checked locking)
- Async/sync boundary management (`run_in_executor`)
- Firebase JWT verification with multi-strategy initialization
- Pydantic v2 schema design for request/response models

**Database:**
- PostgreSQL schema design (normalization, foreign keys, indexes)
- pgvector extension: vector column types, IVFFlat index configuration, cosine similarity search
- SQL function authorship (plpgsql/SQL RPC functions for pgvector + metadata join)
- Supabase SDK (table queries, RPC calls, Storage URL construction)
- PostgREST behavior and workarounds (limit cap, RPC bypass)

**Infrastructure:**
- Docker multi-stage-style image construction with model pre-caching
- Railway deployment configuration (`railway.toml`, health check tuning)
- Environment variable management across dev/prod environments
- Memory footprint optimization (dependency pruning, `low_cpu_mem_usage`)

**Frontend:**
- Framer code component development (React + TypeScript inside Framer's visual editor)
- Framer Motion animations (spring physics, staggered entrances, gesture responses)
- State machine UI (multi-phase upload flow)
- REST API integration from a no-build-pipeline frontend environment
- Query-parameter-based routing in Framer

**AI Pipeline Integration:**
- Connecting research-grade ML components into production API routes
- CLIP model lifecycle management (singleton, warmup, executor offloading)
- Image preprocessing (in-memory resize, format validation) before ML inference
