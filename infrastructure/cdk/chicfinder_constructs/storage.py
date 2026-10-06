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
            # TEARDOWN: was RETAIN. DESTROY + auto_delete_objects so the bucket
            # actually goes away — CloudFormation refuses to delete a non-empty
            # bucket, and RETAIN left it billing after the stack was gone.
            #
            # WARNING: these product images are NOT in git and are not covered
            # by the RDS snapshot. Mirror them locally before destroying:
            #     aws s3 sync s3://<CatalogBucketName> ./backup/catalog-images
            # See docs/aws-teardown.md, step 1.
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
        self.bucket.grant_public_access()
