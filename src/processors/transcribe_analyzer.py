"""
Amazon Transcribe Audio Analysis Module
Handles audio transcription using Amazon Transcribe
"""
import logging
import time
import boto3
from typing import Dict, Any, Optional, List
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class TranscribeAnalyzer:
    """Handles audio transcription using Amazon Transcribe"""
    
    def __init__(self, aws_services):
        self.aws_services = aws_services
        self.transcribe = boto3.client('transcribe')
        self.s3_bucket = aws_services.s3_bucket
        
    def transcribe_audio(self, s3_key: str, job_id: str) -> Dict[str, Any]:
        """
        Transcribe audio from video using Amazon Transcribe
        
        Args:
            s3_key: S3 key of the video file
            job_id: Job identifier
            
        Returns:
            dict: Transcription results
        """
        transcription_job_name = f"transcribe-{job_id}-{int(time.time())}"
        
        try:
            logger.info(f"Starting transcription job: {transcription_job_name}")
            
            # Start transcription job
            media_uri = f"s3://{self.s3_bucket}/{s3_key}"
            
            job_config = {
                'TranscriptionJobName': transcription_job_name,
                'LanguageCode': 'en-US',  # Default to English, could be auto-detected
                'MediaFormat': self._detect_media_format(s3_key),
                'Media': {'MediaFileUri': media_uri},
                'OutputBucketName': self.s3_bucket,
                'OutputKey': f'transcriptions/{job_id}/',
                'Settings': {
                    'ShowSpeakerLabels': True,
                    'MaxSpeakerLabels': 5,
                    'ShowAlternatives': True,
                    'MaxAlternatives': 3
                }
            }
            
            # Add language identification if supported
            try:
                job_config['IdentifyLanguage'] = True
                job_config.pop('LanguageCode')  # Remove language code when using identification
            except Exception:
                pass  # Fall back to English if language identification isn't supported
            
            response = self.transcribe.start_transcription_job(**job_config)
            
            # Wait for job completion
            result = self._wait_for_transcription_completion(transcription_job_name)
            
            # Process and return results
            return self._process_transcription_results(result)
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['BadRequestException', 'ConflictException']:
                logger.warning(f"Transcription not supported for this file: {str(e)}")
                return {
                    'transcript': '',
                    'confidence': 0.0,
                    'error': 'Audio transcription not supported for this video format',
                    'speaker_labels': [],
                    'alternative_transcripts': []
                }
            else:
                logger.error(f"Transcribe client error: {str(e)}")
                raise
        
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            return {
                'transcript': '',
                'confidence': 0.0,
                'error': str(e),
                'speaker_labels': [],
                'alternative_transcripts': []
            }
        
        finally:
            # Clean up transcription job
            try:
                self.transcribe.delete_transcription_job(
                    TranscriptionJobName=transcription_job_name
                )
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup transcription job: {cleanup_error}")
    
    def _detect_media_format(self, s3_key: str) -> str:
        """
        Detect media format from file extension
        
        Args:
            s3_key: S3 key of the media file
            
        Returns:
            str: Media format for Transcribe
        """
        extension = s3_key.lower().split('.')[-1]
        
        format_map = {
            'mp3': 'mp3',
            'mp4': 'mp4',
            'wav': 'wav',
            'flac': 'flac',
            'ogg': 'ogg',
            'amr': 'amr',
            'webm': 'webm',
            'm4a': 'mp4',
            'avi': 'mp4',  # Treat as mp4 for transcription
            'mov': 'mp4',  # Treat as mp4 for transcription
        }
        
        return format_map.get(extension, 'mp4')  # Default to mp4
    
    def _wait_for_transcription_completion(self, job_name: str, timeout: int = 300) -> Dict[str, Any]:
        """
        Wait for transcription job to complete
        
        Args:
            job_name: Transcription job name
            timeout: Maximum wait time in seconds
            
        Returns:
            dict: Transcription job response
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = self.transcribe.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                
                status = response['TranscriptionJob']['TranscriptionJobStatus']
                
                if status == 'COMPLETED':
                    return response
                elif status == 'FAILED':
                    failure_reason = response['TranscriptionJob'].get(
                        'FailureReason', 'Unknown failure'
                    )
                    raise Exception(f"Transcription job failed: {failure_reason}")
                elif status in ['IN_PROGRESS', 'QUEUED']:
                    time.sleep(10)  # Wait 10 seconds before checking again
                else:
                    raise Exception(f"Unexpected transcription status: {status}")
                    
            except ClientError as e:
                if e.response['Error']['Code'] == 'BadRequestException':
                    time.sleep(5)  # Job might not be ready yet
                else:
                    raise
        
        raise Exception(f"Transcription timed out after {timeout} seconds")
    
    def _process_transcription_results(self, transcription_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process transcription results from Amazon Transcribe
        
        Args:
            transcription_response: Response from get_transcription_job
            
        Returns:
            dict: Processed transcription data
        """
        try:
            job = transcription_response['TranscriptionJob']
            transcript_uri = job['Transcript']['TranscriptFileUri']
            
            # Download transcript from S3
            transcript_data = self._download_transcript(transcript_uri)
            
            if not transcript_data:
                return {
                    'transcript': '',
                    'confidence': 0.0,
                    'error': 'No transcript data found',
                    'speaker_labels': [],
                    'alternative_transcripts': []
                }
            
            # Extract main transcript
            main_transcript = transcript_data.get('results', {}).get('transcripts', [])
            transcript_text = main_transcript[0].get('transcript', '') if main_transcript else ''
            
            # Calculate average confidence
            items = transcript_data.get('results', {}).get('items', [])
            confidences = [
                float(item.get('alternatives', [{}])[0].get('confidence', 0))
                for item in items
                if item.get('alternatives') and item['alternatives'][0].get('confidence')
            ]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Extract speaker labels if available
            speaker_labels = self._extract_speaker_labels(transcript_data)
            
            # Extract alternative transcripts
            alternative_transcripts = self._extract_alternatives(transcript_data)
            
            # Extract additional metadata
            language_code = transcript_data.get('results', {}).get('language_code', 'en-US')
            
            return {
                'transcript': transcript_text.strip(),
                'confidence': avg_confidence,
                'language_code': language_code,
                'speaker_labels': speaker_labels,
                'alternative_transcripts': alternative_transcripts,
                'word_count': len(transcript_text.split()) if transcript_text else 0,
                'duration_seconds': self._calculate_duration(items)
            }
            
        except Exception as e:
            logger.error(f"Error processing transcription results: {str(e)}")
            return {
                'transcript': '',
                'confidence': 0.0,
                'error': str(e),
                'speaker_labels': [],
                'alternative_transcripts': []
            }
    
    def _download_transcript(self, transcript_uri: str) -> Optional[Dict[str, Any]]:
        """Download transcript JSON from S3"""
        try:
            import json
            import urllib.parse
            
            # Parse S3 URI
            parsed_uri = urllib.parse.urlparse(transcript_uri)
            bucket = parsed_uri.netloc
            key = parsed_uri.path.lstrip('/')
            
            # Download from S3
            s3_client = boto3.client('s3')
            response = s3_client.get_object(Bucket=bucket, Key=key)
            transcript_json = json.loads(response['Body'].read().decode('utf-8'))
            
            # Clean up the transcript file
            try:
                s3_client.delete_object(Bucket=bucket, Key=key)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup transcript file: {cleanup_error}")
            
            return transcript_json
            
        except Exception as e:
            logger.error(f"Failed to download transcript: {str(e)}")
            return None
    
    def _extract_speaker_labels(self, transcript_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract speaker label information"""
        speaker_labels = transcript_data.get('results', {}).get('speaker_labels', {})
        
        if not speaker_labels:
            return []
        
        segments = speaker_labels.get('segments', [])
        speakers = []
        
        for segment in segments[:10]:  # Limit to first 10 segments
            speaker_info = {
                'speaker': segment.get('speaker_label', 'Speaker_0'),
                'start_time': float(segment.get('start_time', 0)),
                'end_time': float(segment.get('end_time', 0)),
                'text': ' '.join([item.get('alternatives', [{}])[0].get('content', '') 
                                for item in segment.get('items', [])])
            }
            speakers.append(speaker_info)
        
        return speakers
    
    def _extract_alternatives(self, transcript_data: Dict[str, Any]) -> List[str]:
        """Extract alternative transcription possibilities"""
        alternatives = []
        
        items = transcript_data.get('results', {}).get('items', [])
        
        # Look for items with multiple alternatives
        for item in items[:20]:  # Limit processing
            item_alternatives = item.get('alternatives', [])
            if len(item_alternatives) > 1:
                for alt in item_alternatives[1:4]:  # Get up to 3 alternatives
                    content = alt.get('content', '')
                    confidence = alt.get('confidence', 0)
                    if content and confidence > 0.5:
                        alternatives.append(f"{content} ({confidence:.2f})")
        
        return alternatives[:10]  # Return top 10 alternatives
    
    def _calculate_duration(self, items: List[Dict[str, Any]]) -> float:
        """Calculate approximate duration from transcript items"""
        try:
            if not items:
                return 0.0
            
            # Find items with timing information
            timed_items = [
                item for item in items 
                if item.get('start_time') and item.get('end_time')
            ]
            
            if not timed_items:
                return 0.0
            
            # Get the last item's end time
            last_item = max(timed_items, key=lambda x: float(x.get('end_time', 0)))
            return float(last_item.get('end_time', 0))
            
        except Exception as e:
            logger.warning(f"Could not calculate duration: {str(e)}")
            return 0.0