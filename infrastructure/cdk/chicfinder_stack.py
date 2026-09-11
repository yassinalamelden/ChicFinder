from aws_cdk import CfnOutput, Stack, aws_ec2 as ec2
from constructs import Construct

from chicfinder_constructs.networking import Networking
from chicfinder_constructs.storage import Storage
from chicfinder_constructs.database import Database
from chicfinder_constructs.filesystem import Filesystem
from chicfinder_constructs.compute import Compute


class ChicFinderStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.networking = Networking(self, "Networking")
        self.storage = Storage(self, "Storage")
        self.database = Database(self, "Database", vpc=self.networking.vpc)
        self.filesystem = Filesystem(self, "Filesystem", vpc=self.networking.vpc)
        self.compute = Compute(
            self,
            "Compute",
            vpc=self.networking.vpc,
            bucket=self.storage.bucket,
            database=self.database,
            filesystem=self.filesystem,
        )

        CfnOutput(self, "ClusterName", value=self.compute.cluster.cluster_name)
        CfnOutput(self, "ApiServiceName", value=self.compute.api_service.service.service_name)
        CfnOutput(
            self,
            "ApiBaseUrl",
            value=f"http://{self.compute.api_service.load_balancer.load_balancer_dns_name}",
            description=(
                "Plain-HTTP ALB address — the only address the API has until "
                "a domain + ACM certificate are wired up for HTTPS (see the "
                "2026-09-10 audit, finding B0). iOS will refuse to call this "
                "over HTTP by default (App Transport Security)."
            ),
        )
        CfnOutput(
            self,
            "IndexBuilderTaskDefinitionArn",
            value=self.compute.builder_task_definition.task_definition_arn,
        )
        CfnOutput(
            self,
            "IndexBuilderSecurityGroupId",
            value=self.compute.builder_security_group.security_group_id,
        )
        CfnOutput(
            self,
            "PrivateSubnetIds",
            value=",".join(
                self.networking.vpc.select_subnets(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                ).subnet_ids
            ),
        )
        CfnOutput(self, "CatalogBucketName", value=self.storage.bucket.bucket_name)
        CfnOutput(self, "DatabaseSecretArn", value=self.database.secret.secret_arn)
