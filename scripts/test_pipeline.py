"""
scripts/test_pipeline.py — Smoke-test the full RAG pipeline end-to-end.

Tests three levels of depth:
  Level 1 (--level 1): Component import + initialization only (no API calls).
  Level 2 (--level 2): Full pipeline with a real image, but skips GPT-4o reranking.
  Level 3 (--level 3): Full pipeline including GPT-4o vision calls (requires OPENAI_API_KEY).

Usage:
  # Quick sanity check (no GPU, no API key needed):
  python -m scripts.test_pipeline --level 1

  # End-to-end with a test image (needs API key, safe mode — no reranking):
  python -m scripts.test_pipeline --level 2 --image path/to/outfit.jpg

  # Full pipeline including GPT-4o reranking:
  python -m scripts.test_pipeline --level 3 --image path/to/outfit.jpg
"""

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_pipeline")


def test_level_1():
    """Level 1: Import all AI components and confirm they initialize without errors."""
    logger.info("=== Level 1: Component initialization ===")

    from ai_engine.llm.outfit_parser import OutfitParser
    from ai_engine.llm.reranker import VisionReranker
    from ai_engine.embeddings.encoder import FashionEncoder
    from ai_engine.embeddings.vector_store import VectorStore
    from ai_engine.rag.retriever import Retriever
    from ai_engine.rag.pipeline import RAGPipeline

    logger.info("✓  OutfitParser imported")
    logger.info("✓  VisionReranker imported")

    encoder = FashionEncoder()
    logger.info("✓  FashionEncoder initialized on %s", encoder.device)

    store = VectorStore()
    logger.info("✓  VectorStore initialized (size=%d)", store.size)

    retriever = Retriever(store)
    logger.info("✓  Retriever initialized")

    # Instantiate pipeline without running it
    _ = RAGPipeline()
    logger.info("✓  RAGPipeline instantiated (lazy init)")

    logger.info("=== Level 1 PASSED ✅ ===\n")


def test_level_2(image_path: str):
    """Level 2: Run the full pipeline on a real image, skipping GPT-4o reranking."""
    logger.info("=== Level 2: Full pipeline (skip_reranking=True) ===")
    from PIL import Image
    from ai_engine.rag.pipeline import RAGPipeline

    img = Image.open(image_path).convert("RGB")
    logger.info("Loaded image: %s (%dx%d)", image_path, img.width, img.height)

    pipeline = RAGPipeline(skip_reranking=True, top_x_rerank=5)
    logger.info("Running pipeline…")

    results = pipeline.run(img)
    logger.info("Pipeline returned %d Recommendation(s).", len(results))

    for i, rec in enumerate(results):
        item = rec.query_item
        logger.info(
            "  [%d] %s %s %s → %d suggestion(s)",
            i + 1,
            item.get("color", "?"),
            item.get("style", "?"),
            item.get("type", "?"),
            len(rec.suggestions),
        )
        for j, s in enumerate(rec.suggestions[:3]):
            logger.info(
                "       suggestion %d: %s / %s / %s — %s",
                j + 1, s.category, s.sub_category, s.color, s.image_url,
            )

    logger.info("=== Level 2 PASSED ✅ ===\n")
    return results


def test_level_3(image_path: str):
    """Level 3: Full pipeline including GPT-4o reranking."""
    logger.info("=== Level 3: Full pipeline with GPT-4o reranking ===")
    from PIL import Image
    from ai_engine.rag.pipeline import RAGPipeline

    img = Image.open(image_path).convert("RGB")
    logger.info("Loaded image: %s (%dx%d)", image_path, img.width, img.height)

    pipeline = RAGPipeline(skip_reranking=False, top_k_retrieve=25, top_x_rerank=5)
    results = pipeline.run(img)

    logger.info("Pipeline returned %d Recommendation(s).", len(results))
    for i, rec in enumerate(results):
        item = rec.query_item
        logger.info(
            "  [%d] %s %s %s → %d suggestion(s)",
            i + 1,
            item.get("color", "?"),
            item.get("style", "?"),
            item.get("type", "?"),
            len(rec.suggestions),
        )

    logger.info("=== Level 3 PASSED ✅ ===\n")
    return results


def main():
    parser = argparse.ArgumentParser(
        description="ChicFinder — RAG Pipeline smoke test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--level",
        type=int,
        choices=[1, 2, 3],
        default=1,
        help="Test depth level (1=imports only, 2=full pipeline no reranking, 3=full with reranking).",
    )
    parser.add_argument(
        "--image",
        type=str,
        default=None,
        metavar="FILE",
        help="Path to an outfit image (required for levels 2 and 3).",
    )
    args = parser.parse_args()

    if args.level >= 2 and not args.image:
        parser.error("--image is required for level 2 and 3 tests.")

    if args.level >= 1:
        test_level_1()
    if args.level >= 2:
        test_level_2(args.image)
    if args.level >= 3:
        test_level_3(args.image)

    logger.info("All requested test levels completed successfully. 🎉")


if __name__ == "__main__":
    main()
