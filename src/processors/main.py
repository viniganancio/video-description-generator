"""
Video Processing Lambda Function
Main handler for processing video URLs and generating descriptions
"""
import json
import logging
import os
import traceback
from datetime import datetime, timedelta
from decimal import Decimal

import boto3
from video_processor import VideoProcessor
from aws_services import AWSServices

# Configure logging for AWS Lambda
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set log level for boto3 to reduce noise
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# Initialize AWS services
aws_services = AWSServices()


def decimal_default(obj):
    """JSON serializer for objects with Decimal types"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def lambda_handler(event, context):
    """
    Lambda handler for video processing
    
    Args:
        event: Lambda event containing job information
        context: Lambda context
        
    Returns:
        dict: Processing result
    """
    try:
        logger.info(f"🚀 Lambda started processing video job")
        logger.info(f"📋 Event details: {json.dumps(event, default=str)}")
        
        # Extract job information
        if 'Records' in event:
            # Triggered by S3 or SQS
            record = event['Records'][0]
            if 'body' in record:
                # SQS message
                job_data = json.loads(record['body'])
            else:
                # Direct invocation
                job_data = record
        else:
            # Direct invocation
            job_data = event
            
        job_id = job_data.get('job_id')
        s3_key = job_data.get('s3_key')
        
        if not job_id or not s3_key:
            raise ValueError("Missing required job_id or s3_key")
            
        # Update job status to processing
        aws_services.update_job_status(
            job_id=job_id,
            status='processing',
            details={'started_at': datetime.utcnow().isoformat()}
        )
        
        # Initialize video processor
        processor = VideoProcessor(aws_services)
        
        # Process the video
        result = processor.process_video_from_s3(job_id, s3_key)
        
        # Update job with final results
        aws_services.update_job_status(
            job_id=job_id,
            status='completed',
            details={
                'completed_at': datetime.utcnow().isoformat(),
                'description': result.get('description'),
                'visual_analysis': result.get('visual_analysis'),
                'audio_analysis': result.get('audio_analysis'),
                'confidence_score': result.get('confidence_score', 0.0),
                'processing_duration': result.get('processing_duration', 0)
            }
        )
        
        logger.info(f"Successfully processed video job {job_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'job_id': job_id,
                'status': 'completed',
                'description': result.get('description'),
                'confidence_score': result.get('confidence_score', 0.0)
            }, default=decimal_default)
        }
        
    except Exception as e:
        error_message = str(e)
        error_traceback = traceback.format_exc()
        logger.error(f"Error processing video: {error_message}")
        logger.error(f"Traceback: {error_traceback}")
        
        # Update job status to failed if we have job_id
        job_id = None
        try:
            if 'job_id' in locals():
                job_id = locals()['job_id']
            elif isinstance(event, dict):
                job_id = event.get('job_id')
                
            if job_id:
                aws_services.update_job_status(
                    job_id=job_id,
                    status='failed',
                    details={
                        'error': error_message,
                        'failed_at': datetime.utcnow().isoformat()
                    }
                )
        except Exception as update_error:
            logger.error(f"Failed to update job status: {update_error}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_message,
                'job_id': job_id
            }, default=decimal_default)
        }