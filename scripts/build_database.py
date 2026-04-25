"""
scripts/build_database.py — Offline FAISS index builder for ChicFinder.

Encodes all images in a directory using FashionCLIP (512-dim, L2-normalized)
and saves the resulting FAISS IndexFlatIP to disk alongside an index mapping JSON.

Usage:
  python -m scripts.build_database --images ./data/raw_images
  python -m scripts.build_database --images ./data/raw_images --out ./data/embeddings.index
"""

import argparse
import logging
import sys
import warnings
from pathlib import Path

# Ensure project root is on sys.path when running as a script
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_engine.embeddings.database_builder import (
    DEFAULT_INDEX_PATH,
    DEFAULT_MAPPING_PATH,
    FAISSIndexBuilder,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("build_database")


def main():
    warnings.warn(
        "scripts/build_database.py is deprecated. Use scripts/02_build_faiss_index.py instead.",
        DeprecationWarning,
        stacklevel=2,
    )

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
        default=str(DEFAULT_MAPPING_PATH),
        metavar="PATH",
        help=f"Output path for mapping JSON (default: {DEFAULT_MAPPING_PATH}).",
    )

    args = parser.parse_args()

    logger.info("Initializing FAISSIndexBuilder…")
    builder = FAISSIndexBuilder(
        index_path=Path(args.out),
        mapping_path=Path(args.meta),
    )

    logger.info("Building from image directory: %s", args.images)
    builder.build(images_dir=Path(args.images))
    logger.info("✅  Database build complete.")


if __name__ == "__main__":
    main()
