import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "ChicFinder"

    # AI Model Settings
    GEMINI_API_KEY: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Supabase
    SUPABASE_URL: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    SUPABASE_SERVICE_ROLE_KEY: str = field(default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))

    # Legacy (unused after migration, kept for reference)
    EMBEDDING_DIM: int = 512

    def get_image_url(self, image_filename: str) -> str:
        """Build public Supabase Storage URL for a product image."""
        return f"{self.SUPABASE_URL}/storage/v1/object/public/product-images/{image_filename}.jpg"

settings = Config()
