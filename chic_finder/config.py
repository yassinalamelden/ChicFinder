import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    """
    Configuration dataclass for ChicFinder.
    Reads from .env file and provides default values.
    """
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "ChicFinder"
    
    # OpenAI Settings
    OPENAI_API_KEY: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    GPT_MODEL: str = "gpt-4o"
    
    # AI Engine Settings
    MARQO_URL: str = field(default_factory=lambda: os.getenv("MARQO_URL", "http://localhost:8882"))
    MARQO_INDEX_NAME: str = field(default_factory=lambda: os.getenv("MARQO_INDEX_NAME", "chic-finder-index"))
    VECTOR_DB_PATH: str = field(default_factory=lambda: os.getenv("VECTOR_DB_PATH", "data/faiss_index"))
    IMAGE_DB_PATH: str = field(default_factory=lambda: os.getenv("IMAGE_DB_PATH", "data/images"))
    EMBEDDING_DIM: int = 256
    
    # Model Paths
    SEGMENTER_MODEL_PATH: str = field(default_factory=lambda: os.getenv("SEGMENTER_MODEL_PATH", "models/segmenter_vit_b.pth"))
    ENCODER_MODEL_PATH: str = field(default_factory=lambda: os.getenv("ENCODER_MODEL_PATH", "models/fashion_encoder_vgg16.pth"))

settings = Config()
