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
    GEMINI_API_KEY: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""), repr=False)
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Supabase
    SUPABASE_URL: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    SUPABASE_SERVICE_ROLE_KEY: str = field(default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""), repr=False)

    # Legacy (unused after migration, kept for reference)
    EMBEDDING_DIM: int = 512

    def get_image_url(self, image_filename: str) -> str:
        """Return public Supabase Storage URL for a product image.

        Args:
            image_filename: Base filename without extension (e.g. 'tomato_123_0').
        """
        if not self.SUPABASE_URL:
            raise RuntimeError("SUPABASE_URL is not configured; cannot build Storage URL")
        stem = image_filename.rsplit(".", 1)[0] if "." in image_filename else image_filename
        return f"{self.SUPABASE_URL}/storage/v1/object/public/product-images/{stem}.jpg"

settings = Config()
