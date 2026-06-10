terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

locals {
  lambda_zip   = "${path.module}/../dist/lambda.zip"
  frontend_dir = "${path.module}/../frontend"

  # Strip "https://" and trailing "/" from the Function URL to get a bare domain
  lambda_domain = trim(replace(aws_lambda_function_url.obfuscator.function_url, "https://", ""), "/")

  mime_types = {
    ".html" = "text/html"
    ".css"  = "text/css"
    ".js"   = "application/javascript"
    ".json" = "application/json"
    ".ico"  = "image/x-icon"
    ".png"  = "image/png"
    ".svg"  = "image/svg+xml"
  }

  # Python source files bundled for Pyodide (client-side execution)
  pyodide_package_files = jsondecode(file("${path.module}/../pyodide_files.json"))
}

# ── IAM ──────────────────────────────────────────────────────────────────────

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "pyobfuscate-lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ── Lambda ────────────────────────────────────────────────────────────────────

resource "aws_lambda_function" "obfuscator" {
  filename                       = local.lambda_zip
  source_code_hash               = filebase64sha256(local.lambda_zip)
  function_name                  = "pyobfuscate"
  role                           = aws_iam_role.lambda.arn
  handler                        = "lambda_handler.lambda_handler"
  runtime                        = "python3.12"
  timeout     = 10
  memory_size = 256
  description = "pyobfuscate engine — server execution path"
}

resource "aws_lambda_function_url" "obfuscator" {
  function_name      = aws_lambda_function.obfuscator.function_name
  authorization_type = "AWS_IAM"
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/pyobfuscate"
  retention_in_days = 7
}

resource "aws_lambda_permission" "cloudfront" {
  statement_id  = "AllowCloudFrontInvokeFunctionUrl"
  action        = "lambda:InvokeFunctionUrl"
  function_name = aws_lambda_function.obfuscator.function_name
  principal     = "cloudfront.amazonaws.com"
  source_arn    = aws_cloudfront_distribution.main.arn
}

resource "aws_lambda_permission" "cloudfront_invoke" {
  statement_id  = "AllowCloudFrontInvokeFunction"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.obfuscator.function_name
  principal     = "cloudfront.amazonaws.com"
  source_arn    = aws_cloudfront_distribution.main.arn
}

# ── S3 CloudFront access log bucket ──────────────────────────────────────────

resource "aws_s3_bucket" "cf_logs" {
  bucket_prefix = "pyobfuscate-cf-logs-"
  force_destroy = true
}

# CloudFront requires ACLs to write access logs
resource "aws_s3_bucket_ownership_controls" "cf_logs" {
  bucket = aws_s3_bucket.cf_logs.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "cf_logs" {
  depends_on = [aws_s3_bucket_ownership_controls.cf_logs]
  bucket     = aws_s3_bucket.cf_logs.id
  acl        = "private"
}

# ── S3 frontend bucket ────────────────────────────────────────────────────────

resource "aws_s3_bucket" "frontend" {
  bucket_prefix = "pyobfuscate-frontend-"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket                  = aws_s3_bucket.frontend.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ── CloudFront OACs ───────────────────────────────────────────────────────────

resource "aws_cloudfront_origin_access_control" "lambda" {
  name                              = "pyobfuscate-lambda-oac"
  origin_access_control_origin_type = "lambda"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = "pyobfuscate-frontend-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# ── S3 bucket policy (CloudFront OAC only) ───────────────────────────────────

data "aws_iam_policy_document" "s3_cloudfront" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.frontend.arn}/*"]
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.main.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  policy = data.aws_iam_policy_document.s3_cloudfront.json
}

# ── CloudFront Function: /obfuscate viewer-response — convert stray HTML to JSON ─

# custom_error_response is distribution-wide and cannot be scoped to a specific origin.
# If it fires for /obfuscate (e.g. an S3 403 mapped to index.html), the viewer-response
# function detects the HTML content-type and replaces the body with a generic JSON error,
# so the browser always gets application/json on this path.
resource "aws_cloudfront_function" "obfuscate_error_response" {
  name    = "pyobfuscate-obfuscate-error-response"
  runtime = "cloudfront-js-2.0"
  publish = true
  code    = <<-EOF
    function handler(event) {
      var ct = (event.response.headers['content-type'] || {}).value || '';
      if (ct.indexOf('text/html') === 0) {
        return {
          statusCode: 502,
          statusDescription: 'Bad Gateway',
          headers: { 'content-type': { value: 'application/json' } },
          body: { encoding: 'text', data: '{"error":"Processing error"}' }
        };
      }
      return event.response;
    }
  EOF
}

# ── CloudFront response headers policy ───────────────────────────────────────

resource "aws_cloudfront_response_headers_policy" "security" {
  name = "pyobfuscate-security-headers"

  security_headers_config {
    strict_transport_security {
      access_control_max_age_sec = 63072000
      include_subdomains         = true
      preload                    = true
      override                   = true
    }
    content_type_options {
      override = true
    }
    frame_options {
      frame_option = "DENY"
      override     = true
    }
    content_security_policy {
      # Pyodide (client path) loads JS and WASM from cdn.jsdelivr.net and
      # creates blob: workers at runtime.
      content_security_policy = "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https://cdn.jsdelivr.net; worker-src blob:"
      override                = true
    }
  }
}

# ── Managed CloudFront policies (looked up by name) ──────────────────────────

data "aws_cloudfront_cache_policy" "optimized" {
  name = "Managed-CachingOptimized"
}

data "aws_cloudfront_cache_policy" "disabled" {
  name = "Managed-CachingDisabled"
}

data "aws_cloudfront_origin_request_policy" "all_viewer_except_host" {
  name = "Managed-AllViewerExceptHostHeader"
}

# OAC owns the Authorization header — this policy must not forward it
resource "aws_cloudfront_origin_request_policy" "lambda" {
  name = "pyobfuscate-lambda-origin-request"

  headers_config {
    header_behavior = "allExcept"
    headers {
      items = ["authorization", "host"]
    }
  }

  cookies_config {
    cookie_behavior = "all"
  }

  query_strings_config {
    query_string_behavior = "all"
  }
}

# ── CloudFront distribution ───────────────────────────────────────────────────

resource "aws_cloudfront_distribution" "main" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  price_class         = "PriceClass_100"
  aliases             = var.domain_name != null ? [var.domain_name] : []

  logging_config {
    bucket          = aws_s3_bucket.cf_logs.bucket_domain_name
    include_cookies = false
    prefix          = "cf/"
  }

  # S3 origin (frontend)
  origin {
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id                = "s3-frontend"
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
  }

  # Lambda Function URL origin — OAC signs with SigV4; source_arn restricts to this distribution.
  origin {
    domain_name              = local.lambda_domain
    origin_id                = "lambda-obfuscator"
    origin_access_control_id = aws_cloudfront_origin_access_control.lambda.id
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # Default behaviour → S3 (frontend)
  default_cache_behavior {
    target_origin_id          = "s3-frontend"
    viewer_protocol_policy    = "redirect-to-https"
    allowed_methods           = ["GET", "HEAD"]
    cached_methods            = ["GET", "HEAD"]
    compress                  = true
    cache_policy_id           = data.aws_cloudfront_cache_policy.optimized.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
  }

  # /obfuscate → Lambda
  ordered_cache_behavior {
    path_pattern               = "/obfuscate"
    target_origin_id           = "lambda-obfuscator"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.disabled.id
    origin_request_policy_id   = aws_cloudfront_origin_request_policy.lambda.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id

    # reject_truncated removed: accessing event.request.body triggers CloudFront
    # body re-encoding which breaks the x-amz-content-sha256 OAC signature.
    # Oversized body protection is handled by the Lambda handler instead.

    function_association {
      event_type   = "viewer-response"
      function_arn = aws_cloudfront_function.obfuscate_error_response.arn
    }
  }

  custom_error_response {
    error_code         = 403
    response_code      = 404
    response_page_path = "/404.html"
  }

  viewer_certificate {
    cloudfront_default_certificate = var.certificate_arn == null
    acm_certificate_arn            = var.certificate_arn
    ssl_support_method             = var.certificate_arn != null ? "sni-only" : null
    minimum_protocol_version       = var.certificate_arn != null ? "TLSv1.2_2021" : null
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
}

# ── Frontend assets → S3 ─────────────────────────────────────────────────────

resource "aws_s3_object" "frontend" {
  for_each = setsubtract(fileset(local.frontend_dir, "**"), ["package.json"])

  bucket       = aws_s3_bucket.frontend.id
  key          = each.value
  source       = "${local.frontend_dir}/${each.value}"
  etag         = filemd5("${local.frontend_dir}/${each.value}")
  content_type = lookup(local.mime_types, try(regex("\\.[^.]+$", each.value), ""), "application/octet-stream")
}

# package.json for Pyodide — built at apply time from Python sources, served from S3.
# Pyodide path is fully independent of Lambda.
resource "aws_s3_object" "package_json" {
  bucket       = aws_s3_bucket.frontend.id
  key          = "package.json"
  content_type = "application/json"
  content = jsonencode({
    for f in local.pyodide_package_files : f => file("${path.module}/../${f}")
  })
  etag = md5(jsonencode({
    for f in local.pyodide_package_files : f => file("${path.module}/../${f}")
  }))

  depends_on = [aws_s3_object.frontend]
}

# ── CloudFront cache invalidation ────────────────────────────────────────────

resource "terraform_data" "frontend_invalidation" {
  triggers_replace = concat(
    [for obj in aws_s3_object.frontend : obj.etag],
    [aws_s3_object.package_json.etag],
  )

  provisioner "local-exec" {
    command = "aws cloudfront create-invalidation --distribution-id ${aws_cloudfront_distribution.main.id} --paths '/*'"
  }

  depends_on = [aws_s3_object.frontend]
}

# ── Alerts ───────────────────────────────────────────────────────────────────

resource "aws_sns_topic" "alerts" {
  name = "pyobfuscate-alerts"
}

resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "invocations_per_minute" {
  alarm_name          = "pyobfuscate-invocations-per-minute"
  namespace           = "AWS/Lambda"
  metric_name         = "Invocations"
  dimensions          = { FunctionName = aws_lambda_function.obfuscator.function_name }
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 30
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

# ── Route 53 DNS ─────────────────────────────────────────────────────────────

data "aws_route53_zone" "root" {
  name         = "grantwang.dev."
  private_zone = false
}

# Alias records (A + AAAA) — preferred over CNAME for CloudFront
resource "aws_route53_record" "pyobfuscate_a" {
  zone_id = data.aws_route53_zone.root.zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = aws_cloudfront_distribution.main.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "pyobfuscate_aaaa" {
  zone_id = data.aws_route53_zone.root.zone_id
  name    = var.domain_name
  type    = "AAAA"

  alias {
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = aws_cloudfront_distribution.main.hosted_zone_id
    evaluate_target_health = false
  }
}

# ── Alerts ───────────────────────────────────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "invocations_per_hour" {
  alarm_name          = "pyobfuscate-invocations-per-hour"
  namespace           = "AWS/Lambda"
  metric_name         = "Invocations"
  dimensions          = { FunctionName = aws_lambda_function.obfuscator.function_name }
  statistic           = "Sum"
  period              = 3600
  evaluation_periods  = 1
  threshold           = 1000
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
