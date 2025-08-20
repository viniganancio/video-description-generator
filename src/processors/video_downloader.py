"""
Video Downloader Module
Handles downloading videos from URLs and uploading to S3
"""
import os
import tempfile
import logging
import subprocess
import urllib.parse
from typing import Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class VideoDownloader:
    """Handles video downloading from various sources"""
    
    def __init__(self, s3_bucket: str, max_size_mb: int):
        self.s3_bucket = s3_bucket
        self.max_size_mb = max_size_mb
        self.s3_client = boto3.client('s3')
        
    def download_and_upload(self, video_url: str, job_id: str) -> str:
        """
        Download video from URL and upload to S3
        
        Args:
            video_url: URL of the video to download
            job_id: Job identifier for naming
            
        Returns:
            str: S3 key of uploaded video
            
        Raises:
            ValueError: If video URL is invalid or video is too large
            Exception: If download or upload fails
        """
        logger.info(f"Starting download for URL: {video_url}")
        
        # Validate URL
        if not self._is_valid_url(video_url):
            raise ValueError(f"Invalid video URL: {video_url}")
        
        temp_dir = None
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp()
            
            # Determine if this is a YouTube URL or direct video URL
            if self._is_youtube_url(video_url):
                video_path = self._download_youtube_video(video_url, temp_dir, job_id)
            else:
                video_path = self._download_direct_video(video_url, temp_dir, job_id)
            
            # Check file size
            file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
            if file_size_mb > self.max_size_mb:
                raise ValueError(
                    f"Video file too large: {file_size_mb:.1f}MB exceeds limit of {self.max_size_mb}MB"
                )
            
            # Upload to S3
            s3_key = f"videos/{job_id}/{os.path.basename(video_path)}"
            self._upload_to_s3(video_path, s3_key)
            
            logger.info(f"Successfully uploaded video to S3: {s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            raise
        finally:
            # Clean up temporary files
            if temp_dir:
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temp directory: {cleanup_error}")
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate if the URL is properly formatted"""
        try:
            result = urllib.parse.urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _is_youtube_url(self, url: str) -> bool:
        """Check if URL is a YouTube video URL"""
        youtube_domains = [
            'youtube.com', 'www.youtube.com', 'youtu.be', 'm.youtube.com'
        ]
        try:
            parsed_url = urllib.parse.urlparse(url)
            return parsed_url.netloc.lower() in youtube_domains
        except Exception:
            return False
    
    def _download_youtube_video(self, url: str, temp_dir: str, job_id: str) -> str:
        """
        Download YouTube video using yt-dlp
        
        Args:
            url: YouTube video URL
            temp_dir: Temporary directory for downloads
            job_id: Job identifier
            
        Returns:
            str: Path to downloaded video file
        """
        output_template = os.path.join(temp_dir, f"{job_id}_%(title)s.%(ext)s")
        
        # yt-dlp command with size and quality limits
        cmd = [
            'yt-dlp',
            '--format', 'best[filesize<?{}M]/best'.format(self.max_size_mb),
            '--output', output_template,
            '--no-playlist',
            '--extract-flat', 'false',
            url
        ]
        
        try:
            logger.info(f"Running yt-dlp command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd, 
                check=True, 
                capture_output=True, 
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Find the downloaded file
            for file in os.listdir(temp_dir):
                if file.startswith(job_id):
                    return os.path.join(temp_dir, file)
            
            raise Exception("No video file found after download")
            
        except subprocess.TimeoutExpired:
            raise Exception("Video download timed out")
        except subprocess.CalledProcessError as e:
            logger.error(f"yt-dlp error: {e.stderr}")
            raise Exception(f"Failed to download YouTube video: {e.stderr}")
    
    def _download_direct_video(self, url: str, temp_dir: str, job_id: str) -> str:
        """
        Download video from direct URL
        
        Args:
            url: Direct video URL
            temp_dir: Temporary directory for downloads
            job_id: Job identifier
            
        Returns:
            str: Path to downloaded video file
        """
        import requests
        from urllib.parse import urlparse
        
        try:
            # Get file extension from URL
            parsed_url = urlparse(url)
            file_ext = os.path.splitext(parsed_url.path)[1] or '.mp4'
            filename = f"{job_id}_video{file_ext}"
            file_path = os.path.join(temp_dir, filename)
            
            # Download with streaming to handle large files
            with requests.get(url, stream=True, timeout=60) as response:
                response.raise_for_status()
                
                # Check content length if provided
                content_length = response.headers.get('content-length')
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    if size_mb > self.max_size_mb:
                        raise ValueError(f"Video too large: {size_mb:.1f}MB")
                
                # Download in chunks
                with open(file_path, 'wb') as f:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Check size during download
                            downloaded_mb = downloaded / (1024 * 1024)
                            if downloaded_mb > self.max_size_mb:
                                raise ValueError(f"Video too large during download: {downloaded_mb:.1f}MB")
            
            return file_path
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to download video from URL: {str(e)}")
    
    def _upload_to_s3(self, file_path: str, s3_key: str):
        """
        Upload file to S3
        
        Args:
            file_path: Local path to file
            s3_key: S3 object key
        """
        try:
            # Upload with metadata
            self.s3_client.upload_file(
                file_path,
                self.s3_bucket,
                s3_key,
                ExtraArgs={
                    'Metadata': {
                        'uploaded-by': 'video-processor',
                        'content-type': 'video/mp4'
                    },
                    'StorageClass': 'STANDARD_IA'  # Infrequent Access for temporary files
                }
            )
            
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {str(e)}")
            raise Exception(f"S3 upload failed: {str(e)}")