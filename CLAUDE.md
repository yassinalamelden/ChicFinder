# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is ChicFinder
AI-powered outfit recommendation system. Users upload an outfit photo; the system returns visually similar purchasable items from a Barawy fashion dataset using FashionCLIP + FAISS vector search.

## Editing Scope — IMPORTANT
**Only edit `api/` and `FrontEnd/`.**
Everything else (`ai_engine/`, `scripts/`, `data/`, `infrastructure/`, `chic_finder/`, `shared/`) is stable and working. Never modify those directories unless explicitly asked. When connecting new frontend features to AI capabilities, adjust the API layer to call existing AI methods — do not reach into the AI engine directly.

## Development Commands

### Local Development
```bash
# Backend — FastAPI on port 8000, run from repo root
uvicorn api.main:app --reload

# Frontend — Next.js on port 3000, run from FrontEnd/
cd FrontEnd && npm run dev
```

### Docker (full stack)
```bash
cd infrastructure/docker
docker-compose up --build
# API → http://localhost:8000  |  UI → http://localhost:8501  |  Nginx → http://localhost
```

### Environment
```bash
cp .env.example .env
# Required: GEMINI_API_KEY
```

## Architecture

### Request Flow (`/search`)
```
FrontEnd/components/UploadZone.tsx
  → user uploads image → base64-encode
  → POST /api/v1/search (JSON) via FrontEnd/lib/api.ts

api/routes/search.py
  1. base64.decode → raw bytes
  2. FAISSVectorStore.search(image_bytes, top_k=50)
       → encodes image with FashionCLIP → 512-d vector
       → FAISS cosine search → indices + scores
       → maps indices → metadata (brand, price, title, product_url)
  3. Filter by brand (exact match, case-insensitive)
  4. Filter by price range (min_price / max_price, EGP)
  5. Deduplicate, keep top 5
  → SearchResponse

FrontEnd/components/blocks/ProductGallery.tsx
  → renders product card grid
FrontEnd/components/ProductCard.tsx
  → individual product card with brand/price/score/shop link
```

### API Layer (`api/`)
| File | Purpose |
|------|---------|
| `api/main.py` | FastAPI app; lifespan pre-warms `FashionCLIPEncoder` and `FAISSVectorStore` singletons at startup |
| `api/routes/search.py` | Active endpoint: decode base64, call FAISS, apply filters, return results |
| `api/routes/recommend.py` | Full RAG endpoint (disabled, do not modify) |
| `api/routes/health.py` | `GET /health` → `{"status": "ok"}` |
| `api/middleware/logging.py` | Request duration logging |

### Frontend Layer (`FrontEnd/`) — Next.js 16 + TypeScript + Tailwind CSS
| File | Purpose |
|------|---------|
| `FrontEnd/app/page.tsx` | Root page (redirects to `/home` or `/login`) |
| `FrontEnd/app/home/page.tsx` | Main search page: upload zone + results gallery |
| `FrontEnd/app/login/page.tsx` | Firebase auth login screen |
| `FrontEnd/app/onboarding/page.tsx` | New-user onboarding flow |
| `FrontEnd/app/stores/page.tsx` | Browse stores listing |
| `FrontEnd/app/stores/[storeId]/page.tsx` | Individual store page |
| `FrontEnd/components/UploadZone.tsx` | Drag-and-drop image uploader, triggers search |
| `FrontEnd/components/blocks/ProductGallery.tsx` | Product results grid |
| `FrontEnd/components/ProductCard.tsx` | Single product card (image, title, price, brand, link) |
| `FrontEnd/components/AuthGuard.tsx` | Route protection wrapper using Firebase auth |
| `FrontEnd/components/Navbar.tsx` | Top navigation bar |
| `FrontEnd/contexts/AuthContext.tsx` | Firebase auth React context |
| `FrontEnd/lib/api.ts` | API client — calls FastAPI `/search`, `/stores`, etc. |
| `FrontEnd/lib/firebase.ts` | Firebase app + auth initialization |
| `FrontEnd/lib/constants.ts` | Shared constants (API base URL, etc.) |

### Search Response Shape
```json
{
  "results": [
    {
      "image_id": "string",
      "similarity_score": 0.92,
      "brand": "Tomato Store",
      "title": "Casual Blue Shirt",
      "price_egp": 299.0,
      "product_url": "https://..."
    }
  ],
  "processing_time_ms": 45.2
}
```

### Calling AI from the API (how to add new features)
The AI layer exposes two singletons accessed via class methods — never instantiate them in routes:
- `FashionCLIPEncoder.get_instance()` — `encode(image_bytes: bytes) → np.ndarray[512, float32]`
- `FAISSVectorStore.get_instance()` — `search(image_bytes, top_k) → List[dict]` or `search_by_vector(vector, top_k) → List[dict]`

Each result dict contains: `id`, `image_url`, `filename`, `score`, `category`, `brand`, `price`, `title`, `product_url`.

### Available Brands (for filter UI)
`Tomato Store`, `Town Team`, `Mobaco`

### Static File Mounts (set in `api/main.py`)
- `/uploads` → user-uploaded query images
- `/images` → dataset product images (served from `data/raw_images/`)
