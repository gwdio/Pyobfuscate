variable "aws_region" {
  description = "AWS region for Lambda and supporting resources"
  type        = string
  default     = "us-east-1"
}

variable "domain_name" {
  description = "Optional custom domain for the CloudFront distribution (e.g. pyobfuscate.example.com)"
  type        = string
  default     = null
}

variable "certificate_arn" {
  description = "ACM certificate ARN in us-east-1 for the custom domain (required when domain_name is set)"
  type        = string
  default     = null
}

variable "alert_email" {
  description = "Email address for pyobfuscate invocation spike alerts"
  type        = string
}
