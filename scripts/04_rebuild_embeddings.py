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

import numpy as np
from dotenv import load_dotenv
from PIL import Image
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

ENCODE_BATCH = 32   # images per forward pass (CPU-optimised)
EMB_BATCH = 50      # Supabase upsert batch size

if not MODEL_PATH.exists():
    sys.exit(f"ERROR: Fine-tuned model not found at {MODEL_PATH}")
if not METADATA_FILE.exists():
    sys.exit(f"ERROR: {METADATA_FILE} not found")
if not IMAGES_DIR.exists():
    sys.exit(f"ERROR: {IMAGES_DIR} not found")

print(f"Fine-tuned model : {MODEL_PATH} [OK]")
print(f"Images directory : {IMAGES_DIR} [OK]")

# Heavy imports after validation
import torch
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
os.environ["CLIP_MODEL_PATH"] = str(MODEL_PATH)
encoder = FashionCLIPEncoder()
print(f"  Encoder ready [OK]  (device={encoder._device})")

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
for i in tqdm(range(0, len(product_list), 100), desc="Products"):
    supabase.table("products").upsert(
        product_list[i : i + 100], on_conflict="product_id"
    ).execute()

# Fetch DB IDs — paginate to avoid the default 1000-row limit
product_id_map: dict[str, int] = {}
page_size = 1000
offset = 0
while True:
    page = (
        supabase.table("products")
        .select("id, product_id")
        .range(offset, offset + page_size - 1)
        .execute()
    )
    for r in page.data:
        product_id_map[r["product_id"]] = r["id"]
    if len(page.data) < page_size:
        break
    offset += page_size
print(f"  {len(product_id_map)} products upserted [OK]")

# --- 4. Batch-encode images and upsert embeddings ---
print(f"\nEncoding images (batch={ENCODE_BATCH}) and upserting embeddings...")
image_files = sorted(IMAGES_DIR.glob("*.jpg")) + sorted(IMAGES_DIR.glob("*.png"))
print(f"  Found {len(image_files)} images")

embeddings_buffer: list[dict] = []
skipped = 0
total_encoded = 0


def _flush_embeddings(buf: list[dict]) -> None:
    for i in range(0, len(buf), EMB_BATCH):
        supabase.table("embeddings").upsert(
            buf[i : i + EMB_BATCH],
            on_conflict="product_id,image_filename",
        ).execute()


for batch_start in tqdm(range(0, len(image_files), ENCODE_BATCH), desc="Encoding batches"):
    batch_files = image_files[batch_start : batch_start + ENCODE_BATCH]

    # Resolve metadata for each file in this batch
    batch_pil: list[Image.Image] = []
    batch_keys: list[tuple[str, int]] = []   # (image_key, db_id)

    for img_path in batch_files:
        image_key = img_path.stem
        entry = metadata.get(image_key, {})
        pid = entry.get("product_id", image_key)
        db_id = product_id_map.get(pid)
        if db_id is None:
            skipped += 1
            continue
        try:
            batch_pil.append(Image.open(img_path).convert("RGB"))
            batch_keys.append((image_key, db_id))
        except Exception as exc:
            print(f"\n  WARN: cannot load {img_path.name}: {exc}")
            skipped += 1

    if not batch_pil:
        continue

    # Batch forward pass
    try:
        inputs = encoder._processor(images=batch_pil, return_tensors="pt", padding=True)
        inputs = {k: v.to(encoder._device) for k, v in inputs.items()}
        with torch.no_grad():
            vision_out = encoder._model.vision_model(**inputs)
            features = encoder._model.visual_projection(vision_out.pooler_output)
        vectors = features.cpu().numpy().astype(np.float32)  # (N, 512)

        for i, (image_key, db_id) in enumerate(batch_keys):
            vector = encoder._normalize(vectors[i])
            embeddings_buffer.append({
                "product_id": db_id,
                "image_filename": image_key,
                "embedding": vector.tolist(),
            })
        total_encoded += len(batch_keys)

    except Exception as exc:
        print(f"\n  WARN: batch encode failed: {exc}")
        skipped += len(batch_pil)
        continue

    # Flush to Supabase every ~200 embeddings
    if len(embeddings_buffer) >= 200:
        _flush_embeddings(embeddings_buffer)
        embeddings_buffer = []

# Final flush
if embeddings_buffer:
    _flush_embeddings(embeddings_buffer)

print(f"  Encoded: {total_encoded}  |  Skipped: {skipped}")

# --- 5. Upload images to Supabase Storage ---
print("\nUploading images to Supabase Storage (bucket: product-images)...")
upload_errors = 0
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
            upload_errors += 1
            if upload_errors <= 5:
                print(f"\n  WARN: {img_path.name} -- {exc}")

print("\nMigration complete!")
print(f"  Products  : {len(product_id_map)}")
print(f"  Encoded   : {total_encoded}")
print(f"  Skipped   : {skipped}")
print(f"  Images    : {len(image_files)}  (upload errors: {upload_errors})")
