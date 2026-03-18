# ChicFinder 👗

Deep learning-based intelligent expert system for outfit recommendations, based on the **OutfitAI** paper (*Multimedia Tools and Applications, 2025*). It uses RAG (Retrieval-Augmented Generation) to recommend similar fashion items from a clothing database given a user-uploaded outfit photo.

## Tech Stack
- **Backend API**: FastAPI + Uvicorn
- **Frontend**: Streamlit
- **AI Engine**: PyTorch, Transformers (ViT-B / SETR), VGG-16, FAISS, OpenAI GPT-4o
- **Infra**: Docker, docker-compose, Nginx

## Getting Started

### 1. Setup Environment
```bash
cp .env.example .env
# Fill in your OPENAI_API_KEY in .env
```

### 2. Run with Docker
```bash
cd infrastructure/docker
docker-compose up --build
```

### 3. Local Development
```bash
# Backend
uvicorn api.main:app --reload

# Frontend
streamlit run frontend/app.py
```

## Architecture
See [docs/architecture.md](docs/architecture.md) for detailed pipeline flow.
