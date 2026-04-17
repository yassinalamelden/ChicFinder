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
with open("data/metadata.json", "r") as f:
    metadata = json.load(f)

# Load the mapping file
with open("data/index_to_image_id.json", "r") as f:
    index_mapping = json.load(f)

# 2. Get a vector for a "Black" image (ID 002 was black)
encoder = get_encoder()
with open("data/raw_images/002.jpg", "rb") as f:
    query_vector = encoder.encode(f.read())

# 3. Search the top 5 matches
# FAISS expects a 2D array
D, I = index.search(np.expand_dims(query_vector, axis=0), 5)

print("\n--- Search Results for 'Black Square' ---")

# We use .flatten() to turn [] into a 1D array
flat_indices = I.flatten()

for idx in flat_indices:
    str_idx = str(int(idx))
    
    # First, get the real item ID from the mapping
    if str_idx in index_mapping:
        real_id = index_mapping[str_idx]
        
        # Remove the .jpg extension to match the metadata keys
        clean_id = real_id.replace(".jpg", "")

        # Then look up the metadata using the real ID
        if clean_id in metadata:
            item = metadata[clean_id]
            print(f"Match Found: {item['name']} (ID: {item['id']})")
        else:
            print(f"ID {clean_id} found in mapping, but missing from metadata.json")
    else:
        print(f"FAISS Index {str_idx} not found in index_to_image_id.json")