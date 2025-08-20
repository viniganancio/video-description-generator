"""
AWS Services Integration Module
Provides common AWS service operations used across processors
"""
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class AWSServices:
    """Centralized AWS services client"""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.s3_client = boto3.client('s3')
        
        # Get configuration from environment
        self.jobs_table_name = os.environ['DYNAMODB_TABLE_NAME']
        self.cache_table_name = os.environ.get('DYNAMODB_CACHE_TABLE_NAME', f"{self.jobs_table_name}-cache")
        self.s3_bucket = os.environ['S3_BUCKET_NAME']
        self.bedrock_model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
        
        # Initialize DynamoDB tables
        self.jobs_table = self.dynamodb.Table(self.jobs_table_name)
        try:
            self.cache_table = self.dynamodb.Table(self.cache_table_name)
        except Exception as e:
            logger.warning(f"Cache table not available: {e}")
            self.cache_table = None
    
    def update_job_status(self, job_id: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Update job status in DynamoDB
        
        Args:
            job_id: Job identifier
            status: New status (pending, processing, completed, failed)
            details: Additional details to store
        """
        try:
            update_expression = "SET job_status = :status, updated_at = :updated_at"
            expression_values = {
                ':status': status,
                ':updated_at': datetime.utcnow().isoformat()
            }
            
            if details:
                # Flatten details into top-level attributes
                for key, value in details.items():
                    attr_name = f":{key}"
                    update_expression += f", {key} = {attr_name}"
                    expression_values[attr_name] = value
            
            # Add TTL (30 days from now)
            ttl = int(time.time()) + (30 * 24 * 60 * 60)
            update_expression += ", #ttl = :ttl"
            expression_values[':ttl'] = ttl
            
            response = self.jobs_table.update_item(
                Key={'job_id': job_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames={'#ttl': 'ttl'},
                ExpressionAttributeValues=expression_values,
                ReturnValues="UPDATED_NEW"
            )
            
            logger.info(f"Updated job {job_id} status to {status}")
            
        except Exception as e:
            logger.error(f"Failed to update job status: {str(e)}")
            raise
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job status from DynamoDB
        
        Args:
            job_id: Job identifier
            
        Returns:
            dict: Job information or None if not found
        """
        try:
            response = self.jobs_table.get_item(
                Key={'job_id': job_id}
            )
            
            return response.get('Item')
            
        except Exception as e:
            logger.error(f"Failed to get job status: {str(e)}")
            return None
    
    def create_job(self, job_id: str, video_url: str) -> None:
        """
        Create a new job entry in DynamoDB
        
        Args:
            job_id: Job identifier
            video_url: Video URL to process
        """
        try:
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
            
            logger.info(f"Created job {job_id} for URL: {video_url}")
            
        except Exception as e:
            logger.error(f"Failed to create job: {str(e)}")
            raise
    
    def delete_s3_object(self, bucket: str, key: str) -> None:
        """
        Delete object from S3
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
        """
        try:
            self.s3_client.delete_object(Bucket=bucket, Key=key)
            logger.info(f"Deleted S3 object: s3://{bucket}/{key}")
            
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchKey':
                logger.error(f"Failed to delete S3 object: {str(e)}")
                raise
    
    def get_cached_result(self, url_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get cached processing result
        
        Args:
            url_hash: MD5 hash of the video URL
            
        Returns:
            dict: Cached result or None
        """
        if not self.cache_table:
            return None
            
        try:
            response = self.cache_table.get_item(
                Key={'video_url_hash': url_hash}
            )
            
            item = response.get('Item')
            if item:
                # Check if cache is still valid
                current_time = int(time.time())
                if item.get('ttl', 0) > current_time:
                    logger.info(f"Cache hit for URL hash: {url_hash}")
                    # Remove TTL and hash from returned data
                    cached_result = dict(item)
                    cached_result.pop('ttl', None)
                    cached_result.pop('video_url_hash', None)
                    cached_result.pop('created_at', None)
                    return cached_result
                else:
                    logger.info(f"Cache expired for URL hash: {url_hash}")
                    # Delete expired cache entry
                    self.cache_table.delete_item(Key={'video_url_hash': url_hash})
            
            return None
            
        except Exception as e:
            logger.warning(f"Cache lookup failed: {str(e)}")
            return None
    
    def cache_result(self, url_hash: str, result: Dict[str, Any], ttl: int) -> None:
        """
        Cache processing result
        
        Args:
            url_hash: MD5 hash of the video URL
            result: Processing result to cache
            ttl: Time to live (Unix timestamp)
        """
        if not self.cache_table:
            return
            
        try:
            cache_item = dict(result)
            cache_item.update({
                'video_url_hash': url_hash,
                'created_at': datetime.utcnow().isoformat(),
                'ttl': ttl
            })
            
            self.cache_table.put_item(Item=cache_item)
            logger.info(f"Cached result for URL hash: {url_hash}")
            
        except Exception as e:
            logger.warning(f"Failed to cache result: {str(e)}")
    
    def list_jobs_by_status(self, status: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List jobs by status
        
        Args:
            status: Job status to filter by
            limit: Maximum number of jobs to return
            
        Returns:
            list: List of job items
        """
        try:
            response = self.jobs_table.query(
                IndexName='status-created_at-index',
                KeyConditionExpression='job_status = :status',
                ExpressionAttributeValues={':status': status},
                ScanIndexForward=False,  # Most recent first
                Limit=limit
            )
            
            return response.get('Items', [])
            
        except Exception as e:
            logger.error(f"Failed to list jobs by status: {str(e)}")
            return []
    
    def cleanup_old_jobs(self, days_old: int = 7) -> int:
        """
        Clean up old completed/failed jobs
        
        Args:
            days_old: Jobs older than this many days will be deleted
            
        Returns:
            int: Number of jobs cleaned up
        """
        try:
            cutoff_time = datetime.utcnow().timestamp() - (days_old * 24 * 60 * 60)
            cutoff_iso = datetime.fromtimestamp(cutoff_time).isoformat()
            
            # Scan for old jobs
            response = self.jobs_table.scan(
                FilterExpression='created_at < :cutoff AND (job_status = :completed OR job_status = :failed)',
                ExpressionAttributeValues={
                    ':cutoff': cutoff_iso,
                    ':completed': 'completed',
                    ':failed': 'failed'
                }
            )
            
            items_to_delete = response.get('Items', [])
            deleted_count = 0
            
            # Delete in batches
            with self.jobs_table.batch_writer() as batch:
                for item in items_to_delete:
                    batch.delete_item(Key={'job_id': item['job_id']})
                    deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old jobs")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old jobs: {str(e)}")
            return 0