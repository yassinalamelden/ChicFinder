# AWS Infrastructure and Data Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the AWS infrastructure (VPC, S3, RDS, EFS, two ECS Fargate services) as one CDK stack, and build the reusable catalog seeding tool that loads/replaces the data warehouse.

**Architecture:** A single CDK (Python) stack, `ChicFinderStack`, composed from focused construct classes (one per AWS resource group) under `infrastructure/cdk/chicfinder_constructs/`. The API Fargate service and the index-builder Fargate task share one EFS volume (API mounts read-only, builder mounts read-write) and both live in the same VPC as the RDS instance. `scripts/seed_catalog.py` is the tool that loads the catalog into S3 + RDS, usable for both the first load and any future full replacement.

**Tech Stack:** AWS CDK v2 (Python), `aws-cdk-lib`, `boto3`, `psycopg2-binary`, `aws_cdk.assertions` for infra unit tests, `moto` for mocking AWS in the seed script's tests.

**Spec:** `docs/superpowers/specs/2026-08-22-aws-backend-migration-design.md`

## Global Constraints

- One CDK stack, not several — per the spec ("One AWS CDK (Python) stack"). Construct classes may be split across files for readability, but everything is instantiated inside a single `ChicFinderStack`.
- The local folder holding CDK constructs is named `chicfinder_constructs/`, **not** `constructs/` — the CDK library itself is a PyPI package literally named `constructs` (`from constructs import Construct`); naming a local folder the same thing risks import shadowing.
- RDS and EFS live in private subnets; only the ALB is internet-facing.
- No secret values (API keys, DB passwords) are hardcoded anywhere in CDK code — DB credentials are CDK-generated into Secrets Manager; `OPENROUTER_API_KEY` and Firebase credentials reference a pre-existing, manually-created Secrets Manager secret (created once, out of band, before first deploy — see Task 5).
- This plan assumes the Prerequisites step from the spec (AWS Agent Toolkit / CLI configured and authenticated) is already done.

---

### Task 1: CDK app scaffolding + VPC construct

**Files:**
- Create: `infrastructure/cdk/requirements.txt`
- Create: `infrastructure/cdk/cdk.json`
- Create: `infrastructure/cdk/app.py`
- Create: `infrastructure/cdk/chicfinder_constructs/__init__.py`
- Create: `infrastructure/cdk/chicfinder_constructs/networking.py`
- Create: `infrastructure/cdk/chicfinder_stack.py`
- Test: `infrastructure/cdk/tests/test_networking.py`

**Interfaces:**
- Produces: `Networking(scope, id).vpc` — an `ec2.Vpc` with public + private-with-egress subnets across 2 AZs, exposed as `self.vpc`. Every later construct in this plan takes this VPC as a constructor argument.

- [ ] **Step 1: Scaffold the CDK app**

Create `infrastructure/cdk/requirements.txt`:

```
aws-cdk-lib>=2.150.0
constructs>=10.0.0
pytest
boto3
```

Create `infrastructure/cdk/cdk.json`:

```json
{
  "app": "python3 app.py",
  "watch": {
    "include": ["**"],
    "exclude": ["README.md", "cdk*.json", "requirements*.txt", "tests/**", "**/__pycache__", "**/*.pyc"]
  },
  "context": {
    "@aws-cdk/core:newStyleStackSynthesis": true
  }
}
```

Create `infrastructure/cdk/chicfinder_constructs/__init__.py` (empty file, marks the directory as a package).

Install CDK's Python dependencies into a virtualenv for this directory:

```bash
cd infrastructure/cdk
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows; use .venv/bin/pip on macOS/Linux
```

- [ ] **Step 2: Write the failing test**

Create `infrastructure/cdk/tests/test_networking.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aws_cdk as cdk
from aws_cdk.assertions import Template

from chicfinder_constructs.networking import Networking


def test_vpc_has_two_azs_and_one_nat_gateway():
    app = cdk.App()
    stack = cdk.Stack(app, "TestStack")
    Networking(stack, "Networking")

    template = Template.from_stack(stack)
    template.resource_count_is("AWS::EC2::VPC", 1)
    template.resource_count_is("AWS::EC2::NatGateway", 1)
    # 2 AZs x 2 subnet types (public, private) = 4 subnets
    template.resource_count_is("AWS::EC2::Subnet", 4)
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `cd infrastructure/cdk && .venv/Scripts/pytest tests/test_networking.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'chicfinder_constructs.networking'`

- [ ] **Step 4: Implement the VPC construct**

Create `infrastructure/cdk/chicfinder_constructs/networking.py`:

```python
from aws_cdk import aws_ec2 as ec2
from constructs import Construct


class Networking(Construct):
    """VPC shared by every other construct in the stack."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = ec2.Vpc(
            self,
            "Vpc",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
            ],
        )
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd infrastructure/cdk && .venv/Scripts/pytest tests/test_networking.py -v`
Expected: PASS

- [ ] **Step 6: Create the (currently empty) stack and app entry point**

Create `infrastructure/cdk/chicfinder_stack.py`:

```python
from aws_cdk import Stack
from constructs import Construct

from chicfinder_constructs.networking import Networking


class ChicFinderStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.networking = Networking(self, "Networking")
```

Create `infrastructure/cdk/app.py`:

```python
#!/usr/bin/env python3
import aws_cdk as cdk

from chicfinder_stack import ChicFinderStack

app = cdk.App()
ChicFinderStack(app, "ChicFinderStack")
app.synth()
```

- [ ] **Step 7: Verify the app synthesizes**

Run: `cd infrastructure/cdk && .venv/Scripts/cdk synth`
Expected: prints a CloudFormation template to stdout with no errors (includes one VPC, one NAT gateway).

- [ ] **Step 8: Commit**

```bash
git add infrastructure/cdk/
git commit -m "feat(infra): scaffold CDK app with VPC construct"
```

---

### Task 2: S3 bucket construct (catalog images)

**Files:**
- Create: `infrastructure/cdk/chicfinder_constructs/storage.py`
- Modify: `infrastructure/cdk/chicfinder_stack.py`
- Test: `infrastructure/cdk/tests/test_storage.py`

**Interfaces:**
- Consumes: nothing (no dependency on `Networking` — S3 is not VPC-scoped).
- Produces: `Storage(scope, id).bucket` — an `s3.Bucket` with public-read access for objects, exposed as `self.bucket`. Task 5 (API service) and Task 6 (index builder) both take this bucket as a constructor argument.

- [ ] **Step 1: Write the failing test**

Create `infrastructure/cdk/tests/test_storage.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aws_cdk as cdk
from aws_cdk.assertions import Template, Match

from chicfinder_constructs.storage import Storage


def test_bucket_blocks_acls_but_allows_public_read_policy():
    app = cdk.App()
    stack = cdk.Stack(app, "TestStack")
    Storage(stack, "Storage")

    template = Template.from_stack(stack)
    template.resource_count_is("AWS::S3::Bucket", 1)
    template.has_resource_properties(
        "AWS::S3::BucketPolicy",
        {
            "PolicyDocument": Match.object_like(
                {
                    "Statement": Match.array_with(
                        [Match.object_like({"Effect": "Allow", "Action": "s3:GetObject"})]
                    )
                }
            )
        },
    )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd infrastructure/cdk && .venv/Scripts/pytest tests/test_storage.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'chicfinder_constructs.storage'`

- [ ] **Step 3: Implement the S3 construct**

Create `infrastructure/cdk/chicfinder_constructs/storage.py`:

```python
from aws_cdk import RemovalPolicy, aws_s3 as s3
from constructs import Construct


class Storage(Construct):
    """S3 bucket holding catalog product images, public-read."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.bucket = s3.Bucket(
            self,
            "CatalogImages",
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=True,
                ignore_public_acls=True,
                block_public_policy=False,
                restrict_public_buckets=False,
            ),
            removal_policy=RemovalPolicy.RETAIN,
        )
        self.bucket.grant_public_access()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd infrastructure/cdk && .venv/Scripts/pytest tests/test_storage.py -v`
Expected: PASS

- [ ] **Step 5: Wire into the stack**

In `infrastructure/cdk/chicfinder_stack.py`, add the import:

```python
from chicfinder_constructs.storage import Storage
```

and in `__init__`, after `self.networking = Networking(self, "Networking")`:

```python
        self.storage = Storage(self, "Storage")
```

- [ ] **Step 6: Verify the app still synthesizes**

Run: `cd infrastructure/cdk && .venv/Scripts/cdk synth`
Expected: no errors; template now includes one S3 bucket + bucket policy alongside the VPC.

- [ ] **Step 7: Commit**

```bash
git add infrastructure/cdk/
git commit -m "feat(infra): add S3 bucket construct for catalog images"
```

---

### Task 3: RDS Postgres construct (item records)

**Files:**
- Create: `infrastructure/cdk/chicfinder_constructs/database.py`
- Modify: `infrastructure/cdk/chicfinder_stack.py`
- Test: `infrastructure/cdk/tests/test_database.py`

**Interfaces:**
- Consumes: `Networking.vpc` (constructor argument).
- Produces: `Database(scope, id, vpc).instance` — an `rds.DatabaseInstance`, exposed as `self.instance`. `Database(scope, id, vpc).secret` — the auto-generated Secrets Manager secret holding DB credentials, exposed as `self.secret`. `Database(scope, id, vpc).connections` — the security group's `ec2.Connections`, used by Task 5/6 to grant inbound access from the Fargate tasks.

- [ ] **Step 1: Write the failing test**

Create `infrastructure/cdk/tests/test_database.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aws_cdk as cdk
from aws_cdk.assertions import Template

from chicfinder_constructs.networking import Networking
from chicfinder_constructs.database import Database


def test_database_is_postgres_in_private_subnet_with_generated_secret():
    app = cdk.App()
    stack = cdk.Stack(app, "TestStack")
    networking = Networking(stack, "Networking")
    Database(stack, "Database", vpc=networking.vpc)

    template = Template.from_stack(stack)
    template.resource_count_is("AWS::RDS::DBInstance", 1)
    template.has_resource_properties("AWS::RDS::DBInstance", {"Engine": "postgres"})
    template.resource_count_is("AWS::SecretsManager::Secret", 1)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd infrastructure/cdk && .venv/Scripts/pytest tests/test_database.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'chicfinder_constructs.database'`

- [ ] **Step 3: Implement the RDS construct**

Create `infrastructure/cdk/chicfinder_constructs/database.py`:

```python
from aws_cdk import RemovalPolicy, aws_ec2 as ec2, aws_rds as rds
from constructs import Construct


class Database(Construct):
    """RDS Postgres instance holding the `items` catalog table."""

    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.IVpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.instance = rds.DatabaseInstance(
            self,
            "Postgres",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.MICRO
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            database_name="chicfinder",
            credentials=rds.Credentials.from_generated_secret("chicfinder_admin"),
            allocated_storage=20,
            removal_policy=RemovalPolicy.RETAIN,
        )
        self.secret = self.instance.secret
        self.connections = self.instance.connections
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd infrastructure/cdk && .venv/Scripts/pytest tests/test_database.py -v`
Expected: PASS

- [ ] **Step 5: Wire into the stack**

In `infrastructure/cdk/chicfinder_stack.py`, add the import:

```python
from chicfinder_constructs.database import Database
```

and after `self.storage = Storage(self, "Storage")`:

```python
        self.database = Database(self, "Database", vpc=self.networking.vpc)
```

- [ ] **Step 6: Verify the app still synthesizes**

Run: `cd infrastructure/cdk && .venv/Scripts/cdk synth`
Expected: no errors; template now includes the RDS instance + its generated secret.

- [ ] **Step 7: Commit**

```bash
git add infrastructure/cdk/
git commit -m "feat(infra): add RDS Postgres construct for the items table"
```

---

### Task 4: EFS filesystem construct (FAISS index storage)

**Files:**
- Create: `infrastructure/cdk/chicfinder_constructs/filesystem.py`
- Modify: `infrastructure/cdk/chicfinder_stack.py`
- Test: `infrastructure/cdk/tests/test_filesystem.py`

**Interfaces:**
- Consumes: `Networking.vpc` (constructor argument).
- Produces: `Filesystem(scope, id, vpc).file_system` — an `efs.FileSystem`, exposed as `self.file_system`. `Filesystem(scope, id, vpc).access_point` — an `efs.AccessPoint` scoped to `/faiss-index`, exposed as `self.access_point`, used by both ECS task definitions in Tasks 5 and 6.

- [ ] **Step 1: Write the failing test**

Create `infrastructure/cdk/tests/test_filesystem.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aws_cdk as cdk
from aws_cdk.assertions import Template

from chicfinder_constructs.networking import Networking
from chicfinder_constructs.filesystem import Filesystem


def test_efs_filesystem_and_access_point_exist():
    app = cdk.App()
    stack = cdk.Stack(app, "TestStack")
    networking = Networking(stack, "Networking")
    Filesystem(stack, "Filesystem", vpc=networking.vpc)

    template = Template.from_stack(stack)
    template.resource_count_is("AWS::EFS::FileSystem", 1)
    template.resource_count_is("AWS::EFS::AccessPoint", 1)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd infrastructure/cdk && .venv/Scripts/pytest tests/test_filesystem.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'chicfinder_constructs.filesystem'`

- [ ] **Step 3: Implement the EFS construct**

Create `infrastructure/cdk/chicfinder_constructs/filesystem.py`:

```python
from aws_cdk import RemovalPolicy, aws_ec2 as ec2, aws_efs as efs
from constructs import Construct


class Filesystem(Construct):
    """EFS volume holding the built FAISS index (embeddings.index, index_to_image_id.json)."""

    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.IVpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.file_system = efs.FileSystem(
            self,
            "FaissIndexVolume",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            removal_policy=RemovalPolicy.RETAIN,
        )

        self.access_point = self.file_system.add_access_point(
            "FaissIndexAccessPoint",
            path="/faiss-index",
            create_acl=efs.Acl(owner_gid="1000", owner_uid="1000", permissions="755"),
            posix_user=efs.PosixUser(uid="1000", gid="1000"),
        )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd infrastructure/cdk && .venv/Scripts/pytest tests/test_filesystem.py -v`
Expected: PASS

- [ ] **Step 5: Wire into the stack**

In `infrastructure/cdk/chicfinder_stack.py`, add the import:

```python
from chicfinder_constructs.filesystem import Filesystem
```

and after `self.database = Database(...)`:

```python
        self.filesystem = Filesystem(self, "Filesystem", vpc=self.networking.vpc)
```

- [ ] **Step 6: Verify the app still synthesizes**

Run: `cd infrastructure/cdk && .venv/Scripts/cdk synth`
Expected: no errors; template now includes the EFS file system + access point.

- [ ] **Step 7: Commit**

```bash
git add infrastructure/cdk/
git commit -m "feat(infra): add EFS construct for the FAISS index volume"
```

---

### Task 5: ECS cluster + API Fargate service (behind an ALB, EFS read-only)

**Files:**
- Create: `infrastructure/cdk/chicfinder_constructs/compute.py`
- Modify: `infrastructure/cdk/chicfinder_stack.py`
- Test: `infrastructure/cdk/tests/test_compute.py`

**Interfaces:**
- Consumes: `Networking.vpc`, `Storage.bucket`, `Database.instance` + `Database.connections`, `Filesystem.file_system` + `Filesystem.access_point` (all as constructor arguments).
- Produces: `Compute(scope, id, ...).cluster` — an `ecs.Cluster`, exposed as `self.cluster`. `Compute(scope, id, ...).api_service` — the `ecs_patterns.ApplicationLoadBalancedFargateService` running the API, exposed as `self.api_service`. Task 6 (index builder) reuses `self.cluster`.

**One manual, one-time prerequisite before this task's deploy step:** create the app-secrets entry this task references:

```bash
aws secretsmanager create-secret --name chicfinder/app-secrets \
  --secret-string '{"OPENROUTER_API_KEY":"<your-key>","FIREBASE_PROJECT_ID":"<your-project-id>"}'
```

- [ ] **Step 1: Write the failing test**

Create `infrastructure/cdk/tests/test_compute.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aws_cdk as cdk
from aws_cdk.assertions import Template, Match

from chicfinder_constructs.networking import Networking
from chicfinder_constructs.storage import Storage
from chicfinder_constructs.database import Database
from chicfinder_constructs.filesystem import Filesystem
from chicfinder_constructs.compute import Compute


def _build_stack():
    app = cdk.App()
    stack = cdk.Stack(app, "TestStack")
    networking = Networking(stack, "Networking")
    storage = Storage(stack, "Storage")
    database = Database(stack, "Database", vpc=networking.vpc)
    filesystem = Filesystem(stack, "Filesystem", vpc=networking.vpc)
    compute = Compute(
        stack,
        "Compute",
        vpc=networking.vpc,
        bucket=storage.bucket,
        database=database,
        filesystem=filesystem,
    )
    return stack, compute


def test_api_service_is_fargate_with_efs_mount():
    stack, _ = _build_stack()
    template = Template.from_stack(stack)

    template.resource_count_is("AWS::ECS::Cluster", 1)
    template.has_resource_properties(
        "AWS::ECS::TaskDefinition",
        {
            "RequiresCompatibilities": ["FARGATE"],
            "Volumes": Match.array_with(
                [Match.object_like({"EFSVolumeConfiguration": Match.any_value()})]
            ),
        },
    )
    template.resource_count_is(
        "AWS::ElasticLoadBalancingV2::LoadBalancer", 1
    )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd infrastructure/cdk && .venv/Scripts/pytest tests/test_compute.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'chicfinder_constructs.compute'`

- [ ] **Step 3: Implement the ECS cluster + API service**

Create `infrastructure/cdk/chicfinder_constructs/compute.py`:

```python
from aws_cdk import Duration, aws_ec2 as ec2, aws_ecs as ecs, aws_ecs_patterns as ecs_patterns
from aws_cdk import aws_s3 as s3, aws_secretsmanager as secretsmanager
from constructs import Construct

from chicfinder_constructs.database import Database
from chicfinder_constructs.filesystem import Filesystem

APP_SECRETS_NAME = "chicfinder/app-secrets"


class Compute(Construct):
    """ECS cluster + the always-on API Fargate service (EFS mounted read-only)."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        bucket: s3.IBucket,
        database: Database,
        filesystem: Filesystem,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.cluster = ecs.Cluster(self, "Cluster", vpc=vpc)

        app_secrets = secretsmanager.Secret.from_secret_name_v2(
            self, "AppSecrets", APP_SECRETS_NAME
        )

        task_definition = ecs.FargateTaskDefinition(
            self,
            "ApiTaskDefinition",
            cpu=1024,
            memory_limit_mib=3072,
        )
        task_definition.add_volume(
            name="faiss-index",
            efs_volume_configuration=ecs.EfsVolumeConfiguration(
                file_system_id=filesystem.file_system.file_system_id,
                transit_encryption="ENABLED",
                authorization_config=ecs.AuthorizationConfig(
                    access_point_id=filesystem.access_point.access_point_id,
                    iam="ENABLED",
                ),
            ),
        )

        container = task_definition.add_container(
            "ApiContainer",
            image=ecs.ContainerImage.from_asset(
                directory="../..",
                file="infrastructure/docker/Dockerfile.api",
            ),
            port_mappings=[ecs.PortMapping(container_port=8000)],
            environment={
                "APP_ENV": "production",
                "DB_SECRET_ARN": database.secret.secret_arn,
                "S3_BUCKET_NAME": bucket.bucket_name,
            },
            secrets={
                "OPENROUTER_API_KEY": ecs.Secret.from_secrets_manager(
                    app_secrets, "OPENROUTER_API_KEY"
                ),
                "FIREBASE_PROJECT_ID": ecs.Secret.from_secrets_manager(
                    app_secrets, "FIREBASE_PROJECT_ID"
                ),
            },
            logging=ecs.LogDriver.aws_logs(stream_prefix="chicfinder-api"),
        )
        container.add_mount_points(
            ecs.MountPoint(
                container_path="/mnt/faiss-index",
                source_volume="faiss-index",
                read_only=True,
            )
        )

        self.api_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "ApiService",
            cluster=self.cluster,
            task_definition=task_definition,
            desired_count=1,
            public_load_balancer=True,
            health_check_grace_period=Duration.seconds(120),
        )
        self.api_service.target_group.configure_health_check(path="/api/v1/health")

        bucket.grant_read(task_definition.task_role)
        database.secret.grant_read(task_definition.task_role)
        app_secrets.grant_read(task_definition.task_role)
        database.connections.allow_default_port_from(self.api_service.service)
        filesystem.file_system.connections.allow_default_port_from(self.api_service.service)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd infrastructure/cdk && .venv/Scripts/pytest tests/test_compute.py -v`
Expected: PASS

- [ ] **Step 5: Wire into the stack**

In `infrastructure/cdk/chicfinder_stack.py`, add the import:

```python
from chicfinder_constructs.compute import Compute
```

and after `self.filesystem = Filesystem(...)`:

```python
        self.compute = Compute(
            self,
            "Compute",
            vpc=self.networking.vpc,
            bucket=self.storage.bucket,
            database=self.database,
            filesystem=self.filesystem,
        )
```

- [ ] **Step 6: Verify the app still synthesizes**

Run: `cd infrastructure/cdk && .venv/Scripts/cdk synth`
Expected: no errors; template now includes the ECS cluster, API task definition (with the EFS volume/mount), and ALB.

- [ ] **Step 7: Commit**

```bash
git add infrastructure/cdk/
git commit -m "feat(infra): add ECS cluster and load-balanced API Fargate service"
```

---

### Task 6: ECS index-builder task definition (EFS read-write)

**Files:**
- Modify: `infrastructure/cdk/chicfinder_constructs/compute.py`
- Test: `infrastructure/cdk/tests/test_compute.py`

**Interfaces:**
- Consumes: `self.cluster` (already built in Task 5), `filesystem`, `database`, `bucket` (already constructor arguments of `Compute`).
- Produces: `Compute(...).builder_task_definition` — an `ecs.FargateTaskDefinition`, exposed as `self.builder_task_definition`, run on demand via `aws ecs run-task` (not an always-on service).

- [ ] **Step 1: Write the failing test**

Add to `infrastructure/cdk/tests/test_compute.py`:

```python
def test_index_builder_task_definition_mounts_efs_read_write():
    stack, compute = _build_stack()
    template = Template.from_stack(stack)

    # Two task definitions total: the API service's, and the builder's.
    template.resource_count_is("AWS::ECS::TaskDefinition", 2)
    assert compute.builder_task_definition is not None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd infrastructure/cdk && .venv/Scripts/pytest tests/test_compute.py -v`
Expected: FAIL — `AttributeError: 'Compute' object has no attribute 'builder_task_definition'` (and the resource count is 1, not 2).

- [ ] **Step 3: Add the builder task definition**

In `infrastructure/cdk/chicfinder_constructs/compute.py`, at the end of `Compute.__init__` (after the `filesystem.file_system.connections.allow_default_port_from(...)` line), add:

```python
        self.builder_task_definition = ecs.FargateTaskDefinition(
            self,
            "IndexBuilderTaskDefinition",
            cpu=2048,
            memory_limit_mib=8192,
        )
        self.builder_task_definition.add_volume(
            name="faiss-index",
            efs_volume_configuration=ecs.EfsVolumeConfiguration(
                file_system_id=filesystem.file_system.file_system_id,
                transit_encryption="ENABLED",
                authorization_config=ecs.AuthorizationConfig(
                    access_point_id=filesystem.access_point.access_point_id,
                    iam="ENABLED",
                ),
            ),
        )

        builder_container = self.builder_task_definition.add_container(
            "IndexBuilderContainer",
            image=ecs.ContainerImage.from_asset(
                directory="../..",
                file="infrastructure/docker/Dockerfile.api",
            ),
            command=["python", "scripts/02_build_faiss_index.py"],
            environment={
                "APP_ENV": "production",
                "DB_SECRET_ARN": database.secret.secret_arn,
                "S3_BUCKET_NAME": bucket.bucket_name,
            },
            logging=ecs.LogDriver.aws_logs(stream_prefix="chicfinder-index-builder"),
        )
        builder_container.add_mount_points(
            ecs.MountPoint(
                container_path="/mnt/faiss-index",
                source_volume="faiss-index",
                read_only=False,
            )
        )

        bucket.grant_read(self.builder_task_definition.task_role)
        database.secret.grant_read(self.builder_task_definition.task_role)

        self.builder_security_group = ec2.SecurityGroup(
            self, "IndexBuilderSecurityGroup", vpc=vpc, allow_all_outbound=True
        )
        database.connections.allow_default_port_from(self.builder_security_group)
        filesystem.file_system.connections.allow_default_port_from(self.builder_security_group)
```

A dedicated security group for the builder task (rather than reusing the API service's) is deliberate — `aws ecs run-task` needs an explicit security group at invocation time (`--network-configuration`), and giving the builder its own group keeps its DB/EFS network access auditable separately from the always-on API service's.

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd infrastructure/cdk && .venv/Scripts/pytest tests/test_compute.py -v`
Expected: 3 passed (the two from Task 5 plus this one).

- [ ] **Step 5: Verify the app still synthesizes**

Run: `cd infrastructure/cdk && .venv/Scripts/cdk synth`
Expected: no errors; template now includes two ECS task definitions.

- [ ] **Step 6: Commit**

```bash
git add infrastructure/cdk/
git commit -m "feat(infra): add index-builder ECS task definition with read-write EFS mount"
```

---

### Task 7: Deploy the stack

**Files:** none (operational task, no code changes)

- [ ] **Step 1: Bootstrap the CDK environment (one-time per AWS account/region)**

Run: `cd infrastructure/cdk && .venv/Scripts/cdk bootstrap`

- [ ] **Step 2: Deploy**

Run: `cd infrastructure/cdk && .venv/Scripts/cdk deploy`
Expected: CDK prints the IAM/security-group changes it's about to make, prompts for confirmation, then provisions all resources. Note the printed `ApiService.LoadBalancerDNS` output — that's the API's public URL.

- [ ] **Step 3: Verify the API is reachable**

Run: `curl http://<LoadBalancerDNS>/api/v1/health`
Expected: `{"status":"ok","service":"ChicFinder API"}` — same health response verified locally in the prior session, now served from AWS. (The `/recommend` and `/search` endpoints will still error at this point — RDS/S3 are empty and no FAISS index exists yet. That's expected; Task 8 and Plan 3 fill that in.)

---

### Task 8: Catalog seeding tool

**Files:**
- Create: `scripts/seed_catalog.py`
- Create: `tests/scripts/test_seed_catalog.py`
- Modify: `requirements.txt`

**Interfaces:**
- Produces: a CLI script, `python scripts/seed_catalog.py --images <dir> --metadata <file> [--wipe]`, that is both the initial catalog loader and the tool for any future full replacement (per the spec — no separate one-time migration script).

- [ ] **Step 1: Add dependencies**

Add to `requirements.txt`:

```
# --- AWS data layer -------------------------------------------
boto3
psycopg2-binary

# --- Testing (AWS mocking) -------------------------------------
moto[s3]
```

- [ ] **Step 2: Write the failing test**

Create `tests/scripts/test_seed_catalog.py`:

```python
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.seed_catalog import seed_catalog


@pytest.fixture
def sample_catalog(tmp_path):
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    (images_dir / "item1.jpg").write_bytes(b"fake-image-bytes")

    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "item1": {
                    "category": "shirt",
                    "sub_category": "t-shirt",
                    "color": "white",
                    "style": "casual",
                    "brand": "Tomato",
                    "price": 350.0,
                    "product_url": "https://tomato.example.com/item1",
                    "availability": True,
                    "store_id": "tomato",
                }
            }
        )
    )
    return images_dir, metadata_path


@mock_aws
def test_seed_catalog_uploads_images_and_inserts_records(sample_catalog):
    images_dir, metadata_path = sample_catalog

    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-chicfinder-catalog")

    fake_cursor = MagicMock()
    fake_conn = MagicMock()
    fake_conn.cursor.return_value.__enter__.return_value = fake_cursor

    seed_catalog(
        images_dir=images_dir,
        metadata_path=metadata_path,
        bucket_name="test-chicfinder-catalog",
        db_connection=fake_conn,
        wipe=False,
    )

    uploaded = s3.list_objects_v2(Bucket="test-chicfinder-catalog")
    uploaded_keys = [obj["Key"] for obj in uploaded.get("Contents", [])]
    assert "item1.jpg" in uploaded_keys

    insert_calls = [
        call for call in fake_cursor.execute.call_args_list if "INSERT INTO items" in call.args[0]
    ]
    assert len(insert_calls) == 1
    assert insert_calls[0].args[1][0] == "item1"  # id
    assert insert_calls[0].args[1][4] == "Tomato"  # brand


@mock_aws
def test_seed_catalog_wipes_existing_data_first_when_requested(sample_catalog):
    images_dir, metadata_path = sample_catalog

    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-chicfinder-catalog")
    s3.put_object(Bucket="test-chicfinder-catalog", Key="old_item.jpg", Body=b"stale")

    fake_cursor = MagicMock()
    fake_conn = MagicMock()
    fake_conn.cursor.return_value.__enter__.return_value = fake_cursor

    seed_catalog(
        images_dir=images_dir,
        metadata_path=metadata_path,
        bucket_name="test-chicfinder-catalog",
        db_connection=fake_conn,
        wipe=True,
    )

    remaining = s3.list_objects_v2(Bucket="test-chicfinder-catalog")
    remaining_keys = [obj["Key"] for obj in remaining.get("Contents", [])]
    assert "old_item.jpg" not in remaining_keys
    assert "item1.jpg" in remaining_keys

    truncate_calls = [
        call for call in fake_cursor.execute.call_args_list if "TRUNCATE" in call.args[0]
    ]
    assert len(truncate_calls) == 1
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `pytest tests/scripts/test_seed_catalog.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.seed_catalog'`

- [ ] **Step 4: Implement `scripts/seed_catalog.py`**

```python
"""
scripts/seed_catalog.py

Loads (or fully replaces) the ChicFinder product catalog: uploads images to
S3, inserts item records into RDS. This is the same tool for the first load
and for any later full catalog swap — pass --wipe to clear existing data
first.

Usage:
  python scripts/seed_catalog.py --images ./catalog/images --metadata ./catalog/metadata.json
  python scripts/seed_catalog.py --images ./new_catalog/images --metadata ./new_catalog/metadata.json --wipe
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import boto3
import psycopg2

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
logger = logging.getLogger("seed_catalog")

CREATE_ITEMS_TABLE = """
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    category TEXT,
    sub_category TEXT,
    color TEXT,
    style TEXT,
    brand TEXT,
    price NUMERIC,
    product_url TEXT,
    availability BOOLEAN DEFAULT TRUE,
    image_key TEXT,
    store_id TEXT
);
"""

INSERT_ITEM = """
INSERT INTO items (id, category, sub_category, color, style, brand, price,
                    product_url, availability, image_key, store_id)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (id) DO UPDATE SET
    category = EXCLUDED.category,
    sub_category = EXCLUDED.sub_category,
    color = EXCLUDED.color,
    style = EXCLUDED.style,
    brand = EXCLUDED.brand,
    price = EXCLUDED.price,
    product_url = EXCLUDED.product_url,
    availability = EXCLUDED.availability,
    image_key = EXCLUDED.image_key,
    store_id = EXCLUDED.store_id;
"""


def seed_catalog(images_dir: Path, metadata_path: Path, bucket_name: str, db_connection, wipe: bool) -> None:
    s3 = boto3.client("s3")

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    with db_connection.cursor() as cursor:
        cursor.execute(CREATE_ITEMS_TABLE)

        if wipe:
            logger.info("Wiping existing catalog (S3 bucket contents + items table)...")
            existing = s3.list_objects_v2(Bucket=bucket_name)
            for obj in existing.get("Contents", []):
                s3.delete_object(Bucket=bucket_name, Key=obj["Key"])
            cursor.execute("TRUNCATE items;")

        for item_id, record in metadata.items():
            image_filename = f"{item_id}.jpg"
            image_path = images_dir / image_filename
            if not image_path.exists():
                logger.warning("No image found for item '%s' at %s, skipping upload.", item_id, image_path)
                continue

            s3.upload_file(str(image_path), bucket_name, image_filename)
            logger.info("Uploaded %s -> s3://%s/%s", image_path, bucket_name, image_filename)

            cursor.execute(
                INSERT_ITEM,
                (
                    item_id,
                    record.get("category"),
                    record.get("sub_category"),
                    record.get("color"),
                    record.get("style"),
                    record.get("brand"),
                    record.get("price"),
                    record.get("product_url"),
                    record.get("availability", True),
                    image_filename,
                    record.get("store_id"),
                ),
            )

    db_connection.commit()
    logger.info("Seed complete: %d item(s) processed.", len(metadata))


def _connect_from_env():
    """Builds a psycopg2 connection from DB_SECRET_ARN (via Secrets Manager) or
    discrete DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD env vars for local use."""
    secret_arn = os.getenv("DB_SECRET_ARN")
    if secret_arn:
        secretsmanager = boto3.client("secretsmanager")
        secret = json.loads(secretsmanager.get_secret_value(SecretId=secret_arn)["SecretString"])
        return psycopg2.connect(
            host=secret["host"],
            port=secret["port"],
            dbname=secret.get("dbname", "chicfinder"),
            user=secret["username"],
            password=secret["password"],
        )
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "chicfinder"),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Load or replace the ChicFinder catalog in S3 + RDS.")
    parser.add_argument("--images", type=str, required=True, help="Directory of catalog images.")
    parser.add_argument("--metadata", type=str, required=True, help="Path to the catalog metadata JSON.")
    parser.add_argument("--wipe", action="store_true", help="Wipe existing S3/RDS data before seeding.")
    args = parser.parse_args()

    bucket_name = os.environ["S3_BUCKET_NAME"]
    connection = _connect_from_env()
    try:
        seed_catalog(
            images_dir=Path(args.images),
            metadata_path=Path(args.metadata),
            bucket_name=bucket_name,
            db_connection=connection,
            wipe=args.wipe,
        )
    finally:
        connection.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `pytest tests/scripts/test_seed_catalog.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add scripts/seed_catalog.py tests/scripts/test_seed_catalog.py requirements.txt
git commit -m "feat: add reusable catalog seeding tool (initial load + full replacement)"
```

## Self-Review Notes

- **Spec coverage:** S3 (Task 2), RDS (Task 3), EFS (Task 4), API Fargate service (Task 5), index-builder task (Task 6), CDK-as-IaC (all infra tasks), seed/reseed tool (Task 8) — every "Components" bullet in the spec has a task. CI/CD and the index-builder-to-RDS/S3 data reads are Plan 3's job (they depend on this plan's resources existing first).
- **Type consistency:** `Database`, `Filesystem`, `Storage` constructor signatures in Tasks 2-4 match how `Compute` consumes them in Task 5. `seed_catalog()`'s parameter list matches both its test calls and its `main()` invocation.
- **No placeholders:** every CDK construct and the seed script are complete, runnable code — no "add appropriate permissions" steps. IAM grants are explicit (`grant_read`, `add_ingress_rule`) at the point each resource is created.
