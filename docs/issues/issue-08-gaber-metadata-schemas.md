# [Slice 3] Implement Metadata Schemas & Egypt Availability Filters

**Assignee:** @Gaber  
**Labels:** `slice-3`, `backend`, `schema`, `egypt-market`, `high-priority`  
**Milestone:** Egypt Market + Metadata

---

## 🎯 Objective

Define the canonical metadata schema for ChicFinder products with Egypt availability filters. This schema is the single source of truth that aligns `data/metadata.json` (Barawy), the API response (Gendy/Moamen), and the frontend contract (Issue #3).

---

## 📋 Tasks

### 1. Define `metadata.json` Schema

The root must be a JSON object keyed by item ID (matching image filename stem):

```json
{
  "item_001": {
    "id": "item_001",
    "name": "White Linen Shirt",
    "brand": "Concrete",
    "category": "Tops",
    "color": "White",
    "type": "Shirt",
    "price_egp": 850.0,
    "product_url": "https://concrete-eg.com/white-linen-shirt",
    "store_location": "Mall of Arabia, Cairo",
    "availability_egypt": true,
    "sizes": ["S", "M", "L", "XL"]
  }
}
```

### 2. Define Pydantic Schema (`shared/schemas/product.py`)
- [ ] Create `ProductMetadata` Pydantic model:
  ```python
  from pydantic import BaseModel
  from typing import Optional, List

  class ProductMetadata(BaseModel):
      id: str
      name: str
      brand: str
      category: str
      color: Optional[str] = None
      type: Optional[str] = None
      price_egp: Optional[float] = None
      product_url: Optional[str] = None
      store_location: Optional[str] = None
      availability_egypt: bool
      sizes: Optional[List[str]] = None
  ```

### 3. Egypt Availability Filter
- [ ] The `availability_egypt` field is **required** and non-optional in all schemas
- [ ] This boolean drives the Egypt market filter in the frontend (Issue #3)
- [ ] Products with `availability_egypt: false` should be filterable in search results

### 4. Schema Validation Script (`scripts/validate_data.py`)
- [ ] Validate every entry in `data/metadata.json` against `ProductMetadata`
- [ ] Report which items fail validation
- [ ] Exit with code 1 if any items are invalid

### 5. Align with Frontend Contract
Ensure `ProductMetadata` fields align with the TypeScript interface from Issue #3:

| Python Field | TypeScript Field | Notes |
|---|---|---|
| `id` | `image_id` | Used as FAISS lookup key |
| `brand` | `brand` | Nullable in TS |
| `price_egp` | `price_egp` | Nullable in TS |
| `product_url` | `product_url` | Nullable in TS |
| `store_location` | `store_location` | Nullable in TS |
| `availability_egypt` | `availability_egypt` | Required in both |

---

## 📝 Acceptance Criteria

- ✅ `shared/schemas/product.py` defines `ProductMetadata` Pydantic model
- ✅ `scripts/validate_data.py` validates `data/metadata.json` against schema
- ✅ `availability_egypt` is a required boolean in all layers
- ✅ Schema aligns with TypeScript interface in Issue #3
- ✅ All fields match what Barawy's dataset collection will provide

---

## 🔗 Dependencies & Integration

### Depends On
- None — schema can be defined independently

### Blocks
- **Barawy's Issue #7** — Barawy must follow this schema when collecting dataset metadata
- **Moamen's Issue #6** — `FAISSVectorStore.search()` uses this schema to enrich results

### Coordinates With
- **Issue #3** (Gendy/Nour) — TypeScript interface must mirror `ProductMetadata`

---

## 📁 Key Files to Create

```
shared/
└── schemas/
    ├── __init__.py
    └── product.py            # ProductMetadata Pydantic model

scripts/
└── validate_data.py          # Schema validation script for metadata.json
```

---

## 🧪 Testing Commands

```bash
# Validate the dataset metadata
python scripts/validate_data.py

# Expected output (if valid):
# ✅ All 50 items passed validation.
# Expected output (if invalid):
# ❌ item_003: price_egp must be a float
# Exit code: 1
```
