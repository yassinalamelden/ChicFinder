#!/usr/bin/env python3
"""
scripts/04_rebuild_embeddings.py
Encode all raw_images with the fine-tuned FashionCLIP model and
upsert products + embeddings into Supabase. Also uploads images to Storage.

Prerequisites:
  - models/fine_tuned_clip/ must exist (the fine-tuned weights)
  - data/metadata.json must exist (image-level metadata)
  - data/raw_images/ must contain the product images
  - SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env

Run from project root:
  python scripts/04_rebuild_embeddings.py
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Validate env before heavy imports
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
if not SUPABASE_URL or not SUPABASE_KEY:
    sys.exit("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")

DATA = Path("data")
IMAGES_DIR = DATA / "raw_images"
METADATA_FILE = DATA / "metadata.json"
MODEL_PATH = Path("models/fine_tuned_clip")

if not MODEL_PATH.exists():
    sys.exit(f"ERROR: Fine-tuned model not found at {MODEL_PATH}")
if not METADATA_FILE.exists():
    sys.exit(f"ERROR: {METADATA_FILE} not found")
if not IMAGES_DIR.exists():
    sys.exit(f"ERROR: {IMAGES_DIR} not found")

print(f"Fine-tuned model: {MODEL_PATH} ✅")
print(f"Images directory: {IMAGES_DIR} ✅")

# Heavy imports after validation
from supabase import create_client
from ai_engine.embeddings.encoder import FashionCLIPEncoder

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 1. Load metadata ---
print("\nLoading metadata...")
with open(METADATA_FILE, encoding="utf-8") as f:
    metadata: dict = json.load(f)
print(f"  {len(metadata)} image entries")

# --- 2. Load fine-tuned encoder ---
print("\nLoading fine-tuned FashionCLIP encoder...")
# Force the encoder to use the local fine-tuned model
os.environ["CLIP_MODEL_PATH"] = str(MODEL_PATH)
encoder = FashionCLIPEncoder()
print("  Encoder ready ✅")

# --- 3. Upsert products ---
print("\nUpserting products to Supabase...")
products_map: dict[str, dict] = {}
for image_key, entry in metadata.items():
    pid = entry.get("product_id", image_key)
    if pid not in products_map:
        products_map[pid] = {
            "product_id": pid,
            "title": entry.get("title"),
            "brand": entry.get("brand"),
            "category": entry.get("category"),
            "price": entry.get("price"),
            "product_url": entry.get("product_url"),
            "description": entry.get("description"),
            "availability": entry.get("availability", "InStock"),
        }

product_list = list(products_map.values())
BATCH = 100
for i in tqdm(range(0, len(product_list), BATCH), desc="Products"):
    supabase.table("products").upsert(
        product_list[i : i + BATCH], on_conflict="product_id"
    ).execute()

# Fetch DB IDs
result = supabase.table("products").select("id, product_id").execute()
product_id_map: dict[str, int] = {r["product_id"]: r["id"] for r in result.data}
print(f"  {len(product_id_map)} products upserted ✅")

# --- 4. Encode images and upsert embeddings ---
print("\nEncoding images and upserting embeddings...")
image_files = sorted(IMAGES_DIR.glob("*.jpg")) + sorted(IMAGES_DIR.glob("*.png"))
print(f"  Found {len(image_files)} images")

embeddings_batch = []
EMB_BATCH = 50
skipped = 0

for img_path in tqdm(image_files, desc="Encoding"):
    image_key = img_path.stem  # filename without extension
    entry = metadata.get(image_key, {})
    pid = entry.get("product_id", image_key)
    db_id = product_id_map.get(pid)
    if db_id is None:
        skipped += 1
        continue

    try:
        with open(img_path, "rb") as f:
            img_bytes = f.read()
        vector = encoder.encode(img_bytes)
    except Exception as exc:
        print(f"\n  WARN: could not encode {img_path.name}: {exc}")
        skipped += 1
        continue

    embeddings_batch.append({
        "product_id": db_id,
        "image_filename": image_key,
        "embedding": vector.tolist(),
    })

    if len(embeddings_batch) >= EMB_BATCH:
        supabase.table("embeddings").upsert(
            embeddings_batch,
            on_conflict="product_id,image_filename",
        ).execute()
        embeddings_batch = []

# Flush remaining
if embeddings_batch:
    supabase.table("embeddings").upsert(
        embeddings_batch,
        on_conflict="product_id,image_filename",
    ).execute()

print(f"  Embeddings upserted. Skipped: {skipped}")

# --- 5. Upload images to Supabase Storage ---
print("\nUploading images to Supabase Storage (bucket: product-images)...")
for img_path in tqdm(image_files, desc="Uploading images"):
    with open(img_path, "rb") as f:
        img_bytes = f.read()
    content_type = "image/png" if img_path.suffix == ".png" else "image/jpeg"
    try:
        supabase.storage.from_("product-images").upload(
            img_path.name, img_bytes, {"content-type": content_type, "upsert": "true"}
        )
    except Exception as exc:
        if "already exists" not in str(exc).lower():
            print(f"\n  WARN: {img_path.name} -- {exc}")

print("\n✅ Migration complete!")
print(f"  Products  : {len(product_id_map)}")
print(f"  Images    : {len(image_files)}")
print(f"  Skipped   : {skipped}")
