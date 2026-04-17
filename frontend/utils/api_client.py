import sys
import os
import requests
from typing import List, Dict

# Ensure project root is on sys.path so chic_finder package can be found
# (Streamlit only adds the script's own directory — frontend/ — to sys.path)
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from chic_finder.config import settings

class APIClient:
    """
    APIClient: wrapping all requests calls to the ChicFinder API.
    Ensures frontend doesn't import from ai-engine directly.
    """
    def __init__(self, base_url: str = f"http://localhost:8000{settings.API_V1_STR}"):
        self.base_url = base_url

    def get_recommendations(self, image_bytes: bytes) -> List[Dict]:
        """
        Sends the uploaded image to the API and returns recommendations.
        """
        files = {"file": ("image.png", image_bytes, "image/png")}
        response = requests.post(f"{self.base_url}/recommend", files=files)
        response.raise_for_status()
        return response.json()

    def check_health(self) -> Dict:
        """Checks the API health status."""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
