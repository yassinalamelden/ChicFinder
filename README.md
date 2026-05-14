# ChicFinder — Egyptian Fashion Recommendation Engine

Find your perfect outfit style with AI. Browse Egyptian fashion brands, filter by category, and discover products with direct shopping links.

**🌐 Live Site:** [chicfinder.framer.website](https://chicfinder.framer.website)  
**🚀 Backend API:** [chicfinder-production.up.railway.app](https://chicfinder-production.up.railway.app)

---

## Features

- **🛍️ Store Browsing** — Browse all Egyptian fashion brands with product catalogs
- **🔍 Smart Filtering** — Filter by category, search by name/brand
- **🤖 AI Recommendations** *(coming soon)* — Upload an image → get visually similar products
- **🔗 Direct Shopping** — One-click links to buy from store websites

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Framer (visual + code components) |
| **Backend** | FastAPI (Python 3.10) on Railway |
| **Database** | Supabase (PostgreSQL + pgvector) |
| **Vector Search** | pgvector (semantic embeddings) |
| **AI/ML** | Gemini 2.5 Flash + FashionCLIP (512-dim) |
| **Deployment** | Railway (backend) + Framer (frontend) |

---

## Project Structure

```
.
├── api/                    # FastAPI backend
│   ├── main.py            # App entry, routes, CORS
│   ├── db/                # Supabase client singleton
│   ├── routes/            # Endpoints (health, recommend, search, stores)
│   └── services/          # Business logic & RAG pipeline
├── ai_engine/             # Machine learning components
│   ├── embeddings/        # FashionCLIP encoder
│   ├── llm/               # Gemini 2.5 Flash integration
│   └── rag/               # pgvector retrieval & ranking
├── chic_finder/           # Config & utilities
├── shared/                # Pydantic schemas
├── tests/                 # Comprehensive test suite
├── supabase/              # Database migrations & schema
├── infrastructure/        # Docker & deployment configs
├── docs/                  # Architecture & design docs
├── CLAUDE.md              # 📖 Comprehensive documentation
└── DEPLOYMENT_AUDIT_REPORT.md  # 📊 Latest deployment audit
```

---

## Quick Start

### Local Development

**Requirements:** Python 3.10+, pip, Git

```bash
# 1. Clone & setup
git clone <repo-url>
cd chicfinder
python -m venv venv
source venv/bin/activate  # `venv\Scripts\activate` on Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your keys (Supabase, Gemini, Firebase)

# 4. Run backend (FastAPI)
python -m uvicorn api.main:app --reload
# → Swagger UI: http://localhost:8000/docs

# 5. Run tests
pytest -v
```

### Docker (Production-like)

```bash
cd infrastructure/docker
docker-compose up --build
# → Backend: http://localhost:8000
```

---

## API Endpoints

**Base URL (prod):** `https://chicfinder-production.up.railway.app/api/v1`

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/health` | Service health check | No |
| `POST` | `/recommend` | Upload image → get recommendations | No |
| `POST` | `/search` | Image search with filters (price, brand) | Firebase JWT |
| `GET` | `/stores` | List all fashion brands | No |
| `GET` | `/stores/{id}` | Get store details + products | No |
| `GET` | `/stores/{id}/items` | Filter by category/search | No |

**Full Swagger docs:** [localhost:8000/docs](http://localhost:8000/docs) (dev) or [production API/docs](https://chicfinder-production.up.railway.app/docs)

---

## Environment Variables

Create a `.env` file at the project root:

```env
# Supabase (required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-key

# Gemini API (required)
GEMINI_API_KEY=your-key

# Firebase (required for /search)
FIREBASE_PROJECT_ID=your-project

# Optional
ALLOWED_ORIGINS=http://localhost:3000,https://chicfinder.framer.website
PORT=8000
```

See `.env.example` for a template.

---

## How It Works

### AI Recommendation Pipeline

```
📸 User Photo
  ↓
🤖 Gemini 2.5 Flash (parse clothing items)
  ↓
🧠 FashionCLIP (generate 512-dim vectors)
  ↓
🔍 Supabase pgvector (semantic search: top 25)
  ↓
🎯 Gemini 2.5 Flash (rerank to top 5, format)
  ↓
📦 Recommendation JSON + shopping links
```

### Data Model

- **`products`** — Product metadata (name, brand, price, category, URL, description)
- **`embeddings`** — FashionCLIP vectors (pgvector, 512-dim)
- **`product-images`** — Public storage bucket (Supabase)

---

## Deployment

### Production Backend (Railway)

Auto-deployed from this repo. Runs via Docker.

**Key files:**
- `railway.toml` — Start command, health check, vars
- `infrastructure/docker/Dockerfile.api` — Python 3.10, dependencies
- `start.sh` — Uvicorn entry point

**Health check:** `GET /api/v1/health` (600s timeout)

### Production Frontend (Framer)

Deployed independently at **[chicfinder.framer.website](https://chicfinder.framer.website)**

**Live pages:**
- `/stores` — Browse all brands
- `/store?id={brand}` — Store detail + products

---

## Production Readiness

✅ = Complete | ⏳ = In Progress | ❌ = Pending

- ✅ Backend deployed (Railway)
- ✅ Database configured (Supabase)
- ✅ Frontend live (Framer)
- ✅ Store browsing working
- ⏳ CORS config (must include chicfinder.framer.website)
- ⏳ Health check (currently static; should probe DB)
- ⏳ Recommend endpoint test (verify FashionCLIP + pgvector)
- ❌ Image serving (currently ephemeral; move to Supabase Storage)

See **[CLAUDE.md](CLAUDE.md)** for full status and next steps.

---

## Documentation

- **[CLAUDE.md](CLAUDE.md)** — Complete project guide, architecture, development notes
- **[DEPLOYMENT_AUDIT_REPORT.md](DEPLOYMENT_AUDIT_REPORT.md)** — Latest deployment audit (2026-05-13)
- **[docs/architecture.md](docs/architecture.md)** — Detailed pipeline flow

---

## Testing

```bash
# All tests
pytest

# Specific suite
pytest tests/routes/ -v
pytest tests/auth/ -v

# Coverage
pytest --cov=api --cov-report=html
```

---

## Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes, add tests, commit
3. Push and open a PR
4. See [CLAUDE.md](CLAUDE.md) for code style & conventions

---

## Built By

**Nour Atef** (@nour-atef) + team

---

## Questions?

- 📖 See **[CLAUDE.md](CLAUDE.md)** for comprehensive docs
- 🐛 Check **[DEPLOYMENT_AUDIT_REPORT.md](DEPLOYMENT_AUDIT_REPORT.md)** for known issues
- 💬 Open an issue on GitHub
