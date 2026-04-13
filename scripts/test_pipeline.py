import sys
import os

# Adds the root directory (ChicFinder) to the path so it can find ai_engine
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PIL import Image
from ai_engine.rag.pipeline import RAGPipeline
from shared.schemas.item import Recommendation

def main():
    print("Initializing RAG Pipeline (using actual LLM API)...")
    
    # Using the real API for parsing and reranking
    pipeline = RAGPipeline(top_k_retrieve=5, top_x_rerank=2, skip_reranking=False)
    
    # ---------------------------------------------------------
    # 1. Run the test with our local FAISS data
    # ---------------------------------------------------------
    image_path = r"D:\workstation\ChicFinder\dataset\photo-1618354691373-d851c5c3a990.jpg"
    print(f"Loading test image ({image_path})...")
    
    try:
         query_image = Image.open(image_path)
    except FileNotFoundError:
         print(f"Error: Could not find {image_path}. Make sure the raw_images exist.")
         sys.exit(1)
         
    print("Running pipeline test...")
    try:
        results = pipeline.run(query_image)
        import json
        with open("data/metadata.json", "r") as f:
            metadata = json.load(f)

        print("\n=== Pipeline Execution Successful ===")
        for i, rec in enumerate(results):
            print(f"\nDetected Outfit Item #{i+1}: {rec.query_item.get('color', '')} {rec.query_item.get('type', '')}")
            print("Top FAISS Vector Retrieval Suggestions:")
            for item in rec.suggestions:
                # The ID from FAISS usually ends with .jpg depending on the mapping
                clean_id = item.id.replace(".jpg", "")
                
                # Look up the actual details in our metadata.json
                meta = metadata.get(clean_id, {})
                real_name = meta.get("name", "Unknown Item")
                real_color = meta.get("color", "Unknown Color")
                
                print(f" - ID: {clean_id}, Name: {real_name}, Color: {real_color}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Pipeline test failed: {e}")

if __name__ == "__main__":
    main()