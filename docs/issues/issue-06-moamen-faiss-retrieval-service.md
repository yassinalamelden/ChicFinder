# [Slice 2] Implement FAISS Retrieval Service & API Integration

**Assignee:** @Moamen  
**Labels:** `slice-2`, `ai`, `faiss`, `backend`, `high-priority`  
**Milestone:** Real Similarity Search

---

## 🎯 Objective

Implement `FAISSVectorStore` to load the pre-built FAISS index at startup and serve similarity queries at request time. Wire it into the `/api/v1/recommend` endpoint as a **zero-friction drop-in replacement** for the dummy implementation.

---

## 📋 Tasks

### 1. Implement `FAISSVectorStore` (`ai_engine/embeddings/vector_store.py`)
- [ ] Load `data/embeddings.index` (FAISS binary) at startup
- [ ] Load `data/index_to_image_id.json` mapping at startup
- [ ] Raise `FileNotFoundError` if either artifact is missing (with helpful message pointing to `scripts/02_build_faiss_index.py`)
- [ ] Implement singleton pattern via `get_instance()` classmethod
- [ ] Implement `search(image_bytes: bytes, top_k: int) -> list[dict]`

### 2. Search Contract
```python
from ai_engine.embeddings.vector_store import FAISSVectorStore

store = FAISSVectorStore.get_instance()
results = store.search(image_bytes=open("query.jpg", "rb").read(), top_k=4)
# results = [
#   {"rank": 1, "score": 0.94, "filename": "item_023.jpg", "image_url": "/images/item_023.jpg"},
#   {"rank": 2, "score": 0.91, "filename": "item_007.jpg", "image_url": "/images/item_007.jpg"},
#   ...
# ]
```

### 3. Wire into `/api/v1/recommend` (`api/routes/recommend.py`)
- [ ] Remove dummy random logic
- [ ] Call `FAISSVectorStore.get_instance().search(image_bytes, top_k=4)` instead
- [ ] Map FAISS results to `RecommendationResponse` schema
- [ ] Endpoint signature MUST remain exactly:
  ```python
  @router.post("/recommend")
  async def get_recommendations(file: UploadFile = File(...)):
      ...
  ```

### 4. Pre-warm at Startup (`api/main.py`)
- [ ] In the FastAPI `lifespan` context manager, call `FAISSVectorStore.get_instance()` at startup
- [ ] Log a warning (do not crash) if FAISS index not yet built

### 5. Testing
- [ ] Test `search()` with a real image returns top-K results sorted by score descending
- [ ] Test startup gracefully handles missing index
- [ ] Verify end-to-end: upload an image → get real FAISS-based recommendations

---

## 📝 Acceptance Criteria

- ✅ `FAISSVectorStore.get_instance()` loads once at startup
- ✅ `search()` returns results sorted by descending cosine similarity score
- ✅ `/api/v1/recommend` returns real product recommendations (not dummy data)
- ✅ API starts even if FAISS index not built (graceful warning)
- ✅ Compatible with Nour's Streamlit frontend — response schema unchanged

---

## 🔗 Dependencies & Integration

### Depends On
- **Yassin's Issue #4** — `get_encoder()` must be available
- **Amr's Issue #5** — `data/embeddings.index` and `data/index_to_image_id.json` must be built
- **Gendy's Issue #2** — `/api/v1/recommend` endpoint must be in place

### Enables
- **Nour's Issue #1** — Streamlit frontend will automatically use real search results

---

## 📁 Key Files

```
ai_engine/
└── embeddings/
    └── vector_store.py       # FAISSVectorStore singleton + search()

api/
└── routes/
    └── recommend.py          # Wire FAISSVectorStore into /api/v1/recommend
```
