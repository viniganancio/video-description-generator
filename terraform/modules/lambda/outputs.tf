output "processor_function_name" {
  description = "Processor Lambda function name"
  value       = aws_lambda_function.processor.function_name
}

output "processor_function_arn" {
  description = "Processor Lambda function ARN"
  value       = aws_lambda_function.processor.arn
}

output "api_function_name" {
  description = "API Lambda function name"
  value       = aws_lambda_function.api.function_name
}

output "api_function_arn" {
  description = "API Lambda function ARN"
  value       = aws_lambda_function.api.arn
}

output "api_invoke_arn" {
  description = "API Lambda invoke ARN"
  value       = aws_lambda_function.api.invoke_arn
}

output "shared_layer_arn" {
  description = "Shared Lambda layer ARN"
  value       = aws_lambda_layer_version.shared_layer.arn
}

output "dependencies_layer_arn" {
  description = "Dependencies Lambda layer ARN"
  value       = aws_lambda_layer_version.dependencies_layer.arn
}