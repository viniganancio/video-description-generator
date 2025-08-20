# Serverless Video Description Generator

A complete AWS serverless solution that automatically generates engaging video descriptions from YouTube or direct video URLs using AI-powered visual and audio analysis.

## Architecture

- **API Gateway**: REST endpoints for video submission and result retrieval
- **Lambda Functions**: Processing pipeline and API handlers
- **S3**: Temporary video storage with lifecycle policies
- **Amazon Rekognition Video**: Visual analysis (objects, activities, celebrities, text)
- **Amazon Transcribe**: Audio transcription
- **Amazon Bedrock (Claude)**: AI-powered description generation
- **DynamoDB**: Job status and results storage
- **CloudWatch**: Comprehensive logging and monitoring

## Features

- ✅ YouTube URL and direct video URL support
- ✅ Parallel visual and audio analysis
- ✅ Graceful handling of videos without audio
- ✅ Intelligent AI prompt engineering
- ✅ Comprehensive error handling and retry logic
- ✅ Automatic cleanup of temporary files
- ✅ Production-ready monitoring and logging

## API Endpoints

- `POST /analyze` - Submit video for analysis
- `GET /status/{job_id}` - Check processing status
- `GET /result/{job_id}` - Retrieve final description

## Quick Start

1. **Deploy Infrastructure**:
   ```bash
   cd terraform
   terraform init
   terraform plan -var-file="environments/dev.tfvars"
   terraform apply -var-file="environments/dev.tfvars"
   ```

2. **Deploy Lambda Functions**:
   ```bash
   ./scripts/deploy.sh dev
   ```

3. **Test the API**:
   ```bash
   curl -X POST https://your-api-gateway-url/analyze \
     -H "Content-Type: application/json" \
     -d '{"video_url": "https://www.youtube.com/watch?v=example"}'
   ```

## Project Structure

```
├── terraform/                 # Infrastructure as Code
│   ├── modules/               # Reusable Terraform modules
│   ├── environments/          # Environment-specific configurations
│   └── main.tf               # Root configuration
├── src/                      # Lambda function source code
│   ├── handlers/             # API endpoint handlers
│   ├── processors/           # Video processing pipeline
│   ├── shared/               # Shared utilities and AWS integrations
│   └── layers/               # Lambda layers for dependencies
├── scripts/                  # Deployment and utility scripts
└── docs/                     # Additional documentation
```

## Environment Variables

The solution uses environment variables for configuration:

- `S3_BUCKET_NAME`: Temporary video storage bucket
- `DYNAMODB_TABLE_NAME`: Jobs and results table
- `BEDROCK_MODEL_ID`: Claude model identifier
- `MAX_VIDEO_SIZE_MB`: Maximum allowed video size
- `VIDEO_PROCESSING_TIMEOUT`: Processing timeout in seconds

## Monitoring and Logging

- CloudWatch Logs capture all Lambda execution logs
- Custom metrics track processing success rates and duration
- Alarms notify on error rates and processing failures
- X-Ray tracing for performance monitoring

## Security

- IAM roles follow principle of least privilege
- S3 buckets configured with secure policies
- API Gateway includes proper CORS and rate limiting
- VPC endpoints for secure AWS service communication

## Cost Optimization

- S3 lifecycle policies automatically delete temporary files
- Lambda functions optimized for memory and timeout
- Parallel processing reduces overall execution time
- Pay-per-use pricing model scales with usage