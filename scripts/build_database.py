import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_engine.embeddings.database_builder import FAISSIndexBuilder
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

if __name__ == "__main__":
    builder = FAISSIndexBuilder()
    builder.build()
    print("FAISS index built successfully.")
