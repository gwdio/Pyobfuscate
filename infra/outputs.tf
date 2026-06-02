output "cloudfront_url" {
  description = "Public frontend URL"
  value       = "https://${aws_cloudfront_distribution.main.domain_name}"
}

output "lambda_function_url" {
  description = "Lambda Function URL (direct — normally accessed via CloudFront /obfuscate)"
  value       = aws_lambda_function_url.obfuscator.function_url
}

output "frontend_bucket" {
  description = "S3 bucket name for frontend assets"
  value       = aws_s3_bucket.frontend.bucket
}
