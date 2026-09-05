"""
scripts/(C)_build_train_val_split.py
======================================
Builds a train/validation split of the cleaned dataset, following
ChicFinder-Master-Plan.md Sec 6.4's rule: "Split order is law: clean ->
dedup -> then split, BY PRODUCT, never by image, stratified by brand x
category." (Run this after cleaning -- scripts/(C)_remove_brand.py,
the placeholder-image cleanup -- not before.)

Why by-product, not by-image: multiple images of the same product are
near-duplicates. Splitting by image would leak near-identical images of
the same product across train/val, inflating validation metrics.

Stratification key: (source, gender). Category isn't used for
stratification yet -- the raw category taxonomy has 79 unrecociled
labels across brands (see coverage report), so category-stratified
splitting would need the taxonomy unification pass first. Source+gender
is clean and reliable in the current data.

Output:
  data/train/<filename>        -- copied images (default 85%)
  data/validation/<filename>   -- copied images (default 15%)
  data/train_metadata.jsonl    -- per-image records for the train split
  data/validation_metadata.jsonl -- per-image records for the val split

Deterministic: fixed random seed, so re-running reproduces the same split
(only regenerates if you delete data/train, data/validation first).

Usage:
  python scripts/(C)_build_train_val_split.py
"""

import json
import random
import shutil
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

METADATA_JSONL = Path("data/metadata.jsonl")
RAW_IMAGES_DIR = Path("data/raw_images")
TRAIN_DIR = Path("data/train")
VAL_DIR = Path("data/validation")
TRAIN_MANIFEST = Path("data/train_metadata.jsonl")
VAL_MANIFEST = Path("data/validation_metadata.jsonl")

VAL_FRACTION = 0.15
SEED = 42


def main():
    records = []
    with open(METADATA_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if (RAW_IMAGES_DIR / rec["filename"]).exists():
                records.append(rec)

    print(f"Loaded {len(records)} image records with an existing file on disk")

    # Group by product (source, product_id) -- all images of one product
    # must land on the same side of the split.
    products = defaultdict(list)
    for rec in records:
        key = (rec.get("source"), rec.get("product_id"))
        products[key].append(rec)

    print(f"{len(products)} distinct products")

    # Stratify by (source, gender) so each brand/gender combo is
    # represented proportionally in both splits.
    strata = defaultdict(list)
    for key, recs in products.items():
        gender = recs[0].get("gender") or "UNKNOWN"
        source = recs[0].get("source") or "UNKNOWN"
        strata[(source, gender)].append(key)

    rng = random.Random(SEED)
    train_products, val_products = [], []
    for stratum_key, product_keys in strata.items():
        product_keys = sorted(product_keys)  # deterministic order before shuffle
        rng.shuffle(product_keys)
        n_val = max(1, round(len(product_keys) * VAL_FRACTION)) if len(product_keys) > 1 else 0
        val_products.extend(product_keys[:n_val])
        train_products.extend(product_keys[n_val:])

    print(f"Products: {len(train_products)} train / {len(val_products)} validation")

    for d in (TRAIN_DIR, VAL_DIR):
        d.mkdir(parents=True, exist_ok=True)

    def write_split(product_keys, image_dir, manifest_path):
        manifest_records = []
        copied = 0
        for key in product_keys:
            for rec in products[key]:
                src = RAW_IMAGES_DIR / rec["filename"]
                dst = image_dir / rec["filename"]
                if not dst.exists():
                    shutil.copy2(src, dst)
                    copied += 1
                manifest_records.append(rec)
        with open(manifest_path, "w", encoding="utf-8") as f:
            for rec in manifest_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return len(manifest_records), copied

    train_images, train_copied = write_split(train_products, TRAIN_DIR, TRAIN_MANIFEST)
    val_images, val_copied = write_split(val_products, VAL_DIR, VAL_MANIFEST)

    print(f"\nTrain: {train_images} images ({train_copied} copied) -> {TRAIN_DIR}, manifest {TRAIN_MANIFEST}")
    print(f"Val:   {val_images} images ({val_copied} copied) -> {VAL_DIR}, manifest {VAL_MANIFEST}")

    # Sanity check: verify balance held within each split
    def gender_breakdown(image_dir_records):
        c = defaultdict(int)
        for rec in image_dir_records:
            c[rec.get("gender") or "UNKNOWN"] += 1
        return c

    print("\n=== Train gender distribution ===")
    for g, n in gender_breakdown([r for k in train_products for r in products[k]]).items():
        print(f"  {g}: {n}")
    print("=== Validation gender distribution ===")
    for g, n in gender_breakdown([r for k in val_products for r in products[k]]).items():
        print(f"  {g}: {n}")


if __name__ == "__main__":
    main()
