# 👗 ChicFinder: Find Your Style, Shop Local

![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=next.js&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FAISS](https://img.shields.io/badge/FAISS-4285F4?style=for-the-badge&logo=meta&logoColor=white)
![Gemini AI](https://img.shields.io/badge/Gemini_AI-8E44AD?style=for-the-badge&logo=google&logoColor=white)
![OpenRouter](https://img.shields.io/badge/OpenRouter-000000?style=for-the-badge&logoColor=white)
![Firebase](https://img.shields.io/badge/Firebase-FFA611?style=for-the-badge&logo=firebase&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

> **Upload a photo. Find the outfit. Shop Egyptian brands.**

ChicFinder is an AI-powered fashion visual search system built for the Egyptian market. Users upload an outfit photo and receive visually similar, shoppable recommendations from local brands — powered by FashionCLIP embeddings, a local FAISS vector index, and Gemini 2.5 Flash (via OpenRouter) for outfit parsing and visual reranking.

---

## 🚀 Features

### 🧠 AI Visual Search

- **FashionCLIP** (`patrickjohncyh/fashion-clip` by default) — swappable for a fine-tuned model via `CLIP_MODEL_PATH`, either a local checkpoint directory or a Hugging Face Hub repo ID
- **512-dimensional** L2-normalized embeddings
- **FAISS** `IndexFlatIP` cosine similarity search — local, no external vector DB required
- **Deduplication filter** — multiple product angles indexed, only unique products returned per query

### 👁️ Gemini Vision Intelligence (LLM Layer)

- **OutfitParser** — Gemini 2.5 Flash decomposes an outfit photo into structured per-item descriptions (type, color, style, gender, material, fit)
- **VisionReranker** — Gemini visually re-scores FAISS candidates by actual pixel similarity (temperature=0.0 — deterministic)
- Routed through **OpenRouter**'s OpenAI-compatible API — swap models or providers by changing `OPENROUTER_MODEL`, no code changes
- **Automatic fallback** — if the RAG pipeline fails or the model detects nothing, `/recommend` transparently falls back to a direct FashionCLIP + FAISS search rather than erroring out
- Centralized prompt engineering — all prompt templates in `ai_engine/llm/prompt_builder.py`

### 🔒 Secure API

- Firebase JWT authentication on `/recommend`, `/upload`, and `/search`
- Dev-mode fallback when Firebase credentials aren't configured, so local development doesn't require a Firebase project
- File-type allowlisting and PIL stream verification on every upload

### 📱 Modern Frontend

- Next.js + Tailwind CSS
- Image upload zone with drag-and-drop and live camera capture
- Product card results with brand, price, and similarity score
- Firebase Auth — login/onboarding flow

---

## 📸 Screenshots

| Homepage | Search Results |
|---|---|
| *Upload your outfit photo or use camera capture* | *Top-5 matched products from Egyptian brands* |
| ![Homepage](docs/images/homepage.png) | ![Results](docs/images/results.png) |

---

## 🏗️ Architecture

```
User uploads outfit photo (mobile / web)
│
▼
FastAPI /api/v1/recommend   ← Firebase JWT auth
│
├─── FashionCLIP Encoder ──────────► 512-d L2 vector
│
├─── OutfitParser (Gemini, ─────────► Outfit item list
│     via OpenRouter)                 [{type, color, style...}]
│
├─── FAISS IndexFlatIP ─────────────► Top-K candidates per item
│     (local, cosine similarity)
│
├─── VisionReranker (Gemini, ───────► Reordered indices
│     via OpenRouter)
│
▼
Typed Recommendations JSON → Next.js Frontend
        │
        └── on any RAG-step failure, falls back to a direct
            FashionCLIP + FAISS search (no Gemini calls)
```

### Tech Stack

**Frontend**

| Technology | Version | Purpose |
|---|---|---|
| Next.js | 16 | React framework, routing |
| Tailwind CSS | 4 | Styling |
| Firebase Auth | latest | User authentication |

**Backend**

| Technology | Version | Purpose |
|---|---|---|
| FastAPI | latest | REST API framework |
| Python | 3.10+ | Runtime |
| FAISS | `faiss-cpu` | Local vector index (`IndexFlatIP`, cosine similarity) |
| Firebase Admin | latest | JWT token verification |
| Uvicorn | latest | ASGI server |

**AI & ML**

| Technology | Purpose |
|---|---|
| FashionCLIP (`patrickjohncyh/fashion-clip`, swappable) | 512-d fashion-aware image embeddings |
| FAISS | Local cosine similarity vector search |
| Gemini 2.5 Flash | Outfit decomposition + visual reranking |
| OpenAI SDK, routed via OpenRouter | LLM client for the Gemini calls above |
| PyTorch | FashionCLIP inference |

**Infrastructure**

| Technology | Purpose |
|---|---|
| Docker | Containerization (`infrastructure/docker/Dockerfile.api`) |
| GitHub Actions | CI/CD |

---

## 🛠️ Installation & Setup

**Prerequisites**

- Python 3.10+
- Node.js 18+
- An [OpenRouter](https://openrouter.ai/) API key (used for the Gemini calls)
- A Firebase project (optional for local dev — falls back to a stub user without it)

**1. Clone the repository**

```bash
git clone https://github.com/yassinalamelden/ChicFinder.git
cd ChicFinder
```

**2. Environment Variables**

```bash
cp .env.example .env
```

Fill in at least:

```env
OPENROUTER_API_KEY=your-openrouter-key
OPENROUTER_MODEL=google/gemini-2.5-flash

# Optional — use your own fine-tuned CLIP model instead of the default
# CLIP_MODEL_PATH=your-username/your-fine-tuned-clip

# Optional — only needed to enforce real auth in production
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_CREDENTIALS_PATH=
```

**3. Backend Setup**

```bash
pip install -r requirements.txt

# Build the local FAISS index from data/raw_images/
python scripts/02_build_faiss_index.py

uvicorn api.main:app --reload
# Backend runs on http://localhost:8000
```

**4. Frontend Setup**

```bash
cd FrontEnd
npm install
npm run dev
# Frontend runs on http://localhost:3000
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for troubleshooting and more detail.

---

## 📦 Deployment

**Docker (local or any container host)**

```bash
docker build -f infrastructure/docker/Dockerfile.api -t chicfinder-api .
docker run -p 8000:8000 --env-file .env chicfinder-api
```

The image installs from `requirements.lock` for a reproducible build.

> `infrastructure/docker/docker-compose.yml` predates the Next.js migration and still targets the old Streamlit frontend — don't rely on it until it's updated.

---

## 🔌 API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/recommend` | 🔒 Firebase JWT | Upload an outfit image (multipart), get Gemini-parsed + FAISS-matched recommendations, with automatic FAISS-only fallback |
| POST | `/api/v1/upload` | 🔒 Firebase JWT | Upload an image, get back a stored URL |
| POST | `/api/v1/search` | 🔒 Firebase JWT | Upload a base64 image, get Top-5 similar products with brand/price filters |
| GET | `/api/v1/stores` | Public | List all brand stores |
| GET | `/api/v1/stores/{store_id}` | Public | Store detail + paginated item catalog |
| GET | `/api/v1/stores/{store_id}/items` | Public | Store's product catalog |
| GET | `/api/v1/health` | Public | Liveness probe |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'feat: add your feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request
