
import os
import json
from PIL import Image
from pathlib import Path

IMAGE_DIR = "data/raw_images"
METADATA_FILE = "data/metadata.json"

def fix_extensions():
    if not os.path.exists(IMAGE_DIR):
        print(f"Directory {IMAGE_DIR} not found.")
        return

    # Load metadata if exists
    metadata = {}
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    
    new_metadata = {}
    files = [f for f in os.listdir(IMAGE_DIR) if os.path.isfile(os.path.join(IMAGE_DIR, f))]
    
    print(f"Scanning {len(files)} files in {IMAGE_DIR}...")
    
    renamed_count = 0
    errors = 0
    
    for filename in files:
        filepath = os.path.join(IMAGE_DIR, filename)
        try:
            with Image.open(filepath) as img:
                actual_format = img.format.lower() # e.g., 'jpeg', 'png', 'webp'
                
            if actual_format == 'jpeg':
                ext = '.jpg'
            else:
                ext = f'.{actual_format}'
            
            current_ext = Path(filename).suffix.lower()
            
            if current_ext != ext:
                new_filename = Path(filename).stem + ext
                new_filepath = os.path.join(IMAGE_DIR, new_filename)
                
                # If target exists, just remove the current one (duplicate)
                if os.path.exists(new_filepath) and new_filepath != filepath:
                    os.remove(filepath)
                    filename = new_filename # Use the existing correct one for metadata
                else:
                    os.rename(filepath, new_filepath)
                    filename = new_filename
                renamed_count += 1
            
            # Rebuild metadata entry
            base_id = Path(filename).stem
            # try to find old metadata if it was under a different key
            old_keys = [base_id, base_id + ".jpg", base_id.replace('.jpg', '')]
            item_data = {}
            for k in old_keys:
                if k in metadata:
                    item_data = metadata[k]
                    break
            
            if not item_data:
                # If not found in original metadata, we might have a gap
                continue

            item_data["filename"] = filename
            new_metadata[base_id] = item_data
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            try:
                os.remove(filepath)
            except OSError:
                pass
            errors += 1

    # Save corrected metadata
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_metadata, f, indent=4)
    
    print(f"Standardization complete.")
    print(f"Renamed/Fixed: {renamed_count}")
    print(f"Errors: {errors}")
    print(f"Total entries in metadata: {len(new_metadata)}")

if __name__ == "__main__":
    fix_extensions()
