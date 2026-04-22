import json
import os
import requests
import time
import datetime

# Setup paths
INPUT_JSONL = "data/metadata.jsonl"
OUTPUT_IMAGE_DIR = "data/raw_images"
OUTPUT_METADATA = "data/metadata.json"

# Ensure the image directory exists
os.makedirs(OUTPUT_IMAGE_DIR, exist_ok=True)

final_metadata = {}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

print("Scanning dataset to calculate total images...")

# 1. Quick First Pass: Count exactly how many images we expect to process
total_expected_images = 0
with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
    for line in f:
        if not line.strip(): continue
        item = json.loads(line)
        image_urls = item.get('image_urls', [])
        total_expected_images += len(image_urls[:4]) # We are slicing at 4

print(f"Found {total_expected_images} total images to process. Starting download...\n")

# 2. Setup counters and timers
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
        
        # Loop through a MAXIMUM of 4 images for this product
        for idx, url in enumerate(image_urls[:4]):
            filename = f"{brand}_{product_id}_{idx}.jpg"
            filepath = os.path.join(OUTPUT_IMAGE_DIR, filename)
            
            # Download the image if we haven't already
            if not os.path.exists(filepath):
                try:
                    response = requests.get(url, headers=headers, stream=True, timeout=10)
                    if response.status_code == 200:
                        with open(filepath, 'wb') as img_file:
                            for chunk in response.iter_content(1024):
                                img_file.write(chunk)
                                
                        total_images_downloaded += 1
                        status = "Downloaded"
                    else:
                        status = f"Failed (Status: {response.status_code})"
                except Exception as e:
                    status = f"Error"
            else:
                status = "Skipped (Exists)"
            
            # Add this specific image to the final metadata dictionary
            # FIX APPLIED HERE: Stripping the .jpg extension from the key!
            final_metadata[filename.replace('.jpg', '')] = {
                "product_id": product_id,
                "title": item.get('title'),
                "brand": item.get('brand'),
                "category": item.get('category'),
                "subcategory": item.get('subcategory'),
                "price": item.get('price'),
                "product_url": item.get('product_url')
            }
            
            # 3. Calculate ETA
            processed_images += 1
            elapsed_time = time.time() - start_time
            avg_time_per_image = elapsed_time / processed_images
            images_left = total_expected_images - processed_images
            eta_seconds = int(images_left * avg_time_per_image)
            
            # Format the ETA beautifully (e.g., 0:04:12)
            eta_formatted = str(datetime.timedelta(seconds=eta_seconds))
            
            # Print the live stats
            print(f"[{processed_images}/{total_expected_images}] {status}: {filename} | ETA: {eta_formatted}")
            
            # Small delay to avoid overloading the servers
            time.sleep(0.1)

# Save the final metadata dictionary
with open(OUTPUT_METADATA, 'w', encoding='utf-8') as f:
    json.dump(final_metadata, f, indent=4)

total_time = str(datetime.timedelta(seconds=int(time.time() - start_time)))

print(f"\n✅ Done!")
print(f"Total time elapsed: {total_time}")
print(f"Successfully downloaded {total_images_downloaded} new images.")
print(f"Saved {len(final_metadata)} total entries to {OUTPUT_METADATA}.")