import os
from typing import List, Dict, Any
from chic_finder.config import settings
from ai_engine.embeddings.vector_store import VectorStore

class DatabaseBuilder:
    """
    DatabaseBuilder class for offline Marqo index construction.
    Iterates through image datasets and adds documents to Marqo.
    Referencing: OutfitAI architecture step 4 (offline - refactored).
    """
    def __init__(self, index_name: str = None):
        self.vector_store = VectorStore(index_name=index_name)
    
    def build(self, documents: List[Dict[str, Any]]):
        """
        Builds the database by adding documents to Marqo.
        Documents should contain 'image_url' and 'description'.
        """
        print(f"Adding {len(documents)} documents to Marqo...")
        self.vector_store.add_documents(documents)
        print("Database build complete.")

def build_database(documents: List[Dict[str, Any]], index_name: str = None):
    """Functional wrapper for DatabaseBuilder.build"""
    builder = DatabaseBuilder(index_name=index_name)
    builder.build(documents)
