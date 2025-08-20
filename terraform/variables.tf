variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "video-description-gen"
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "max_video_size_mb" {
  description = "Maximum video size in MB"
  type        = number
  default     = 500
}

variable "video_processing_timeout" {
  description = "Video processing timeout in seconds"
  type        = number
  default     = 900
}

variable "bedrock_model_id" {
  description = "Amazon Bedrock model ID for description generation"
  type        = string
  default     = "anthropic.claude-3-sonnet-20240229-v1:0"
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 1024
}

variable "s3_lifecycle_days" {
  description = "Days to keep temporary files in S3"
  type        = number
  default     = 1
}

variable "api_throttle_burst_limit" {
  description = "API Gateway throttle burst limit"
  type        = number
  default     = 200
}

variable "api_throttle_rate_limit" {
  description = "API Gateway throttle rate limit"
  type        = number
  default     = 100
}

variable "enable_vpc_endpoints" {
  description = "Enable VPC endpoints for AWS services"
  type        = bool
  default     = false
}

variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "video-description-generator"
    ManagedBy   = "terraform"
    Environment = "dev"
  }
}