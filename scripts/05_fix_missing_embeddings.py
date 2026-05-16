#!/usr/bin/env python3
"""
scripts/05_fix_missing_embeddings.py
Re-encode images that are missing embeddings in Supabase (skipped due to
pagination bug in the previous migration run).

Fetches all existing embedding image_filenames, then encodes only the
images not yet in the embeddings table.

Run from project root:
  python scripts/05_fix_missing_embeddings.py
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

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
if not SUPABASE_URL or not SUPABASE_KEY:
    sys.exit("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")

DATA = Path("data")
IMAGES_DIR = DATA / "raw_images"
METADATA_FILE = DATA / "metadata.json"
MODEL_PATH = Path("models/fine_tuned_clip")

ENCODE_BATCH = 32
EMB_BATCH = 50

if not MODEL_PATH.exists():
    sys.exit(f"ERROR: Fine-tuned model not found at {MODEL_PATH}")

import torch
from supabase import create_client
from ai_engine.embeddings.encoder import FashionCLIPEncoder

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Load metadata ---
print("Loading metadata...")
with open(METADATA_FILE, encoding="utf-8") as f:
    metadata: dict = json.load(f)

# --- Fetch all product DB IDs (paginated) ---
print("Fetching all product IDs from Supabase...")
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
print(f"  {len(product_id_map)} products in DB")

# --- Fetch existing embedding filenames (to skip already-encoded images) ---
print("Fetching existing embedding filenames...")
existing: set[str] = set()
offset = 0
while True:
    page = (
        supabase.table("embeddings")
        .select("image_filename")
        .range(offset, offset + page_size - 1)
        .execute()
    )
    for r in page.data:
        existing.add(r["image_filename"])
    if len(page.data) < page_size:
        break
    offset += page_size
print(f"  {len(existing)} embeddings already in DB")

# --- Find images that need encoding ---
all_images = sorted(IMAGES_DIR.glob("*.jpg")) + sorted(IMAGES_DIR.glob("*.png"))
missing = [p for p in all_images if p.stem not in existing]
print(f"  {len(missing)} images need embedding")

if not missing:
    print("Nothing to do — all images are already embedded.")
    sys.exit(0)

# --- Load encoder ---
print("\nLoading fine-tuned FashionCLIP encoder...")
os.environ["CLIP_MODEL_PATH"] = str(MODEL_PATH)
encoder = FashionCLIPEncoder()
print(f"  Encoder ready [OK]  (device={encoder._device})")

# --- Batch encode and upsert ---
print(f"\nEncoding {len(missing)} missing images (batch={ENCODE_BATCH})...")

embeddings_buffer: list[dict] = []
skipped = 0
total_encoded = 0


def _flush(buf: list[dict]) -> None:
    for i in range(0, len(buf), EMB_BATCH):
        supabase.table("embeddings").upsert(
            buf[i : i + EMB_BATCH],
            on_conflict="product_id,image_filename",
        ).execute()


for batch_start in tqdm(range(0, len(missing), ENCODE_BATCH), desc="Encoding"):
    batch_files = missing[batch_start : batch_start + ENCODE_BATCH]

    batch_pil: list[Image.Image] = []
    batch_keys: list[tuple[str, int]] = []

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

    try:
        inputs = encoder._processor(images=batch_pil, return_tensors="pt", padding=True)
        inputs = {k: v.to(encoder._device) for k, v in inputs.items()}
        with torch.no_grad():
            vision_out = encoder._model.vision_model(**inputs)
            features = encoder._model.visual_projection(vision_out.pooler_output)
        vectors = features.cpu().numpy().astype(np.float32)

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

    if len(embeddings_buffer) >= 200:
        _flush(embeddings_buffer)
        embeddings_buffer = []

if embeddings_buffer:
    _flush(embeddings_buffer)

print(f"\nDone! Encoded: {total_encoded}  |  Skipped: {skipped}")
