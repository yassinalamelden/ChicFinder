#!/usr/bin/env python3
"""
One-time migration: FAISS + JSON files -> Supabase (products, embeddings, images).

Prerequisites:
  - pip install supabase faiss-cpu tqdm Pillow
  - SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY set in .env
  - data/metadata.json, data/metadata.jsonl, data/embeddings.index,
    data/index_to_image_id.json, data/raw_images/ all present locally

Run:
  python scripts/03_migrate_to_supabase.py
"""

import json
import os
import sys
from pathlib import Path

import faiss
import numpy as np
from dotenv import load_dotenv
from supabase import create_client
from tqdm import tqdm

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
if not SUPABASE_URL or not SUPABASE_KEY:
    sys.exit("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

DATA = Path("data")


# --- 1. Load local data ------------------------------------------------------

print("Loading local data files...")
with open(DATA / "metadata.json", encoding="utf-8") as f:
    metadata: dict = json.load(f)

product_details: dict = {}
with open(DATA / "metadata.jsonl", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            r = json.loads(line)
            product_details[r["product_id"]] = r

with open(DATA / "index_to_image_id.json", encoding="utf-8") as f:
    index_to_image_id: dict = json.load(f)  # {"0": "tomato_123_0", ...}

print(f"  {len(metadata)} image entries, {len(product_details)} product detail records")
print(f"  {len(index_to_image_id)} FAISS index entries")

faiss_index = faiss.read_index(str(DATA / "embeddings.index"))
print(f"  FAISS index: {faiss_index.ntotal} vectors")


# --- 2. Insert products -------------------------------------------------------

print("\nInserting products...")
products_to_insert: dict[str, dict] = {}
for image_key, entry in metadata.items():
    pid = entry.get("product_id", image_key)
    if pid not in products_to_insert:
        detail = product_details.get(pid, {})
        products_to_insert[pid] = {
            "product_id": pid,
            "title": entry.get("title"),
            "brand": entry.get("brand"),
            "category": entry.get("category"),
            "price": entry.get("price"),
            "product_url": entry.get("product_url"),
            "description": detail.get("description"),
            "availability": detail.get("availability", "InStock"),
        }

product_list = list(products_to_insert.values())
BATCH = 100
for i in tqdm(range(0, len(product_list), BATCH), desc="Products"):
    supabase.table("products").upsert(
        product_list[i : i + BATCH], on_conflict="product_id"
    ).execute()

# Fetch db IDs
result = supabase.table("products").select("id, product_id").execute()
product_id_map: dict[str, int] = {r["product_id"]: r["id"] for r in result.data}
print(f"  Inserted/updated {len(product_id_map)} products")


# --- 3. Insert embeddings -----------------------------------------------------

print("\nInserting embeddings...")
embeddings_to_insert = []
for faiss_idx_str, image_key in index_to_image_id.items():
    faiss_idx = int(faiss_idx_str)
    # index_to_image_id values may include ".jpg"; strip it to match metadata keys
    meta_key = image_key[:-4] if image_key.endswith(".jpg") else image_key
    entry = metadata.get(meta_key, {})
    pid = entry.get("product_id", meta_key)
    db_id = product_id_map.get(pid)
    if db_id is None:
        continue
    vector: list[float] = faiss_index.reconstruct(faiss_idx).tolist()
    embeddings_to_insert.append({
        "product_id": db_id,
        "image_filename": meta_key,
        "embedding": vector,
    })

EMB_BATCH = 50  # smaller batches — vectors are large
for i in tqdm(range(0, len(embeddings_to_insert), EMB_BATCH), desc="Embeddings"):
    supabase.table("embeddings").upsert(
        embeddings_to_insert[i : i + EMB_BATCH],
        on_conflict="product_id,image_filename",
    ).execute()
print(f"  Inserted {len(embeddings_to_insert)} embedding rows")


# --- 4. Upload images to Supabase Storage ------------------------------------

print("\nUploading images to Supabase Storage (bucket: product-images)...")
images_dir = DATA / "raw_images"
image_files = list(images_dir.glob("*.jpg"))
print(f"  Found {len(image_files)} images")

for img_path in tqdm(image_files, desc="Uploading images"):
    storage_path = img_path.name  # e.g. "tomato_123_0.jpg"
    with open(img_path, "rb") as f:
        img_bytes = f.read()
    try:
        supabase.storage.from_("product-images").upload(
            storage_path, img_bytes, {"content-type": "image/jpeg", "upsert": "true"}
        )
    except Exception as exc:
        # Skip if already exists
        if "already exists" not in str(exc).lower():
            print(f"\n  WARN: {img_path.name} -- {exc}")

print("\nMigration complete!")
print(f"  Products : {len(product_id_map)}")
print(f"  Embeddings: {len(embeddings_to_insert)}")
print(f"  Images   : {len(image_files)}")
