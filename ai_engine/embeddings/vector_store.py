import marqo
from typing import List, Dict, Any
from chic_finder.config import settings

class VectorStore:
    """
    VectorStore using Marqo for multimodal/vector search.
    Referencing: OutfitAI architecture step 4b (refactored).
    """
    def __init__(self, url: str = None, index_name: str = None):
        self.url = url or settings.MARQO_URL
        self.index_name = index_name or settings.MARQO_INDEX_NAME
        self.mq = marqo.Client(url=self.url)
        self._initialize_index()
    
    def _initialize_index(self):
        """Initializes the Marqo index if it doesn't exist."""
        try:
            self.mq.create_index(self.index_name, model="ViT-L/14")
        except Exception:
            # Index might already exist
            pass
    
    def search(self, query: Any, top_k: int = 25) -> List[Dict[str, Any]]:
        """
        Searches for the nearest neighbors using Marqo.
        Can take text or image URL/path as query.
        """
        results = self.mq.index(self.index_name).search(
            q=query,
            limit=top_k
        )
        return results["hits"]

    def add_documents(self, documents: List[Dict[str, Any]]):
        """Adds documents (metadata + image pointers) to the Marqo index."""
        self.mq.index(self.index_name).add_documents(
            documents,
            tensor_fields=["image_url", "description"]
        )
