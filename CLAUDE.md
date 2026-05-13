# ChicFinder — Claude Context File

Egyptian fashion recommendation engine implementing the OutfitAI paper. Users upload photos → GPT-4o Vision extracts clothing items → FashionCLIP embeddings → FAISS KNN retrieval → GPT-4o reranking → typed recommendations.

AI-powered outfit recommendation system. Users upload an outfit photo; the system returns visually similar purchasable items from a Barawy fashion dataset using FashionCLIP + FAISS vector search.

---

## Who's Building This

**You** — Full-stack development, RAG pipeline architecture, integration work

**Friends/Team** — Contributing to GitHub repo

---

## Claude's Role

Help with:
- RAG pipeline debugging and optimization
- Backend/frontend feature work
- Database/FAISS integration issues
- Deployment and configuration
- Feature ideation and architecture decisions

**Prime Directive:** This project is ~90% complete. Focus on **shipping enhancements fast**, not perfect. Polish and launch — iterate post-launch.

---

## Project Structure & Key Files

**Backend (`/` root):**
- `ai_engine/llm/` — OutfitParser (GPT-4o Vision item extraction), VisionReranker (reranking)
- `ai_engine/embeddings/` — FashionCLIPEncoder (512-dim), FAISSVectorStore (must be built first)
- `ai_engine/rag/` — RAGPipeline orchestrator, Retriever
- `api/` — FastAPI app (routes: `/api/v1/recommend`, `/api/v1/health`, `/api/v1/stores`)
- `chic_finder/config.py` — Config dataclass, env vars
- `shared/` — Pydantic schemas (ClothingItem, Recommendation)
- `scripts/build_database.py` — Build FAISS index (MUST run before search works)
- `scripts/test_pipeline.py` — Test RAG end-to-end

**Frontend (`FrontEnd/`):**
- Next.js 16 App Router, React 19, Tailwind 4, shadcn/ui, Firebase auth
- Pages: `app/home/`, `app/login/`, `app/onboarding/`, `app/stores/[storeId]/`
- Protected routes via `components/AuthGuard.tsx`

**Config:**
- `.env` — OpenAI API key, environment settings
- `FrontEnd/.env.local` — `NEXT_PUBLIC_API_URL=http://localhost:8000` + Firebase keys

---

## How to Run

```bash
# One-time setup
pip install -r requirements.txt
cd FrontEnd && npm install && cd ..

# Start both servers (Windows — recommended)
dev-server.bat

# Or manually
npm run dev:backend     # FastAPI on port 8000
npm run dev:frontend    # Next.js on port 3000
npm run dev             # Both via concurrently

# Build FAISS index (REQUIRED before AI search works)
python scripts/build_database.py

# Test RAG pipeline manually
python scripts/test_pipeline.py

# Build frontend for production
npm run build
```

---

## API Reference

**Swagger UI:** `http://localhost:8000/docs`

**Key Endpoints:**
- `POST /api/v1/recommend` — Upload image, get recommendations
- `GET /api/v1/health` — Health check
- `GET /api/v1/stores` — List available stores

---

## Architecture Highlights

**RAG Pipeline:**
```
User Photo → GPT-4o Vision (OutfitParser)
          → FashionCLIP encoding (512-dim)
          → FAISS KNN retrieval (top 25)
          → GPT-4o Vision reranking (top 5)
          → Typed Recommendation objects
```

**Key Dependencies:**
- FastAPI (backend)
- Next.js 16 (frontend)
- GPT-4o Vision (item parsing + reranking)
- FashionCLIP (embeddings, 512-dim)
- FAISS (vector search)
- Firebase (authentication)

---

## Rules & Conventions

- **`(C)` prefix** — Files created by Claude get `(C)` prefix
- **Ask before editing** — Before editing non-`(C)` files, ask for permission
- **GitHub first** — All code changes go to the repo
- **FAISS index** — Must be built before AI features work. Backend starts gracefully without it.
- **Ship > Perfect** — Enhancements should launch quickly or be deferred

---

## Skills

- **Capture** (`../05 Skills/capture.md`) — Save brainstorms, decisions, ideas, and project updates to the vault. Trigger: "save this", "capture this", "log this", "save to vault". Claude will auto-route to the right folder based on type.

## Current Status

> **Last updated:** 2026-04-28
> **Status:** ~90% complete — finishing enhancements, ready for launch
> **Tech Stack:** FastAPI + Next.js 16 + GPT-4o + FashionCLIP + FAISS

<!-- TODO: Track enhancements needed before launch -->
<!-- TODO: Document store data structure -->
<!-- TODO: Plan post-launch iteration roadmap -->
