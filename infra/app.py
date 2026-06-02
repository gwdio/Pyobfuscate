import os
import aws_cdk as cdk
from pyobfuscate_stack import PyobfuscateStack

app = cdk.App()

PyobfuscateStack(
    app,
    "PyobfuscateStack",
    domain_name=os.environ.get("DOMAIN_NAME"),
    certificate_arn=os.environ.get("CERTIFICATE_ARN"),
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
        region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
    ),
)

app.synth()
