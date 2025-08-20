output "api_gateway_url" {
  description = "API Gateway invoke URL"
  value       = module.api_gateway.api_gateway_url
}

output "api_gateway_id" {
  description = "API Gateway ID"
  value       = module.api_gateway.api_gateway_id
}

output "s3_bucket_name" {
  description = "S3 bucket name for video storage"
  value       = module.s3.bucket_name
}

output "dynamodb_table_name" {
  description = "DynamoDB table name for job storage"
  value       = module.dynamodb.table_name
}

output "lambda_processor_function_name" {
  description = "Lambda processor function name"
  value       = module.lambda.processor_function_name
}

output "lambda_api_function_name" {
  description = "Lambda API handler function name"
  value       = module.lambda.api_function_name
}

output "cloudwatch_log_group_processor" {
  description = "CloudWatch log group for processor function"
  value       = module.cloudwatch.processor_log_group
}

output "cloudwatch_log_group_api" {
  description = "CloudWatch log group for API function"
  value       = module.cloudwatch.api_log_group
}

output "iam_processor_role_arn" {
  description = "IAM role ARN for processor Lambda"
  value       = module.iam.processor_role_arn
}

output "iam_api_role_arn" {
  description = "IAM role ARN for API Lambda"
  value       = module.iam.api_role_arn
}

output "vpc_id" {
  description = "VPC ID (not used - internet gateway architecture)"
  value       = null
}

output "deployment_info" {
  description = "Deployment information"
  value = {
    environment = var.environment
    region      = var.aws_region
    timestamp   = timestamp()
  }
}