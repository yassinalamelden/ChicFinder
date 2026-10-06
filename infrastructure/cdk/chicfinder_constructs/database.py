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
            storage_encrypted=True,
            # TEARDOWN: was RETAIN, which left the instance billing as an orphan
            # after `cdk destroy` removed the stack that managed it. SNAPSHOT
            # deletes the instance but takes a final snapshot on the way out, so
            # the catalog is recoverable (`aws rds restore-db-instance-from-db-snapshot`)
            # without paying for a running instance. Snapshot storage is a few
            # euros a month at 20GB — delete the snapshot for true zero cost.
            removal_policy=RemovalPolicy.SNAPSHOT,
            # CDK defaults deletion_protection to True whenever the removal
            # policy is RETAIN. Set it explicitly so the delete is not blocked.
            deletion_protection=False,
            delete_automated_backups=True,
        )
        self.secret = self.instance.secret
        self.connections = self.instance.connections
