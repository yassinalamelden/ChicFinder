import sys
import os
# Adds the root directory (ChicFinder-1) to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import faiss
import json
import numpy as np
from ai_engine.embeddings.encoder import get_encoder

# 1. Load the "Brain"
index = faiss.read_index("data/embeddings.index")
with open("data/metadata.json", "r", encoding="utf-8") as f:
    metadata = json.load(f)

# Load the mapping file
with open("data/index_to_image_id.json", "r", encoding="utf-8") as f:
    index_mapping = json.load(f)

# 2. Get a vector for the test image
encoder = get_encoder()
with open("test_shirt.jpg", "rb") as f:
    query_vector = encoder.encode(f.read())

# 3. Search for matches (Asking for 15 so we have enough leftovers after filtering)
D, I = index.search(np.expand_dims(query_vector, axis=0), 15)

print("\n--- Unique Search Results for 'test_shirt.jpg' ---")

flat_indices = I.flatten()

# --- DEDUPLICATION FILTER SETUP ---
seen_product_ids = set()
unique_matches_found = 0
desired_results = 5

for idx in flat_indices:
    # Stop searching once we have 5 completely unique products
    if unique_matches_found >= desired_results:
        break

    str_idx = str(int(idx))
    
    # Get the real item ID from the mapping
    if str_idx in index_mapping:
        real_id = index_mapping[str_idx]
        clean_id = real_id.replace(".jpg", "")

        # Look up the metadata
        if clean_id in metadata:
            item = metadata[clean_id]
            product_id = item.get('product_id', 'Unknown ID')
            
            # --- THE FILTER LOGIC ---
            # If we haven't seen this product_id yet, print it and remember it!
            if product_id not in seen_product_ids:
                seen_product_ids.add(product_id)
                
                brand = item.get('brand', 'Unknown Brand')
                title = item.get('title', 'Unknown Title')
                
                print(f"Match {unique_matches_found + 1}: {brand} - {title} (ID: {product_id})")
                unique_matches_found += 1