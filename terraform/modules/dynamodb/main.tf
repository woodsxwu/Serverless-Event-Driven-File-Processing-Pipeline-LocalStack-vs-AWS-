# DynamoDB Module - File metadata table

resource "aws_dynamodb_table" "file_metadata" {
  name           = "${var.project_name}-file-metadata-${var.environment}"
  billing_mode   = var.billing_mode
  hash_key       = "file_name"

  # For provisioned mode
  read_capacity  = var.billing_mode == "PROVISIONED" ? var.read_capacity : null
  write_capacity = var.billing_mode == "PROVISIONED" ? var.write_capacity : null

  attribute {
    name = "file_name"
    type = "S"
  }

  tags = {
    Name        = "${var.project_name}-file-metadata"
    Environment = var.environment
  }
}

