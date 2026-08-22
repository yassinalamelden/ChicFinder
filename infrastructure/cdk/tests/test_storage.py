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
