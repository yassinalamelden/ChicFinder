import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from chic_finder.config import settings

def download_file(url, dest):
    print(f"Downloading {url} to {dest}...")
    # Placeholder for actual download logic
    pass

def main():
    models_dir = "models"
    os.makedirs(models_dir, exist_ok=True)
    
    models = {
        "segmenter": (settings.SEGMENTER_MODEL_PATH, "https://example.com/segmenter.pth"),
        "encoder": (settings.ENCODER_MODEL_PATH, "https://example.com/encoder.pth")
    }
    
    for name, (path, url) in models.items():
        download_file(url, path)

if __name__ == "__main__":
    main()
