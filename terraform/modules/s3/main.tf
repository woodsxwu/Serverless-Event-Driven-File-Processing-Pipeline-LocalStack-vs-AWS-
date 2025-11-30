# S3 Module - Storage bucket

resource "aws_s3_bucket" "data_bucket" {
  bucket = var.bucket_name

  force_destroy = true

  tags = {
    Name        = "${var.project_name}-bucket"
    Environment = var.environment
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "data_bucket" {
  bucket = aws_s3_bucket.data_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Create uploads/ and processed/ prefixes
resource "aws_s3_object" "uploads_prefix" {
  bucket  = aws_s3_bucket.data_bucket.id
  key     = "uploads/"
  content = ""
}

resource "aws_s3_object" "processed_prefix" {
  bucket  = aws_s3_bucket.data_bucket.id
  key     = "processed/"
  content = ""
}

# Configure event notification to Lambda (if Lambda ARN provided)
resource "aws_s3_bucket_notification" "bucket_notification" {
  count  = var.lambda_function_arn != "" ? 1 : 0
  bucket = aws_s3_bucket.data_bucket.id

  lambda_function {
    lambda_function_arn = var.lambda_function_arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/"
    filter_suffix       = ".csv"
  }
}

