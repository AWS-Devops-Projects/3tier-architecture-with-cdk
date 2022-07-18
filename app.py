#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk_python.app_stack import AppStack


app = cdk.App()
AppStack(app, "CdkPythonStack", three_tier=False)

app.synth()
