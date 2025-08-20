output "processor_log_group" {
  description = "CloudWatch log group for processor Lambda"
  value       = aws_cloudwatch_log_group.processor_lambda.name
}

output "api_log_group" {
  description = "CloudWatch log group for API Lambda"
  value       = aws_cloudwatch_log_group.api_lambda.name
}

output "api_gateway_log_group" {
  description = "CloudWatch log group for API Gateway"
  value       = aws_cloudwatch_log_group.api_gateway.name
}

output "dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = var.enable_detailed_monitoring ? "https://console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${aws_cloudwatch_dashboard.main[0].dashboard_name}" : null
}