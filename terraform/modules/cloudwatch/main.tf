# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "processor_lambda" {
  name              = "/aws/lambda/${var.name_prefix}-processor"
  retention_in_days = 14

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-processor-logs"
    Purpose = "lambda-logs"
  })
}

resource "aws_cloudwatch_log_group" "api_lambda" {
  name              = "/aws/lambda/${var.name_prefix}-api"
  retention_in_days = 14

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-api-logs"
    Purpose = "lambda-logs"
  })
}

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${var.name_prefix}"
  retention_in_days = 14

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-api-gateway-logs"
    Purpose = "api-gateway-logs"
  })
}

# CloudWatch Metrics and Alarms
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  count = var.enable_detailed_monitoring ? 1 : 0

  alarm_name          = "${var.name_prefix}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors lambda errors"
  alarm_actions       = []

  dimensions = {
    FunctionName = "${var.name_prefix}-processor"
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  count = var.enable_detailed_monitoring ? 1 : 0

  alarm_name          = "${var.name_prefix}-lambda-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = "600000"  # 10 minutes
  alarm_description   = "This metric monitors lambda duration"
  alarm_actions       = []

  dimensions = {
    FunctionName = "${var.name_prefix}-processor"
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "api_gateway_4xx" {
  count = var.enable_detailed_monitoring ? 1 : 0

  alarm_name          = "${var.name_prefix}-api-4xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "4XXError"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors API Gateway 4xx errors"
  alarm_actions       = []

  dimensions = {
    ApiName = "${var.name_prefix}-api"
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "api_gateway_5xx" {
  count = var.enable_detailed_monitoring ? 1 : 0

  alarm_name          = "${var.name_prefix}-api-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors API Gateway 5xx errors"
  alarm_actions       = []

  dimensions = {
    ApiName = "${var.name_prefix}-api"
  }

  tags = var.tags
}

# Custom CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  count = var.enable_detailed_monitoring ? 1 : 0

  dashboard_name = "${var.name_prefix}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", "${var.name_prefix}-processor"],
            ["AWS/Lambda", "Errors", "FunctionName", "${var.name_prefix}-processor"],
            ["AWS/Lambda", "Duration", "FunctionName", "${var.name_prefix}-processor"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Lambda Processor Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiName", "${var.name_prefix}-api"],
            ["AWS/ApiGateway", "4XXError", "ApiName", "${var.name_prefix}-api"],
            ["AWS/ApiGateway", "5XXError", "ApiName", "${var.name_prefix}-api"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "API Gateway Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "${var.name_prefix}-video-jobs"],
            ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", "${var.name_prefix}-video-jobs"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "DynamoDB Metrics"
          period  = 300
        }
      }
    ]
  })
}

data "aws_region" "current" {}