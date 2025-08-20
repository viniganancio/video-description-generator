variable "name_prefix" {
  description = "Name prefix for resources"
  type        = string
}

variable "random_suffix" {
  description = "Random suffix for unique naming"
  type        = string
}

variable "lifecycle_days" {
  description = "Days to keep temporary files"
  type        = number
  default     = 1
}

variable "max_video_size_mb" {
  description = "Maximum video size in MB"
  type        = number
  default     = 500
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}