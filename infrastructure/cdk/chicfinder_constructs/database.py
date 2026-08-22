from aws_cdk import RemovalPolicy, aws_ec2 as ec2, aws_rds as rds
from constructs import Construct


class Database(Construct):
    """RDS Postgres instance holding the `items` catalog table."""

    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.IVpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.instance = rds.DatabaseInstance(
            self,
            "Postgres",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.MICRO
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            database_name="chicfinder",
            credentials=rds.Credentials.from_generated_secret("chicfinder_admin"),
            allocated_storage=20,
            removal_policy=RemovalPolicy.RETAIN,
        )
        self.secret = self.instance.secret
        self.connections = self.instance.connections
