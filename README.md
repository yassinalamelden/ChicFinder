# ChicFinder 👗

Deep learning-based intelligent expert system for outfit recommendations, based on the **OutfitAI** paper (*Multimedia Tools and Applications, 2025*). It uses RAG (Retrieval-Augmented Generation) to recommend similar fashion items from a clothing database given a user-uploaded outfit photo.

## Tech Stack
- **Backend API**: FastAPI + Uvicorn
- **Frontend**: Next.js (React) — `FrontEnd/`
- **AI Engine**: FashionCLIP (CLIP ViT-B/32) embeddings, FAISS vector search, Gemini (via OpenRouter) for outfit parsing + reranking
- **Auth**: Firebase

## Getting Started

See [DEVELOPMENT.md](DEVELOPMENT.md) for full setup and local-dev instructions (installing dependencies, running both servers, environment variables, troubleshooting).

Quick version:
```bash
pip install -r requirements.txt
cd FrontEnd && npm install && cd ..
cp .env.example .env   # fill in OPENROUTER_API_KEY and Firebase settings

# Two terminals:
python -m uvicorn api.main:app --reload   # backend, port 8000
cd FrontEnd && npm run dev                # frontend, port 3000
```

## Architecture
See [docs/architecture.md](docs/architecture.md) for the pipeline flow.

> **Note:** `infrastructure/docker/docker-compose.yml` predates the Next.js migration and still targets the old Streamlit frontend (port 8501) — it hasn't been updated yet. Use the manual setup above until it's revisited.
