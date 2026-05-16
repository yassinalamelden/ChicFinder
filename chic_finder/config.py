import os
import logging
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

@dataclass
class Config:
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "ChicFinder"

    # AI Model Settings
    GEMINI_API_KEY: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""), repr=False)
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Supabase
    SUPABASE_URL: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    SUPABASE_SERVICE_ROLE_KEY: str = field(default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""), repr=False)

    # Legacy (unused after migration, kept for reference)
    EMBEDDING_DIM: int = 512

    def __post_init__(self):
        warnings = []
        if not self.SUPABASE_URL:
            warnings.append("SUPABASE_URL env var is not set — database operations will fail")
        if not self.SUPABASE_SERVICE_ROLE_KEY:
            warnings.append("SUPABASE_SERVICE_ROLE_KEY env var is not set — database operations will fail")
        if not self.GEMINI_API_KEY:
            warnings.append("GEMINI_API_KEY env var is not set — LLM-dependent features will fail")
        for w in warnings:
            logger.warning("Config warning: %s", w)

    def get_image_url(self, image_filename: str) -> str:
        """Return public Supabase Storage URL for a product image.

        Args:
            image_filename: Base filename without extension (e.g. 'tomato_123_0').
        """
        if not self.SUPABASE_URL:
            raise RuntimeError("SUPABASE_URL is not configured; cannot build Storage URL")
        stem = image_filename.rsplit(".", 1)[0] if "." in image_filename else image_filename
        return f"{self.SUPABASE_URL.rstrip('/')}/storage/v1/object/public/product-images/{stem}.jpg"

settings = Config()
