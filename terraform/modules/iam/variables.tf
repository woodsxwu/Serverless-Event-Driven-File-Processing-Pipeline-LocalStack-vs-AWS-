variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "use_existing_role" {
  description = "Whether to use an existing IAM role instead of creating a new one"
  type        = bool
}

variable "existing_role_arn" {
  description = "ARN of existing IAM role (if use_existing_role is true)"
  type        = string
  default     = ""
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  type        = string
}

variable "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table"
  type        = string
}

