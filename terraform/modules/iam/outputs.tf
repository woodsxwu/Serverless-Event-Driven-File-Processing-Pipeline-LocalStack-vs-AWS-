output "lambda_role_arn" {
  description = "ARN of the Lambda IAM role"
  value       = var.use_existing_role ? var.existing_role_arn : aws_iam_role.lambda_role[0].arn
}

output "lambda_role_name" {
  description = "Name of the Lambda IAM role"
  value       = var.use_existing_role ? "" : aws_iam_role.lambda_role[0].name
}

output "lambda_role_id" {
  description = "ID of the Lambda IAM role"
  value       = var.use_existing_role ? "" : aws_iam_role.lambda_role[0].id
}

