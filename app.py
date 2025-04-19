#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cspc_infra.cspc_infra_stack import CspcInfraStack
from apply_site.database import DatabaseStack
from apply_site.backend import BackendStack
from apply_site.infra import InfraStack
from apply_site.cloud_front import StaticWebsiteStack


app = cdk.App()



infra_stack = InfraStack(app, "InfraStack")

database_stack = DatabaseStack(app, "DatabaseStack")

static_site_stack = StaticWebsiteStack(app, "ApplySiteStaticWebsiteStack")
app.synth()
