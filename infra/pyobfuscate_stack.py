from pathlib import Path

import aws_cdk as cdk
from aws_cdk import (
    Duration,
    Fn,
    RemovalPolicy,
    aws_certificatemanager as acm,
    aws_cloudfront as cf,
    aws_cloudfront_origins as origins,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
)
from constructs import Construct

_REPO_ROOT = Path(__file__).parent.parent


class PyobfuscateStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        domain_name: str | None = None,
        certificate_arn: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── IAM role (logs only) ─────────────────────────────────────────────
        role = iam.Role(
            self,
            "LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        # ── Lambda function ──────────────────────────────────────────────────
        lambda_zip = _REPO_ROOT / "dist" / "lambda.zip"
        fn = lambda_.Function(
            self,
            "ObfuscatorFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="lambda_handler.lambda_handler",
            code=lambda_.Code.from_asset(str(lambda_zip)),
            role=role,
            timeout=Duration.seconds(30),
            memory_size=512,
            description="pyobfuscate engine — server execution path",
        )

        # ── Lambda Function URL (no auth — CloudFront is the gatekeeper) ────
        fn_url = fn.add_function_url(
            auth_type=lambda_.FunctionUrlAuthType.NONE,
            cors=lambda_.FunctionUrlCorsOptions(
                allowed_origins=["*"],
                allowed_methods=[lambda_.HttpMethod.POST],
                allowed_headers=["Content-Type"],
            ),
        )

        # Strip "https://" and trailing slash from the function URL token
        lambda_domain = Fn.select(2, Fn.split("/", fn_url.url))

        # ── S3 bucket for frontend ───────────────────────────────────────────
        bucket = s3.Bucket(
            self,
            "FrontendBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )

        # ── CloudFront OAC + origins ─────────────────────────────────────────
        oac = cf.S3OriginAccessControl(self, "OAC")
        s3_origin = origins.S3BucketOrigin.with_origin_access_control(
            bucket, origin_access_control=oac
        )

        lambda_origin = origins.HttpOrigin(
            lambda_domain,
            protocol_policy=cf.OriginProtocolPolicy.HTTPS_ONLY,
        )

        # ── Optional custom domain + ACM certificate ─────────────────────────
        domain_names = [domain_name] if domain_name else None
        certificate = (
            acm.Certificate.from_certificate_arn(self, "Cert", certificate_arn)
            if certificate_arn
            else None
        )

        # ── CloudFront distribution ──────────────────────────────────────────
        distribution = cf.Distribution(
            self,
            "Distribution",
            default_root_object="index.html",
            domain_names=domain_names,
            certificate=certificate,
            default_behavior=cf.BehaviorOptions(
                origin=s3_origin,
                viewer_protocol_policy=cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cf.CachePolicy.CACHING_OPTIMIZED,
                compress=True,
            ),
            additional_behaviors={
                # Proxy POST /obfuscate to the Lambda Function URL
                "/obfuscate": cf.BehaviorOptions(
                    origin=lambda_origin,
                    viewer_protocol_policy=cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cf.CachePolicy.CACHING_DISABLED,
                    allowed_methods=cf.AllowedMethods.ALLOW_ALL,
                    origin_request_policy=cf.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
                )
            },
        )

        # ── Deploy frontend assets to S3 ────────────────────────────────────
        s3deploy.BucketDeployment(
            self,
            "FrontendDeploy",
            sources=[s3deploy.Source.asset(str(_REPO_ROOT / "frontend"))],
            destination_bucket=bucket,
            distribution=distribution,
            distribution_paths=["/*"],
        )

        # ── Outputs ──────────────────────────────────────────────────────────
        cdk.CfnOutput(
            self,
            "CloudFrontURL",
            value=f"https://{distribution.domain_name}",
            description="Public frontend URL",
        )
        cdk.CfnOutput(
            self,
            "LambdaFunctionURL",
            value=fn_url.url,
            description="Lambda Function URL (direct — normally accessed via CloudFront)",
        )
