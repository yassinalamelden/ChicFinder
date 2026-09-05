"""
scripts/(C)_sync_metadata_json.py
===================================
Rebuilds data/metadata.json from data/metadata.jsonl.

Note: data/metadata.jsonl is already the *expanded, per-image* format
(one row per image, with a `filename` field) -- NOT the raw pre-download
scraper format (`image_urls` list) that scripts/01b_ingest_barawy_data.py
expects as input. Re-running 01b against the current metadata.jsonl would
silently produce an empty metadata.json (it loops over `image_urls`,
which no longer exists on these rows). Use this script instead whenever
metadata.jsonl changes but no new images need downloading (e.g. after
scripts/(C)_remove_brand.py, or after Step 3's merge once new images are
already on disk).

Only rows whose image file actually exists in data/raw_images are kept,
so metadata.json never points at a missing file.

Usage:
  python scripts/(C)_sync_metadata_json.py
"""

import json
from pathlib import Path

METADATA_JSONL = Path("data/metadata.jsonl")
METADATA_JSON = Path("data/metadata.json")
RAW_IMAGES_DIR = Path("data/raw_images")

# Same field set data/metadata.json has always used (mirrors metadata.jsonl
# minus product_type_fine/product_type_group).
JSON_FIELDS = [
    "product_id", "title", "brand", "category", "subcategory",
    "price", "product_url", "filename", "source", "gender",
]


def main():
    existing_images = {p.name for p in RAW_IMAGES_DIR.iterdir() if p.is_file()}

    final_metadata = {}
    missing_image = 0
    with open(METADATA_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            filename = rec.get("filename")
            if not filename or filename not in existing_images:
                missing_image += 1
                continue
            key = Path(filename).stem
            final_metadata[key] = {k: rec.get(k) for k in JSON_FIELDS}

    with open(METADATA_JSON, "w", encoding="utf-8") as f:
        json.dump(final_metadata, f, indent=4, ensure_ascii=False)

    print(f"Wrote {len(final_metadata)} entries to {METADATA_JSON}")
    if missing_image:
        print(f"Skipped {missing_image} metadata.jsonl rows with no matching "
              f"file in {RAW_IMAGES_DIR}")


if __name__ == "__main__":
    main()
