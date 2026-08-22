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
