environment = "prod"
aws_region  = "us-east-1"

# Video processing settings
max_video_size_mb         = 500
video_processing_timeout  = 900  # 15 minutes
lambda_memory_size       = 1536  # More memory for production

# Bedrock configuration
bedrock_model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

# S3 settings
s3_lifecycle_days = 1

# API Gateway throttling (more restrictive for prod)
api_throttle_burst_limit = 200
api_throttle_rate_limit  = 100

# Monitoring
enable_detailed_monitoring = true
enable_vpc_endpoints      = false

# Tags
tags = {
  Environment = "prod"
  Project     = "video-description-generator"
  ManagedBy   = "terraform"
  Owner       = "platform-team"
  CostCenter  = "ai-services"
}