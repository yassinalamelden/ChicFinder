# ChicFinder — Master Plan & Vision (Canonical Document)

> **Single source of truth** for everything decided and envisioned for ChicFinder, as of 2026-07-08.
> **How to use:** the team does the thinking and the work; tooling scaffolds and verifies. Where any summary doc differs from this file, **this file wins.** File home: `docs/MASTER-PLAN.md`.

---

# PART 1 — Mission and strategy

## 1.1 End state (locked)

A **mix of portfolio piece and real product**: the deployed v1 IS the user experiment. Three deliverables by October 2026:
1. **Live product**: secured FastAPI backend + Next.js web + Android app (Play closed testing), used by 40–50 real users.
2. **JAC paper submission** built on that deployment, its experiments, and its user study.
3. **Captured vision**: this document + a GitHub Projects backlog board, so nothing imagined is lost and nothing unvalidated is built.

## 1.2 Deadline hierarchy (when things slip, they slip DOWN this list)

1. Paper submission (October — exact date pending B1)
2. Live app with real users (deploy freeze ~Aug 31; study runs September)
3. Everything else

## 1.3 North Star

**The fashion discovery and shopping layer for Egyptian local brands.** Photo in → "where to buy this look in Egypt, in stock, at my budget" out.

JTBD: *"When I see an outfit I like on Instagram/TikTok, I want to find where to buy something similar in Egypt, at my budget, so I don't spend an evening scrolling store pages."* What users currently "hire": asking friends, scrolling brand Instagrams.

## 1.4 Moat ranking — invest in this order, always

1. **Click/preference data flywheel** — events → training signal → better retrieval → more clicks. Proprietary Egyptian fashion preference data nobody else can collect.
2. **Brand relationships + fresh inventory feeds** — legalizes and outclasses scraping.
3. **The Egyptian fashion dataset** (10k+ products, growing; modest-wear as first-class categories — no Western dataset does this).
4. **Pipeline code** — least defensible; anyone can wire CLIP to a vision LLM. **Never spend differentiation budget here.**

Summary principle: **boring tech, exciting data.** (Applied consistently, this principle auto-answers vector-store migrations, backend-language switches, and rewrite temptations.)

## 1.5 Truth about current state

- ChicFinder was a **university course project finished to discussion standard** — not "production-ready." Production v1 starts now.
- Users so far: only the founding team. Zero external users.
- Catalog: ~10k products scraped from local brands. Never refreshed; no in_stock tracking.
- Cost per recommendation: **unknown** (2 GPT-4o Vision calls per request, one carrying ~25 candidate images). Pull from the model-provider dashboard — unowned, assign it.
- Repos out of sync: the GitHub repo (Supabase pgvector) vs a local copy (FAISS). Which is truth = blocker B5.

---

# PART 2 — Locked decisions (with the why — do not relitigate before November)

| Decision | Why | Status |
|---|---|---|
| **Backend = FastAPI, FROZEN until after October.** No Node/Express this cycle. | AI pipeline is Python; a backend is client-agnostic so Express does nothing for mobile; no named pain justifies a rewrite. Express motive never established — do not reopen before the November design doc. | LOCKED |
| **Vector index = Supabase pgvector, permanently this cycle.** | 10k products × 512-dim ≈ 20 MB. Compression/scale-oriented indexes solve problems 1000× this size. No further vector-store migration. Any new index = an optional benchmark write-up, nothing shipped. | LOCKED |
| **Native Android app, exactly 4 screens** (sign-in, upload, results, store click-out), React Native or Flutter (builder's choice). iOS deferred — web is the iOS answer. | Egypt ~85%+ Android; thin client on the same `/api/v1`; a 5th screen before October = scope alarm. | LOCKED |
| **Play Store closed testing track = the user study.** | Google requires new personal dev accounts to run closed testing (12+ testers/14 days) before production anyway — the 40–50 cohort satisfies it; production listing becomes a button press post-study. | LOCKED |
| **Mobile app = one single accountable owner.** That owner is on the app; whoever owns backend/study/paper is fully OFF mobile by August. | Split ownership = no ownership; the study + paper owner cannot also learn a mobile framework in the same weeks. | LOCKED |
| **User study: 40–50 connections.** Convenience sample — MUST be disclosed in the paper. Cold link/install, no guided demos; measure behavior, not opinions; **unprompted return visits = the honest metric** (friends click to be polite). | n≈50 carries weight in an applied venue; politeness bias mitigated by behavioral metrics. | LOCKED |
| **Full rework / "production-grade system design" before October: VETOED.** | 7.5 weeks, small part-time team; invisible to users AND reviewers; the paper deadline settles it by arithmetic. System design = November DOC with 50 users of operational evidence, then strangler-fig only what measurably hurts. | LOCKED |
| **Brand vision calibrated**: "every local brand in Egypt" → 2–3 brand conversations AFTER the study produces a number. | The scraped catalog + traffic data IS the pitch; partnerships also legalize the scraped-gray data. | LOCKED |
| Auth strategy: leaning Firebase everywhere (ChicFinder already Firebase). | Free social login/reset/verification = undifferentiated work. | OPEN — confirm (B4) |

---

# PART 3 — Blockers (close before/during Sprint 1)

| # | Question | Why it gates | Owner role |
|---|---|---|---|
| B1 | **JAC exact CFP link, submission date, page limit, review type** | The entire calendar is pinned to "October" — a guess. Mid-Sept reality would compress everything. | Paper owner |
| B2 | **Faculty supervisor co-authoring?** | Acceptance odds + rigor; recruiting one is a week-1 action if none. | Paper owner |
| B3 | **Does the mobile owner know RN or Flutter?** | If not: plan absorbs ~2 learning weeks in July; S2–S3 app tasks shift right. | Mobile owner |
| B4 | **Auth strategy confirmation** (Firebase everywhere?) | Touches every client. | Backend owner |
| B5 | **Which repo is truth** (GitHub/pgvector vs local/FAISS)? | Deep work on the wrong repo is wasted; Sprint 1 DB task changes if FAISS. | Repo owner |
| B6 | **Push access / collaborator rights** | Fork vs collaborator setup before any commit. | Repo owner |

**B5 and B6 gate ALL deep work. Do them first.**
**Suggested role split:** backend security + DB + experiments (backend owner); Android app (mobile owner); scraper/data pipeline + web polish (data/repo owner); study + paper (paper owner). One person may hold more than one role, but each role has exactly one accountable name.

---

# PART 4 — The paper

## 4.1 Contribution (decide final framing week 1 — it shapes what gets measured)

Re-implementing OutfitAI (Multimedia Tools and Applications, 2025) is not a paper — reviewers check. Cite it as the base; claim the delta:

1. **A 10k-product Egyptian local-brand fashion dataset** — novel; includes modest-wear taxonomy no Western dataset treats properly.
2. **Domain-adapted FashionCLIP** — fine-tune vs stock CLIP, with retrieval numbers.
3. **Cost/quality rerank ablation** — vision-rerank-25 vs CLIP-prune→cheap-rerank-8: cost/request vs relevance. (Same work as the production cost fix — one effort, two payoffs.)
4. **User study in an underserved market** (n≈50, convenience sample disclosed).

Frame: *"An adaptation and production deployment of OutfitAI for the Egyptian market: dataset, domain tuning, cost analysis, and a user study."*

## 4.2 User study design

- **Cohort**: 40–50 connections. Recruit people who actually shop fashion, not polite acquaintances. **Recruiting starts in August**, not September.
- **Protocol**: cold install link (Play closed track) or web URL. No guided demos, no "try this photo." Consent note at sign-up (data use for research).
- **Measured (behavioral, from the events table)**: recommendations requested/user, click-through rate to stores, **unprompted return visits**, web-vs-android split (`client` column), session depth.
- **Asked (questionnaire, end of study)**: short SUS-style usability items + "would you install this as a full app?" + "what did you expect that it didn't do?" (feeds the backlog).
- **Duration**: ~3 weeks (Sep 1–25), satisfying Google's 14-day closed-testing minimum.
- **Disclosures in paper**: convenience sampling, cohort composition, Egypt-only.

## 4.3 Paper section → workstream mapping

| Paper section | Produced by |
|---|---|
| Dataset | Part 6 dataset workstream (stats table, quality metrics, taxonomy) |
| System | Existing architecture + S1–S4 hardening (describe as deployed, not aspirational) |
| Experiments | `experiments.md` rows from S2–S3 (cost baseline, CLIP-prune ablation, model swap, eval harness numbers) |
| User study | S5 events data + questionnaire |
| Related work | OutfitAI + fashion-retrieval literature (write in S5 gaps) |

**Global rule: an unlogged experiment is a lost paper table.** Every run gets an `experiments.md` row: ID, date, hypothesis, one-variable change, data version, metrics, result, verdict.

---

# PART 5 — Execution: sprints (2 weeks each, one goal sentence)

## Sprint 1 — Jul 8–21 · "The dangerous endpoints are safe and the data has a real home."

Code-level detail (reviewed at file:line). TDD throughout; per endpoint: tests green → docs → commit → tag.

### Track A — ChicFinder security

**A1. Auth + rate limit on `/recommend` (cost-DoS fix) — the #1 fix in the whole plan**
- Files: `api/routes/recommend.py` (~line 41); test `tests/api/test_recommend_auth.py` (new).
- Why: endpoint is unauthenticated, fires GPT-4o Vision twice per call, no rate limiting anywhere in the repo → any bot drains the provider budget. `require_auth` (Firebase) already exists in `api/dependencies/auth.py`; it simply isn't applied here.
- Steps: (1) failing test: POST without `Authorization` → expect 401; (2) confirm it fails; (3) add `Depends(require_auth)` to the route; (4) green; (5) failing test: request N+1 in window → 429; (6) add `slowapi`, per-user limit (start `10/minute`, tune from study traffic); (7) green + authed-under-limit still 200; (8) commit `fix(security): require auth + rate limit on /recommend`.
- Also: `auth.py:68,71` leak exception detail into 401 bodies (`f"Auth error: {type(e).__name__}: {e}"`) — replace with generic messages, keep detail in logs (upstream errors never leak internals).

**A2. Provider decision**: repo carries `OPENAI_API_KEY` + `GEMINI_API_KEY` both load-bearing. Pick one primary, make the other an explicit fallback path.

### Track B — Hotel-Booking security (interleaved — live liabilities in production)

**B1. Close the auth-free admin router**: `backend/app/api/admin_routes.py` (docstring: "auth-free for development") is mounted at `/api/admin` (`main.py:37`) — every booking's guest PII + room CRUD unauthenticated. A protected twin exists (`v1/admin.py`, `get_current_admin`). Preferred: DELETE the old router, route through v1 (kills a duplicate surface). TDD: 401-no-token / 403-non-admin tests first.
**B2. `SECRET_KEY` fail-fast**: `core/config.py:49` defaults to `"CHANGE_ME_IN_PRODUCTION"` → forgeable JWTs if env unset. Remove default; raise on unset/sentinel. Test: startup raises on sentinel.
**B3. CORS lock**: `main.py:26` `allow_origins=["*"]` → real frontend origin via env.
(Hotel gotchas: payment webhook already verifies HMAC — don't "fix" it; `/api/payments/checkout` is unauthenticated + on `mock_booking_repo` — that's unfinished, not broken; two parallel route generations `*_routes.py` vs `v1/` — never add features to the old surface.)

### Track C — Database

**C1. Four tables** (Alembic migration; replaces in-memory `products.json`):
- `stores` (id, name, url, **partnership_status**: scraped|contacted|partner)
- `products` (id, store_id FK, name, description, price, currency, image_url, product_url, category, gender, color, **season/occasion** tags, **in_stock** bool, **first_seen_at**, **last_seen_at**)
- `product_embeddings` (product_id FK, embedding vector(512))
- `events` (id, user_id, product_id, **event_type**: impression|click_through, **client**: web|android, created_at)
- Why each: `in_stock`/`last_seen_at` = freshness (stale products would poison the study metric); `partnership_status` = makes the future partner-brands section a query filter, not a build; `season/occasion` = Ramadan/Eid retail rhythm, enables Stage-1 collections; **`events` is sacred — it is simultaneously the paper's study data and the future ML training set.** Retrieval filters `WHERE in_stock = true`.

### Track D — Mobile start
Framework choice (B3), project scaffold, Firebase sign-in screen against the real API.

**Exit criteria**: no unauthenticated expensive/admin endpoint in either repo; SECRET_KEY required; DB-backed catalog with events flowing; B1–B6 answered.

## Sprint 2 — Jul 22–Aug 4 · "Recommendations are fresh and cheap, and the app talks to the backend."

- **Freshness cron**: weekly re-scrape; upsert products; stamp `last_seen_at`; unseen-for-N-runs → `in_stock=false`. NOT real-time inventory.
- **Ingest validation** (same scraper code): EGP price sanity ranges; image URL resolves + decodes + ≥512px shorter side; required fields non-null. Bad rows never enter.
- **Dedup pass**: pHash + embedding-cosine threshold. Duplicates inflate eval metrics and leak across train/test splits — correctness, not cosmetics. Report dedup rate (paper stat).
- **Canonical taxonomy**: ~25 categories incl. modest-wear/hijabs/abayas as first-class; per-store mapping table.
- **Cost baseline**: pull actual cost/rec from the provider dashboard → `experiments.md` row #1.
- **CLIP-prune experiment**: fine-tuned FashionCLIP scores prune rerank candidates 25→~8; cheap vision model reranks. Candidates (July 2026 prices): GPT-5 Mini ($0.25/$2.00 per M tokens), Gemini 2.5 Flash ($0.30/$2.50). Log cost + relevance vs baseline. Optional: image-hash result cache (repeat photo skips the model calls).
- **App screens 1–2**: sign-in, upload → live `/api/v1`.

## Sprint 3 — Aug 5–18 · "We can prove quality with numbers, and the app is feature-complete."

- **Eval harness**: query set = real outfit photos (phone/Instagram-style — NOT catalog images; the distribution shift is the point). Pool top-k from pipeline variants; 3-annotator graded relevance; then **frozen forever** (tuning on the eval set makes it measure nothing). Metrics: recall@k / nDCG@5, rerank win-rate.
- **Label spot-check**: random 200 products, 3 annotators on category/color, report inter-annotator agreement (kappa) in the paper; fix systematic errors found.
- **Coverage report**: distribution across category × gender × price tier × brand; targeted re-scraping for gaps.
- **Train/test splits** (before any fine-tuning): by product (never by image), stratified brand × category; plus small **held-out-brands** set → generalization table for the paper. Dedup runs first (leakage).
- **Model-swap decision**: lock production model from logged S2–S3 rows. Decision rule: cheapest within an agreed relevance tolerance of baseline — switch on the logged number, never on price alone.
- **App screens 3–4**: results, store click-out; `client=android` events verified end-to-end from both clients.

## Sprint 4 — Aug 19–31 · "Deployed, hardened, frozen." ← THE deploy deadline

- Prod env hardening: all env vars set (no sentinels), Sentry live, **cost dashboard live** (cost/rec is a permanent KPI), health checks, HTTPS, upload cap confirmed (10MB/413 exists), DB backups on.
- Play closed testing configured; tester list loaded.
- **Dataset v1.0 freeze**: checksummed snapshot + stats table (N products/brands, category/gender/price distributions, image stats, dedup rate, label kappa) → the paper's dataset section, done before the study starts.
- 5-user pilot; fix what breaks.
- **FREEZE**: after Aug 31, bugfixes only. "One more thing" = the failure mode. Stop.

## Sprint 5 — Sep 1–25 · "The study runs and the data is clean."

- Study live to 40–50 users (recruited during August). Bugfixes only. Watch events fill; watch cost/day.
- Draft paper Methods + Related Work (system & study design are fresh; OutfitAI cited as base).

## Sprint 6 — Sep 26 → submission · "Analysis and paper."

- Analyze: CTR, return rate, client split, cost/rec; questionnaire synthesis.
- Assemble tables: dataset stats, domain-tuning results, cost/quality ablation, study results.
- Write → supervisor review (B2) → submit to JAC.

## Parallel tracks summary

| Track | Owner role | Notes |
|---|---|---|
| Backend security + DB + experiments | Backend owner | Off mobile from August |
| Android app (4 screens) | Mobile owner | Starts S1 against existing API; +2 learning weeks if B3 negative |
| Scraper/data pipeline + web polish | Data/repo owner | Owns the repo |
| Study + paper | Paper owner | Recruiting in August; writing S5–S6 |

---

# PART 6 — Dataset quality (the "really good dataset" contract)

The two known problem areas are **balance** and **cleanliness** — they get full treatment first (6.1, 6.2). The remaining dimensions follow (6.3), then splits/eval/versioning (6.4), automation gates (6.5), and ethics (6.6). Every subsection produces a number for the paper's dataset section.

## 6.1 Balance — the #1 known issue

**Step 1: measure before fixing.** Build the coverage report first: full distribution across **category × gender × price tier × brand**, plus two headline numbers — *largest brand share* and *smallest retained category count*. You cannot fix an imbalance you haven't quantified, and the report itself is a paper table.

**Step 2: define "balanced" numerically (proposed targets — adjust once the report exists):**
- No single brand > **20%** of the dataset.
- Every *retained* category ≥ **300 products** (below that, retrieval quality in the category is noise).
- Both genders ≥ 25% within any category where both plausibly exist.
- Each of 3–4 price tiers (define in EGP quartiles) ≥ 15% overall.

**Step 3: fix in this order (acquisition beats math):**
1. **Targeted acquisition — the primary fix.** Scrape *new stores* that serve the thin categories/genders/price tiers; deepen pagination on thin categories in existing stores. Balance problems are best solved with more of the missing data, not less of the plentiful data.
2. **Consolidate or honestly drop.** Merge sparse subcategories into parents (per the taxonomy). A category that can't reach the floor gets **dropped and disclosed** ("dataset covers N categories; X excluded for insufficient coverage") — a smaller honest scope beats a padded fake one; reviewers reward the former and catch the latter.
3. **Training-time mitigation** (only for residual imbalance acquisition can't fix): stratified batch sampling with **inverse-frequency capping** — *cap* the over-represented classes rather than heavily oversampling rare ones (oversampling small classes = memorizing duplicates). Alternative: class-weighted loss. Log whichever is used as an experiment row (it's an ablation table).
4. **Eval-time discipline so imbalance can't hide**: report **macro-averaged metrics alongside micro** (per-category and per-brand breakdowns). A model that's great on the dominant brand and terrible elsewhere shows up in macro, hides in micro.
- **What does NOT fix balance:** image augmentation (crops/flips increase visual diversity, not representation) and synthetic/AI-generated products (instant credibility kill in a dataset paper — never).
- **Balance is a pipeline property, not a one-time fix.** The weekly freshness cron changes the distribution every run — so the coverage report runs automatically after every scrape, with drift alerts (e.g., any brand share moving >5 points).

### 6.1.1 KNOWN ISSUE — gender skew: catalog is mostly men's products; system recommends men's clothes regardless of query

**Two candidate causes produce this same symptom — diagnose before fixing (one logged experiment, ~a day):**
- **(a) Retrieval-pool composition**: KNN can only return what's in the index. If ~80% of candidates are men's items, even a *perfect* encoder returns mostly men's items. Not a learning failure — an inventory failure surfacing at retrieval.
- **(b) Encoder degradation from skewed fine-tuning**: contrastive fine-tuning on mostly-men's data can collapse gender-distinguishing structure in embedding space.
- **Diagnosis experiments** (both are `experiments.md` rows): (1) run the same women's-item queries against STOCK FashionCLIP on the same index — if stock also returns men's items, the problem is (a), not the model; (2) re-run against a women-only slice of the index — if results become sensible, the encoder differentiates fine and the fix is filtering + acquisition, not retraining.

**Fix layers, in order of cost (do them in this order):**
1. **Hard metadata filtering at retrieval (days, ships in S2 — likely kills most of the symptom).** The parse stage (vision LLM) already extracts item attributes — make it output gender; retrieval becomes `WHERE gender IN (…) AND in_stock` + vector ranking. pgvector lives in Postgres: metadata filtering + KNN in one SQL query is exactly why we're on it. **Principle: stop asking embeddings to do a database's job** — structured attributes (gender, category, price) are SQL filters; embeddings rank style similarity *within* the filtered slice. Category gets the same treatment (hard filter or strong boost; keep unisex items reachable via an `unisex` tag rather than loosening the gender filter).
2. **Targeted acquisition (the real fix, S2–S3 scraping).** Scrape women's-focused Egyptian brands until the 6.1 gender floors are met. Strategic note: Instagram-driven fashion discovery — the product's core use case — skews heavily female; a mostly-men's catalog is misaligned with the likely core user, so this acquisition is product strategy, not just ML hygiene.
3. **Model-level (ONLY if diagnosis shows (b), decided in S3 with the eval harness):** retrain the fine-tune with gender-stratified batches + inverse-frequency capping so contrastive negatives include cross-gender same-category pairs (teaches the separation); OR ship stock FashionCLIP + hard filters for v1 if it evals better — a skew-damaged fine-tune can lose to stock+filters. Never retrain on the same skewed data and expect a different result.
4. **Eval guardrails so the regression can't return silently**: add *gender-match rate of top-k vs query gender* and *category-match rate* to the S3 harness, reported per-gender (macro). Before/after numbers for filters and retraining = a strong paper ablation subsection ("handling catalog imbalance in production retrieval").

## 6.2 Cleanliness — the #2 known issue: a staged cleaning pipeline

Order matters — each stage assumes the previous ran. Every stage emits a metric into the per-scrape quality report.

1. **Ingest validation (reject at the door):** required fields non-null (image, price, brand, category, URL); price parses and falls within **per-category EGP bounds** (one global range is useless — a plausible abaya price and a plausible scarf price differ; maintain a small bounds table per category); URL resolves (HTTP 200); image decodes; ≥512px shorter side; sane aspect ratio. Rejected rows are logged with reasons, never silently dropped.
2. **Image-level cleaning:** detect **placeholder images** (stores serve "no image available" stock graphics — hash the known placeholders per store and reject matches); flag **collage/multi-garment images** (they poison single-item embeddings — a zero-shot CLIP check "a collage of multiple products" vs "a single clothing item" works as a cheap classifier, route flags to human review); drop exact-duplicate images (pHash).
3. **Text-level cleaning:** strip HTML entities/tags from names and descriptions; Unicode-normalize mixed Arabic/English (NFC); strip marketing boilerplate prefixes ("NEW ARRIVAL!!", "خصم 50%"); normalize size vocabularies (S/M/L vs 36/38/40 → one scheme with the original preserved); one currency field, always EGP-normalized.
4. **Record-level dedup:** canonical-URL rules per store (same product, different query params); then near-duplicate detection via pHash + embedding-cosine threshold. **Decision required — colorway policy:** recommended: *one product row + a variants field* (retrieval may show variants; eval and stats count one product). Whatever is chosen, apply it before splits and state it in the paper.
5. **Label auditing (don't trust scraped labels):** zero-shot CLIP as an *auditor* — compare each image against its claimed canonical category; agreement below threshold → human review queue. Auto-flag, never auto-fix (the flag rate is itself a reported data-quality stat).
6. **Embedding-space outlier sweep:** items whose embedding sits far from their category centroid are mislabeled, miscategorized, or junk — top-N outliers per category go to the review queue. Cheap to run (embeddings already exist for retrieval).
7. **Recurring human QA:** the 200-sample 3-annotator spot-check runs on dataset v1.0 (kappa reported in the paper), then a smaller sample per subsequent scrape batch — track the error rate *over time*, not once.

**Tooling (keep it boring):** pandas + Pillow for checks, `imagehash` for pHash, existing FashionCLIP embeddings for cosine/outlier/audit work. No new infrastructure.

## 6.3 Remaining quality dimensions (expanded)

- **Completeness:** field-level fill-rate table (not one aggregate number — "98% have price, 60% have color" is actionable; a single "85% complete" is not). Imputation policy: **never impute price or category** (silent poison); optional fields (color, description) may stay null and models must tolerate it.
- **Consistency/taxonomy governance:** the ~25-category canonical taxonomy (modest-wear, hijabs, abayas first-class) is **versioned**; any change re-runs every store mapping + the balance report. Per-store mapping tables live in the repo, reviewed like code — taxonomy drift between scrapes is a silent killer of comparability across experiments.
- **Label accuracy:** kappa target ≥ 0.75 on the spot-check; disagreements resolved by discussion + a written adjudication rule (so the next batch is judged the same way); systematic errors found (e.g., one store's "dresses" are actually mixed) get fixed in the mapping table, not by hand-editing rows.

## 6.4 Splits, eval set, versioning (expanded)

- **Split order is law:** clean → dedup → *then* split, **by product, never by image**, stratified by brand × category. Colorway variants stay on one side of the split (the variants policy makes this automatic). Plus a small **held-out-brands** split → the generalization table.
- **Eval set:** queries are real outfit photos (phone/Instagram-style — the distribution shift from catalog images is the point); candidates pooled from multiple pipeline variants; 3-annotator graded relevance; **frozen forever** after construction — tuning against it makes it measure nothing.
- **Versioning:** dataset v1.0 = checksummed snapshot at the S4 freeze, with a changelog (what was added/dropped/re-labeled since raw scrape); every `experiments.md` row records the data version; the paper reports against v1.0 only.

## 6.5 Automation: quality gates on the pipeline

The scraper cron doesn't just fetch — it **fails loudly**: if a run's reject rate, dedup rate, or any brand share drifts beyond thresholds, the run is marked failed and the report says why. Rationale: a store silently changing its page layout breaks scrapers *quietly* — garbage flows in for weeks unnoticed. The gate converts silent corruption into a visible failed run. The quality report (balance + cleaning metrics) regenerates on every run and is diffable between runs.

## 6.6 Ethics/licensing (unchanged in substance)

Methodology + statistics publish freely; any dataset release is URL+metadata or gated access (never redistribute scraped images); brand partnerships convert scraped-gray data into a licensable asset (possible paper #2 / community resource, with brand consent).

---

# PART 7 — Post-October vision (evidence-gated stages; NOTHING here starts before October)

Each stage opens only when its **trigger metric** is real. This gate list is the anti-perfectionism mechanism at product scale.

## Stage 0 — Paper MVP (now → Oct, ≤100 users) — FROZEN = Part 5 above.

## Stage 1 — Post-paper product
*Triggers: study CTR validates the JTBD; ≥30% unprompted return; a brand says yes.*
- **Product**: Arabic + RTL (Egyptian mass market is Arabic-first — do not defer past this stage; retrofitting RTL is misery), favorites/wardrobe-lite, price + size filters, iOS via RN reuse, Instagram/TikTok share-sheet intake, **partner-brands showcase section** (trigger: first signed brand — until then there is nothing to showcase; `partnership_status` makes it a filter + one screen).
- **Architecture** (monolith stays; seams sharpen): AI pipeline behind a clean internal interface; recommendations become async jobs (upload → job id → poll/push) so p95 stops being hostage to GPT latency; Redis for image-hash cache + rate limits; seasonal retrieval boosting.
- **Node/BFF question answered by evidence here** (November doc): if the main non-AI contributors are JS-native → Node BFF in front of the Python AI service; else stay pure FastAPI.

## Stage 2 — The flywheel business
*Triggers: retention curve exists; ≥3 brand partners; catalog >100k items.*
- **ML**: fine-tune CLIP v2 on OWN click data — the events table becomes the training set; the moat compounds. Hybrid retrieval (text + vector). pgvector honestly holds to ~1M vectors; only then evaluate a dedicated store, by measurement.
- **Architecture**: extract AI inference service (serverless GPU / dedicated box; batch embedding pipeline), image CDN (Egyptian bandwidth), replicas/partitioning only when p95 says so.
- **Dataset release** as licensed academic asset (brand consent) → citations + brand-pitch credibility.

## Stage 3 — Expansion (dream tier)
*Trigger: Egypt works and pays.* Outfit completion, wardrobe assistant, size/fit intelligence (Egyptian sizing chaos = real unsolved pain), Gulf expansion (multi-tenant catalog), try-on only if everything else is boring.

---

# PART 8 — Add-on catalog (backlog cards; every one gated; none pre-October)

## 8.1 Revenue add-ons, ranked
**Governing principle: monetize brands, not consumers, until data says otherwise** (Egyptian consumer subscription willingness is low; the flywheel needs user volume; brands have budgets and no digital alternatives).

1. **Affiliate via promo codes** *(Stage 1, first brand)* — local brands lack affiliate infra; a per-ChicFinder promo code is the attribution MVP; upgrade to UTM/API later.
2. **Sponsored placement** *(Stage 1–2)* — boosted ranking, always labeled, volume-capped (the cap protects the trust that makes placement sellable).
3. **Brand analytics dashboard** *(Stage 2)* — recurring B2B: demand intelligence (search/click/ignore × category × price × season). No local substitute exists; pure exhaust from the events table. Possibly the biggest line.
4. **Collection-launch packages** *(Stage 2)* — targeted push + placement for drops (Eid/Ramadan collections); bundles with #2/#3 into one brand offer.
5. **Trend reports / data licensing** *(Stage 2)* — quarterly Egyptian fashion demand report; revenue + PR + pitch credibility.
6. **In-app checkout commission** *(Stage 3)* — cart + Paymob/COD, % of order. The e-commerce prize but drags logistics/returns/support. Parked hard.
7. **White-label visual search API** *(Stage 3)* — monetizes the least defensible asset; ranked accordingly.
8. **Consumer freemium** *(experiment tier — skeptical)* — if ever tried: EGP pricing, Vodafone Cash/Fawry rails, only after retention proves people would miss it.

## 8.2 Feature add-ons, ranked
**Selection filter: feeds the events flywheel + drives unprompted returns + cheap on existing infra.**

1. **Instagram/TikTok share-sheet intake** *(Stage 1)* — meets discovery where it lives; the growth loop; an intent-filter, not a subsystem.
2. **Price-drop / back-in-stock alerts** *(Stage 1)* — rides the freshness pipeline; manufactures return visits; alert subscriptions = intent data that later sells the analytics dashboard. Compounds into retention AND revenue.
3. **Budget mode + similar-but-cheaper toggle** *(Stage 1)* — "this look under 1500 EGP"; retrieval filters; maximum differentiation per line of code in the current Egyptian economy.
4. **Modest-wear / hijabi-first filter** *(Stage 1)* — the taxonomy already treats it first-class; huge underserved segment, near-zero cost.
5. **Occasion/season collections** *(Stage 1–2)* — Ramadan/Eid/wedding-guest feeds off S2 metadata.
6. **Wardrobe/closet** *(Stage 2)* → prerequisite for:
7. **Outfit completion** *(Stage 2)* — flagship ML feature; plausible paper #2.
8. **Personalized "for you" feed** *(Stage 2)* — first consumer of the click flywheel.
9. **Size/fit intelligence** *(Stage 3)* — start crowd-sourced ("runs small"), evolve to per-brand fit mapping.
10. **Referral loops** (only if freemium exists) · **AR try-on** (dream tier; expensive, off-moat) — parked.

**The interlock** (why this ordering is the business): alerts (F2) generate intent data that sells the dashboard (R3); wardrobe/completion (F6–7) raise basket relevance → affiliate value (R1); share-sheet (F1) grows the volume that makes everything sellable. Features feed data; data feeds revenue; the tech stays boring.

---

# PART 9 — Risks, out-of-scope, self-review

## Risk register
| Risk | Mitigation |
|---|---|
| JAC date earlier than assumed (B1 unknown) | Verify week 1; if mid-Sept, compress S3–S4 and shrink study to Google's 14-day minimum |
| Mobile owner doesn't know RN/Flutter (B3) | ~2 learning weeks absorbed in July; S2–S3 app tasks shift right; web app remains the fallback client for the study |
| No push access / wrong repo truth (B5/B6) | Resolve before ANY deep work |
| Study recruitment shortfall | Recruiting starts August (not September); 50 invited ≈ 30–35 active is still a valid study |
| Cost overrun during study | Cost dashboard + budget alert; cheap-model swap decided BEFORE study (S3) |
| Mobile owner bandwidth unknown | 4-screen scope is the buffer; web app is the fallback |
| Perfectionism relapse (scope keeps trying to grow: index swaps, backend rewrites, "production-grade design", extra screens) | This document's gates + freeze date + deadline hierarchy; a ship-check on every "one more thing" |

## Out of scope before November (the frozen list — reopening any of these requires accepting the paper slips)
Express/Node backend · iOS · screens beyond 4 · caching layers beyond optional image-hash · real-time inventory · microservices/AI-service extraction · vector-store migration · system redesign · every Part 8 card.

## Self-review (honest gaps)
- Sprints 2–6 are deliberately roadmap-level; each gets its bite-sized code-level plan at sprint start (writing code steps now for undecided tooling = fiction).
- Plan assumes B5 → pgvector repo; if the FAISS copy wins, S1 Track C changes substantially.
- Hotel-Booking is only covered for security fixes; its product plan (starting with "will the university administration allow real bookings?") is a separate effort.
- JAC venue requirements unverified (B1) — the single biggest calendar risk.
