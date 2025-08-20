# DynamoDB table for job status and results
resource "aws_dynamodb_table" "video_jobs" {
  name           = "${var.name_prefix}-video-jobs"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "job_id"

  attribute {
    name = "job_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  # Global Secondary Index for querying by status
  global_secondary_index {
    name               = "status-created_at-index"
    hash_key           = "status"
    range_key          = "created_at"
    projection_type    = "ALL"
  }

  # Enable point-in-time recovery
  point_in_time_recovery {
    enabled = true
  }

  # Enable server-side encryption
  server_side_encryption {
    enabled = true
  }

  # TTL for automatic cleanup of old jobs
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-video-jobs-table"
    Purpose = "video-processing-jobs"
  })
}

# DynamoDB table for video analysis cache (optional optimization)
resource "aws_dynamodb_table" "video_cache" {
  name           = "${var.name_prefix}-video-cache"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "video_url_hash"

  attribute {
    name = "video_url_hash"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  # Global Secondary Index for cleanup by creation date
  global_secondary_index {
    name            = "created_at-index"
    hash_key        = "created_at"
    projection_type = "ALL"
  }

  # Enable point-in-time recovery
  point_in_time_recovery {
    enabled = true
  }

  # Enable server-side encryption
  server_side_encryption {
    enabled = true
  }

  # TTL for automatic cleanup (7 days for cache)
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-video-cache-table"
    Purpose = "video-analysis-cache"
  })
}