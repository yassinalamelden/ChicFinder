# [Slice 2] Implement CLIP Embedder & Background Remover

**Assignee:** @Yassin  
**Labels:** `slice-2`, `ai`, `embeddings`, `high-priority`  
**Milestone:** Real Similarity Search

---

## 🎯 Objective

Implement the `FashionCLIPEncoder` singleton using the `patrickjohncyh/fashion-clip` model from HuggingFace. This encoder is the single source of embeddings for both the offline index-building pipeline (Amr) and the online query pipeline (Moamen).

---

## 📋 Tasks

### 1. Implement `FashionCLIPEncoder` (`ai_engine/embeddings/encoder.py`)
- [ ] Load `patrickjohncyh/fashion-clip` via HuggingFace Transformers
- [ ] Support local fine-tuned model fallback via `CLIP_MODEL_PATH` env var
- [ ] Implement singleton pattern via `get_instance()` classmethod
- [ ] Implement `encode(image_bytes: bytes) -> np.ndarray` with L2 normalization
- [ ] Output contract: `shape=(512,)`, `dtype=float32`, `||v||_2 = 1.0`

### 2. Encoder Contract (agreed with Amr + Moamen)
```python
from ai_engine.embeddings.encoder import get_encoder

encoder = get_encoder()
vector = encoder.encode(open("image.jpg", "rb").read())
# vector.shape == (512,)
# np.linalg.norm(vector) ≈ 1.0
```

### 3. Module-level Convenience Accessor
```python
def get_encoder() -> FashionCLIPEncoder:
    """Return the singleton encoder — model loaded only on first call."""
    return FashionCLIPEncoder.get_instance()
```

### 4. Constants (shared across all slices)
```python
EMBEDDING_DIM = 512          # fixed — agreed contract
CLIP_MODEL_ID = "patrickjohncyh/fashion-clip"
DEFAULT_LOCAL_CLIP_PATH = "models/fine_tuned_clip"
```

### 5. Testing
- [ ] Verify `encode()` returns a 512-d L2-normalized vector
- [ ] Verify singleton pattern (second call returns same instance)
- [ ] Verify graceful fallback when local model is absent

---

## 📝 Acceptance Criteria

- ✅ `FashionCLIPEncoder.get_instance()` loads model exactly once
- ✅ `encode(image_bytes)` returns `np.ndarray` with `shape=(512,)`, `dtype=float32`
- ✅ Returned vectors are L2-normalized (`np.linalg.norm(v) ≈ 1.0`)
- ✅ Falls back to `patrickjohncyh/fashion-clip` if local model not found
- ✅ Compatible with CUDA (auto-detected) and CPU

---

## 🔗 Dependencies & Integration

### Depends On
- None — encoder is standalone

### Blocks
- **Amr's Issue #5** — `FAISSIndexBuilder` calls `get_encoder().encode()` for every dataset image
- **Moamen's Issue #6** — `FAISSVectorStore` calls `get_encoder().encode()` for every query image

---

## 📁 Key Files

```
ai_engine/
└── embeddings/
    ├── __init__.py
    └── encoder.py          # FashionCLIPEncoder singleton + get_encoder()
```
