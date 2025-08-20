terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(var.tags, {
      Environment = var.environment
    })
  }
}

# Generate unique suffix for resource names
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  common_tags = merge(var.tags, {
    Environment = var.environment
  })
}

# No VPC - using internet gateway for AWS service calls

# IAM Module
module "iam" {
  source = "./modules/iam"

  name_prefix                = local.name_prefix
  s3_bucket_arn             = module.s3.bucket_arn
  dynamodb_table_arn        = module.dynamodb.table_arn
  dynamodb_cache_table_arn  = module.dynamodb.cache_table_arn
  tags                      = local.common_tags
}

# S3 Module
module "s3" {
  source = "./modules/s3"

  name_prefix         = local.name_prefix
  random_suffix       = random_string.suffix.result
  lifecycle_days      = var.s3_lifecycle_days
  max_video_size_mb   = var.max_video_size_mb
  tags                = local.common_tags
}

# DynamoDB Module
module "dynamodb" {
  source = "./modules/dynamodb"

  name_prefix = local.name_prefix
  tags        = local.common_tags
}

# CloudWatch Module
module "cloudwatch" {
  source = "./modules/cloudwatch"

  name_prefix                = local.name_prefix
  enable_detailed_monitoring = var.enable_detailed_monitoring
  tags                      = local.common_tags
}

# Lambda Module
module "lambda" {
  source = "./modules/lambda"

  name_prefix                = local.name_prefix
  aws_region                = var.aws_region
  s3_bucket_name            = module.s3.bucket_name
  dynamodb_table_name       = module.dynamodb.table_name
  processor_role_arn        = module.iam.processor_role_arn
  api_role_arn              = module.iam.api_role_arn
  processor_log_group_name  = module.cloudwatch.processor_log_group
  api_log_group_name        = module.cloudwatch.api_log_group
  memory_size               = var.lambda_memory_size
  timeout                   = var.video_processing_timeout
  bedrock_model_id          = var.bedrock_model_id
  max_video_size_mb         = var.max_video_size_mb
  vpc_subnet_ids            = null
  vpc_security_group_ids    = null
  tags                      = local.common_tags

  depends_on = [
    module.s3,
    module.dynamodb,
    module.iam,
    module.cloudwatch
  ]
}

# API Gateway Module
module "api_gateway" {
  source = "./modules/api_gateway"

  name_prefix                = local.name_prefix
  aws_region                = var.aws_region
  lambda_api_function_name   = module.lambda.api_function_name
  lambda_api_invoke_arn      = module.lambda.api_invoke_arn
  throttle_burst_limit       = var.api_throttle_burst_limit
  throttle_rate_limit        = var.api_throttle_rate_limit
  tags                       = local.common_tags

  depends_on = [module.lambda]
}