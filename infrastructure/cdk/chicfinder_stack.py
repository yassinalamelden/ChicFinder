from aws_cdk import Stack
from constructs import Construct

from chicfinder_constructs.networking import Networking
from chicfinder_constructs.storage import Storage
from chicfinder_constructs.database import Database
from chicfinder_constructs.filesystem import Filesystem
from chicfinder_constructs.compute import Compute


class ChicFinderStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.networking = Networking(self, "Networking")
        self.storage = Storage(self, "Storage")
        self.database = Database(self, "Database", vpc=self.networking.vpc)
        self.filesystem = Filesystem(self, "Filesystem", vpc=self.networking.vpc)
        self.compute = Compute(
            self,
            "Compute",
            vpc=self.networking.vpc,
            bucket=self.storage.bucket,
            database=self.database,
            filesystem=self.filesystem,
        )
