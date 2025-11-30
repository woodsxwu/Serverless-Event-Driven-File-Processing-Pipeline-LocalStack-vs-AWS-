# Main Terraform configuration
# Uses modular structure for better organization
# Provider configuration is in provider.tf

# Random ID for unique bucket naming
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# Local variables
locals {
  bucket_name = "${var.project_name}-${var.environment}-${random_id.bucket_suffix.hex}"
}

# Step 1: Create DynamoDB table
module "dynamodb" {
  source = "./modules/dynamodb"

  project_name = var.project_name
  environment  = var.environment
}

# Step 2: Create S3 bucket (without event notifications yet)
module "s3" {
  source = "./modules/s3"

  project_name = var.project_name
  environment  = var.environment
  bucket_name  = local.bucket_name
  # Lambda ARN not provided yet - notification will be added later
}

# Step 3: Create IAM role for Lambda
module "iam" {
  source = "./modules/iam"

  project_name       = var.project_name
  environment        = var.environment
  use_existing_role  = var.lab_role_arn != "" && !local.use_localstack
  existing_role_arn  = var.lab_role_arn
  s3_bucket_arn      = module.s3.bucket_arn
  dynamodb_table_arn = module.dynamodb.table_arn
}

# Step 4: Create Lambda function
module "lambda" {
  source = "./modules/lambda"

  project_name   = var.project_name
  environment    = var.environment
  lambda_runtime = var.lambda_runtime
  lambda_timeout = var.lambda_timeout
  lambda_memory  = var.lambda_memory

  lambda_source_dir   = "${path.module}/../lambda"
  lambda_role_arn     = module.iam.lambda_role_arn
  dynamodb_table_name = module.dynamodb.table_name
  s3_bucket_name      = module.s3.bucket_name
  s3_bucket_arn       = module.s3.bucket_arn
}

# Step 5: Add S3 event notification to trigger Lambda
resource "aws_s3_bucket_notification" "lambda_trigger" {
  bucket = module.s3.bucket_id

  lambda_function {
    lambda_function_arn = module.lambda.function_arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/"
    filter_suffix       = ".csv"
  }

  depends_on = [module.lambda]
}
