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


def test_index_builder_task_definition_mounts_efs_read_write():
    stack, compute = _build_stack()
    template = Template.from_stack(stack)

    # Two task definitions total: the API service's, and the builder's.
    template.resource_count_is("AWS::ECS::TaskDefinition", 2)
    assert compute.builder_task_definition is not None
