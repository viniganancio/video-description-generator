"""
Custom Exceptions Module
Define custom exceptions for the video description generation service
"""


class VideoProcessingError(Exception):
    """Base exception for video processing errors"""
    pass


class VideoDownloadError(VideoProcessingError):
    """Raised when video download fails"""
    pass


class VideoTooLargeError(VideoProcessingError):
    """Raised when video exceeds size limits"""
    pass


class UnsupportedVideoFormatError(VideoProcessingError):
    """Raised when video format is not supported"""
    pass


class VideoAnalysisError(VideoProcessingError):
    """Raised when video analysis fails"""
    pass


class RekognitionError(VideoAnalysisError):
    """Raised when Rekognition analysis fails"""
    pass


class TranscribeError(VideoAnalysisError):
    """Raised when Transcribe analysis fails"""
    pass


class BedrockError(VideoProcessingError):
    """Raised when Bedrock description generation fails"""
    pass


class InvalidVideoUrlError(VideoProcessingError):
    """Raised when video URL is invalid or inaccessible"""
    pass


class JobNotFoundError(Exception):
    """Raised when a job ID is not found"""
    pass


class JobStatusError(Exception):
    """Raised when job is in an invalid state for the requested operation"""
    pass


class RateLimitExceededError(Exception):
    """Raised when rate limits are exceeded"""
    pass


class ConfigurationError(Exception):
    """Raised when there's a configuration error"""
    pass


class AWSServiceError(Exception):
    """Base class for AWS service errors"""
    pass


class S3Error(AWSServiceError):
    """Raised when S3 operations fail"""
    pass


class DynamoDBError(AWSServiceError):
    """Raised when DynamoDB operations fail"""
    pass


class LambdaError(AWSServiceError):
    """Raised when Lambda operations fail"""
    pass