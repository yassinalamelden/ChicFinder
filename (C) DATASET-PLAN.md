# Dataset Cleanup & Brand Expansion — Plan

> Created by Claude (`(C)` prefix per `CLAUDE.md`) on branch `data/dataset-cleanup-and-brand-expansion`.
> Companion to `ChicFinder-Master-Plan.md` §6 (Dataset quality) — this doc is the working plan for one concrete pass of that contract: drop an underperforming brand, add local women's/kids' brands to fix the gender skew, rebuild the index, and measure.

---

## Why

Measured directly from `data/metadata.jsonl` (11,464 image records, local files — confirmed as the active source of truth, not Supabase, for this pass):

**By gender:**
| Gender | Count | Share |
|---|---|---|
| Men | 6,551 | 57.1% |
| Kids | 2,499 | 21.8% |
| Women | 2,414 | 21.1% |

**By brand:**
| Brand | Count | Share |
|---|---|---|
| concrete | 2,782 | 24.3% ⚠️ over the 20% cap from Master Plan §6.1 |
| mobaco | 1,605 | 14.0% |
| ravin | 1,542 | 13.5% |
| in_your_shoe | 1,454 | 12.7% |
| Tomato Store | 1,359 | 11.9% |
| **activ** | **1,190** | **10.4% → being removed** |
| Town Team | 1,145 | 10.0% |
| asili | 255 | 2.2% |
| defacto | 82 | 0.7% |
| y_studios | 50 | 0.4% |

This matches the "gender skew" and "balance" issues already flagged in `ChicFinder-Master-Plan.md` §6.1 / §6.1.1. Per that doc's own rule, image augmentation does **not** fix imbalance — only real acquisition does. The fix here: (1) drop `activ`, (2) scrape real product data from local Egyptian brands that skew toward women's/kids' wear, (3) rebuild the index, (4) measure again with a reusable coverage report.

---

## New brands

Verified live via their JSON APIs (real, currently-operating Egyptian local stores — no synthetic/AI-generated data, per Master Plan ethics §6.6):

| Brand | Segment | Platform | API confirmed |
|---|---|---|---|
| **BOHEME** (bohemeshop.net) | Women's (boho/dresses) | Shopify | `/products.json` ✅ vendor="BOHEME" |
| **OR** (or-egypt.com) | Unisex, young adult casual | Shopify | `/products.json` ✅ vendor="OR" |
| **Solang** (solangshop.com) | Kids | Shopify | `/products.json` ✅ vendor="Solang" |
| **Carrot Kids** (carrotegypt.com) | Kids (3mo–16y) | WooCommerce | `/wp-json/wc/store/v1/products` ✅ |

**Bonus source — `locallyeg.com`**: a curated multi-brand marketplace covering 14+ local Egyptian brands (Studio L, Yonyo, Psych, Denjoe, Vega, 47, Black Edition, Jiggy & Co, Seemly, XC, Eighties, Richness, Dapperz, Hayah) across Women/Men/Kids — potentially bigger than the 4 above combined. Unlike the Shopify/WooCommerce stores, it's client-side-rendered with no discoverable JSON API from static fetching, so its real product API needs finding via browser devtools/network tab before a scraper can be written. Treated as a priority investigation, not a blocking dependency.

---

## Steps

### Step 1 — Remove `activ`
New script `scripts/(C)_remove_brand.py`:
- Filters `activ` out of `data/metadata.jsonl` (match on `source`/`brand`, case-insensitive).
- Rebuilds `data/metadata.json` by re-running `scripts/01b_ingest_barawy_data.py` (already idempotent/source-agnostic, rebuilds from `metadata.jsonl` each run).
- Deletes `data/raw_images/activ_activ_*` files (verified filename prefix).
- FAISS index rows are dropped as part of the Step 4 rebuild (no in-place delete in `IndexFlatIP`).
- Prints a before/after count.

### Step 2a — Investigate `locallyeg.com`'s real product API
Browser devtools/network tab, capture the real XHR/fetch endpoint, confirm schema + pagination + auth needs.
- Clean JSON API found → `scrapers/(C)_scrape_locally.py`, same output schema as the others.
- No clean API → fall back to HTML scraping with `BeautifulSoup` (needs adding to `requirements.txt`), respecting `robots.txt`.

### Step 2b — New scrapers for the 4 confirmed brands
Same pattern as `scrapers/scrape_tomato.py` (Shopify) / `scrapers/scrape_mobaco.py` (WooCommerce). Output schema: `source, product_id, title, brand, category, subcategory, price, availability, image_urls, product_url, description, scraped_at` → `data/raw/<brand>.jsonl`.
- `scrapers/(C)_scrape_boheme.py`
- `scrapers/(C)_scrape_or.py`
- `scrapers/(C)_scrape_solang.py`
- `scrapers/(C)_scrape_carrot.py`

Same politeness as existing scrapers: 0.5s delay between requests, standard `User-Agent`, no auth bypass.

### Step 3 — Merge & ingest
- Extend `scrapers/merge_and_clean.py` to include the new `data/raw/*.jsonl` files alongside the existing 3 (non-`(C)` file edit, pre-approved as part of this plan).
- Append merged records into `data/metadata.jsonl` (after Step 1 removal).
- Re-run `scripts/01b_ingest_barawy_data.py` to download only the new images and rebuild `metadata.json`.

### Step 4 — Rebuild the local FAISS index
`scripts/build_database.py` is currently broken (imports missing `ai_engine/embeddings/database_builder.py`). New script `scripts/(C)_build_faiss_index.py`:
- Encodes every file in `data/raw_images/` with `FashionCLIPEncoder` (`ai_engine/embeddings/encoder.py` — no changes needed).
- Writes a fresh `IndexFlatIP` to `data/embeddings.index` + matching `data/index_to_image_id.json`.

### Step 5 — Coverage report
New script `scripts/(C)_coverage_report.py` — reusable brand × gender breakdown (this is literally what Master Plan §6.1 asks for as a standing artifact). Confirms `activ` at 0, gender split less skewed, `concrete`'s share diluted toward the 20% target.

---

## Verification
1. `scripts/(C)_coverage_report.py` before/after.
2. `scripts/test_pipeline.py` and `scripts/test_search.py` against the rebuilt index.
3. Spot-check new images open correctly and match metadata.

## Out of scope (this pass)
- No synthetic/image-level augmentation — real data growth only.
- Supabase untouched (local files are the confirmed active source of truth for this pass; `scripts/03_migrate_to_supabase.py` is a separate follow-up if that changes).
- `locallyeg.com` is a bonus source, not a blocker for the rest of the plan.
