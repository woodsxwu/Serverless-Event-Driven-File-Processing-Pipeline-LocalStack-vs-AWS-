terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # LocalStack uses dummy credentials, AWS uses real credentials from environment
  access_key = local.use_localstack ? "test" : null
  secret_key = local.use_localstack ? "test" : null
  token      = local.use_localstack ? "test" : null

  # LocalStack configuration (auto-enabled when environment=localstack)
  skip_credentials_validation = local.use_localstack
  skip_metadata_api_check     = local.use_localstack
  skip_requesting_account_id  = local.use_localstack
  s3_use_path_style          = local.use_localstack

  endpoints {
    s3         = local.use_localstack ? var.localstack_endpoint : null
    lambda     = local.use_localstack ? var.localstack_endpoint : null
    dynamodb   = local.use_localstack ? var.localstack_endpoint : null
    iam        = local.use_localstack ? var.localstack_endpoint : null
    sts        = local.use_localstack ? var.localstack_endpoint : null
    cloudwatchlogs = local.use_localstack ? var.localstack_endpoint : null
  }
}

