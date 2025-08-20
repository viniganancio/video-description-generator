"""
API Handler Class
Implements the REST API endpoints for video analysis
"""
import json
import logging
import os
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional
import urllib.parse

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class APIHandler:
    """Handles REST API requests for video analysis service"""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.lambda_client = boto3.client('lambda')
        
        # Configuration from environment
        self.jobs_table_name = os.environ['DYNAMODB_TABLE_NAME']
        self.processor_function_name = os.environ['PROCESSOR_FUNCTION_NAME']
        
        # Initialize DynamoDB table
        self.jobs_table = self.dynamodb.Table(self.jobs_table_name)
    
    def handle_analyze(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle POST /analyze endpoint
        
        Args:
            body: Request body containing video_url
            
        Returns:
            dict: HTTP response
        """
        try:
            # Validate request
            video_url = body.get('video_url')
            if not video_url:
                return self.error_response(400, "Missing required field: video_url")
            
            # Validate URL format
            if not self._is_valid_url(video_url):
                return self.error_response(400, "Invalid video URL format")
            
            # Check URL length
            if len(video_url) > 2048:
                return self.error_response(400, "Video URL too long (max 2048 characters)")
            
            # Generate unique job ID
            job_id = str(uuid.uuid4())
            
            # Create job record
            self._create_job_record(job_id, video_url)
            
            # Trigger video processor Lambda asynchronously
            self._trigger_video_processor(job_id, video_url)
            
            return self.success_response(202, {
                'job_id': job_id,
                'status': 'pending',
                'message': 'Video analysis started',
                'estimated_completion_time': self._estimate_completion_time()
            })
            
        except Exception as e:
            logger.error(f"Error in analyze endpoint: {str(e)}")
            return self.error_response(500, "Failed to start video analysis")
    
    def handle_status(self, job_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle GET /status/{job_id} endpoint
        
        Args:
            job_id: Job identifier
            query_params: Query parameters
            
        Returns:
            dict: HTTP response
        """
        try:
            if not job_id:
                return self.error_response(400, "Missing job_id in path")
            
            # Get job from DynamoDB
            job_data = self._get_job_record(job_id)
            if not job_data:
                return self.error_response(404, f"Job not found: {job_id}")
            
            # Build response
            status_response = {
                'job_id': job_id,
                'status': job_data.get('job_status', 'unknown'),
                'video_url': job_data.get('video_url'),
                'created_at': job_data.get('created_at'),
                'updated_at': job_data.get('updated_at')
            }
            
            # Add progress information based on status
            status = job_data.get('job_status')
            if status == 'processing':
                status_response['progress'] = {
                    'stage': 'analyzing',
                    'estimated_remaining_seconds': 300  # Conservative estimate
                }
                if job_data.get('started_at'):
                    elapsed_seconds = (datetime.utcnow() - datetime.fromisoformat(job_data['started_at'].replace('Z', ''))).total_seconds()
                    status_response['progress']['elapsed_seconds'] = int(elapsed_seconds)
            
            elif status == 'completed':
                # Include basic completion info (full results available via /result endpoint)
                status_response['completion_info'] = {
                    'completed_at': job_data.get('completed_at'),
                    'processing_duration': job_data.get('processing_duration'),
                    'has_description': bool(job_data.get('description'))
                }
            
            elif status == 'failed':
                status_response['error'] = job_data.get('error', 'Unknown error occurred')
                status_response['failed_at'] = job_data.get('failed_at')
            
            return self.success_response(200, status_response)
            
        except Exception as e:
            logger.error(f"Error in status endpoint: {str(e)}")
            return self.error_response(500, "Failed to get job status")
    
    def handle_result(self, job_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle GET /result/{job_id} endpoint
        
        Args:
            job_id: Job identifier
            query_params: Query parameters
            
        Returns:
            dict: HTTP response
        """
        try:
            if not job_id:
                return self.error_response(400, "Missing job_id in path")
            
            # Get job from DynamoDB
            job_data = self._get_job_record(job_id)
            if not job_data:
                return self.error_response(404, f"Job not found: {job_id}")
            
            status = job_data.get('job_status')
            
            if status == 'pending':
                return self.error_response(202, "Job is still pending", {
                    'job_id': job_id,
                    'status': status,
                    'message': 'Analysis not yet started'
                })
            
            elif status == 'processing':
                return self.error_response(202, "Job is still processing", {
                    'job_id': job_id,
                    'status': status,
                    'message': 'Analysis in progress'
                })
            
            elif status == 'failed':
                return self.error_response(500, "Job failed", {
                    'job_id': job_id,
                    'status': status,
                    'error': job_data.get('error', 'Unknown error'),
                    'failed_at': job_data.get('failed_at')
                })
            
            elif status == 'completed':
                # Include detailed option based on query parameter
                include_analysis = query_params.get('include_analysis', '').lower() == 'true'
                
                result_response = {
                    'job_id': job_id,
                    'status': status,
                    'video_url': job_data.get('video_url'),
                    'description': job_data.get('description'),
                    'confidence_score': job_data.get('confidence_score', 0.0),
                    'created_at': job_data.get('created_at'),
                    'completed_at': job_data.get('completed_at'),
                    'processing_duration': job_data.get('processing_duration')
                }
                
                # Include detailed analysis if requested
                if include_analysis:
                    result_response['visual_analysis'] = job_data.get('visual_analysis', {})
                    result_response['audio_analysis'] = job_data.get('audio_analysis', {})
                
                return self.success_response(200, result_response)
            
            else:
                return self.error_response(500, f"Unknown job status: {status}")
            
        except Exception as e:
            logger.error(f"Error in result endpoint: {str(e)}")
            return self.error_response(500, "Failed to get job result")
    
    def handle_options(self) -> Dict[str, Any]:
        """
        Handle OPTIONS requests for CORS preflight
        
        Returns:
            dict: CORS response
        """
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token',
                'Access-Control-Max-Age': '86400'
            },
            'body': ''
        }
    
    def success_response(self, status_code: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a successful HTTP response"""
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'X-Request-ID': str(uuid.uuid4())[:8]
            },
            'body': json.dumps(data, default=str)
        }
    
    def error_response(self, status_code: int, message: str, extra_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create an error HTTP response"""
        error_body = {
            'error': message,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        if extra_data:
            error_body.update(extra_data)
        
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'X-Request-ID': str(uuid.uuid4())[:8]
            },
            'body': json.dumps(error_body)
        }
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            result = urllib.parse.urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _create_job_record(self, job_id: str, video_url: str) -> None:
        """Create job record in DynamoDB"""
        current_time = datetime.utcnow().isoformat()
        ttl = int(time.time()) + (30 * 24 * 60 * 60)  # 30 days TTL
        
        self.jobs_table.put_item(
            Item={
                'job_id': job_id,
                'video_url': video_url,
                'job_status': 'pending',
                'created_at': current_time,
                'updated_at': current_time,
                'ttl': ttl
            }
        )
        
        logger.info(f"Created job record: {job_id}")
    
    def _get_job_record(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job record from DynamoDB"""
        try:
            response = self.jobs_table.get_item(Key={'job_id': job_id})
            return response.get('Item')
        except Exception as e:
            logger.error(f"Failed to get job record: {str(e)}")
            return None
    
    def _trigger_video_processor(self, job_id: str, video_url: str) -> None:
        """Trigger video processor Lambda asynchronously"""
        payload = {
            'job_id': job_id,
            'video_url': video_url
        }
        
        try:
            self.lambda_client.invoke(
                FunctionName=self.processor_function_name,
                InvocationType='Event',  # Asynchronous invocation
                Payload=json.dumps(payload)
            )
            
            logger.info(f"Triggered video processor for job: {job_id}")
            
        except Exception as e:
            logger.error(f"Failed to trigger video processor: {str(e)}")
            # Update job status to failed
            try:
                self.jobs_table.update_item(
                    Key={'job_id': job_id},
                    UpdateExpression="SET job_status = :status, #error = :error, updated_at = :updated_at",
                    ExpressionAttributeNames={'#error': 'error'},
                    ExpressionAttributeValues={
                        ':status': 'failed',
                        ':error': f"Failed to trigger processor: {str(e)}",
                        ':updated_at': datetime.utcnow().isoformat()
                    }
                )
            except Exception as update_error:
                logger.error(f"Failed to update job status: {update_error}")
            
            raise
    
    def _estimate_completion_time(self) -> str:
        """Estimate completion time for video analysis"""
        # Conservative estimate: 5-10 minutes depending on video length
        estimated_seconds = 300  # 5 minutes
        completion_time = datetime.utcnow().timestamp() + estimated_seconds
        return datetime.fromtimestamp(completion_time).isoformat() + 'Z'