from PIL import Image
from typing import List
import io
from ai_engine.embeddings.vector_store import search_similar_items
from shared.schemas.item import Recommendation, ClothingItem

class RAGPipeline:
    """
    RAGPipeline: final orchestrator combining all AI components.
    Simplified for FAISS-based execution.
    """
    def __init__(self):
        # Dependencies like segmenter and parser are skipped for now
        # to ensure the project runs with the available FAISS setup.
        pass

    def run(self, query_image: Image.Image) -> List[Recommendation]:
        """
        Executes a simplified RAG pipeline flow using FAISS.
        """
        # Convert PIL Image to bytes for the vector store
        img_byte_arr = io.BytesIO()
        query_image.save(img_byte_arr, format='PNG')
        image_bytes = img_byte_arr.getvalue()

        # Step 1: Similarity Search via FAISS
        hits = search_similar_items(image_bytes)

        # Step 2: Construct results
        suggestions = [
            ClothingItem(
                id=hit.get("id", "N/A"),
                category="Unknown",
                sub_category="Unknown",
                color="Unknown",
                style="Unknown",
                image_url=hit.get("image_url", ""),
                brand=hit.get("brand"),
                price=hit.get("price")
            ) for hit in hits
        ]
        
        # Single recommendation for the whole uploaded image
        recommendation = Recommendation(
            query_item={"type": "uploaded_outfit", "color": "multi", "style": "custom"},
            suggestions=suggestions
        )
        
        return [recommendation]
