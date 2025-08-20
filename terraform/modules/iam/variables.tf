variable "name_prefix" {
  description = "Name prefix for resources"
  type        = string
}

variable "s3_bucket_arn" {
  description = "S3 bucket ARN for video storage"
  type        = string
}

variable "dynamodb_table_arn" {
  description = "DynamoDB table ARN"
  type        = string
}

variable "dynamodb_cache_table_arn" {
  description = "DynamoDB cache table ARN"
  type        = string
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}