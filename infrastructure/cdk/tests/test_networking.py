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
