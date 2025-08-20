# S3 bucket for temporary video storage
resource "aws_s3_bucket" "video_storage" {
  bucket = "${var.name_prefix}-videos-${var.random_suffix}"

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-video-storage"
    Purpose = "temporary-video-storage"
  })
}

# S3 bucket versioning
resource "aws_s3_bucket_versioning" "video_storage" {
  bucket = aws_s3_bucket.video_storage.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "video_storage" {
  bucket = aws_s3_bucket.video_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# S3 bucket public access block
resource "aws_s3_bucket_public_access_block" "video_storage" {
  bucket = aws_s3_bucket.video_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket lifecycle configuration for automatic cleanup
resource "aws_s3_bucket_lifecycle_configuration" "video_storage" {
  bucket = aws_s3_bucket.video_storage.id

  rule {
    id     = "delete_temporary_videos"
    status = "Enabled"

    expiration {
      days = var.lifecycle_days
    }

    noncurrent_version_expiration {
      noncurrent_days = 1
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }

    filter {
      prefix = "videos/"
    }
  }

  rule {
    id     = "delete_transcription_files"
    status = "Enabled"

    expiration {
      days = var.lifecycle_days
    }

    filter {
      prefix = "transcriptions/"
    }
  }

  depends_on = [aws_s3_bucket_versioning.video_storage]
}

# S3 bucket policy for Lambda access
resource "aws_s3_bucket_policy" "video_storage" {
  bucket = aws_s3_bucket.video_storage.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureConnections"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.video_storage.arn,
          "${aws_s3_bucket.video_storage.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
      {
        Sid       = "EnforceSizeLimit"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.video_storage.arn}/*"
        Condition = {
          NumericGreaterThan = {
            "s3:object-size" = var.max_video_size_mb * 1024 * 1024
          }
        }
      }
    ]
  })
}

# S3 bucket notification for video processing
resource "aws_s3_bucket_notification" "video_processing" {
  bucket = aws_s3_bucket.video_storage.id

  # Placeholder for Lambda trigger - will be configured in Lambda module
  depends_on = [aws_s3_bucket.video_storage]
}