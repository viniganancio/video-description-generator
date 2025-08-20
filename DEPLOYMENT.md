# Video Description Generator - Deployment Guide

This document provides comprehensive deployment instructions for the serverless video description generation system.

## Quick Start

### Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured with credentials
3. **Terraform** (>= 1.0)
4. **Python 3.11+**
5. **jq** for JSON processing

### 1. Environment Setup

```bash
# Clone and setup
git clone <repository-url>
cd video-description-generator

# Run setup script (installs dependencies)
./scripts/setup-environment.sh

# Or use make
make setup
```

### 2. Configure Environment

```bash
# Copy and edit environment configuration
cp terraform/environments/dev.tfvars terraform/environments/my-env.tfvars

# Edit the configuration
vi terraform/environments/my-env.tfvars
```

### 3. Deploy Infrastructure

```bash
# Deploy everything
./scripts/deploy.sh dev deploy

# Or use make
make deploy ENV=dev
```

### 4. Test Deployment

```bash
# Test API endpoints
./scripts/test-api.sh

# Or use make
make test-api ENV=dev
```

## Architecture Overview

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   API Gateway   │───▶│   Lambda     │───▶│   Lambda        │
│   (REST API)    │    │   (API)      │    │   (Processor)   │
└─────────────────┘    └──────────────┘    └─────────────────┘
                              │                       │
                              ▼                       ▼
                       ┌──────────────┐    ┌─────────────────┐
                       │   DynamoDB   │    │       S3        │
                       │   (Jobs)     │    │   (Videos)      │
                       └──────────────┘    └─────────────────┘
                                                      │
                                                      ▼
                              ┌─────────────────────────────────┐
                              │         AWS Services            │
                              │  ┌─────────────────────────────┐ │
                              │  │      Rekognition Video      │ │
                              │  └─────────────────────────────┘ │
                              │  ┌─────────────────────────────┐ │
                              │  │      Transcribe            │ │
                              │  └─────────────────────────────┘ │
                              │  ┌─────────────────────────────┐ │
                              │  │      Bedrock (Claude)      │ │
                              │  └─────────────────────────────┘ │
                              └─────────────────────────────────┘
```

## Environment Configuration

### Development Environment (`dev.tfvars`)

```hcl
environment = "dev"
aws_region  = "us-east-1"

# Video processing settings
max_video_size_mb         = 300
video_processing_timeout  = 900
lambda_memory_size       = 1024

# API Gateway throttling
api_throttle_burst_limit = 500
api_throttle_rate_limit  = 250

# Monitoring
enable_detailed_monitoring = true
```

### Production Environment (`prod.tfvars`)

```hcl
environment = "prod"
aws_region  = "us-east-1"

# Video processing settings
max_video_size_mb         = 500
video_processing_timeout  = 900
lambda_memory_size       = 1536

# API Gateway throttling
api_throttle_burst_limit = 200
api_throttle_rate_limit  = 100

# Monitoring
enable_detailed_monitoring = true
```

## Detailed Deployment Process

### Step 1: Infrastructure Deployment

```bash
cd terraform
terraform init
terraform workspace select dev || terraform workspace new dev
terraform plan -var-file="environments/dev.tfvars"
terraform apply -var-file="environments/dev.tfvars"
```

### Step 2: Lambda Function Deployment

The deployment script automatically:

1. **Builds Lambda Layers**:
   - Dependencies layer (yt-dlp, boto3, requests)
   - Shared utilities layer

2. **Packages Lambda Functions**:
   - Video processor function
   - API handler function

3. **Deploys to AWS**:
   - Updates function code
   - Configures environment variables
   - Sets up triggers and permissions

### Step 3: Configuration

Key environment variables set automatically:

```bash
# Core Configuration
S3_BUCKET_NAME=<generated-bucket-name>
DYNAMODB_TABLE_NAME=<generated-table-name>
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Processing Limits
MAX_VIDEO_SIZE_MB=500
VIDEO_PROCESSING_TIMEOUT=900

# AWS Region
AWS_REGION=us-east-1
```

## API Endpoints

### POST /analyze
Submit a video URL for analysis.

```bash
curl -X POST https://your-api-url/analyze \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://www.youtube.com/watch?v=example"}'
```

**Response:**
```json
{
  "job_id": "uuid-here",
  "status": "pending",
  "message": "Video analysis started",
  "estimated_completion_time": "2024-01-01T12:05:00Z"
}
```

### GET /status/{job_id}
Check the status of a video analysis job.

```bash
curl https://your-api-url/status/job-id-here
```

**Response:**
```json
{
  "job_id": "uuid-here",
  "status": "processing",
  "video_url": "https://example.com/video.mp4",
  "created_at": "2024-01-01T12:00:00Z",
  "progress": {
    "stage": "analyzing",
    "estimated_remaining_seconds": 300
  }
}
```

### GET /result/{job_id}
Retrieve the analysis results.

```bash
curl https://your-api-url/result/job-id-here
```

**Response:**
```json
{
  "job_id": "uuid-here",
  "status": "completed",
  "description": "An engaging video featuring...",
  "confidence_score": 0.87,
  "processing_duration": 245.6,
  "completed_at": "2024-01-01T12:04:05Z"
}
```

## Monitoring and Logging

### CloudWatch Logs

- **Processor Logs**: `/aws/lambda/video-description-gen-{env}-processor`
- **API Logs**: `/aws/lambda/video-description-gen-{env}-api`

### Viewing Logs

```bash
# Tail processor logs
make logs-processor ENV=dev

# Tail API logs
make logs-api ENV=dev

# Or use AWS CLI directly
aws logs tail "/aws/lambda/video-description-gen-dev-processor" --follow
```

### CloudWatch Metrics

Automatic monitoring includes:
- Lambda execution duration and errors
- API Gateway request counts and error rates
- DynamoDB read/write capacity
- S3 object counts and sizes

### Alarms

Pre-configured alarms:
- Lambda error rate > 5%
- Lambda duration > 10 minutes
- API Gateway 4xx error rate > 10 requests/5 minutes
- API Gateway 5xx error rate > 5 requests/5 minutes

## Security Considerations

### IAM Permissions

The system uses least-privilege IAM roles:

**Processor Lambda Role**:
- S3: GetObject, PutObject, DeleteObject
- DynamoDB: GetItem, PutItem, UpdateItem
- Rekognition: Start*/Get* operations
- Transcribe: Start*/Get* operations
- Bedrock: InvokeModel

**API Lambda Role**:
- DynamoDB: GetItem, PutItem, UpdateItem, Query
- Lambda: InvokeFunction

### Network Security

- All Lambda functions use internet gateway (no VPC configuration)
- S3 buckets block public access
- API Gateway includes CORS configuration
- DynamoDB uses encryption at rest

### Data Protection

- Videos are automatically deleted after 24 hours
- Job records have 30-day TTL
- All S3 transfers use HTTPS
- DynamoDB encryption enabled

## Troubleshooting

### Common Issues

1. **Lambda Timeout**:
   ```bash
   # Increase timeout in tfvars
   video_processing_timeout = 1200  # 20 minutes
   ```

2. **Memory Issues**:
   ```bash
   # Increase memory in tfvars
   lambda_memory_size = 2048  # 2GB
   ```

3. **Permission Errors**:
   ```bash
   # Check IAM role permissions
   aws iam get-role-policy --role-name video-description-gen-dev-processor-lambda-role --policy-name video-description-gen-dev-processor-lambda-policy
   ```

4. **API Gateway CORS Issues**:
   ```bash
   # Test CORS preflight
   curl -X OPTIONS https://your-api-url/analyze \
     -H "Origin: https://example.com" \
     -H "Access-Control-Request-Method: POST"
   ```

### Debugging

1. **Enable Debug Logging**:
   ```bash
   # Set in Lambda environment variables
   LOG_LEVEL=DEBUG
   ENABLE_DEBUG_LOGGING=true
   ```

2. **Check Job Status**:
   ```bash
   # Query DynamoDB directly
   aws dynamodb get-item \
     --table-name video-description-gen-dev-video-jobs \
     --key '{"job_id": {"S": "your-job-id"}}'
   ```

3. **Check S3 Objects**:
   ```bash
   # List S3 objects
   aws s3 ls s3://your-bucket-name/videos/ --recursive
   ```

### Performance Tuning

1. **Parallel Processing**: Already enabled for Rekognition and Transcribe
2. **Caching**: Results cached for 7 days by default
3. **Memory Optimization**: Adjust `lambda_memory_size` based on usage
4. **Timeout Optimization**: Set `video_processing_timeout` based on video lengths

## Cost Optimization

### Expected Costs (per 1000 videos)

- **Lambda**: $2-5 (depending on processing time)
- **Rekognition**: $10-15 (video analysis)
- **Transcribe**: $5-10 (audio transcription)
- **Bedrock**: $1-3 (description generation)
- **S3**: $0.50 (temporary storage)
- **DynamoDB**: $0.25 (job storage)
- **API Gateway**: $1 (API requests)

**Total: ~$20-35 per 1000 videos**

### Cost Reduction Strategies

1. **Optimize Video Size Limits**:
   ```hcl
   max_video_size_mb = 200  # Reduce from 500MB
   ```

2. **Reduce Analysis Scope**:
   - Skip celebrity recognition for basic use cases
   - Limit Rekognition labels to top 10

3. **Use Caching Effectively**:
   - Enable caching for repeated URLs
   - Increase cache TTL for stable content

## Cleanup

### Destroy Infrastructure

```bash
# Using deployment script
./scripts/deploy.sh dev destroy

# Using make
make destroy ENV=dev

# Manual Terraform
cd terraform
terraform workspace select dev
terraform destroy -var-file="environments/dev.tfvars"
```

### Clean Local Files

```bash
# Clean build artifacts
make clean

# Remove all temporary files
rm -rf .terraform/
rm -f *.tfstate*
rm -f deployment-outputs-*.json
```

## Support and Maintenance

### Regular Maintenance Tasks

1. **Update Dependencies** (monthly):
   ```bash
   pip install --upgrade -r requirements.txt
   ```

2. **Review Logs** (weekly):
   ```bash
   make logs-processor ENV=prod | grep ERROR
   ```

3. **Check Costs** (monthly):
   ```bash
   aws ce get-cost-and-usage --time-period Start=2024-01-01,End=2024-02-01 --granularity MONTHLY --metrics BlendedCost
   ```

4. **Update Terraform Providers** (quarterly):
   ```bash
   terraform init -upgrade
   ```

### Scaling Considerations

- **Concurrent Executions**: Lambda default limit is 1000
- **API Gateway**: Rate limiting configured per environment
- **DynamoDB**: Auto-scaling enabled
- **S3**: No limits, but costs scale with storage

For production deployments processing >10,000 videos/month, consider:
- Reserved Lambda capacity
- DynamoDB reserved capacity
- S3 Intelligent Tiering
- CloudFront for API caching