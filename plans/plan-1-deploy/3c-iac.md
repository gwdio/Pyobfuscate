# 3c: IaC

**Depends on:** 3a, 3b (Lambda zip must exist before deploy)

## What

Define all infrastructure as code. Tool choice: TBD (Terraform or CDK — decide before starting this step).

## Resources

| Resource | Purpose |
|----------|---------|
| Lambda function | Engine execution (server path) |
| Lambda Function URL | Public HTTPS endpoint (simpler than API Gateway for a single function) |
| Lambda IAM role | Logs-only permissions |
| S3 bucket | Frontend static asset hosting |
| CloudFront distribution | CDN in front of S3; also proxies Lambda Function URL under the same domain to avoid CORS |
| ACM certificate | HTTPS for the CloudFront domain |

## Structure

```
infra/
  main.tf (or lib/stack.ts for CDK)
  variables.tf / config
  outputs.tf         — prints the CloudFront URL and Lambda Function URL after deploy
```

## Files

- New: `infra/` directory with all IaC source

## Verification

1. `terraform plan` (or `cdk synth`) runs without errors against a dev AWS account
2. `terraform apply` deploys all resources; `outputs` prints the live URLs
3. `curl -X POST <lambda-function-url> -d @tests/fixtures/sample_event.json` returns 200 with obfuscated source
4. `curl <cloudfront-url>` returns the frontend HTML
5. `terraform destroy` tears down cleanly with no orphaned resources
