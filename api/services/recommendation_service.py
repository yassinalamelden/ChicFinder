from typing import List
from ai_engine.rag.pipeline import RAGPipeline
from shared.utils.image_utils import bytes_to_image
from api.models.schemas import RecommendationResponse, RecommendedItem

class RecommendationService:
    """
    RecommendationService: glue: HTTP ↔ RAGPipeline.
    Orchestrates the conversion of API requests to AI pipeline tasks.
    """
    def __init__(self):
        self.pipeline = RAGPipeline()
    
    def process_recommendation(self, image_bytes: bytes) -> List[RecommendationResponse]:
        """
        Processes image bytes, runs the RAG pipeline, and formats response.
        """
        # Convert bytes to PIL Image
        query_image = bytes_to_image(image_bytes)

        # Run RAG Pipeline
        rag_results = self.pipeline.run(query_image)

        # Map to API response schema
        response = []
        for res in rag_results:
            recommendations_list = [
                RecommendedItem(
                    id=item.id,
                    category=item.category,
                    sub_category=item.sub_category,
                    color=item.color,
                    style=item.style,
                    image_url=item.image_url,
                    brand=item.brand,
                    price=item.price
                ) for item in res.suggestions
            ]
            
            response.append(RecommendationResponse(
                query_item=res.query_item,
                recommendations=recommendations_list
            ))
            
        return response
