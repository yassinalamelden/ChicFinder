"""
scripts/02_build_faiss_index.py

Offline FAISS index builder for ChicFinder.

Usage:
  python scripts/02_build_faiss_index.py
  python scripts/02_build_faiss_index.py --images data/raw_images

Environment:
  CLIP_MODEL_PATH  Path to local fine-tuned CLIP model.
                   Defaults to models/fine_tuned_clip.
"""

import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path when running as a script
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_engine.embeddings.database_builder import (
    DEFAULT_IMAGES_DIR,
    DEFAULT_INDEX_PATH,
    DEFAULT_MAPPING_PATH,
    DEFAULT_METADATA_SOURCE_PATH,
    FAISSIndexBuilder,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("build_faiss_index")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the offline FAISS vector index."
    )
    parser.add_argument(
        "--images",
        type=str,
        default=str(DEFAULT_IMAGES_DIR),
        help=f"Directory containing product images (default: {DEFAULT_IMAGES_DIR}).",
    )
    parser.add_argument(
        "--index",
        type=str,
        default=str(DEFAULT_INDEX_PATH),
        help=f"Output path for FAISS index (default: {DEFAULT_INDEX_PATH}).",
    )
    parser.add_argument(
        "--mapping",
        type=str,
        default=str(DEFAULT_MAPPING_PATH),
        help=f"Output path for index mapping JSON (default: {DEFAULT_MAPPING_PATH}).",
    )
    parser.add_argument(
        "--metadata",
        type=str,
        default=str(DEFAULT_METADATA_SOURCE_PATH),
        help=(
            "Path to metadata JSON used for validation "
            f"(default: {DEFAULT_METADATA_SOURCE_PATH})."
        ),
    )

    args = parser.parse_args()

    images_dir = Path(args.images)
    images_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Initializing FAISS index builder...")
    builder = FAISSIndexBuilder(
        index_path=Path(args.index),
        mapping_path=Path(args.mapping),
        metadata_source_path=Path(args.metadata),
    )
    builder.build(images_dir=images_dir)
    logger.info("Done. Offline FAISS artifacts are ready.")


if __name__ == "__main__":
    main()
