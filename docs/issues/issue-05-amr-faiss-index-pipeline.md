# [Slice 2] Build FAISS Index Pipeline from Dataset

**Assignee:** @Amr  
**Labels:** `slice-2`, `ai`, `faiss`, `high-priority`  
**Milestone:** Real Similarity Search

---

## 🎯 Objective

Build an offline pipeline that encodes all dataset images using `FashionCLIPEncoder` and saves the resulting FAISS index plus an `index_to_image_id.json` mapping to disk. This runs once before the API starts.

---

## 📋 Tasks

### 1. Implement `FAISSIndexBuilder` (`ai_engine/embeddings/database_builder.py`)
- [ ] Iterate over all images in `data/raw_images/`
- [ ] For each image, validate it has a matching key in `data/metadata.json`
- [ ] Call `get_encoder().encode(image_bytes)` to produce a 512-d L2-normalized vector
- [ ] Add vector to `faiss.IndexFlatIP` (cosine similarity via dot product)
- [ ] Build `data/index_to_image_id.json` mapping `faiss_id → filename`
- [ ] Save FAISS index to `data/embeddings.index`
- [ ] Raise `ValueError` if zero valid images were indexed

### 2. Output Artifacts
```
data/
├── embeddings.index          # FAISS IndexFlatIP binary (512-d vectors)
├── index_to_image_id.json    # {"0": "item_001.jpg", "1": "item_002.jpg", ...}
└── metadata.json             # Must exist before building (Gaber's schema)
```

### 3. Build Script (`scripts/02_build_faiss_index.py`)
```bash
# Build with default paths
python scripts/02_build_faiss_index.py

# Build with custom paths
python scripts/02_build_faiss_index.py \
  --images data/raw_images \
  --index data/embeddings.index \
  --mapping data/index_to_image_id.json \
  --metadata data/metadata.json
```

### 4. Strict Validation Rules
- [ ] Skip images with no matching key in `metadata.json` (log a warning)
- [ ] Raise `FileNotFoundError` if `metadata.json` is missing
- [ ] Raise `ValueError` if `metadata.json` root is not a JSON object
- [ ] Raise `ValueError` if zero images pass validation

### 5. Convenience Entrypoint
```python
from ai_engine.embeddings.database_builder import build_index

build_index()  # uses all defaults
```

---

## 📝 Acceptance Criteria

- ✅ Running `python scripts/02_build_faiss_index.py` produces `data/embeddings.index` and `data/index_to_image_id.json`
- ✅ FAISS index contains exactly N vectors (one per valid image)
- ✅ `index_to_image_id.json` maps every FAISS index integer to an image filename
- ✅ Images without metadata entries are skipped with a warning (no crash)
- ✅ Pipeline runs independently — no API server needed
- ✅ `tqdm` progress bar shown during indexing

---

## 🔗 Dependencies & Integration

### Depends On
- **Yassin's Issue #4** — `get_encoder()` must be available
- **Gaber's Issue #7** — `data/metadata.json` must be present with correct schema

### Blocks
- **Moamen's Issue #6** — `FAISSVectorStore` loads the artifacts built here

---

## 📁 Key Files

```
ai_engine/
└── embeddings/
    └── database_builder.py   # FAISSIndexBuilder + build_index()

scripts/
└── 02_build_faiss_index.py   # CLI wrapper for FAISSIndexBuilder
```

---

## 🧪 Testing Commands

```bash
# 1. Ensure metadata.json exists with at least one entry
# 2. Place images in data/raw_images/
# 3. Run the pipeline
python scripts/02_build_faiss_index.py

# 4. Verify outputs
python -c "
import faiss, json
idx = faiss.read_index('data/embeddings.index')
mapping = json.load(open('data/index_to_image_id.json'))
print(f'Vectors: {idx.ntotal}, Mapping entries: {len(mapping)}')
assert idx.ntotal == len(mapping)
print('OK')
"
```
