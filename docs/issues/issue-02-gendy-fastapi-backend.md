# [Slice 1] Build FastAPI Backend Skeleton & Search Endpoint

**Assignee:** @Gendy  
**Labels:** `slice-1`, `backend`, `fastapi`, `high-priority`  
**Milestone:** Working Skeleton

---

## 🎯 Objective

Build the FastAPI backend skeleton with Pydantic schemas and a working `/api/v1/recommend` endpoint that returns dummy clothing recommendations. This is the foundation that Slice 2 will enhance with real CLIP + FAISS similarity search.

---

## 📋 Tasks

### 1. Set Up Project Structure
- [ ] Create `api/` directory with `__init__.py`
- [ ] Create `api/main.py` with FastAPI app initialization
- [ ] Create `api/routers/` directory with `__init__.py`
- [ ] Create `api/models/` directory with `__init__.py`
- [ ] Create `requirements.txt` with dependencies:
  ```
  fastapi==0.104.1
  uvicorn==0.24.0
  pydantic==2.5.0
  pillow==10.0.0
  python-multipart==0.0.6
  ```

### 2. Define Pydantic Schemas (`api/models/schemas.py`)
- [ ] Create `ClothingItem` schema:
  ```python
  from pydantic import BaseModel
  from typing import Optional

  class ClothingItem(BaseModel):
      id: str
      name: str
      category: str
      image_url: str
      embedding_id: Optional[int] = None  # Will be populated by Slice 2
  ```
- [ ] Create `SearchResponse` schema:
  ```python
  from pydantic import BaseModel
  from typing import List, Optional

  class SearchResponse(BaseModel):
      query_image_url: str
      recommendations: List[ClothingItem]
      similarity_scores: Optional[List[float]] = None  # Will be populated by Slice 2
  ```

### 3. Implement Search Router (`api/routers/search.py`)
- [ ] Create `/api/v1/recommend` POST endpoint that:
  - Accepts `file: UploadFile` (image in JPEG or PNG format)
  - Temporarily saves image to disk
  - Returns 3 dummy `ClothingItem` objects with realistic data
  - Returns `SearchResponse` with `similarity_scores` as placeholder `[0.95, 0.92, 0.88]`
  - Deletes the temporary image file after processing
  - Handles errors gracefully (invalid file type, upload failure)
- [ ] **Exact endpoint signature** (this contract CANNOT change for Slice 2):
  ```python
  from fastapi import APIRouter, File, UploadFile
  from api.models.schemas import SearchResponse

  router = APIRouter()

  @router.post("/recommend", response_model=SearchResponse)
  async def get_recommendations(file: UploadFile = File(...)) -> SearchResponse:
      """
      Search for similar clothing items based on an uploaded image.

      Args:
          file: Image file (JPEG or PNG)

      Returns:
          SearchResponse with query_image_url and top 3 recommendations
      """
      # Implementation here
      pass
  ```

### 4. Set Up FastAPI App (`api/main.py`)
- [ ] Initialize FastAPI app with:
  - Title: `"ChicFinder"`
  - Version: `"0.1.0"`
  - Description: `"AI-powered outfit recommendation system"`
- [ ] Include search router with prefix `/api/v1`
- [ ] Add CORS middleware to allow frontend (Streamlit on port 8501) requests:
  ```python
  from fastapi.middleware.cors import CORSMiddleware

  app.add_middleware(
      CORSMiddleware,
      allow_origins=["http://localhost:8501", "http://localhost:3000"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
- [ ] Create `/health` endpoint for testing:
  ```python
  @app.get("/health")
  def health_check():
      return {"status": "ok", "service": "ChicFinder API"}
  ```
- [ ] **Run instruction:**
  ```bash
  uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
  ```

### 5. Testing
- [ ] Test `/health` endpoint returns `200 OK` with JSON response
- [ ] Test `/api/v1/recommend` endpoint with a sample image (JPEG or PNG)
- [ ] Verify response structure matches `SearchResponse` schema exactly
- [ ] Verify temporary image file is cleaned up after search
- [ ] Test with invalid file types (should return 422 or 400)

---

## 📝 Acceptance Criteria

- ✅ FastAPI server starts without errors on `http://localhost:8000`
- ✅ `/health` endpoint returns `{"status": "ok", "service": "ChicFinder API"}`
- ✅ `/api/v1/recommend` endpoint accepts image uploads (multipart/form-data with `file` key)
- ✅ Response structure **exactly** matches `SearchResponse` schema:
  ```json
  {
    "query_image_url": "/uploads/upload_abc123.jpg",
    "recommendations": [
      {
        "id": "item_001",
        "name": "Blue Denim Jacket",
        "category": "Outerwear",
        "image_url": "https://example.com/item1.jpg",
        "embedding_id": null
      },
      {
        "id": "item_002",
        "name": "White T-Shirt",
        "category": "Tops",
        "image_url": "https://example.com/item2.jpg",
        "embedding_id": null
      },
      {
        "id": "item_003",
        "name": "Black Jeans",
        "category": "Bottoms",
        "image_url": "https://example.com/item3.jpg",
        "embedding_id": null
      }
    ],
    "similarity_scores": [0.95, 0.92, 0.88]
  }
  ```
- ✅ All dependencies are pinned in `requirements.txt`
- ✅ Code is type-hinted (using Python 3.10+ type hints)
- ✅ No temporary files are left on disk after `/api/v1/recommend` completes

---

## 🔗 Dependencies & Integration

### Depends On
- None — Slice 1 backend is independent and can be developed in parallel

### Blocks
- **Moamen's Slice 2 integration** — Moamen will wire CLIP embeddings + FAISS index into this endpoint as a **zero-friction drop-in replacement**
- The `/api/v1/recommend` endpoint signature MUST NOT change after this issue is merged

### Coordinates With
- **Nour's Issue #1** — must match the exact `SearchResponse` schema and `/api/v1/recommend` contract

---

## 📁 Key Files to Create

```
api/
├── __init__.py
├── main.py                 # FastAPI app setup, CORS, routes
├── models/
│   ├── __init__.py
│   └── schemas.py          # Pydantic schemas (ClothingItem, SearchResponse)
└── routers/
    ├── __init__.py
    └── search.py           # /api/v1/recommend endpoint (dummy implementation)

requirements.txt            # All Python dependencies
```

---

## 🧪 Testing Commands

```bash
# Start the API
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Test /health
curl http://localhost:8000/health

# Test /api/v1/recommend with an image
curl -X POST "http://localhost:8000/api/v1/recommend" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/image.jpg"
```
