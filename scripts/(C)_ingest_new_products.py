"""
scripts/(C)_ingest_new_products.py
====================================
Downloads images for newly-scraped products (data/clean/all_products.jsonl,
produced by scrapers/merge_and_clean.py) and appends per-image records to
data/metadata.jsonl in the same expanded/per-image schema the rest of the
dataset already uses.

Parallel downloads (ThreadPoolExecutor) -- serial requests were far too slow
(~1-8 images/30s observed, i.e. many hours for the full run). Metadata is
flushed to disk incrementally every FLUSH_EVERY completed images, so a
stop/crash never loses more than one batch of progress -- re-running is
always safe (existing image files are skipped, not re-downloaded).

Gender assignment:
  - Uses the record's own "gender" field when present (currently only the
    OR scraper captures this per-product, since OR mixes Men's/Women's).
  - Falls back to a brand-level default for single-gender brands.
  - Left blank if neither applies (logged, not silently guessed).

Mirrors scripts/01b_ingest_barawy_data.py's conventions: max 4 images per
product, filename = f"{source}_{product_id}_{idx}{ext}".

Backs up data/metadata.jsonl before appending (data/ is git-ignored --
no version-control safety net).

After running this, run scripts/(C)_sync_metadata_json.py to rebuild
data/metadata.json.

Usage:
  python scripts/(C)_ingest_new_products.py
"""

import json
import os
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

INPUT_JSONL = Path("data/clean/all_products.jsonl")
METADATA_JSONL = Path("data/metadata.jsonl")
RAW_IMAGES_DIR = Path("data/raw_images")

BRAND_GENDER_DEFAULTS = {
    "boheme": "Women",
    "solang": "Kids",
    "carrot": "Kids",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
MAX_WORKERS = 32
FLUSH_EVERY = 200


def build_tasks(products):
    """One task per image (capped at 4/product), each carrying the metadata
    needed to write its record once downloaded."""
    tasks = []
    skipped_no_gender = 0
    for item in products:
        source = (item.get("source") or "unknown").lower()
        product_id = item.get("product_id")
        gender = item.get("gender") or BRAND_GENDER_DEFAULTS.get(source) or ""
        if not gender:
            # Policy (established earlier in this dataset-cleanup pass):
            # ungendered products are dropped, not ingested with a blank
            # gender -- skip before even downloading, so this can't
            # regenerate the records a previous cleanup pass removed.
            skipped_no_gender += 1
            continue
        image_urls = item.get("image_urls") or []
        for idx, url in enumerate(image_urls[:4]):
            tasks.append({
                "url": url,
                "source": source,
                "product_id": product_id,
                "idx": idx,
                "gender": gender,
                "title": item.get("title"),
                "brand": item.get("brand"),
                "category": item.get("category"),
                "subcategory": item.get("subcategory"),
                "price": item.get("price"),
                "product_url": item.get("product_url"),
            })
    if skipped_no_gender:
        print(f"Skipping {skipped_no_gender} ungendered products entirely (not ingested)")
    return tasks


def download_one(task, session):
    """Downloads (or confirms already-downloaded) a single image. Returns a
    metadata record dict, or None on failure."""
    url = task["url"]
    ext = os.path.splitext(url.split("?")[0])[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        ext = ".jpg"
    filename = f"{task['source']}_{task['product_id']}_{task['idx']}{ext}"
    filepath = RAW_IMAGES_DIR / filename

    if not filepath.exists():
        try:
            resp = session.get(url, timeout=15, stream=True)
            if resp.status_code != 200:
                return None, "failed"
            content_type = resp.headers.get("Content-Type", "")
            if "image/webp" in content_type and not filename.endswith(".webp"):
                filename = filename.rsplit(".", 1)[0] + ".webp"
                filepath = RAW_IMAGES_DIR / filename
            with open(filepath, "wb") as img_file:
                for chunk in resp.iter_content(1024):
                    img_file.write(chunk)
            status = "downloaded"
        except Exception:
            return None, "failed"
    else:
        status = "existing"

    record = {
        "product_id": task["product_id"],
        "title": task["title"],
        "brand": task["brand"],
        "category": task["category"],
        "subcategory": task["subcategory"],
        "price": task["price"],
        "product_url": task["product_url"],
        "filename": filename,
        "source": task["source"],
        "gender": task["gender"],
        "product_type_fine": "Unknown",
        "product_type_group": "Other",
    }
    return record, status


def main():
    RAW_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    backup_path = METADATA_JSONL.with_suffix(".jsonl.bak2")
    if not backup_path.exists():
        shutil.copy2(METADATA_JSONL, backup_path)
        print(f"Backed up {METADATA_JSONL} -> {backup_path}")

    with open(INPUT_JSONL, "r", encoding="utf-8") as f:
        products = [json.loads(line) for line in f if line.strip()]

    # Every filename already logged in metadata.jsonl (from this script's
    # earlier runs, however many times it was restarted) -- never append a
    # second row for the same image.
    already_logged = set()
    with open(METADATA_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                already_logged.add(json.loads(line).get("filename"))

    tasks = build_tasks(products)
    print(f"Ingesting {len(products)} products / {len(tasks)} images "
          f"from {INPUT_JSONL} with {MAX_WORKERS} parallel workers "
          f"({len(already_logged)} filenames already logged)...")

    session = requests.Session()
    session.headers.update(HEADERS)

    downloaded = existing = failed = no_gender = 0
    pending_records = []
    start = time.time()

    def flush():
        nonlocal pending_records
        if not pending_records:
            return
        with open(METADATA_JSONL, "a", encoding="utf-8") as f:
            for rec in pending_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        pending_records = []

    pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    futures = {pool.submit(download_one, t, session): t for t in tasks}
    interrupted = False
    try:
        done = 0
        for future in as_completed(futures):
            record, status = future.result()
            done += 1
            if status == "downloaded":
                downloaded += 1
            elif status == "existing":
                existing += 1
            else:
                failed += 1

            if record is not None and record["filename"] not in already_logged:
                already_logged.add(record["filename"])
                if not record["gender"]:
                    no_gender += 1
                pending_records.append(record)

            if len(pending_records) >= FLUSH_EVERY:
                flush()

            if done % 500 == 0:
                elapsed = time.time() - start
                rate = done / elapsed if elapsed > 0 else 0
                remaining = (len(tasks) - done) / rate if rate > 0 else float("inf")
                print(f"  [{done}/{len(tasks)}] downloaded={downloaded} existing={existing} "
                      f"failed={failed} | {rate:.1f} img/s | ETA {remaining/60:.1f} min")
    except KeyboardInterrupt:
        # Ctrl+C: cancel every task that hasn't started yet and stop
        # immediately -- don't wait for the whole queue to drain. Requires
        # Python 3.9+ (cancel_futures).
        interrupted = True
        print("\nCtrl+C received -- pausing (cancelling queued downloads, "
              "letting in-flight ones finish)...")
        pool.shutdown(wait=True, cancel_futures=True)
    else:
        pool.shutdown(wait=True)

    flush()

    elapsed = time.time() - start
    print()
    if interrupted:
        print(f"PAUSED after {elapsed/60:.1f} min. downloaded={downloaded} existing={existing} failed={failed}")
        print("Progress is saved -- re-run this same command anytime to resume "
              "(already-downloaded images are skipped, not re-fetched).")
    else:
        print(f"Done in {elapsed/60:.1f} min. downloaded={downloaded} existing={existing} failed={failed}")
        if no_gender:
            print(f"WARNING: {no_gender} image records had no gender (no tag match, no brand default)")
        print()
        print("Next step: run scripts/(C)_sync_metadata_json.py to rebuild data/metadata.json")


if __name__ == "__main__":
    main()
