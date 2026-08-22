import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aws_cdk as cdk
from aws_cdk.assertions import Template, Match

from chicfinder_stack import ChicFinderStack


def _build_stack():
    app = cdk.App()
    stack = ChicFinderStack(app, "TestChicFinderStack")
    return stack


def test_no_efs_filesystem_policy_resource():
    """The EFS access is granted via manually scoped IAM PolicyStatements on
    each task role, not via FileSystem.grant_read()/grant_read_write(). Those
    built-in helpers have a side effect: they attach an
    AWS::EFS::FileSystemPolicy resource that grants ClientWrite +
    ClientRootAccess to Principal "*" whenever AccessedViaMountTarget is
    true — independently handing every mounting role write/root access
    regardless of the task role's own IAM policy. If this resource ever
    reappears, that hole has been reintroduced.
    """
    stack = _build_stack()
    template = Template.from_stack(stack)

    template.resource_count_is("AWS::EFS::FileSystemPolicy", 0)


def test_api_task_definition_efs_mount_is_read_only():
    stack = _build_stack()
    template = Template.from_stack(stack)

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
                                            "ReadOnly": True,
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


def test_alb_listener_protocol_is_unchanged():
    """Pins the ALB listener's current protocol so an accidental future
    change is caught by a regression test. This is NOT an assertion that
    the current protocol (HTTP) is correct/final — moving to HTTPS is a
    separate, not-yet-fixed finding.
    """
    stack = _build_stack()
    template = Template.from_stack(stack)

    template.has_resource_properties(
        "AWS::ElasticLoadBalancingV2::Listener",
        {"Protocol": "HTTP"},
    )


def test_stack_has_exactly_one_of_each_singleton_resource():
    stack = _build_stack()
    template = Template.from_stack(stack)

    template.resource_count_is("AWS::ECS::Cluster", 1)
    template.resource_count_is("AWS::RDS::DBInstance", 1)
    template.resource_count_is("AWS::EFS::FileSystem", 1)
    # API task definition + index-builder task definition.
    template.resource_count_is("AWS::ECS::TaskDefinition", 2)
