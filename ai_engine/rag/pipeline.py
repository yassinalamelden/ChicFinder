from PIL import Image
from typing import List, Dict
from ai_engine.background_removal.segmenter import FashionSegmenter
from ai_engine.llm.outfit_parser import OutfitParser
from ai_engine.embeddings.vector_store import VectorStore
from ai_engine.llm.reranker import VisionReranker
from shared.schemas.item import Recommendation, ClothingItem

class RAGPipeline:
    """
    RAGPipeline: final orchestrator combining all AI components.
    Referencing: OutfitAI full pipeline entry point (refactored).
    """
    def __init__(self):
        self.segmenter = FashionSegmenter()
        self.parser = OutfitParser()
        self.vector_store = VectorStore()
        self.reranker = VisionReranker()

    def run(self, query_image: Image.Image) -> List[Recommendation]:
        """
        Executes the full RAG pipeline flow.
        1. Background removal (rembg)
        2. LLM outfit parsing (GPT-4o)
        3. Multimodal search (Marqo)
        4. Vision-based reranking (GPT-4o)
        """
        # Step 1: Background removal
        clean_image = self.segmenter.segment(query_image)

        # Step 2: LLM outfit parsing
        items_meta = self.parser.parse(clean_image)

        recommendations = []
        for item_meta in items_meta:
            # Step 3: Multimodal search via Marqo
            # We can use the item description or a temporary image URL/path
            query_str = f"{item_meta.get('color')} {item_meta.get('style')} {item_meta.get('type')}"
            hits = self.vector_store.search(query=query_str, top_k=25)

            # Step 4: Vision Reranking
            candidate_images = [] # Fetch images from hits
            top_indices = self.reranker.rerank(clean_image, candidate_images, top_x=5)

            # Step 5: Construct results
            suggestions = [
                ClothingItem(
                    id=hit["_id"],
                    category=hit.get("category", "N/A"),
                    sub_category=hit.get("sub_category", "N/A"),
                    color=hit.get("color", "N/A"),
                    style=hit.get("style", "N/A"),
                    image_url=hit.get("image_url", ""),
                    brand=hit.get("brand"),
                    price=hit.get("price")
                ) for hit in hits[:5] # Simplified for now
            ]
            
            recommendations.append(Recommendation(query_item=item_meta, suggestions=suggestions))
        
        return recommendations
