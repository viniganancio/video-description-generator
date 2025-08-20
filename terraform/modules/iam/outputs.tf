output "processor_role_arn" {
  description = "ARN of the processor Lambda role"
  value       = aws_iam_role.processor_lambda_role.arn
}

output "api_role_arn" {
  description = "ARN of the API Lambda role"
  value       = aws_iam_role.api_lambda_role.arn
}

output "api_gateway_role_arn" {
  description = "ARN of the API Gateway role"
  value       = aws_iam_role.api_gateway_role.arn
}