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

# 2. Get a vector for a "Black" image (ID 002 was black)
encoder = get_encoder()
with open("data/images/002.jpg", "rb") as f:
    query_vector = encoder.encode(f.read())

# 3. Search the top 5 matches
# FAISS expects a 2D array
D, I = index.search(np.expand_dims(query_vector, axis=0), 5)

print("\n--- Search Results for 'Black Square' ---")

# We use .flatten() to turn [] into
flat_indices = I.flatten()

for idx in flat_indices:
    # Convert numpy int to a standard string for the JSON lookup
    str_idx = str(int(idx))
    
    if str_idx in metadata:
        item = metadata[str_idx]
        print(f"Match Found: {item['filename']} (ID: {item['id']})")
    else:
        print(f"Index {str_idx} not found in metadata.json")