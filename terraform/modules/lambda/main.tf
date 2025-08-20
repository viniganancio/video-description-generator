# Data source for Lambda deployment packages
data "archive_file" "processor_zip" {
  type        = "zip"
  output_path = "${path.module}/processor.zip"
  source_dir  = "${path.root}/../src/processors"
}

data "archive_file" "api_zip" {
  type        = "zip"
  output_path = "${path.module}/api.zip"
  source_dir  = "${path.root}/../src/handlers"
}

data "archive_file" "shared_layer_zip" {
  type        = "zip"
  output_path = "${path.module}/shared_layer.zip"
  source_dir  = "${path.root}/../src/shared"
}

# Lambda Layer for shared utilities
resource "aws_lambda_layer_version" "shared_layer" {
  filename   = data.archive_file.shared_layer_zip.output_path
  layer_name = "${var.name_prefix}-shared-layer"

  compatible_runtimes = ["python3.11"]
  description         = "Shared utilities for video processing"

  source_code_hash = data.archive_file.shared_layer_zip.output_base64sha256

  lifecycle {
    create_before_destroy = true
  }
}

# Lambda Layer for external dependencies
resource "aws_lambda_layer_version" "dependencies_layer" {
  filename   = "${path.root}/../src/layers/dependencies.zip"
  layer_name = "${var.name_prefix}-dependencies-layer"

  compatible_runtimes = ["python3.11"]
  description         = "External dependencies (yt-dlp, boto3, etc.)"

  lifecycle {
    create_before_destroy = true
  }
}

# Video Processor Lambda Function
resource "aws_lambda_function" "processor" {
  filename         = data.archive_file.processor_zip.output_path
  function_name    = "${var.name_prefix}-processor"
  role            = var.processor_role_arn
  handler         = "main.lambda_handler"
  runtime         = "python3.11"
  timeout         = var.timeout
  memory_size     = var.memory_size
  source_code_hash = data.archive_file.processor_zip.output_base64sha256

  layers = [
    aws_lambda_layer_version.shared_layer.arn,
    aws_lambda_layer_version.dependencies_layer.arn
  ]

  dynamic "vpc_config" {
    for_each = var.vpc_subnet_ids != null ? [1] : []
    content {
      subnet_ids         = var.vpc_subnet_ids
      security_group_ids = var.vpc_security_group_ids
    }
  }

  environment {
    variables = {
      S3_BUCKET_NAME          = var.s3_bucket_name
      DYNAMODB_TABLE_NAME     = var.dynamodb_table_name
      DYNAMODB_CACHE_TABLE_NAME = var.dynamodb_cache_table_name
      BEDROCK_MODEL_ID        = var.bedrock_model_id
      MAX_VIDEO_SIZE_MB       = tostring(var.max_video_size_mb)
      LOG_LEVEL              = "INFO"
    }
  }

  tracing_config {
    mode = "Active"
  }

  depends_on = [
    aws_cloudwatch_log_group.processor_lambda
  ]

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-processor"
    Type = "video-processor"
  })
}

# API Handler Lambda Function
resource "aws_lambda_function" "api" {
  filename         = data.archive_file.api_zip.output_path
  function_name    = "${var.name_prefix}-api"
  role            = var.api_role_arn
  handler         = "main.lambda_handler"
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 256
  source_code_hash = data.archive_file.api_zip.output_base64sha256

  layers = [
    aws_lambda_layer_version.shared_layer.arn
  ]

  dynamic "vpc_config" {
    for_each = var.vpc_subnet_ids != null ? [1] : []
    content {
      subnet_ids         = var.vpc_subnet_ids
      security_group_ids = var.vpc_security_group_ids
    }
  }

  environment {
    variables = {
      DYNAMODB_TABLE_NAME     = var.dynamodb_table_name
      PROCESSOR_FUNCTION_NAME = aws_lambda_function.processor.function_name
      S3_BUCKET_NAME          = var.s3_bucket_name
      LOG_LEVEL              = "INFO"
    }
  }

  tracing_config {
    mode = "Active"
  }

  depends_on = [
    aws_cloudwatch_log_group.api_lambda
  ]

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-api"
    Type = "api-handler"
  })
}

# CloudWatch Log Groups (referenced in lambda functions)
resource "aws_cloudwatch_log_group" "processor_lambda" {
  name              = var.processor_log_group_name
  retention_in_days = 14
  
  tags = var.tags
}

resource "aws_cloudwatch_log_group" "api_lambda" {
  name              = var.api_log_group_name
  retention_in_days = 14
  
  tags = var.tags
}

# Lambda permissions for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
}