import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aws_cdk as cdk
from aws_cdk.assertions import Template

from chicfinder_constructs.networking import Networking
from chicfinder_constructs.database import Database


def test_database_is_postgres_in_private_subnet_with_generated_secret():
    app = cdk.App()
    stack = cdk.Stack(app, "TestStack")
    networking = Networking(stack, "Networking")
    Database(stack, "Database", vpc=networking.vpc)

    template = Template.from_stack(stack)
    template.resource_count_is("AWS::RDS::DBInstance", 1)
    template.has_resource_properties("AWS::RDS::DBInstance", {"Engine": "postgres"})
    template.resource_count_is("AWS::SecretsManager::Secret", 1)
