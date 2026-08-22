from aws_cdk import Stack
from constructs import Construct

from chicfinder_constructs.networking import Networking
from chicfinder_constructs.storage import Storage


class ChicFinderStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.networking = Networking(self, "Networking")
        self.storage = Storage(self, "Storage")
