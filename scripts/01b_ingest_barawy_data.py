import json
import os
import requests
import time
import datetime

# Setup paths
INPUT_JSONL = "data/metadata.jsonl"
OUTPUT_IMAGE_DIR = "data/raw_images"
OUTPUT_METADATA = "data/metadata.json"

os.makedirs(OUTPUT_IMAGE_DIR, exist_ok=True)

final_metadata = {}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# Detect format by peeking at the first record
with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            first_record = json.loads(line)
            break

HAS_IMAGE_URLS = 'image_urls' in first_record

if HAS_IMAGE_URLS:
    # ── OLD FORMAT: download images from image_urls ──────────────────────────
    print("Detected format: image_urls present — downloading images...\n")

    total_expected_images = 0
    with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            item = json.loads(line)
            total_expected_images += len(item.get('image_urls', [])[:4])

    print(f"Found {total_expected_images} total images to process. Starting download...\n")

    processed_images = 0
    total_images_downloaded = 0
    start_time = time.time()

    with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            item = json.loads(line)

            product_id = item.get('product_id')
            brand = item.get('source', 'unknown').lower()
            image_urls = item.get('image_urls', [])

            for idx, url in enumerate(image_urls[:4]):
                ext = os.path.splitext(url.split('?')[0])[1].lower()
                if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
                    ext = '.jpg'

                filename = f"{brand}_{product_id}_{idx}{ext}"
                filepath = os.path.join(OUTPUT_IMAGE_DIR, filename)

                if not os.path.exists(filepath):
                    try:
                        response = requests.get(url, headers=headers, stream=True, timeout=10)
                        if response.status_code == 200:
                            content_type = response.headers.get('Content-Type', '')
                            if 'image/webp' in content_type and not filename.endswith('.webp'):
                                filename = filename.rsplit('.', 1)[0] + '.webp'
                                filepath = os.path.join(OUTPUT_IMAGE_DIR, filename)

                            with open(filepath, 'wb') as img_file:
                                for chunk in response.iter_content(1024):
                                    img_file.write(chunk)

                            total_images_downloaded += 1
                            status = "Downloaded"
                        else:
                            status = f"Failed (Status: {response.status_code})"
                    except Exception:
                        status = "Error"
                else:
                    status = "Skipped (Exists)"

                final_metadata[os.path.splitext(filename)[0]] = {
                    "product_id": product_id,
                    "title": item.get('title'),
                    "brand": item.get('brand'),
                    "category": item.get('category'),
                    "subcategory": item.get('subcategory'),
                    "price": item.get('price'),
                    "product_url": item.get('product_url'),
                    "filename": filename,
                    "source": item.get('source'),
                    "gender": item.get('gender'),
                }

                processed_images += 1
                elapsed_time = time.time() - start_time
                avg_time_per_image = elapsed_time / processed_images
                images_left = total_expected_images - processed_images
                eta_seconds = int(images_left * avg_time_per_image)
                eta_formatted = str(datetime.timedelta(seconds=eta_seconds))
                print(f"[{processed_images}/{total_expected_images}] {status}: {filename} | ETA: {eta_formatted}")
                time.sleep(0.1)

    total_time = str(datetime.timedelta(seconds=int(time.time() - start_time)))
    print(f"\n✅ Done! Downloaded {total_images_downloaded} new images in {total_time}.")

else:
    # ── NEW FORMAT: filename already set, just convert JSONL → JSON ──────────
    print("Detected format: pre-processed (filename present, no image_urls).")
    print("Converting metadata.jsonl → metadata.json (no image download)...\n")

    total = 0
    with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            item = json.loads(line)
            filename = item.get('filename', '')
            key = os.path.splitext(filename)[0]
            final_metadata[key] = {
                "product_id": item.get('product_id'),
                "title": item.get('title'),
                "brand": item.get('brand'),
                "category": item.get('category'),
                "subcategory": item.get('subcategory'),
                "price": item.get('price'),
                "product_url": item.get('product_url'),
                "filename": filename,
                "source": item.get('source'),
                "gender": item.get('gender'),
            }
            total += 1
            if total % 1000 == 0:
                print(f"  Processed {total} records...")

    print(f"\n✅ Converted {total} records.")
    print(f"⚠️  Images are NOT downloaded — place image files in {OUTPUT_IMAGE_DIR}/")

# Save metadata.json
with open(OUTPUT_METADATA, 'w', encoding='utf-8') as f:
    json.dump(final_metadata, f, indent=4)

print(f"Saved {len(final_metadata)} entries to {OUTPUT_METADATA}.")