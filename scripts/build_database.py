"""
scripts/build_database.py — Offline FAISS index builder for ChicFinder.

Encodes all images in a directory using FashionCLIP (512-dim, L2-normalized)
and saves the resulting FAISS IndexFlatIP to disk alongside a metadata JSON.

Usage:
  python -m scripts.build_database --images ./data/raw_images
  python -m scripts.build_database --images ./data/raw_images --out ./data/embeddings.index
"""

import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path when running as a script
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_engine.embeddings.database_builder import FAISSIndexBuilder, DEFAULT_INDEX_PATH, DEFAULT_METADATA_PATH

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

    parser.add_argument(
        "--images",
        type=str,
        required=True,
        metavar="DIR",
        help="Path to the image directory (e.g. data/raw_images).",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=str(DEFAULT_INDEX_PATH),
        metavar="PATH",
        help=f"Output path for the FAISS index (default: {DEFAULT_INDEX_PATH}).",
    )
    parser.add_argument(
        "--meta",
        type=str,
        default=str(DEFAULT_METADATA_PATH),
        metavar="PATH",
        help=f"Output path for metadata JSON (default: {DEFAULT_METADATA_PATH}).",
    )

    args = parser.parse_args()

    logger.info("Initializing FAISSIndexBuilder…")
    builder = FAISSIndexBuilder(
        index_path=Path(args.out),
        metadata_path=Path(args.meta),
    )

    logger.info("Building from image directory: %s", args.images)
    builder.build(images_dir=Path(args.images))
    logger.info("✅  Database build complete.")


if __name__ == "__main__":
    main()
