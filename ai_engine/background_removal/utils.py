from PIL import Image
import numpy as np

def preprocess(image: Image.Image) -> Image.Image:
    """
    Preprocess image for FashionSegmenter.
    Includes resizing and normalization.
    """
    # Resize to standard input size for ViT-B / SETR
    image = image.resize((512, 512))
    return image

def apply_mask(image: Image.Image, mask: np.ndarray) -> Image.Image:
    """
    Applies the binary mask to the original image to remove background.
    """
    # Placeholder implementation
    return image
