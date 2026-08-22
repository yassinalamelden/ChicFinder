import time
from unittest.mock import MagicMock

import pytest
from PIL import Image

from ai_engine.rag.pipeline import RAGPipeline
from shared.schemas.item import ClothingItem


class FakeParser:
    def parse(self, image):
        return [
            {"type": "shirt", "color": "white"},
            {"type": "pants", "color": "black"},
            {"type": "shoes", "color": "red"},
        ]


class FakeRetriever:
    def retrieve_candidates(self, query_vector, top_k):
        return [
            ClothingItem(
                id=f"item_{i}",
                category="test",
                sub_category="test",
                color="test",
                style="test",
                image_url=f"http://example.com/{i}.jpg",
            )
            for i in range(3)
        ]


class SlowFakeReranker:
    """Sleeps 0.2s per call to simulate a real Gemini/OpenRouter round-trip."""

    def rerank(self, query_image, candidate_images, top_x=5):
        time.sleep(0.2)
        return list(range(len(candidate_images)))


async def test_run_reranks_multiple_items_concurrently(monkeypatch):
    pipeline = RAGPipeline(top_k_retrieve=3, top_x_rerank=2, skip_reranking=False)
    pipeline._parser = FakeParser()
    pipeline._retriever = FakeRetriever()
    pipeline._reranker = SlowFakeReranker()

    monkeypatch.setattr(
        "ai_engine.rag.pipeline.get_encoder",
        lambda: MagicMock(encode=lambda image_bytes: [0.0] * 512),
    )
    monkeypatch.setattr(
        RAGPipeline,
        "_fetch_image",
        staticmethod(lambda source: Image.new("RGB", (10, 10))),
    )

    query_image = Image.new("RGB", (10, 10))

    start = time.monotonic()
    results = await pipeline.run(query_image)
    elapsed = time.monotonic() - start

    assert len(results) == 3
    for rec in results:
        assert len(rec.suggestions) == 2  # top_x_rerank=2

    # Sequential reranking of 3 items at 0.2s each would take ~0.6s.
    # Concurrent reranking should take ~0.2s. Assert well under the
    # sequential total, with margin for CI jitter.
    assert elapsed < 0.45, f"expected concurrent execution (<0.45s), took {elapsed:.2f}s"


async def test_run_returns_empty_list_when_no_items_detected(monkeypatch):
    pipeline = RAGPipeline()
    pipeline._parser = MagicMock(parse=lambda image: [])

    results = await pipeline.run(Image.new("RGB", (10, 10)))

    assert results == []
