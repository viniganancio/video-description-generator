"""
Video Processor Class
Handles downloading, analyzing, and generating descriptions for videos
"""
import os
import time
import uuid
import tempfile
import logging
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib

from video_downloader import VideoDownloader
from rekognition_analyzer import RekognitionAnalyzer  
from transcribe_analyzer import TranscribeAnalyzer
from bedrock_client import BedrockClient

logger = logging.getLogger(__name__)


class VideoProcessor:
    """Main video processing orchestrator"""
    
    def __init__(self, aws_services):
        self.aws_services = aws_services
        self.s3_bucket = os.environ['S3_BUCKET_NAME']
        self.max_video_size_mb = int(os.environ.get('MAX_VIDEO_SIZE_MB', 500))
        
        # Initialize components
        self.video_downloader = VideoDownloader(self.s3_bucket, self.max_video_size_mb)
        self.rekognition_analyzer = RekognitionAnalyzer(aws_services)
        self.transcribe_analyzer = TranscribeAnalyzer(aws_services)
        self.bedrock_client = BedrockClient(aws_services)
        
    def process_video(self, job_id: str, video_url: str) -> Dict[str, Any]:
        """
        Process a video URL and generate description
        
        Args:
            job_id: Unique job identifier
            video_url: URL of video to process
            
        Returns:
            dict: Processing results with description and analysis data
        """
        start_time = time.time()
        s3_key = None
        
        try:
            logger.info(f"Starting video processing for job {job_id}")
            
            # Check cache first
            cached_result = self._check_cache(video_url)
            if cached_result:
                logger.info(f"Found cached result for video URL")
                return cached_result
            
            # Step 1: Download and upload video to S3
            logger.info("Downloading video...")
            s3_key = self.video_downloader.download_and_upload(video_url, job_id)
            
            # Step 2: Run parallel analysis
            logger.info("Starting parallel analysis...")
            visual_analysis, audio_analysis = self._run_parallel_analysis(s3_key, job_id)
            
            # Step 3: Generate description using Bedrock
            logger.info("Generating description...")
            description_result = self.bedrock_client.generate_description(
                visual_analysis=visual_analysis,
                audio_analysis=audio_analysis,
                video_url=video_url
            )
            
            # Step 4: Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                visual_analysis, audio_analysis, description_result
            )
            
            processing_duration = time.time() - start_time
            
            result = {
                'description': description_result.get('description'),
                'visual_analysis': visual_analysis,
                'audio_analysis': audio_analysis,
                'confidence_score': confidence_score,
                'processing_duration': processing_duration,
                'bedrock_metrics': description_result.get('metrics', {})
            }
            
            # Cache the result
            self._cache_result(video_url, result)
            
            logger.info(f"Video processing completed in {processing_duration:.2f} seconds")
            return result
            
        except Exception as e:
            logger.error(f"Error in video processing: {str(e)}")
            raise
        finally:
            # Clean up S3 file
            if s3_key:
                try:
                    self.aws_services.delete_s3_object(self.s3_bucket, s3_key)
                    logger.info(f"Cleaned up S3 object: {s3_key}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup S3 object {s3_key}: {cleanup_error}")
    
    def _run_parallel_analysis(self, s3_key: str, job_id: str) -> tuple:
        """
        Run visual and audio analysis in parallel
        
        Args:
            s3_key: S3 object key for video
            job_id: Job identifier
            
        Returns:
            tuple: (visual_analysis, audio_analysis)
        """
        visual_analysis = {}
        audio_analysis = {}
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit tasks
            visual_future = executor.submit(
                self._run_visual_analysis, s3_key, job_id
            )
            audio_future = executor.submit(
                self._run_audio_analysis, s3_key, job_id
            )
            
            # Collect results
            for future in as_completed([visual_future, audio_future]):
                try:
                    if future == visual_future:
                        visual_analysis = future.result()
                        logger.info("Visual analysis completed")
                    else:
                        audio_analysis = future.result()  
                        logger.info("Audio analysis completed")
                except Exception as e:
                    if future == visual_future:
                        logger.error(f"Visual analysis failed: {str(e)}")
                        visual_analysis = {'error': str(e)}
                    else:
                        logger.error(f"Audio analysis failed: {str(e)}")
                        audio_analysis = {'error': str(e)}
        
        return visual_analysis, audio_analysis
    
    def _run_visual_analysis(self, s3_key: str, job_id: str) -> Dict[str, Any]:
        """Run Rekognition visual analysis"""
        try:
            return self.rekognition_analyzer.analyze_video(s3_key, job_id)
        except Exception as e:
            logger.error(f"Rekognition analysis failed: {str(e)}")
            return {'error': str(e), 'labels': [], 'celebrities': [], 'text': []}
    
    def _run_audio_analysis(self, s3_key: str, job_id: str) -> Dict[str, Any]:
        """Run Transcribe audio analysis"""
        try:
            return self.transcribe_analyzer.transcribe_audio(s3_key, job_id)
        except Exception as e:
            logger.error(f"Transcribe analysis failed: {str(e)}")
            return {'error': str(e), 'transcript': '', 'confidence': 0.0}
    
    def _calculate_confidence_score(
        self, 
        visual_analysis: Dict[str, Any], 
        audio_analysis: Dict[str, Any],
        description_result: Dict[str, Any]
    ) -> float:
        """
        Calculate overall confidence score for the generated description
        
        Args:
            visual_analysis: Results from Rekognition
            audio_analysis: Results from Transcribe
            description_result: Results from Bedrock
            
        Returns:
            float: Confidence score between 0.0 and 1.0
        """
        try:
            scores = []
            
            # Visual analysis confidence
            if not visual_analysis.get('error'):
                labels = visual_analysis.get('labels', [])
                if labels:
                    avg_visual_confidence = sum(
                        label.get('confidence', 0) for label in labels[:10]
                    ) / min(len(labels), 10) / 100.0
                    scores.append(avg_visual_confidence)
            
            # Audio analysis confidence
            if not audio_analysis.get('error'):
                audio_confidence = audio_analysis.get('confidence', 0.0)
                if audio_confidence > 0:
                    scores.append(audio_confidence)
            
            # Bedrock response quality (based on length and structure)
            description = description_result.get('description', '')
            if description:
                # Simple heuristic: longer, well-structured descriptions get higher scores
                desc_quality = min(len(description) / 200.0, 1.0)  # Normalize to 200 chars
                scores.append(desc_quality)
            
            # Return average of available scores
            return sum(scores) / len(scores) if scores else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating confidence score: {str(e)}")
            return 0.5  # Default moderate confidence
    
    def _check_cache(self, video_url: str) -> Optional[Dict[str, Any]]:
        """Check if we have a cached result for this video URL"""
        try:
            url_hash = hashlib.md5(video_url.encode()).hexdigest()
            return self.aws_services.get_cached_result(url_hash)
        except Exception as e:
            logger.warning(f"Cache check failed: {str(e)}")
            return None
    
    def _cache_result(self, video_url: str, result: Dict[str, Any]):
        """Cache the processing result"""
        try:
            url_hash = hashlib.md5(video_url.encode()).hexdigest()
            # Cache for 7 days
            ttl = int(time.time()) + (7 * 24 * 60 * 60)
            self.aws_services.cache_result(url_hash, result, ttl)
        except Exception as e:
            logger.warning(f"Failed to cache result: {str(e)}")