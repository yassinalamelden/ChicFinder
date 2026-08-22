# ChicFinder — Production AWS Backend Migration

## Context

ChicFinder's backend currently runs entirely against local state: images in `data/raw_images/`, catalog metadata in flat JSON files (`data/metadata.json`, `products.json`, `stores.json`), and a FAISS index built and read from local disk. This works for local development but can't be deployed as a stable, persistent service, and there's no way to update the catalog without hand-editing files on whatever machine is running it.

The project's frontend delivery target has changed: the Next.js app in `FrontEnd/` will not be used going forward. Moamen is building a native mobile app end-to-end, and will take this backend over once it's production-ready. This spec defines what "production-ready" means here: a stable, AWS-hosted API with a real, updatable data warehouse, that Moamen can build and depend on without needing to understand or babysit the underlying infrastructure.

This also resolves the architectural ambiguity flagged in `ChicFinder-Master-Plan.md` as "blocker B5" (local FAISS vs. an earlier, abandoned Supabase-pgvector lineage on `main`) — this spec supersedes that question. FAISS is the permanent vector search engine; Supabase is not used anywhere in this design.

**Explicitly out of scope:** the `FrontEnd/` Next.js codebase (not touched, not deployed, not maintained further under this work), Supabase in any form (fresh AWS-native design instead), and the git-history/`main`-branch cleanup work from the prior session (unrelated).

## Goals

- The API (auth, `/recommend`, `/search`, `/stores`, `/health`) runs as a persistent, deployed AWS service Moamen's mobile app can depend on.
- The product catalog (images + item records) lives in AWS, not local files, and can be fully replaced (wiped and reseeded with a different dataset) at any time without code changes.
- Rebuilding the FAISS index after a catalog change never risks live-search downtime.
- Response latency stays low — the design shouldn't introduce new latency, and one known existing latency risk gets fixed as part of this work.
- Infrastructure is defined as code (CDK), not manual console clicks, so it's reproducible and reviewable.

## Prerequisites

- **AWS Agent Toolkit set up for this project** — following [the official setup instructions](https://raw.githubusercontent.com/aws/agent-toolkit-for-aws/refs/heads/main/setup-instructions/setup.md): AWS CLI v2, `aws login`, `aws configure agent-toolkit`, and the AWS MCP Server connection so Claude has direct AWS skill/MCP access for the CDK and deployment work below. (Already installed globally per prior setup on 2026-07-26 — this step is about confirming it's correctly configured/authenticated for whichever AWS account and region this project's resources will actually live in, not a from-scratch install.)

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │         Moamen's Mobile App               │
                    └──────────────────┬──────────────────────┘
                                       │ HTTPS (Firebase JWT)
                                       ▼
                    ┌─────────────────────────────────────────┐
                    │   ECS Fargate — API Service (FastAPI)     │
                    │   /recommend /search /stores /health      │
                    │   EFS mount: READ-ONLY                    │
                    └──────┬──────────────────────┬─────────────┘
                            │                       │
                    ┌───────▼───────┐      ┌────────▼────────┐
                    │  EFS Volume    │      │   RDS Postgres   │
                    │  FAISS index   │      │   item records   │
                    │ (loaded at     │      │  (brand, price,  │
                    │  boot, served  │      │   category, ...) │
                    │  from memory)  │      │                  │
                    └───────▲────────┘      └────────▲─────────┘
                            │ writes                  │ reads
                    ┌───────┴──────────────────────────┴────────┐
                    │  ECS Task — Index Builder                   │
                    │  (manually/schedule-triggered, not always-on)│
                    │  pulls catalog from RDS + S3, encodes with   │
                    │  FashionCLIP, writes fresh index to EFS      │
                    └───────────────────────┬─────────────────────┘
                                            │ reads images
                                    ┌───────▼────────┐
                                    │   S3 Bucket     │
                                    │  catalog images │
                                    │  (public-read)  │
                                    └─────────────────┘
```

## Components

### Data warehouse (AWS-native, no Supabase)

- **S3 bucket** — catalog product images. Public-read (these are non-sensitive product photos the mobile app renders directly; no presigned-URL complexity needed).
- **RDS Postgres** (small instance, e.g. `db.t4g.micro`) — single `items` table: `id`, `category`, `sub_category`, `color`, `style`, `brand`, `price`, `product_url`, `availability`, `image_key` (S3 key), `store_id`. Private subnet, same VPC as compute.
- Both are freshly designed for this purpose — no reuse of the old Supabase pgvector schema/client code from `main`/`Final-Product`.

### Compute

- **ECS Fargate — API service.** Runs the existing FastAPI app (`Dockerfile.api`, unchanged) as a persistent, always-on service behind a load balancer. Mounts the EFS volume **read-only**. Never rebuilds the index itself — only serves.
- **ECS task — index builder.** A separate task definition, not an always-on service. Triggered via `aws ecs run-task` (manually today; a schedule/webhook can be added later without changing this design). Pulls the full catalog from RDS + S3, re-runs FashionCLIP encoding (`ai_engine/embeddings/database_builder.py`, adapted to read from RDS/S3 instead of local files), writes fresh `embeddings.index` + `index_to_image_id.json` to the EFS volume.
- **App Runner was considered and rejected** — it still does not support EFS mounts (an open AWS feature request since 2021, unresolved as of this writing), which the EFS-backed persistent index requires. ECS Fargate has supported EFS since 2020 (platform version 1.4.0+).

### Why builder and server are split (not one service)

A single service that both serves live traffic and periodically rebuilds its own index would let a bad or slow rebuild affect live search. Splitting them means: the API is always serving from a known-good index; a failed or in-progress rebuild is invisible to users; rebuilds can be retried freely without any user-facing risk.

### Picking up a new index after a rebuild

FAISS loads into memory once at process startup. The builder task rewriting files on EFS does not get automatically picked up by an already-running API process. After a successful rebuild, trigger a normal **ECS rolling deployment** of the API service (`aws ecs update-service --force-new-deployment`) — new tasks boot with the fresh EFS-mounted index, ECS drains the old ones, zero downtime. No custom hot-reload/file-watcher logic is being built for this — it's unneeded complexity given ECS already does this natively. (If catalog swaps ever become frequent enough that a redeploy-per-swap is annoying, hot-reload can be revisited then — not now.)

### Metadata enrichment: per-request, not cached

Today's app caches `metadata.json` in memory at startup (`app.state.metadata`) and never refreshes it without a restart. This design replaces that with a per-request RDS query, scoped only to the item IDs FAISS actually returned (`WHERE id IN (...)`, typically 5-50 rows). Same-VPC RDS latency for this is single-digit milliseconds — cheap enough that the simplicity and always-fresh behavior beats cache-invalidation complexity. A side effect: updating an existing item's price/availability/etc. in RDS takes effect immediately, with no restart needed (only adding/removing items from the *vector search* itself requires the rebuild+redeploy cycle above, since that's what changes the FAISS index).

### Catalog seeding and full replacement

A new script, `scripts/seed_catalog.py`, is both the initial loader and the tool for any future full catalog replacement — there is no separate one-time "migration" script. It takes a local folder of images + a metadata file (same shape as today's `data/metadata.json`/`products.json`) and:

1. If `--wipe` is passed: empties the S3 bucket and `TRUNCATE`s the RDS `items` table.
2. Uploads each image to S3, recording its key.
3. Inserts one row per item into RDS.

A full catalog swap is three commands:

```bash
python scripts/seed_catalog.py --images ./new_catalog/images --metadata ./new_catalog/metadata.json --wipe
aws ecs run-task --cluster chicfinder --task-definition chicfinder-index-builder
aws ecs update-service --cluster chicfinder --service chicfinder-api --force-new-deployment
```

### Infrastructure as code

One AWS CDK (Python) stack, per the project's standing AWS guidance (prefer CDK/CloudFormation over manual console work or Terraform): VPC, RDS instance, S3 bucket, EFS volume, the two ECS task definitions/services, IAM roles, and Secrets Manager entries for `OPENROUTER_API_KEY`, DB credentials, and Firebase credentials. Choosing CDK over raw CloudFormation because it lets infra be written in Python, consistent with the rest of the stack — no new language/tooling for whoever maintains this.

### CI/CD

Extend the existing `.github/workflows/ci.yml`: build the API image, push to ECR, update the Fargate service. Same trigger model (push to a deploy branch) as whatever's already configured there.

## Performance

The AWS additions (S3/RDS/EFS/ECS) do not introduce meaningful latency — same-VPC RDS queries are single-digit milliseconds, and FAISS continues to be loaded fully into memory at boot, so search itself is unaffected by moving from local disk to EFS.

The one real latency risk in the system today is independent of this migration: `RAGPipeline.run()` (`ai_engine/rag/pipeline.py`) calls `VisionReranker.rerank()` **sequentially, once per outfit item** detected by `OutfitParser`. Each Gemini-via-OpenRouter call realistically costs 1-4+ seconds; a photo with 3 detected items (e.g. shirt + pants + shoes) means those calls stack sequentially, potentially 3-12+ seconds for one search.

**Fix included in this work:** parallelize the per-item reranking calls (e.g. `asyncio.gather` over `run_in_threadpool(reranker.rerank, ...)` per item, matching the `run_in_threadpool` pattern already used in `api/routes/search.py`) so total added latency becomes the slowest single item's call, not the sum of all items. This is the only pipeline-latency change included in this spec — an explicit timeout-with-fallback and exposing the existing `skip_reranking` flag were both considered and explicitly deferred to a possible future follow-up, not part of this work.

## What doesn't change

Firebase JWT auth, the `/api/v1/...` API contract shape, the FAISS search logic and `IndexFlatIP` cosine similarity approach, and the Gemini/OpenRouter RAG pipeline's actual parsing/reranking logic (aside from the parallelization fix above) — all stay exactly as built and verified in the prior session.

## Open items for the implementation plan

- Exact RDS instance sizing and Multi-AZ decision (single-AZ is likely fine to start, given this isn't yet at production traffic scale).
- Whether the index builder task should get a schedule (e.g. nightly) now or stay manual-only until there's a real need.
- CloudFront in front of the S3 bucket — not included now, worth revisiting if image load times from the mobile app become a concern.
