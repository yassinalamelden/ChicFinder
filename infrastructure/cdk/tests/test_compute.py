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

    # The builder's container mount point must be read-write (ReadOnly: False).
    template.has_resource_properties(
        "AWS::ECS::TaskDefinition",
        {
            "ContainerDefinitions": Match.array_with(
                [
                    Match.object_like(
                        {
                            "MountPoints": Match.array_with(
                                [
                                    Match.object_like(
                                        {
                                            "ContainerPath": "/mnt/faiss-index",
                                            "ReadOnly": False,
                                        }
                                    )
                                ]
                            )
                        }
                    )
                ]
            )
        },
    )

    # The builder gets its own, distinct EC2 security group (not reused from the API service).
    template.has_resource_properties(
        "AWS::EC2::SecurityGroup",
        {"GroupDescription": Match.string_like_regexp(".*IndexBuilderSecurityGroup.*")},
    )
    assert compute.builder_security_group is not None
    assert (
        compute.builder_security_group.security_group_id
        != compute.api_service.service.connections.security_groups[0].security_group_id
    )


def test_index_builder_writes_to_the_efs_mount_the_api_reads_from():
    """The builder must be told (via --index/--mapping) to write its FAISS
    artifacts onto the EFS mount rather than the container's own ephemeral
    filesystem, and the API must be told (via env vars) to read from the
    exact same EFS paths. Otherwise the built index never reaches the API."""
    stack, _ = _build_stack()
    template = Template.from_stack(stack)

    template.has_resource_properties(
        "AWS::ECS::TaskDefinition",
        {
            "ContainerDefinitions": Match.array_with(
                [
                    Match.object_like(
                        {
                            "Command": [
                                "python",
                                "scripts/02_build_faiss_index.py",
                                "--index",
                                "/mnt/faiss-index/embeddings.index",
                                "--mapping",
                                "/mnt/faiss-index/index_to_image_id.json",
                            ],
                        }
                    )
                ]
            )
        },
    )

    template.has_resource_properties(
        "AWS::ECS::TaskDefinition",
        {
            "ContainerDefinitions": Match.array_with(
                [
                    Match.object_like(
                        {
                            "Environment": Match.array_with(
                                [
                                    {
                                        "Name": "FAISS_INDEX_PATH",
                                        "Value": "/mnt/faiss-index/embeddings.index",
                                    },
                                    {
                                        "Name": "FAISS_MAPPING_PATH",
                                        "Value": "/mnt/faiss-index/index_to_image_id.json",
                                    },
                                ]
                            )
                        }
                    )
                ]
            )
        },
    )
