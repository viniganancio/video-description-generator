"""
Configuration Module
Centralized configuration management for the video description generation service
"""
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class Config:
    """Configuration management class"""
    
    def __init__(self):
        self._config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        return {
            # AWS Configuration
            'aws_region': os.environ.get('AWS_REGION', 'us-east-1'),
            
            # DynamoDB Configuration
            'dynamodb_table_name': os.environ.get('DYNAMODB_TABLE_NAME'),
            'dynamodb_cache_table_name': os.environ.get('DYNAMODB_CACHE_TABLE_NAME'),
            
            # S3 Configuration
            's3_bucket_name': os.environ.get('S3_BUCKET_NAME'),
            
            # Lambda Configuration
            'processor_function_name': os.environ.get('PROCESSOR_FUNCTION_NAME'),
            
            # Video Processing Configuration
            'max_video_size_mb': int(os.environ.get('MAX_VIDEO_SIZE_MB', 500)),
            'video_processing_timeout': int(os.environ.get('VIDEO_PROCESSING_TIMEOUT', 900)),
            'supported_video_formats': os.environ.get('SUPPORTED_VIDEO_FORMATS', 'mp4,avi,mov,wmv,flv,webm').split(','),
            
            # Bedrock Configuration
            'bedrock_model_id': os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0'),
            'bedrock_max_tokens': int(os.environ.get('BEDROCK_MAX_TOKENS', 300)),
            'bedrock_temperature': float(os.environ.get('BEDROCK_TEMPERATURE', 0.7)),
            
            # Rekognition Configuration
            'rekognition_max_labels': int(os.environ.get('REKOGNITION_MAX_LABELS', 20)),
            'rekognition_min_confidence': float(os.environ.get('REKOGNITION_MIN_CONFIDENCE', 80.0)),
            
            # Transcribe Configuration
            'transcribe_language_code': os.environ.get('TRANSCRIBE_LANGUAGE_CODE', 'en-US'),
            'transcribe_enable_speaker_labels': os.environ.get('TRANSCRIBE_ENABLE_SPEAKER_LABELS', 'true').lower() == 'true',
            'transcribe_max_speakers': int(os.environ.get('TRANSCRIBE_MAX_SPEAKERS', 5)),
            
            # Cache Configuration
            'cache_ttl_days': int(os.environ.get('CACHE_TTL_DAYS', 7)),
            'enable_caching': os.environ.get('ENABLE_CACHING', 'true').lower() == 'true',
            
            # Rate Limiting
            'rate_limit_per_minute': int(os.environ.get('RATE_LIMIT_PER_MINUTE', 60)),
            'rate_limit_per_hour': int(os.environ.get('RATE_LIMIT_PER_HOUR', 1000)),
            
            # Logging Configuration
            'log_level': os.environ.get('LOG_LEVEL', 'INFO'),
            'enable_debug_logging': os.environ.get('ENABLE_DEBUG_LOGGING', 'false').lower() == 'true',
            
            # Retry Configuration
            'max_retries': int(os.environ.get('MAX_RETRIES', 3)),
            'retry_base_delay': float(os.environ.get('RETRY_BASE_DELAY', 1.0)),
            'retry_max_delay': float(os.environ.get('RETRY_MAX_DELAY', 60.0)),
            
            # YouTube-DL Configuration
            'yt_dlp_format': os.environ.get('YT_DLP_FORMAT', 'best[filesize<?{}M]/best'.format(
                int(os.environ.get('MAX_VIDEO_SIZE_MB', 500))
            )),
            'yt_dlp_timeout': int(os.environ.get('YT_DLP_TIMEOUT', 300)),
            
            # API Configuration
            'api_request_timeout': int(os.environ.get('API_REQUEST_TIMEOUT', 30)),
            'enable_cors': os.environ.get('ENABLE_CORS', 'true').lower() == 'true',
            
            # Monitoring Configuration
            'enable_xray': os.environ.get('ENABLE_XRAY', 'true').lower() == 'true',
            'enable_cloudwatch_metrics': os.environ.get('ENABLE_CLOUDWATCH_METRICS', 'true').lower() == 'true',
            
            # Security Configuration
            'allowed_domains': os.environ.get('ALLOWED_DOMAINS', '').split(',') if os.environ.get('ALLOWED_DOMAINS') else [],
            'blocked_domains': os.environ.get('BLOCKED_DOMAINS', '').split(',') if os.environ.get('BLOCKED_DOMAINS') else [],
            
            # Performance Configuration
            'parallel_analysis': os.environ.get('PARALLEL_ANALYSIS', 'true').lower() == 'true',
            'analysis_timeout': int(os.environ.get('ANALYSIS_TIMEOUT', 600)),
            
            # Job Management
            'job_ttl_days': int(os.environ.get('JOB_TTL_DAYS', 30)),
            'cleanup_old_jobs': os.environ.get('CLEANUP_OLD_JOBS', 'true').lower() == 'true',
        }
    
    def _validate_config(self):
        """Validate required configuration values"""
        required_configs = [
            'dynamodb_table_name',
            's3_bucket_name',
        ]
        
        missing_configs = []
        for config_key in required_configs:
            if not self._config.get(config_key):
                missing_configs.append(config_key.upper())
        
        if missing_configs:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_configs)}")
        
        # Validate numeric ranges
        if self._config['max_video_size_mb'] <= 0:
            raise ValueError("MAX_VIDEO_SIZE_MB must be positive")
        
        if self._config['video_processing_timeout'] <= 0:
            raise ValueError("VIDEO_PROCESSING_TIMEOUT must be positive")
        
        if not 0.0 <= self._config['bedrock_temperature'] <= 1.0:
            raise ValueError("BEDROCK_TEMPERATURE must be between 0.0 and 1.0")
        
        if not 0.0 <= self._config['rekognition_min_confidence'] <= 100.0:
            raise ValueError("REKOGNITION_MIN_CONFIDENCE must be between 0.0 and 100.0")
        
        logger.info("Configuration validation completed successfully")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self._config.get(key, default)
    
    def get_aws_region(self) -> str:
        """Get AWS region"""
        return self._config['aws_region']
    
    def get_dynamodb_table_name(self) -> str:
        """Get DynamoDB table name"""
        return self._config['dynamodb_table_name']
    
    def get_s3_bucket_name(self) -> str:
        """Get S3 bucket name"""
        return self._config['s3_bucket_name']
    
    def get_max_video_size_mb(self) -> int:
        """Get maximum video size in MB"""
        return self._config['max_video_size_mb']
    
    def get_bedrock_model_id(self) -> str:
        """Get Bedrock model ID"""
        return self._config['bedrock_model_id']
    
    def is_caching_enabled(self) -> bool:
        """Check if caching is enabled"""
        return self._config['enable_caching']
    
    def is_debug_logging_enabled(self) -> bool:
        """Check if debug logging is enabled"""
        return self._config['enable_debug_logging']
    
    def get_retry_config(self) -> Dict[str, Any]:
        """Get retry configuration"""
        return {
            'max_retries': self._config['max_retries'],
            'base_delay': self._config['retry_base_delay'],
            'max_delay': self._config['retry_max_delay']
        }
    
    def get_rate_limits(self) -> Dict[str, int]:
        """Get rate limit configuration"""
        return {
            'per_minute': self._config['rate_limit_per_minute'],
            'per_hour': self._config['rate_limit_per_hour']
        }
    
    def get_supported_formats(self) -> list:
        """Get list of supported video formats"""
        return self._config['supported_video_formats']
    
    def is_domain_allowed(self, domain: str) -> bool:
        """Check if domain is allowed"""
        allowed_domains = self._config['allowed_domains']
        blocked_domains = self._config['blocked_domains']
        
        # If no allowed domains specified, allow all except blocked
        if not allowed_domains:
            return domain.lower() not in [d.lower() for d in blocked_domains]
        
        # Check against allowed domains
        return domain.lower() in [d.lower() for d in allowed_domains]
    
    def to_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary"""
        return dict(self._config)
    
    def __str__(self) -> str:
        """String representation (excluding sensitive values)"""
        safe_config = dict(self._config)
        # Remove potentially sensitive information
        sensitive_keys = ['aws_access_key', 'aws_secret_key', 'api_key']
        for key in sensitive_keys:
            if key in safe_config:
                safe_config[key] = '***'
        
        return f"Config({safe_config})"


# Global configuration instance
config = Config()