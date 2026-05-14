# ChicFinder — Claude Context File

Egyptian fashion recommendation engine. Users upload outfit photos → Gemini 2.5 Flash + FashionCLIP embeddings → Supabase pgvector retrieval → typed recommendations. Live at **[chicfinder.framer.website](https://chicfinder.framer.website)** — store browsing, image search (upcoming).

---

## Who's Building This

**You** — Full-stack development, RAG pipeline, deployment, Framer frontend integration

**Friends/Team** — Contributing to GitHub repo

---

## Claude's Role

Help with:
- RAG pipeline debugging and optimization (FashionCLIP + pgvector)
- Backend/frontend feature work
- Supabase database/storage integration
- Deployment and configuration (Railway, Framer)
- Feature ideation and architecture decisions

**Prime Directive:** This project is ~95% complete. Focus on **shipping production-ready fast**. Polish and launch — iterate post-launch.

---

## Project Structure & Key Files

**Backend (`/` root) — deployed on Railway:**
- `api/` — FastAPI app with routes: `/health`, `/recommend`, `/search`, `/stores`, `/stores/{id}`, `/stores/{id}/items`
  - `api/main.py` — FastAPI app setup, CORS config, static files
  - `api/db/client.py` — Supabase client (singleton, thread-safe)
  - `api/routes/` — Organized by feature (health, recommend, search, stores)
- `ai_engine/llm/` — LLM integration (Gemini 2.5 Flash for parsing + reranking)
- `ai_engine/embeddings/` — FashionCLIP encoder (512-dim) for vector embeddings
- `ai_engine/rag/` — RAGPipeline orchestrator, pgvector retriever (replaced FAISS)
- `chic_finder/config.py` — Config dataclass, env vars (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, GEMINI_API_KEY, FIREBASE_PROJECT_ID, ALLOWED_ORIGINS)
- `shared/` — Pydantic schemas (ClothingItem, Recommendation, StoreItem)
- `scripts/` — Utility scripts (removed FAISS build script; not needed for prod)
- `infrastructure/` — Docker config for Railway deployment

**Frontend — Framer (chicfinder.framer.website):**
- Framer code components: `StoreGrid` (lists all stores), `StoreProducts` (store detail page with category filters + search)
- Query-param routing: `/store?id={store-id}` for store detail pages
- Uses Framer Motion for animations, built on Framer's visual/code component system
- No Next.js on production site; `FrontEnd/` directory is legacy (local dev only, not deployed)

**Config:**
- `.env` (local dev) — OpenAI API key, environment settings (not used in production; Railway has its own env vars)
- No `.env.example` — reference the DEPLOYMENT_AUDIT_REPORT.md or this CLAUDE.md for required env vars

---

## How to Run

**Local Development:**
```bash
# One-time setup
pip install -r requirements.txt
cd FrontEnd && npm install && cd ..

# Start backend (FastAPI on port 8000)
python -m uvicorn api.main:app --reload

# Backend Swagger UI: http://localhost:8000/docs

# Note: FAISS index build is no longer needed (using pgvector on Supabase)
# Note: Next.js frontend in FrontEnd/ is for local dev reference only; 
#       live site is at chicfinder.framer.website
```

**Production:**
- **Backend:** Railway (`https://chicfinder-production.up.railway.app`)
  - Deployed via Docker + `railway.toml` start command
  - Health check: `GET /api/v1/health`
- **Frontend:** Framer (`https://chicfinder.framer.website`)
  - Published from Framer editor (no build/deploy step needed)
  - Stores page lists all available stores
  - `/store?id={store-id}` page shows store detail + products

---

## API Reference

**Production Base URL:** `https://chicfinder-production.up.railway.app`

**Swagger UI (dev):** `http://localhost:8000/docs`

**Endpoints:**

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/api/v1/health` | No | Health check. Returns `{"status":"ok"}`. Currently static; could probe Supabase. |
| POST | `/api/v1/recommend` | No | Upload image → FashionCLIP encode → pgvector search → top 5 items |
| POST | `/api/v1/search` | Firebase JWT | Base64 image, filters (price, brand) → top 5 deduplicated results |
| GET | `/api/v1/stores` | No | List all brands as "stores" from `products` table |
| GET | `/api/v1/stores/{store_id}` | No | Store detail: info + all items with images |
| GET | `/api/v1/stores/{store_id}/items` | No | Items for a store; filterable by `category` and `search` query params |

---

## Architecture Highlights

**RAG Pipeline:**
```
User Photo (Framer UI)
    ↓
Gemini 2.5 Flash (item parsing + extraction)
    ↓
FashionCLIP encoding (512-dim vectors)
    ↓
Supabase pgvector search (top 25 similar items)
    ↓
Gemini 2.5 Flash (reranking to top 5)
    ↓
Recommendation objects (JSON)
```

**Data Sources:**
- `products` table (Supabase) — product metadata (name, brand, price, category, product_url, description, availability)
- `embeddings` table (Supabase) — product vectors (product_id, embedding, image_filename)
- `product-images` bucket (Supabase Storage) — product images served at `{SUPABASE_URL}/storage/v1/object/public/product-images/{filename}`

**Key Dependencies:**
- **Backend:** FastAPI, Supabase SDK, Gemini 2.5 Flash API, FashionCLIP, pgvector
- **Frontend:** Framer, React, Framer Motion
- **Database:** PostgreSQL (Supabase) with pgvector extension
- **Storage:** Supabase Storage (public bucket for product images)
- **Auth (search endpoint):** Firebase JWT verification

---

## Environment Variables (Production)

**Required on Railway:**
- `SUPABASE_URL` — Supabase project URL (hard fail without it)
- `SUPABASE_SERVICE_ROLE_KEY` — Supabase auth token (hard fail without it)
- `GEMINI_API_KEY` — Gemini 2.5 Flash API key (hard fail without it)
- `FIREBASE_PROJECT_ID` — Firebase project ID for JWT verification on `/search` endpoint (hard fail without it)

**Optional:**
- `ALLOWED_ORIGINS` — CORS allowlist (default: `http://localhost:3000`; must include `https://chicfinder.framer.website` for live site)
- `PORT` — Uvicorn port (default: 8000)

---

## Rules & Conventions

- **`(C)` prefix** — Files created by Claude get `(C)` prefix
- **Ask before editing** — Before editing non-`(C)` files, ask for permission (but you're already updating CLAUDE.md now, so this is explicit)
- **GitHub first** — All code changes go to the repo
- **Ship > Perfect** — Enhancements should launch quickly or be deferred
- **Framer components** — Live code components (`StoreGrid`, `StoreProducts`) are in the Framer project, not in the local repo

---

## Skills

- **Capture** (`../../05 Skills/capture.md`) — Save brainstorms, decisions, ideas to vault. Trigger: "save this", "capture this", "log this"

---

## Current Status

> **Last updated:** 2026-05-14
> **Status:** ~95% complete — store browsing live, recommend endpoint ready for testing
> **Tech Stack:** FastAPI + Supabase + Gemini 2.5 Flash + FashionCLIP + pgvector + Framer
> **Production URL:** https://chicfinder.framer.website

---

## Production Readiness Checklist

### ✅ Done
- [x] Backend deployed on Railway
- [x] Supabase database configured (pgvector + product data + image storage)
- [x] Framer frontend live (store browsing pages)
- [x] Query-param routing working (`/store?id=...`)
- [x] StoreProducts layout updated (padding + proportions)

### 🔴 Blocking (fix before production go-live)
- [ ] **CORS config** — `ALLOWED_ORIGINS` on Railway must include `https://chicfinder.framer.website`
- [ ] **Publish latest Framer changes** — StoreProducts layout updates need to be published to live site

### 🟡 Important (fix soon after launch)
- [ ] **Health check** — Upgrade `/api/v1/health` to probe Supabase instead of static response
- [ ] **Image URLs** — Verify `/recommend` endpoint image URLs don't 404 after Railway restart
- [ ] **`.env.example`** — Create reference file for required env vars
- [ ] **End-to-end test** — Test full recommend flow on production (FashionCLIP + pgvector on Railway hardware)

### 🟢 Nice-to-have
- [ ] **UI/UX polish** — Navbar visibility on `/store` page, accessibility
- [ ] **Analytics** — Track recommendation clicks, store visits
- [ ] **Search endpoint integration** — Wire up Firebase auth + `/search` endpoint in Framer UI when ready

---

## Known Issues & Notes

1. **`/recommend` returns ephemeral image URLs** — The endpoint returns `/uploads/{uuid}.png` which live on Railway's ephemeral filesystem. These will be lost on restart. Consider serving images from Supabase Storage instead.
2. **`/search` endpoint requires Firebase JWT** — Asymmetric with `/recommend` (which is open). Frontend needs to gate this endpoint appropriately.
3. **Next.js `FrontEnd/` directory not deployed** — It's reference/legacy code only. All active frontend work is in Framer.
4. **No static file serving for `/uploads/`** — FastAPI StaticFiles is configured, but the ephemeral nature of Railway makes this unreliable long-term.

---

## Next Steps for Growth (Post-Launch)

- [ ] Recommend image upload flow integration into Framer
- [ ] Search by image (Firebase auth + `/search` endpoint)
- [ ] User accounts + saved recommendations (Firebase)
- [ ] Analytics dashboard (who's viewing stores, which items are most recommended)
- [ ] Expand product catalog (more brands, Egyptian fashion partners)
- [ ] Mobile app (React Native based on current frontend code)
