"""
scripts/(C)_remove_brand.py
============================
Removes every record/image belonging to a given brand from the local dataset.

`data/` is entirely git-ignored (no version-control safety net), so this
script backs up `data/metadata.jsonl` before touching anything.

What it does:
  1. Backs up data/metadata.jsonl -> data/metadata.jsonl.bak
  2. Filters the brand out of data/metadata.jsonl (match on `source` or
     `brand`, case-insensitive)
  3. Deletes the brand's image files from data/raw_images/ (filename
     prefix `{source}_`, matching how scripts/01b_ingest_barawy_data.py
     names files: f"{source}_{product_id}_{idx}{ext}")
  4. Prints before/after counts

Does NOT touch data/embeddings.index / data/index_to_image_id.json --
those are rebuilt wholesale in the FAISS rebuild step, since
IndexFlatIP has no in-place delete.

Does NOT rebuild data/metadata.json -- re-run
scripts/(C)_sync_metadata_json.py afterwards. (Note: data/metadata.jsonl
is already the expanded per-image format, not the raw pre-download
format scripts/01b_ingest_barawy_data.py expects -- running 01b against
it would silently produce an empty metadata.json.)

Usage:
  python scripts/(C)_remove_brand.py activ
"""

import json
import shutil
import sys
from pathlib import Path

METADATA_JSONL = Path("data/metadata.jsonl")
RAW_IMAGES_DIR = Path("data/raw_images")


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/(C)_remove_brand.py <brand>")
        sys.exit(1)

    target = sys.argv[1].strip().lower()

    backup_path = METADATA_JSONL.with_suffix(".jsonl.bak")
    shutil.copy2(METADATA_JSONL, backup_path)
    print(f"Backed up {METADATA_JSONL} -> {backup_path}")

    kept, removed = [], []
    with open(METADATA_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            source = (rec.get("source") or "").strip().lower()
            brand = (rec.get("brand") or "").strip().lower()
            if source == target or brand == target:
                removed.append(rec)
            else:
                kept.append(rec)

    if not removed:
        print(f"No records found for brand '{target}'. Nothing to do.")
        return

    with open(METADATA_JSONL, "w", encoding="utf-8") as f:
        for rec in kept:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"data/metadata.jsonl: {len(kept) + len(removed)} -> {len(kept)} records "
          f"({len(removed)} '{target}' records removed)")

    deleted_images = 0
    prefix = f"{target}_"
    if RAW_IMAGES_DIR.exists():
        for img_path in RAW_IMAGES_DIR.iterdir():
            if img_path.is_file() and img_path.name.lower().startswith(prefix):
                img_path.unlink()
                deleted_images += 1

    print(f"Deleted {deleted_images} image files from {RAW_IMAGES_DIR} "
          f"matching prefix '{prefix}'")
    print()
    print("Next steps:")
    print("  1. Run scripts/(C)_sync_metadata_json.py to rebuild data/metadata.json")
    print("  2. Rebuild data/embeddings.index + data/index_to_image_id.json "
          "(FAISS rebuild step) so removed images drop out of retrieval")


if __name__ == "__main__":
    main()
