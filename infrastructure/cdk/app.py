#!/usr/bin/env python3
import aws_cdk as cdk

from chicfinder_stack import ChicFinderStack

app = cdk.App()
ChicFinderStack(app, "ChicFinderStack")
app.synth()
