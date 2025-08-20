variable "name_prefix" {
  description = "Name prefix for resources"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "s3_bucket_name" {
  description = "S3 bucket name for video storage"
  type        = string
}

variable "dynamodb_table_name" {
  description = "DynamoDB table name"
  type        = string
}

variable "processor_role_arn" {
  description = "IAM role ARN for processor Lambda"
  type        = string
}

variable "api_role_arn" {
  description = "IAM role ARN for API Lambda"
  type        = string
}

variable "processor_log_group_name" {
  description = "CloudWatch log group name for processor"
  type        = string
}

variable "api_log_group_name" {
  description = "CloudWatch log group name for API"
  type        = string
}

variable "memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 1024
}

variable "timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 900
}

variable "bedrock_model_id" {
  description = "Bedrock model ID"
  type        = string
}

variable "max_video_size_mb" {
  description = "Maximum video size in MB"
  type        = number
}

variable "vpc_subnet_ids" {
  description = "VPC subnet IDs for Lambda"
  type        = list(string)
  default     = null
}

variable "vpc_security_group_ids" {
  description = "VPC security group IDs for Lambda"
  type        = list(string)
  default     = null
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}