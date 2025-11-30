# Environment configuration
variable "environment" {
  description = "Environment: 'localstack' or 'aws'"
  type        = string
  default     = "localstack"
  
  validation {
    condition     = contains(["localstack", "aws"], var.environment)
    error_message = "Environment must be either 'localstack' or 'aws'."
  }
}

# AWS configuration
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "lab_role_arn" {
  description = "AWS Learner Lab role ARN (only for AWS deployments, leave empty to create new role)"
  type        = string
  default     = ""
}

# Project configuration
variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "data-ingestion-pipeline"
}

# Lambda configuration
variable "lambda_runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.9"
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 300
}

variable "lambda_memory" {
  description = "Lambda memory in MB"
  type        = number
  default     = 512
}

# LocalStack configuration (advanced users only)
variable "localstack_endpoint" {
  description = "LocalStack endpoint URL (only used when environment=localstack)"
  type        = string
  default     = "http://localhost:4566"
}

# Derived locals - automatically determined from environment
locals {
  use_localstack = var.environment == "localstack"
}

