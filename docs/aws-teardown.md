# AWS teardown runbook

Full teardown of the ChicFinder AWS stack, with the catalog preserved as an RDS
snapshot. Written for someone with **no local AWS CLI** — every step can be done
from the GitHub Actions and AWS consoles.

- **Stack:** `ChicFinderStack` (CloudFormation)
- **Region:** `eu-central-1`
- **Approximate cost being switched off:** ~EUR 135/month

| Resource | Config | ~Monthly |
|---|---|---|
| Fargate API service | 2 tasks, 1 vCPU / 3 GB, 24/7 | ~EUR 70 |
| NAT Gateway | 1 | ~EUR 32 |
| Application Load Balancer | public | ~EUR 18 |
| RDS Postgres 16 | `t4g.micro`, 20 GB encrypted | ~EUR 14 |
| EFS (FAISS index) | encrypted | pennies |
| S3 (catalog images) | public-read | pennies |

Figures are list-price estimates for `eu-central-1`, excluding data transfer.
Check Cost Explorer for the real number.

---

## What changed in the code to make this work

`cdk destroy` on the previous configuration would **not** have stopped the
billing. RDS, EFS and S3 were all `RemovalPolicy.RETAIN`, so CloudFormation
would have deleted the stack and left those three resources behind as orphans —
still charging, with nothing managing them.

| File | Was | Now | Why |
|---|---|---|---|
| [`database.py`](../infrastructure/cdk/chicfinder_constructs/database.py) | `RETAIN` | `SNAPSHOT`, `deletion_protection=False` | Deletes the instance but takes a final snapshot, so the catalog is recoverable. CDK defaults `deletion_protection` to `True` whenever the policy is `RETAIN`, which would have blocked the delete. |
| [`filesystem.py`](../infrastructure/cdk/chicfinder_constructs/filesystem.py) | `RETAIN` | `DESTROY` | The FAISS index is a build artifact, regenerable from the catalog images. |
| [`storage.py`](../infrastructure/cdk/chicfinder_constructs/storage.py) | `RETAIN` | `DESTROY` + `auto_delete_objects=True` | CloudFormation refuses to delete a non-empty bucket. |
| [`deploy-api.yml`](../.github/workflows/deploy-api.yml) | `push` + `workflow_dispatch` | `workflow_dispatch` only | Otherwise merging this change to `main` would trigger CI and **re-provision the entire stack**. |

**Deletion policies are read from the _deployed_ template, not from your working
copy.** That is why step 4 (deploy) must happen before step 5 (destroy). Skipping
step 4 reproduces the original orphaning problem.

Verified against the synthesized template: RDS `DeletionPolicy=Snapshot`,
`DeletionProtection=false`; EFS `Delete`; S3 `Delete` plus the
`Custom::S3AutoDeleteObjects` resource.

---

## Step 1 — Mirror the S3 catalog images (do this first)

**The product images are not in git and are not covered by the RDS snapshot.**
Once the bucket is deleted they are gone, and the FAISS index cannot be rebuilt
without re-scraping.

Find the bucket name from the stack outputs (`CatalogBucketName`):
CloudFormation console → `ChicFinderStack` → **Outputs** tab.

If you have the AWS CLI:

```bash
aws s3 sync s3://<CatalogBucketName> ./backup/catalog-images --region eu-central-1
aws s3 ls s3://<CatalogBucketName> --recursive --summarize | tail -3   # compare counts
```

Without the CLI, use the S3 console and download the prefixes. Confirm the local
count matches before continuing. Keep this backup outside the repo — it is
gitignored territory, not something to commit.

## Step 2 — Take a named RDS snapshot (belt and braces)

The `SNAPSHOT` removal policy creates a final snapshot automatically, but its
name is generated and it is created *during* the delete. An explicit one taken
now is easier to find and verify.

RDS console → Databases → the `chicfinder` instance → **Actions → Take snapshot**.
Name it something like `chicfinder-pre-teardown-2026-10-06`.

Wait for status **Available** before continuing.

## Step 3 — Land the policy change

Merge the branch carrying these changes to `main`. This is now safe: the push
trigger is disabled, so nothing deploys on merge.

Confirm after pushing that no workflow run started (Actions tab).

## Step 4 — Deploy the policy change (required before destroying)

GitHub → **Actions** → **Deploy API** → **Run workflow** → branch `main`.

This runs `cdk deploy`, which updates the deployed template's deletion policies.
It changes metadata only — no replacement of the database, no downtime beyond a
normal service update.

Verify it worked before moving on: CloudFormation → `ChicFinderStack` →
**Resources**, find the `AWS::RDS::DBInstance`, and check its deletion policy
now reads `Snapshot`. If it still says `Retain`, stop — step 5 will orphan it.

## Step 5 — Delete the stack

CloudFormation console → `ChicFinderStack` → **Delete**.

This honours the deployed deletion policies, exactly as `cdk destroy` would.
Expect 20-40 minutes: RDS snapshotting and NAT gateway / ENI detachment are the
slow parts.

If the delete fails and the stack lands in `DELETE_FAILED`, read the events tab
for the blocking resource rather than retrying blindly. The usual causes are an
ENI still attached to a subnet, or a security group still referenced.

## Step 6 — Clean up what the stack does not own

These are **not** part of `ChicFinderStack` and survive its deletion:

| Resource | Why it survives | ~Monthly | Action |
|---|---|---|---|
| `chicfinder/app-secrets` (Secrets Manager) | Imported with `from_secret_name_v2`, i.e. created outside CDK | ~EUR 0.40/secret | Delete in Secrets Manager (7-30 day recovery window) — **but see note below** |
| CDK bootstrap ECR repo `cdk-hnb659fds-container-assets-<account>-eu-central-1` | Belongs to the `CDKToolkit` stack. Holds the API image, which bundles torch, so it is multi-GB | ~EUR 1-2 | Delete the image tags |
| CDK bootstrap S3 bucket `cdk-hnb659fds-assets-<account>-eu-central-1` | Same | pennies | Empty it |
| CloudWatch log groups (`/ecs/...`) | Log groups can outlive their tasks | pennies | Delete, or set a retention policy |

**Note on `chicfinder/app-secrets`:** it holds `OPENROUTER_API_KEY` and
`FIREBASE_PROJECT_ID`. Copy the values somewhere safe before deleting, and treat
the OpenRouter key as worth rotating regardless, since it has been live in a
deployed service.

Leave the `CDKToolkit` bootstrap stack itself in place unless you are certain no
other project in this account uses it — re-bootstrapping is cheap but deleting a
shared bootstrap breaks other stacks.

## Step 7 — Confirm the bill is actually zero

Two days after teardown, check **Cost Explorer** filtered to `eu-central-1`,
grouped by service. Anything still accruing is something the teardown missed.
The specific things to confirm are gone: NAT Gateway, Application Load Balancer,
RDS instance (the *snapshot* will still show a small line), and Fargate.

The final snapshot is the deliberate residual — roughly EUR 1-2/month at 20 GB.

## Step 8 — True zero (optional, irreversible)

When you are confident the catalog is not needed: RDS console → **Snapshots** →
delete both the explicit snapshot from step 2 and the auto-generated final one.

**After this the catalog data is unrecoverable.** The S3 mirror from step 1 and
the scrapers are the only remaining path back.

---

## Bringing it back

1. Uncomment the `push` block in [`deploy-api.yml`](../.github/workflows/deploy-api.yml).
2. Decide whether `RETAIN` should come back for `database.py` / `storage.py`
   (it is the safer policy for a live environment; these were changed
   specifically to enable teardown).
3. `cdk deploy`, or run the workflow manually.
4. Restore the database: `aws rds restore-db-instance-from-db-snapshot`, then
   re-point `DB_SECRET_ARN`. Note that a restored instance has a **new
   endpoint**, and the CDK-managed secret will not match it.
5. Re-upload the catalog images to the new bucket and rebuild the FAISS index
   via `ai_engine/embeddings/database_builder.py`.
6. The ALB DNS name will be **different** — update `mobile/src/lib/api.ts` and
   anything else holding the old URL.

Step 4-6 are the reason teardown is not quite symmetric with deploy: the stack
rebuilds automatically, the data and URLs do not.
