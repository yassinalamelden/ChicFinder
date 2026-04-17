# [Slice 3] Collect Egyptian Local Brands Dataset with Metadata

**Assignee:** @Barawy  
**Labels:** `slice-3`, `dataset`, `data-collection`, `high-priority`  
**Milestone:** Egypt Market + Metadata

---

## 🎯 Objective

Collect a dataset of Egyptian local fashion brand products with images and structured metadata. This dataset feeds directly into Amr's FAISS index pipeline and Gaber's metadata schema.

---

## 📋 Tasks

### 1. Dataset Collection
- [ ] Collect product images from Egyptian local brands (minimum 50 products to start)
- [ ] Save raw images to `data/raw_images/` using the naming convention `{item_id}.jpg`
- [ ] Supported formats: `.jpg`, `.jpeg`, `.png`, `.webp`

### 2. Metadata File (`data/metadata.json`)
- [ ] Create `data/metadata.json` as a JSON object keyed by item ID (matching image filename stem)
- [ ] Each entry must include at minimum:
  ```json
  {
    "item_001": {
      "id": "item_001",
      "name": "Product Name",
      "brand": "Brand Name",
      "category": "Tops",
      "color": "White",
      "price_egp": 450.0,
      "product_url": "https://brand.com/product",
      "store_location": "Cairo Festival City",
      "availability_egypt": true,
      "sizes": ["S", "M", "L", "XL"]
    }
  }
  ```
- [ ] Ensure every image in `data/raw_images/` has a matching key in `data/metadata.json`

### 3. Target Egyptian Brands
- [ ] Include a mix of brands available in the Egyptian market
- [ ] Prioritize brands with online presence and clear product photography
- [ ] Include at least 3 different categories (tops, bottoms, outerwear, etc.)

### 4. Data Quality
- [ ] Images must be clear product photos (white or neutral background preferred)
- [ ] No duplicate products
- [ ] Accurate pricing in Egyptian Pounds (EGP)
- [ ] Accurate availability information

---

## 📝 Acceptance Criteria

- ✅ At least 50 product images in `data/raw_images/`
- ✅ Every image has a matching entry in `data/metadata.json`
- ✅ All required metadata fields are present and non-null
- ✅ `price_egp` is a valid float
- ✅ `availability_egypt` is a boolean
- ✅ Running `python scripts/02_build_faiss_index.py` succeeds with the collected dataset

---

## 🔗 Dependencies & Integration

### Depends On
- **Gaber's Issue #8** — metadata schema definition (coordinate to ensure `metadata.json` structure aligns)

### Blocks
- **Amr's Issue #5** — `FAISSIndexBuilder` requires `data/raw_images/` and `data/metadata.json`
- **Moamen's Issue #6** — retrieval results reference filenames from this dataset

---

## 📁 Key Files to Create

```
data/
├── raw_images/
│   ├── item_001.jpg
│   ├── item_002.jpg
│   └── ...
└── metadata.json             # Full product catalog (keyed by item ID)
```
