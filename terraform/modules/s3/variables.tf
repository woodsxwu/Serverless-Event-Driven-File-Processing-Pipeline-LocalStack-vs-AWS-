variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
}

variable "lambda_function_arn" {
  description = "ARN of the Lambda function to trigger (empty to skip notification)"
  type        = string
  default     = ""
}

