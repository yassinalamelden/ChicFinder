# [Slice 1] Build Streamlit Frontend & Image Upload Integration

**Assignee:** @Nour  
**Labels:** `slice-1`, `frontend`, `streamlit`, `high-priority`  
**Milestone:** Working Skeleton

---

## 🎯 Objective

Build a Streamlit frontend that allows users to upload an outfit/clothing image and displays the top 3 recommendations from the FastAPI backend. This UI serves as the testing ground for the entire system.

---

## 📋 Tasks

### 1. Set Up Streamlit Project
- [ ] Create `frontend/` directory with `__init__.py`
- [ ] Create `frontend/app.py` (main Streamlit app)
- [ ] Create `frontend/requirements.txt` with dependencies:
  ```
  streamlit==1.28.0
  requests==2.31.0
  pillow==10.0.0
  python-dotenv==1.0.0
  ```

### 2. Streamlit App Structure (`frontend/app.py`)
- [ ] Set page config with title `"ChicFinder - AI Outfit Recommendations"`
- [ ] Create sidebar with:
  - App description
  - Backend URL input field (default: `http://localhost:8000`)
  - Instructions for users

### 3. Image Upload & Display
- [ ] Create main content area with:
  - File uploader widget for JPEG/PNG images
  - Display uploaded image in the UI
  - Show file size and dimensions

### 4. Backend Integration
- [ ] On image upload, make POST request to `http://localhost:8000/api/v1/recommend`
  - Use `requests` library
  - Include image file in multipart form data
  - Handle errors gracefully (network, backend timeout, invalid image)
- [ ] Parse `SearchResponse` JSON from backend
- [ ] Extract `recommendations` array

### 5. Results Display
- [ ] Display top 3 recommendations in 3 columns:
  - Each column shows:
    - Clothing item image (from `image_url`)
    - Item name
    - Category
    - Similarity score (formatted as percentage, e.g., "95% Similar")
  - Use `st.columns()` for layout
  - Use `st.image()` to display recommendation images

### 6. Error Handling
- [ ] Handle case where backend is unreachable
- [ ] Handle case where image is invalid
- [ ] Handle case where recommendations are empty
- [ ] Display user-friendly error messages

### 7. Run Instructions
- [ ] Create `.streamlit/config.toml` (optional, for custom theming)
- [ ] Run command: `streamlit run frontend/app.py`
- [ ] Accessible at `http://localhost:8501`

---

## 📝 Acceptance Criteria

- ✅ Streamlit app starts without errors on `http://localhost:8501`
- ✅ User can upload an image (JPEG/PNG)
- ✅ Uploaded image displays correctly in the UI
- ✅ On upload, app makes request to FastAPI backend
- ✅ Top 3 recommendations display with images, names, categories, and similarity scores
- ✅ Error messages display if backend is unavailable
- ✅ UI is responsive and user-friendly
- ✅ All dependencies are in `frontend/requirements.txt`

---

## 🔗 Dependencies & Integration

### Depends On
- **Gendy's Issue #2** — FastAPI backend (`api/main.py`, `/api/v1/recommend` endpoint) must be running

### Coordinates With
- **Moamen's Slice 2 integration** — frontend will automatically work with real CLIP + FAISS once backend is wired

---

## 📁 Key Files to Create

```
frontend/
├── __init__.py
├── app.py                  # Streamlit app (image upload + results display)
└── requirements.txt        # Streamlit dependencies

.streamlit/
└── config.toml             # (optional) custom theme
```
