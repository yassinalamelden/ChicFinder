from pathlib import Path

from aws_cdk import Duration, aws_ec2 as ec2, aws_ecs as ecs, aws_ecs_patterns as ecs_patterns
from aws_cdk import aws_iam as iam, aws_s3 as s3, aws_secretsmanager as secretsmanager
from constructs import Construct

from chicfinder_constructs.database import Database
from chicfinder_constructs.filesystem import Filesystem

APP_SECRETS_NAME = "chicfinder/app-secrets"

# Container path where the shared EFS volume is mounted in both task
# definitions (read-only for the API, read-write for the index builder).
EFS_MOUNT_PATH = "/mnt/faiss-index"
FAISS_INDEX_PATH = f"{EFS_MOUNT_PATH}/embeddings.index"
FAISS_MAPPING_PATH = f"{EFS_MOUNT_PATH}/index_to_image_id.json"

# Repo root, computed from this file's own location so the Docker build context
# resolves correctly regardless of the directory `cdk synth`/`cdk deploy` is
# invoked from (a cwd-relative "../.." would otherwise silently point at the
# wrong directory when invoked from anywhere but infrastructure/cdk/).
_REPO_ROOT = Path(__file__).resolve().parents[3]


class Compute(Construct):
    """ECS cluster + the always-on API Fargate service (EFS mounted read-only)
    and the index-builder Fargate task definition (EFS mounted read-write)."""

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
                directory=str(_REPO_ROOT),
                file="infrastructure/docker/Dockerfile.api",
            ),
            port_mappings=[ecs.PortMapping(container_port=8000)],
            environment={
                "APP_ENV": "production",
                "DB_SECRET_ARN": database.secret.secret_arn,
                "S3_BUCKET_NAME": bucket.bucket_name,
                "FAISS_INDEX_PATH": FAISS_INDEX_PATH,
                "FAISS_MAPPING_PATH": FAISS_MAPPING_PATH,
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
                container_path=EFS_MOUNT_PATH,
                source_volume="faiss-index",
                read_only=True,
            )
        )

        self.api_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "ApiService",
            cluster=self.cluster,
            task_definition=task_definition,
            desired_count=2,
            public_load_balancer=True,
            health_check_grace_period=Duration.seconds(120),
        )
        self.api_service.target_group.configure_health_check(path="/api/v1/health")

        bucket.grant_read(task_definition.task_role)
        database.secret.grant_read(task_definition.task_role)
        app_secrets.grant_read(task_definition.task_role)
        # NOTE: deliberately not using efs.FileSystem.grant_read() here. That helper has a
        # side effect: it flips FileSystem's internal "granted client" flag, which makes CDK
        # auto-attach a *separate* file-system resource policy statement granting
        # ClientWrite + ClientRootAccess to Principal "*" (AnyPrincipal) whenever
        # AccessedViaMountTarget is true. Per AWS's EFS docs, an allow in *either* an identity
        # policy *or* the resource policy grants that action - so that auto-added statement
        # would independently hand this read-only role write/root access, defeating the
        # read-only intent. A manual statement scoped to this access point avoids that.
        task_definition.task_role.add_to_principal_policy(
            iam.PolicyStatement(
                actions=["elasticfilesystem:ClientMount"],
                resources=[filesystem.file_system.file_system_arn],
                conditions={
                    "StringEquals": {
                        "elasticfilesystem:AccessPointArn": filesystem.access_point.access_point_arn
                    }
                },
            )
        )
        database.connections.allow_default_port_from(self.api_service.service)
        filesystem.file_system.connections.allow_default_port_from(self.api_service.service)

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
                directory=str(_REPO_ROOT),
                file="infrastructure/docker/Dockerfile.api",
            ),
            command=[
                "python",
                "scripts/02_build_faiss_index.py",
                "--index",
                FAISS_INDEX_PATH,
                "--mapping",
                FAISS_MAPPING_PATH,
            ],
            environment={
                "APP_ENV": "production",
                "DB_SECRET_ARN": database.secret.secret_arn,
                "S3_BUCKET_NAME": bucket.bucket_name,
            },
            logging=ecs.LogDriver.aws_logs(stream_prefix="chicfinder-index-builder"),
        )
        builder_container.add_mount_points(
            ecs.MountPoint(
                container_path=EFS_MOUNT_PATH,
                source_volume="faiss-index",
                read_only=False,
            )
        )

        bucket.grant_read(self.builder_task_definition.task_role)
        database.secret.grant_read(self.builder_task_definition.task_role)
        # See the API task role's grant above for why this is a manual PolicyStatement
        # rather than efs.FileSystem.grant_read_write().
        self.builder_task_definition.task_role.add_to_principal_policy(
            iam.PolicyStatement(
                actions=["elasticfilesystem:ClientMount", "elasticfilesystem:ClientWrite"],
                resources=[filesystem.file_system.file_system_arn],
                conditions={
                    "StringEquals": {
                        "elasticfilesystem:AccessPointArn": filesystem.access_point.access_point_arn
                    }
                },
            )
        )

        self.builder_security_group = ec2.SecurityGroup(
            self, "IndexBuilderSecurityGroup", vpc=vpc, allow_all_outbound=True
        )
        database.connections.allow_default_port_from(self.builder_security_group)
        filesystem.file_system.connections.allow_default_port_from(self.builder_security_group)
