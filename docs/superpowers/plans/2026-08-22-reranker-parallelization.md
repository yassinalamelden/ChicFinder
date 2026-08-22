# Reranker Parallelization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `RAGPipeline.run()` process multiple detected outfit items concurrently instead of sequentially, so a multi-item photo's total latency is bounded by the slowest single item's Gemini call, not the sum of all items.

**Architecture:** `RAGPipeline.run()` becomes `async def`. Per-item retrieval + reranking logic moves into a new `_process_item()` async method; all detected items are processed concurrently via `asyncio.gather`. The synchronous `VisionReranker.rerank()` call is wrapped in Starlette's `run_in_threadpool` (the same pattern already used in `api/routes/search.py`) so it doesn't block the event loop while waiting on the OpenRouter HTTP call.

**Tech Stack:** Python `asyncio`, `starlette.concurrency.run_in_threadpool`, `pytest` + `pytest-asyncio` (new — this repo has no test suite yet).

**Spec:** `docs/superpowers/specs/2026-08-22-aws-backend-migration-design.md` (Performance section)

## Global Constraints

- `RAGPipeline.run()`'s public return type stays `List[Recommendation]` — only its execution model changes, never its contract.
- `OutfitParser.parse()` and `VisionReranker.rerank()`'s own signatures do not change — only how `RAGPipeline` calls them.
- Every existing caller of `RAGPipeline.run()` must be updated to `await` it — a partial migration that leaves one caller calling it synchronously is a broken build, not a valid stopping point.

---

### Task 1: Make `RAGPipeline.run()` async and rerank items concurrently

**Files:**
- Create: `pytest.ini`
- Modify: `requirements.txt`
- Create: `tests/ai_engine/rag/test_pipeline.py`
- Modify: `ai_engine/rag/pipeline.py`
- Modify: `api/services/recommendation_service.py`
- Modify: `api/routes/recommend.py`
- Modify: `scripts/test_pipeline.py`

**Interfaces:**
- Produces: `RAGPipeline.run(self, query_image: Image.Image) -> List[Recommendation]` — now a coroutine; callers must `await` it.
- Produces: `RAGPipeline._process_item(self, item_meta: dict, query_image: Image.Image, query_vector) -> Recommendation` — new internal coroutine, one per detected outfit item.
- Produces: `RecommendationService.process_recommendation(self, image_bytes: bytes) -> List[RecommendationResponse]` — now a coroutine.

- [ ] **Step 1: Add test tooling**

Add to `requirements.txt`, under a new section:

```
# --- Testing -------------------------------------------------
pytest
pytest-asyncio
```

Create `pytest.ini` at the repo root:

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

Install the new dependencies:

```bash
pip install pytest pytest-asyncio
```

- [ ] **Step 2: Write the failing test**

Create `tests/ai_engine/rag/test_pipeline.py`:

```python
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
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `pytest tests/ai_engine/rag/test_pipeline.py -v`
Expected: FAIL — `RAGPipeline.run()` is currently a plain synchronous method, so `await pipeline.run(...)` raises `TypeError: object list can't be used in 'await' expression`.

- [ ] **Step 4: Rewrite `RAGPipeline.run()` as async with concurrent per-item processing**

In `ai_engine/rag/pipeline.py`, add to the imports at the top of the file:

```python
import asyncio
from starlette.concurrency import run_in_threadpool
```

Replace the existing `run()` method (and everything from `# ── Step 1: LLM outfit parsing` through the final `return recommendations`) with:

```python
    async def run(self, query_image: Image.Image) -> List[Recommendation]:
        """
        Executes the full RAG pipeline on the given outfit image.

        Args:
            query_image: RGB PIL Image of the user's outfit.

        Returns:
            List of Recommendation objects, one per detected outfit item.
            Each Recommendation contains:
              - query_item: dict with the parsed item metadata
              - suggestions: List[ClothingItem] ordered by relevance
        """
        logger.info("RAGPipeline Step 1: LLM outfit parsing…")
        items_meta = self.parser.parse(query_image)

        if not items_meta:
            logger.warning("RAGPipeline: no outfit items detected. Returning empty.")
            return []

        logger.info("RAGPipeline: %d item(s) detected.", len(items_meta))

        logger.info("RAGPipeline Step 2: Query encoding with FashionCLIP…")
        encoder = get_encoder()
        image_bytes = self._pil_to_bytes(query_image)
        query_vector = encoder.encode(image_bytes)

        logger.info(
            "RAGPipeline Steps 3+4: retrieving and reranking %d item(s) concurrently…",
            len(items_meta),
        )
        recommendations = await asyncio.gather(
            *[
                self._process_item(item_meta, query_image, query_vector)
                for item_meta in items_meta
            ]
        )
        return list(recommendations)

    async def _process_item(
        self,
        item_meta: dict,
        query_image: Image.Image,
        query_vector,
    ) -> Recommendation:
        item_type = item_meta.get("type", "clothing")
        item_color = item_meta.get("color", "")
        item_style = item_meta.get("style", "")
        logger.info(
            "RAGPipeline: processing item → %s %s %s",
            item_color, item_style, item_type,
        )

        logger.info("RAGPipeline Step 3: KNN retrieval (top %d)…", self.top_k_retrieve)
        candidates: List[ClothingItem] = self.retriever.retrieve_candidates(
            query_vector, top_k=self.top_k_retrieve
        )

        if not candidates:
            logger.warning(
                "RAGPipeline: no candidates retrieved for item '%s'. "
                "Is the FAISS database built? Run build_database first.",
                item_type,
            )
            return Recommendation(query_item=item_meta, suggestions=[])

        if self.skip_reranking or len(candidates) <= self.top_x_rerank:
            top_items = candidates[: self.top_x_rerank]
        else:
            logger.info(
                "RAGPipeline Step 4: Vision reranking %d → top %d…",
                len(candidates),
                self.top_x_rerank,
            )
            candidate_images = [
                self._fetch_image(item.image_url) for item in candidates
            ]
            valid_pairs = [
                (img, item)
                for img, item in zip(candidate_images, candidates)
                if img is not None
            ]
            if valid_pairs:
                valid_images, valid_items = zip(*valid_pairs)
                ranked_indices = await run_in_threadpool(
                    self.reranker.rerank, query_image, list(valid_images), self.top_x_rerank
                )
                top_items = [valid_items[i] for i in ranked_indices][: self.top_x_rerank]
            else:
                top_items = candidates[: self.top_x_rerank]

        logger.info(
            "RAGPipeline: %d recommendation(s) finalized for item '%s'.",
            len(top_items),
            item_type,
        )
        return Recommendation(query_item=item_meta, suggestions=top_items)
```

- [ ] **Step 5: Update `RecommendationService.process_recommendation` to await the pipeline**

In `api/services/recommendation_service.py`, change:

```python
    def process_recommendation(self, image_bytes: bytes) -> List[RecommendationResponse]:
```
to
```python
    async def process_recommendation(self, image_bytes: bytes) -> List[RecommendationResponse]:
```

and change:

```python
        rag_results = self.pipeline.run(query_image)
```
to
```python
        rag_results = await self.pipeline.run(query_image)
```

- [ ] **Step 6: Update `/recommend` to await the now-async service call**

In `api/routes/recommend.py`, change:

```python
        rag_responses = service.process_recommendation(raw_bytes)
```
to
```python
        rag_responses = await service.process_recommendation(raw_bytes)
```

- [ ] **Step 7: Update `scripts/test_pipeline.py` to run the async pipeline**

Add `import asyncio` near the top of `scripts/test_pipeline.py` (alongside the existing `import sys` / `import os`).

Change:

```python
        results = pipeline.run(query_image)
```
to
```python
        results = asyncio.run(pipeline.run(query_image))
```

- [ ] **Step 8: Run the test suite to verify it passes**

Run: `pytest tests/ai_engine/rag/test_pipeline.py -v`
Expected: 2 passed.

- [ ] **Step 9: Manual smoke test against the real pipeline**

Run: `python scripts/test_pipeline.py`
Expected: same successful output as before (outfit item detected, FAISS suggestions printed) — this exercises the real async path end-to-end, not just the mocked unit test. Requires `OPENROUTER_API_KEY` set in `.env`.

- [ ] **Step 10: Commit**

```bash
git add pytest.ini requirements.txt tests/ai_engine/rag/test_pipeline.py ai_engine/rag/pipeline.py api/services/recommendation_service.py api/routes/recommend.py scripts/test_pipeline.py
git commit -m "perf: rerank detected outfit items concurrently instead of sequentially

RAGPipeline.run() now processes all detected items via asyncio.gather
instead of a sequential for-loop, so a multi-item photo's added
latency is bounded by the slowest single item's Gemini call rather
than the sum of all items. VisionReranker.rerank() (sync, blocking)
runs via run_in_threadpool so it doesn't block the event loop."
```

## Self-Review Notes

- **Spec coverage:** Implements the Performance section's one included fix (parallelize per-item reranking) in full; the explicit timeout and `skip_reranking` exposure were deferred in the spec and are correctly not part of this plan.
- **Type consistency:** `run()` and `_process_item()`'s signatures match how they're called in Step 4; `process_recommendation()`'s new `async def` matches its new caller in Step 6.
- **No placeholders:** every step has real, complete code — no "add error handling" style steps.
