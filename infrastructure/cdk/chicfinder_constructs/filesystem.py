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
            encrypted=True,
            # TEARDOWN: was RETAIN. The FAISS index here is a build artifact —
            # regenerable from the catalog images via
            # ai_engine/embeddings/database_builder.py — so it is not worth
            # preserving, and RETAIN only left the volume billing after the
            # stack was gone.
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.access_point = self.file_system.add_access_point(
            "FaissIndexAccessPoint",
            path="/faiss-index",
            create_acl=efs.Acl(owner_gid="1000", owner_uid="1000", permissions="755"),
            posix_user=efs.PosixUser(uid="1000", gid="1000"),
        )
