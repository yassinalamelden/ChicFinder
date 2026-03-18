import base64
import io
from PIL import Image

def bytes_to_image(image_bytes: bytes) -> Image.Image:
    """Converts raw bytes to a PIL Image object."""
    return Image.open(io.BytesIO(image_bytes))

def image_to_base64(image: Image.Image, format: str = "PNG") -> str:
    """Converts a PIL Image object to a base64 string."""
    buffered = io.BytesIO()
    image.save(buffered, format=format)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")
