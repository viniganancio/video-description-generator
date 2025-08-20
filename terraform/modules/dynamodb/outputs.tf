output "table_name" {
  description = "Name of the main DynamoDB table"
  value       = aws_dynamodb_table.video_jobs.name
}

output "table_arn" {
  description = "ARN of the main DynamoDB table"
  value       = aws_dynamodb_table.video_jobs.arn
}

output "cache_table_name" {
  description = "Name of the cache DynamoDB table"
  value       = aws_dynamodb_table.video_cache.name
}

output "cache_table_arn" {
  description = "ARN of the cache DynamoDB table"
  value       = aws_dynamodb_table.video_cache.arn
}