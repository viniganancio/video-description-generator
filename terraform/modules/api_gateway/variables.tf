variable "name_prefix" {
  description = "Name prefix for resources"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "lambda_api_function_name" {
  description = "Lambda API function name"
  type        = string
}

variable "lambda_api_invoke_arn" {
  description = "Lambda API invoke ARN"
  type        = string
}

variable "throttle_burst_limit" {
  description = "API Gateway throttle burst limit"
  type        = number
  default     = 200
}

variable "throttle_rate_limit" {
  description = "API Gateway throttle rate limit"
  type        = number
  default     = 100
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}