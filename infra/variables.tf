variable "aws_region" {
  description = "AWS region for Lambda and supporting resources"
  type        = string
  default     = "us-east-1"
}

variable "domain_name" {
  description = "Custom domain for the CloudFront distribution"
  type        = string
  default     = "pyobfuscate.grantwang.dev"
}

variable "certificate_arn" {
  description = "ACM certificate ARN in us-east-1 covering the domain (*.grantwang.dev)"
  type        = string
}

variable "alert_email" {
  description = "Email address for pyobfuscate invocation spike alerts"
  type        = string
}
