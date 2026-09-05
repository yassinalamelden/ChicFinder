# Dataset Cleanup & Brand Expansion

> Created by Claude (`(C)` prefix per `CLAUDE.md`) on branch `data/dataset-cleanup-and-brand-expansion`.
> Companion to `ChicFinder-Master-Plan.md` §6 (Dataset quality). **Status: dataset work complete locally; NOT yet live in production — see "Supabase gap" below before assuming this affects real users.**

---

## Result summary (as of this pass)

| Metric | Before | After |
|---|---|---|
| Total image records | 11,464 | 25,309 |
| Gender split | Men 57.1% / Kids 21.8% / Women 21.1% | **Kids 34.0% / Women 33.7% / Men 32.3%** |
| Brands | 10 | 14 |
| Corrupt/placeholder files | unknown, present | 0 (1,146 found and removed) |
| FAISS index | 10,443 vectors, stale | **25,299 vectors, 0 decode failures** |
| Train/validation split | none | 21,497 / 3,802 images, product-level, stratified by brand × gender |

`data/` folder final layout: `train/`, `validation/` (images — `raw_images/` was deleted, it duplicated every file already in the splits), `metadata.jsonl`/`metadata.json` (full dataset), `train_metadata.jsonl`/`validation_metadata.jsonl` (per-split manifests), `embeddings.index`/`index_to_image_id.json` (live FAISS index), `clean/`/`raw/` (scraper provenance), `(C)_bad_images.txt` (audit log of removed corrupt files).

## 🔴 Supabase gap — read this before assuming any of this is live

**The deployed `/api/v1/recommend` endpoint (`api/routes/recommend.py`) reads from Supabase pgvector, not `data/embeddings.index`.** None of this pass's work — `activ` removal, the 5 new brands, gender rebalancing, corruption cleanup, the FAISS rebuild — is visible to real users until it's migrated to Supabase. `scripts/03_migrate_to_supabase.py` has been updated to carry this data across correctly (gender field, new file layout, non-`.jpg` extensions) but has not been run — no `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` are configured in this environment. **Before running it: the Supabase `products` table needs a `gender` column added, or the migration's upsert will fail** — this is the whole point of the gender-balance work, so don't skip it.

Also found: `ai_engine/rag/pipeline.py` (the `RAGPipeline` class `scripts/test_pipeline.py` expects) doesn't exist anywhere in the repo. That test script's path/field bugs were fixed anyway, but it can't actually run until that module exists — separate, pre-existing gap, unrelated to this dataset work.

---

## Why (original diagnosis)

Measured from `data/metadata.jsonl` at the start of this pass (11,464 records):

**By gender:** Men 6,551 (57.1%) / Kids 2,499 (21.8%) / Women 2,414 (21.1%)

**By brand:** concrete 2,782 (24.3%, over the 20% cap) / mobaco 1,605 / ravin 1,542 / in_your_shoe 1,454 / Tomato Store 1,359 / **activ 1,190 (removed)** / Town Team 1,145 / asili 255 / defacto 82 / y_studios 50

Matches the "gender skew" issue `ChicFinder-Master-Plan.md` §6.1/§6.1.1 already flagged. Per that doc's own rule, image augmentation doesn't fix imbalance — only real acquisition does.

## What was done

1. **Removed `activ`** (1,190 records) — `scripts/(C)_remove_brand.py` (reusable for any future brand removal).
2. **Added 5 new brands**, verified as real, currently-operating Egyptian stores with clean gender data:

| Brand | Segment | Platform | Images added |
|---|---|---|---|
| BOHEME (bohemeshop.net) | Women's boho/dresses | Shopify | 1,439 |
| OR (or-egypt.com) | Mixed — gender read from per-product Shopify tags | Shopify | 7,104 |
| Solang (solangshop.com) | Kids | Shopify | 3,774 |
| Carrot Kids (carrotegypt.com) | Kids | WooCommerce | 2,865 |
| PSYCH (psychonlinestore.com) | Mixed — gender read from Men/Women collection membership | Shopify | 864 |

3. **Dropped 324 (then 320 more, after a re-run regression that was fixed at the source) ungendered products** — a deliberate policy: no reliable gender signal means the record is excluded, not guessed.
4. **Found and removed 1,146 corrupt files** — mostly SVG placeholder icons saved with a `.jpg` extension in the *original* `concrete` and `defacto` data (pre-existing bug, not introduced by this pass), plus a handful of genuinely truncated downloads. `data/(C)_bad_images.txt` has the full list with reasons.
5. **Rebuilt the FAISS index from scratch** twice (once after cleanup, once after adding PSYCH) — `scripts/(C)_build_faiss_index.py`. Had to run CPU-forced (`CUDA_VISIBLE_DEVICES=""`) with an OpenMP fix (`KMP_DUPLICATE_LIB_OK=TRUE OMP_NUM_THREADS=1`) after repeated CUDA OOM / native segfault crashes on this machine's 6GB shared GPU — GPU wasn't meaningfully faster anyway (~4 img/s either way, overhead-bound not compute-bound).
6. **Built a product-level, brand×gender-stratified train/validation split** — `scripts/(C)_build_train_val_split.py`, 85/15, seeded for reproducibility. Multi-image products never split across train/val (would leak near-duplicates).
7. **Cleaned up `data/`** for handoff to collaborators — deleted 9 stale backup files and the redundant `raw_images/` flat copy (train+validation already contain 100% of it), ~18GB → ~9.7GB.
8. **Committed everything** — also discovered and fixed that `scrapers/` (and a duplicate `data/` line) was fully gitignored, meaning no scraper code, old or new, had ever been in git history. Fixed in `.gitignore`, committed.

## Brands investigated and not added (with reasons)

Sourced from exploring `locallyeg.com`, a 14+ brand Egyptian marketplace aggregator — its own site is unscrapeable in bulk (client-rendered React, no API discoverable via static fetching; only its homepage carousels are server-rendered, yielding ~24 hand-readable products). Instead, each brand's *own* standalone store was searched for and evaluated individually:

| Brand | Outcome |
|---|---|
| Vega (vegaegy.com) | Reachable, but genuinely unisex — no Men/Women collection split, no reliable gender signal. Skipped. |
| Denjoe (denjoestore.com) | Same — genuinely unisex. Skipped. |
| Black Edition (blackeditionshop.com) | 49 collections, none gender-split. Skipped. |
| Richness (richnesseg.com) | Site returns 401 Unauthorized (password-protected). Inaccessible. |
| Twenty Seven (twentysevenegy.com) | Site unreachable (connection fails entirely). |
| 47 | No dedicated store found. |
| Seemly | Ambiguous — multiple similarly-named stores (seemlyessentials.com, seemlycollective.com, seamsbyseemly.com); unclear which matches the Locally listing. Not resolved. |

## Category taxonomy — separate, still-open gap

79 distinct raw category labels across brands (e.g. "Tops" / "Tops & Tees" / "T-Shirts" never unified into one canonical taxonomy per brand mapping table, per Master Plan §6.3). 61 of 79 fall below the "≥300 products" floor (§6.1) — some genuinely thin, some just fragmented labels for the same real category. Not addressed in this pass.

## Verification performed

- `scripts/(C)_coverage_report.py` before/after every change — brand × gender breakdown.
- `scripts/test_search.py` — confirmed real, correct retrieval against the rebuilt local FAISS index (surfaced a Carrot Kids result on a test query, proving new brands are genuinely searchable, not just present in the index file).
- Zero orphan files (every file on disk has a metadata row; every non-orphan metadata row has a file).

## Explicitly out of scope (this pass)

- No synthetic/image-level augmentation — real data growth only.
- Supabase migration prepped but not run (see gap above).
- Category taxonomy unification.
- The `locallyeg.com` client-rendered API (would need a real browser/devtools session to crack, not available in this environment).
