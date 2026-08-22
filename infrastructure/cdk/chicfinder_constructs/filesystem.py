from aws_cdk import RemovalPolicy, aws_ec2 as ec2, aws_efs as efs
from constructs import Construct


class Filesystem(Construct):
    """EFS volume holding the built FAISS index (embeddings.index, index_to_image_id.json)."""

    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.IVpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.file_system = efs.FileSystem(
            self,
            "FaissIndexVolume",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            removal_policy=RemovalPolicy.RETAIN,
        )

        self.access_point = self.file_system.add_access_point(
            "FaissIndexAccessPoint",
            path="/faiss-index",
            create_acl=efs.Acl(owner_gid="1000", owner_uid="1000", permissions="755"),
            posix_user=efs.PosixUser(uid="1000", gid="1000"),
        )
