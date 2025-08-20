environment = "dev"
aws_region  = "us-east-1"

# Video processing settings
max_video_size_mb         = 300
video_processing_timeout  = 900  # 15 minutes
lambda_memory_size       = 1024

# Bedrock configuration
bedrock_model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

# S3 settings
s3_lifecycle_days = 1

# API Gateway throttling (more lenient for dev)
api_throttle_burst_limit = 500
api_throttle_rate_limit  = 250

# Monitoring
enable_detailed_monitoring = true
enable_vpc_endpoints      = false

# Tags
tags = {
  Environment = "dev"
  Project     = "video-description-generator"
  ManagedBy   = "terraform"
  Owner       = "development-team"
}