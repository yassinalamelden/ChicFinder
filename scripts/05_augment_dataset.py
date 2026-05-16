"""
scripts/05_augment_dataset.py

Augments underrepresented categories to reach a target count per category.
Generates new image files + metadata entries without touching existing data.

Strategy per category below target:
  - RandomHorizontalFlip
  - RandomRotation (±10 degrees)
  - ColorJitter (brightness, contrast, saturation)
  - RandomResizedCrop (scale 0.85-1.0)

Usage:
    python scripts/05_augment_dataset.py
    python scripts/05_augment_dataset.py --target 1000
    python scripts/05_augment_dataset.py --target 1000 --dry-run
"""

import argparse
import json
import math
import random
import logging
from collections import defaultdict, Counter
from pathlib import Path

from PIL import Image
from tqdm import tqdm

try:
    import torchvision.transforms as T
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
logger = logging.getLogger("augment_dataset")

ROOT          = Path(__file__).resolve().parent.parent
METADATA_JSON = ROOT / "data" / "metadata.json"
METADATA_JSONL= ROOT / "data" / "metadata.jsonl"
IMAGES_DIR    = ROOT / "data" / "raw_images"

CATEGORIES = ["Tops", "Bottoms", "Dresses", "Footwear",
              "Outerwear", "Accessories", "Underwear"]


# ── Augmentation pipeline ─────────────────────────────────────────────────────

def build_augmenter():
    if not HAS_TORCH:
        raise ImportError("pip install torchvision")
    return T.Compose([
        T.RandomHorizontalFlip(p=0.5),
        T.RandomRotation(degrees=10),
        T.ColorJitter(brightness=0.25, contrast=0.25, saturation=0.20, hue=0.04),
        T.RandomResizedCrop(size=(512, 512), scale=(0.85, 1.0), ratio=(0.9, 1.1)),
    ])


def augment_image(img: Image.Image, augmenter) -> Image.Image:
    tensor = T.ToTensor()(img)
    augmented = augmenter(tensor)
    return T.ToPILImage()(augmented)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=1000,
                        help="Target item count per category (default: 1000)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print plan without writing any files")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    # ── Load metadata ─────────────────────────────────────────────────────────
    logger.info("Loading metadata from %s", METADATA_JSON)
    with open(METADATA_JSON, encoding="utf-8") as f:
        metadata = json.load(f)

    by_category = defaultdict(list)
    for key, item in metadata.items():
        cat = item.get("category", "")
        if cat in CATEGORIES:
            img_path = IMAGES_DIR / item["filename"]
            if img_path.exists():
                by_category[cat].append((key, item, img_path))

    # ── Print current counts and plan ─────────────────────────────────────────
    logger.info("\nCurrent counts vs target (%d):", args.target)
    logger.info("  %-15s %8s %8s %10s", "Category", "Current", "Target", "To Add")
    logger.info("  " + "-" * 45)

    plan = {}
    for cat in CATEGORIES:
        current = len(by_category[cat])
        needed  = max(0, args.target - current)
        plan[cat] = needed
        status = "OK" if needed == 0 else f"+{needed}"
        logger.info("  %-15s %8d %8d %10s", cat, current, args.target, status)

    total_new = sum(plan.values())
    logger.info("\n  Total new images to generate: %d", total_new)

    if args.dry_run:
        logger.info("Dry run — no files written.")
        return

    if total_new == 0:
        logger.info("All categories already at or above target. Nothing to do.")
        return

    # ── Build augmenter ───────────────────────────────────────────────────────
    augmenter = build_augmenter()
    new_metadata_entries = {}

    # ── Augment each underrepresented category ────────────────────────────────
    for cat in CATEGORIES:
        needed = plan[cat]
        if needed == 0:
            continue

        pool = by_category[cat]
        logger.info("\nAugmenting %s: need %d more from %d originals", cat, needed, len(pool))

        # How many augmented variants per original image
        aug_per_image = math.ceil(needed / len(pool))

        generated = 0
        bar = tqdm(total=needed, desc=f"  {cat}", unit="img")

        random.shuffle(pool)

        for key, item, img_path in pool:
            if generated >= needed:
                break

            try:
                original = Image.open(img_path).convert("RGB")
            except Exception as e:
                logger.warning("  Skipping %s: %s", img_path.name, e)
                continue

            stem = img_path.stem
            ext  = img_path.suffix.lower() or ".jpg"

            for n in range(1, aug_per_image + 1):
                if generated >= needed:
                    break

                # Generate unique filename
                new_filename = f"{stem}_aug{n}{ext}"
                new_path = IMAGES_DIR / new_filename
                new_key  = f"{stem}_aug{n}"

                # Skip if already exists (resumable)
                if new_path.exists() and new_key in metadata:
                    generated += 1
                    bar.update(1)
                    continue

                # Apply augmentation and save
                try:
                    aug_img = augment_image(original, augmenter)
                    aug_img.save(new_path, quality=92)
                except Exception as e:
                    logger.warning("  Augmentation failed for %s: %s", stem, e)
                    continue

                # Build metadata entry
                new_metadata_entries[new_key] = {
                    "product_id"  : f"{item['product_id']}_aug{n}",
                    "title"       : item.get("title"),
                    "brand"       : item.get("brand"),
                    "category"    : item.get("category"),
                    "subcategory" : item.get("subcategory"),
                    "price"       : item.get("price"),
                    "product_url" : item.get("product_url"),
                    "filename"    : new_filename,
                    "source"      : item.get("source"),
                    "gender"      : item.get("gender"),
                }

                generated += 1
                bar.update(1)

        bar.close()
        logger.info("  Generated %d images for %s", generated, cat)

    # ── Save updated metadata ─────────────────────────────────────────────────
    if not new_metadata_entries:
        logger.info("No new entries generated.")
        return

    logger.info("\nSaving %d new entries to metadata.json...", len(new_metadata_entries))
    metadata.update(new_metadata_entries)
    with open(METADATA_JSON, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info("Appending to metadata.jsonl...")
    with open(METADATA_JSONL, "a", encoding="utf-8") as f:
        for entry in new_metadata_entries.values():
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ── Final summary ─────────────────────────────────────────────────────────
    final_counts = Counter(v["category"] for v in metadata.values())
    logger.info("\nFinal dataset counts:")
    for cat in CATEGORIES:
        logger.info("  %-15s %d", cat, final_counts.get(cat, 0))
    logger.info("  %-15s %d", "TOTAL", sum(final_counts.values()))
    logger.info("\nDone. Run scripts/02_build_faiss_index.py to rebuild the index.")


if __name__ == "__main__":
    main()
