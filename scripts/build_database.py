"""
scripts/build_database.py — Offline FAISS index builder for ChicFinder.

Usage examples:

  # From an image directory (metadata inferred from folder structure):
  python -m scripts.build_database --images ./data/images --out ./data/faiss_index

  # From a JSON manifest file:
  python -m scripts.build_database --manifest ./data/manifest.json --out ./data/faiss_index

  # Manifest format (JSON array):
  [
    {
      "image_url": "data/images/tops/casual/item_001.jpg",
      "category": "tops",
      "sub_category": "casual",
      "color": "white",
      "style": "casual",
      "brand": "Zara",
      "price": 29.99
    },
    ...
  ]
"""

import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path when running as a script
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_engine.embeddings.database_builder import DatabaseBuilder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("build_database")


def main():
    parser = argparse.ArgumentParser(
        description="ChicFinder — Build the FAISS fashion retrieval database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--images",
        type=str,
        metavar="DIR",
        help="Path to the root image directory. Metadata inferred from folder names.",
    )
    source_group.add_argument(
        "--manifest",
        type=str,
        metavar="FILE",
        help="Path to a JSON manifest file with document metadata.",
    )

    parser.add_argument(
        "--out",
        type=str,
        default=None,
        metavar="PATH",
        help="Output path for the FAISS index (default: from .env VECTOR_DB_PATH).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        metavar="N",
        help="Encoding batch size (default: 32).",
    )

    args = parser.parse_args()

    logger.info("Initializing DatabaseBuilder…")
    builder = DatabaseBuilder(index_path=args.out, batch_size=args.batch_size)

    if args.images:
        logger.info("Building from image directory: %s", args.images)
        builder.build_from_directory(args.images)
    else:
        logger.info("Building from manifest: %s", args.manifest)
        builder.build_from_manifest(args.manifest)

    total = builder.vector_store.size
    logger.info("✅  Database build complete. %d vectors indexed.", total)


if __name__ == "__main__":
    main()
