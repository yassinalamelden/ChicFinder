import numpy as np
from PIL import Image
from rembg import remove
from chic_finder.config import settings

class FashionSegmenter:
    """
    FashionSegmenter class using rembg for background removal.
    Referencing: OutfitAI architecture step 2 (refactored).
    """
    def __init__(self):
        # rembg handles model loading internally
        pass
    
    def segment(self, image: Image.Image) -> Image.Image:
        """
        Segments the fashion items and removes the background using rembg.
        Returns a masked image with transparency.
        """
        try:
            # rembg.remove returns an image with the background removed
            output = remove(image)
            return output
        except Exception as e:
            # Fallback to original image if rembg fails
            return image
