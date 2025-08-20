"""
Shared Utilities Module
Common utility functions used across the video description generation service
"""
import hashlib
import json
import logging
import re
import time
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)


def generate_hash(text: str) -> str:
    """
    Generate MD5 hash of text
    
    Args:
        text: Text to hash
        
    Returns:
        str: MD5 hash as hex string
    """
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def is_valid_url(url: str) -> bool:
    """
    Validate if URL is properly formatted
    
    Args:
        url: URL to validate
        
    Returns:
        bool: True if valid URL format
    """
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def is_youtube_url(url: str) -> bool:
    """
    Check if URL is a YouTube video URL
    
    Args:
        url: URL to check
        
    Returns:
        bool: True if YouTube URL
    """
    youtube_domains = [
        'youtube.com', 'www.youtube.com', 'youtu.be', 
        'm.youtube.com', 'music.youtube.com'
    ]
    try:
        parsed_url = urllib.parse.urlparse(url)
        return parsed_url.netloc.lower() in youtube_domains
    except Exception:
        return False


def extract_youtube_video_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from URL
    
    Args:
        url: YouTube URL
        
    Returns:
        str: Video ID or None if not found
    """
    try:
        # Handle different YouTube URL formats
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/.*[?&]v=([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    except Exception:
        return None


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    Sanitize filename for safe storage
    
    Args:
        filename: Original filename
        max_length: Maximum filename length
        
    Returns:
        str: Sanitized filename
    """
    # Remove unsafe characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove multiple spaces and underscores
    sanitized = re.sub(r'[_\s]+', '_', sanitized)
    
    # Trim length
    if len(sanitized) > max_length:
        name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
        name = name[:max_length - len(ext) - 1]
        sanitized = f"{name}.{ext}" if ext else name
    
    return sanitized.strip('_')


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        str: Formatted duration (e.g., "2m 30s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def format_file_size(bytes_size: int) -> str:
    """
    Format file size in bytes to human-readable string
    
    Args:
        bytes_size: Size in bytes
        
    Returns:
        str: Formatted size (e.g., "1.2MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f}{unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f}TB"


def calculate_confidence_score(scores: List[float], weights: Optional[List[float]] = None) -> float:
    """
    Calculate weighted average confidence score
    
    Args:
        scores: List of confidence scores (0.0 to 1.0)
        weights: Optional weights for each score
        
    Returns:
        float: Weighted average confidence score
    """
    if not scores:
        return 0.0
    
    # Filter out invalid scores
    valid_scores = [score for score in scores if 0.0 <= score <= 1.0]
    
    if not valid_scores:
        return 0.0
    
    if weights and len(weights) == len(valid_scores):
        weighted_sum = sum(score * weight for score, weight in zip(valid_scores, weights))
        total_weight = sum(weights)
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    else:
        return sum(valid_scores) / len(valid_scores)


def truncate_text(text: str, max_length: int = 1000, ellipsis: str = "...") -> str:
    """
    Truncate text to maximum length with ellipsis
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        ellipsis: Ellipsis string to append
        
    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    
    truncated = text[:max_length - len(ellipsis)]
    
    # Try to break at word boundary
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.8:  # Only if we don't lose too much
        truncated = truncated[:last_space]
    
    return truncated + ellipsis


def extract_keywords(text: str, min_length: int = 3, max_keywords: int = 20) -> List[str]:
    """
    Extract keywords from text using simple frequency analysis
    
    Args:
        text: Text to analyze
        min_length: Minimum keyword length
        max_keywords: Maximum number of keywords to return
        
    Returns:
        list: List of keywords sorted by frequency
    """
    if not text:
        return []
    
    # Simple keyword extraction
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    
    # Filter by length and common stop words
    stop_words = {
        'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 
        'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 
        'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 
        'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'
    }
    
    filtered_words = [
        word for word in words 
        if len(word) >= min_length and word not in stop_words
    ]
    
    # Count frequencies
    word_freq = {}
    for word in filtered_words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Sort by frequency and return top keywords
    sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_keywords[:max_keywords]]


def retry_with_exponential_backoff(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,)
):
    """
    Retry function with exponential backoff
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exceptions: Exceptions to catch and retry on
        
    Returns:
        Result of function call
    """
    def wrapper(*args, **kwargs):
        delay = base_delay
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt == max_retries:
                    break
                
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, max_delay)
        
        raise last_exception
    
    return wrapper


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Safely parse JSON string with default fallback
    
    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails
        
    Returns:
        Parsed JSON or default value
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_get_nested(data: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    """
    Safely get nested dictionary value
    
    Args:
        data: Dictionary to search
        keys: List of keys to navigate (e.g., ['level1', 'level2'])
        default: Default value if key not found
        
    Returns:
        Nested value or default
    """
    try:
        result = data
        for key in keys:
            result = result[key]
        return result
    except (KeyError, TypeError):
        return default


def create_presigned_url(
    bucket: str, 
    key: str, 
    expiration: int = 3600,
    http_method: str = 'GET'
) -> Optional[str]:
    """
    Create presigned URL for S3 object
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        expiration: URL expiration in seconds
        http_method: HTTP method for the URL
        
    Returns:
        str: Presigned URL or None if failed
    """
    try:
        import boto3
        s3_client = boto3.client('s3')
        
        url = s3_client.generate_presigned_url(
            http_method.lower() + '_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expiration
        )
        return url
    except Exception as e:
        logger.error(f"Failed to create presigned URL: {str(e)}")
        return None


def batch_process(items: List[Any], batch_size: int = 25, processor_func=None):
    """
    Process items in batches
    
    Args:
        items: List of items to process
        batch_size: Number of items per batch
        processor_func: Function to process each batch
        
    Yields:
        Processed batch results
    """
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        if processor_func:
            yield processor_func(batch)
        else:
            yield batch


class RateLimiter:
    """Simple rate limiter implementation"""
    
    def __init__(self, max_calls: int, time_window: int = 60):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    def can_proceed(self) -> bool:
        """Check if we can make another call"""
        now = time.time()
        
        # Remove old calls outside time window
        self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]
        
        # Check if we're under the limit
        return len(self.calls) < self.max_calls
    
    def record_call(self):
        """Record a new call"""
        self.calls.append(time.time())
    
    def wait_time(self) -> float:
        """Get time to wait before next call is allowed"""
        if self.can_proceed():
            return 0.0
        
        # Time until oldest call expires
        if self.calls:
            return self.time_window - (time.time() - self.calls[0])
        return 0.0