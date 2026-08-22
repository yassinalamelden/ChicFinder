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
