"""
Amazon Rekognition Video Analysis Module
Handles visual analysis of videos using Amazon Rekognition Video
"""
import logging
import time
from typing import Dict, Any, List
import boto3
from botocore.exceptions import ClientError

# Ensure logging is properly configured for AWS Lambda
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)


class RekognitionAnalyzer:
    """Handles video analysis using Amazon Rekognition Video"""
    
    def __init__(self, aws_services):
        self.aws_services = aws_services
        self.rekognition = boto3.client('rekognition')
        self.s3_bucket = aws_services.s3_bucket
        
    def analyze_video(self, s3_key: str, job_id: str) -> Dict[str, Any]:
        """
        Analyze video using multiple Rekognition Video APIs
        
        Args:
            s3_key: S3 key of the video file
            job_id: Job identifier
            
        Returns:
            dict: Combined analysis results
        """
        start_time = time.time()
        logger.info(f"👀 REKOGNITION STEP 1/4: Starting visual analysis for s3://{self.s3_bucket}/{s3_key}")
        logger.info(f"🎯 Job ID: {job_id}")
        
        video_input = {
            'S3Object': {
                'Bucket': self.s3_bucket,
                'Name': s3_key
            }
        }
        
        # Start multiple analysis jobs in parallel
        analysis_jobs = {}
        
        try:
            logger.info(f"🚀 REKOGNITION STEP 2/4: Starting parallel analysis jobs...")
            
            # Start label detection
            logger.info(f"  📋 Starting label detection...")
            labels_response = self.rekognition.start_label_detection(
                Video=video_input,
                JobTag=f"labels-{job_id}"
            )
            analysis_jobs['labels'] = labels_response['JobId']
            logger.info(f"  ✅ Label detection started - Job ID: {labels_response['JobId']}")
            
            # Start celebrity recognition
            try:
                logger.info(f"  🌟 Starting celebrity recognition...")
                celebrities_response = self.rekognition.start_celebrity_recognition(
                    Video=video_input,
                    JobTag=f"celebrities-{job_id}"
                )
                analysis_jobs['celebrities'] = celebrities_response['JobId']
                logger.info(f"  ✅ Celebrity recognition started - Job ID: {celebrities_response['JobId']}")
            except ClientError as e:
                logger.warning(f"  ⚠️ Celebrity recognition not available: {str(e)}")
            
            # Start text detection
            try:
                logger.info(f"  📝 Starting text detection...")
                text_response = self.rekognition.start_text_detection(
                    Video=video_input,
                    JobTag=f"text-{job_id}"
                )
                analysis_jobs['text'] = text_response['JobId']
                logger.info(f"  ✅ Text detection started - Job ID: {text_response['JobId']}")
            except ClientError as e:
                logger.warning(f"  ⚠️ Text detection not available: {str(e)}")
            
            # Start content moderation
            try:
                logger.info(f"  🛡️ Starting content moderation...")
                moderation_response = self.rekognition.start_content_moderation(
                    Video=video_input,
                    JobTag=f"moderation-{job_id}"
                )
                analysis_jobs['moderation'] = moderation_response['JobId']
                logger.info(f"  ✅ Content moderation started - Job ID: {moderation_response['JobId']}")
            except ClientError as e:
                logger.warning(f"  ⚠️ Content moderation not available: {str(e)}")
            
            logger.info(f"🎉 Started {len(analysis_jobs)} Rekognition analysis jobs successfully")
            
            # Wait for all jobs to complete and collect results
            logger.info(f"⏳ REKOGNITION STEP 3/4: Waiting for analysis jobs to complete...")
            results = {}
            job_count = len(analysis_jobs)
            completed_count = 0
            
            for analysis_type, job_id_rek in analysis_jobs.items():
                try:
                    logger.info(f"  🔄 Waiting for {analysis_type} analysis to complete...")
                    result = self._wait_for_analysis_completion(analysis_type, job_id_rek)
                    results[analysis_type] = result
                    completed_count += 1
                    logger.info(f"  ✅ {analysis_type} analysis completed ({completed_count}/{job_count})")
                except Exception as e:
                    logger.error(f"  ❌ Failed to get {analysis_type} results: {str(e)}")
                    results[analysis_type] = {'error': str(e)}
                    completed_count += 1
            
            # Process and combine results
            logger.info(f"📊 REKOGNITION STEP 4/4: Processing and combining results...")
            combined_results = self._process_results(results)
            
            processing_duration = time.time() - start_time
            logger.info(f"🎉 Rekognition analysis completed successfully in {processing_duration:.2f} seconds")
            logger.info(f"📈 Results summary:")
            logger.info(f"  - Labels found: {len(combined_results.get('labels', []))}")
            logger.info(f"  - Celebrities found: {len(combined_results.get('celebrities', []))}")
            logger.info(f"  - Text detections: {len(combined_results.get('text', []))}")
            logger.info(f"  - Moderation flags: {len(combined_results.get('moderation_flags', []))}")
            return combined_results
            
        except Exception as e:
            logger.error(f"Rekognition analysis failed: {str(e)}")
            return {
                'error': str(e),
                'labels': [],
                'celebrities': [],
                'text': [],
                'moderation': []
            }
    
    def _wait_for_analysis_completion(self, analysis_type: str, job_id: str, timeout: int = 300) -> Dict[str, Any]:
        """
        Wait for Rekognition analysis job to complete
        
        Args:
            analysis_type: Type of analysis (labels, celebrities, text, moderation)
            job_id: Rekognition job ID
            timeout: Maximum wait time in seconds
            
        Returns:
            dict: Analysis results
        """
        start_time = time.time()
        check_count = 0
        
        logger.info(f"    ⏳ Polling {analysis_type} job status (Job ID: {job_id})...")
        
        while time.time() - start_time < timeout:
            try:
                if analysis_type == 'labels':
                    response = self.rekognition.get_label_detection(JobId=job_id)
                elif analysis_type == 'celebrities':
                    response = self.rekognition.get_celebrity_recognition(JobId=job_id)
                elif analysis_type == 'text':
                    response = self.rekognition.get_text_detection(JobId=job_id)
                elif analysis_type == 'moderation':
                    response = self.rekognition.get_content_moderation(JobId=job_id)
                else:
                    raise ValueError(f"Unknown analysis type: {analysis_type}")
                
                job_status = response['JobStatus']
                check_count += 1
                elapsed_time = time.time() - start_time
                
                if job_status == 'SUCCEEDED':
                    logger.info(f"    ✅ {analysis_type} job completed successfully after {elapsed_time:.1f}s ({check_count} checks)")
                    return self._extract_analysis_data(analysis_type, response)
                elif job_status == 'FAILED':
                    error_msg = response.get('StatusMessage', 'Analysis failed')
                    logger.error(f"    ❌ {analysis_type} job failed: {error_msg}")
                    raise Exception(f"Rekognition job failed: {error_msg}")
                elif job_status in ['IN_PROGRESS']:
                    if check_count % 3 == 0:  # Log every 3rd check to reduce noise
                        logger.info(f"    🔄 {analysis_type} still in progress... ({elapsed_time:.1f}s elapsed, {check_count} checks)")
                    time.sleep(5)  # Wait 5 seconds before checking again
                else:
                    logger.error(f"    ❌ Unexpected job status for {analysis_type}: {job_status}")
                    raise Exception(f"Unexpected job status: {job_status}")
                    
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFound':
                    time.sleep(2)  # Job might not be ready yet
                else:
                    raise
        
        logger.error(f"    ⏰ {analysis_type} analysis timed out after {timeout} seconds ({check_count} checks)")
        raise Exception(f"Analysis timed out after {timeout} seconds")
    
    def _extract_analysis_data(self, analysis_type: str, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant data from Rekognition response
        
        Args:
            analysis_type: Type of analysis
            response: Rekognition API response
            
        Returns:
            dict: Processed analysis data
        """
        if analysis_type == 'labels':
            return {
                'labels': [
                    {
                        'name': label['Label']['Name'],
                        'confidence': label['Label']['Confidence'],
                        'timestamp': label['Timestamp'],
                        'instances': len(label['Label'].get('Instances', []))
                    }
                    for label in response.get('Labels', [])
                ]
            }
        
        elif analysis_type == 'celebrities':
            return {
                'celebrities': [
                    {
                        'name': celeb['Celebrity']['Name'],
                        'confidence': celeb['Celebrity']['Confidence'],
                        'timestamp': celeb['Timestamp'],
                        'urls': celeb['Celebrity'].get('Urls', [])
                    }
                    for celeb in response.get('Celebrities', [])
                ]
            }
        
        elif analysis_type == 'text':
            return {
                'text_detections': [
                    {
                        'text': text['TextDetection']['DetectedText'],
                        'confidence': text['TextDetection']['Confidence'],
                        'timestamp': text['Timestamp'],
                        'type': text['TextDetection']['Type']
                    }
                    for text in response.get('TextDetections', [])
                ]
            }
        
        elif analysis_type == 'moderation':
            return {
                'moderation_labels': [
                    {
                        'name': mod['ModerationLabel']['Name'],
                        'confidence': mod['ModerationLabel']['Confidence'],
                        'timestamp': mod['Timestamp'],
                        'parent_name': mod['ModerationLabel'].get('ParentName', '')
                    }
                    for mod in response.get('ModerationLabels', [])
                ]
            }
        
        return {}
    
    def _process_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and combine all Rekognition results
        
        Args:
            results: Raw results from all analysis types
            
        Returns:
            dict: Processed and combined results
        """
        processed = {
            'labels': [],
            'celebrities': [],
            'text': [],
            'moderation_flags': [],
            'summary': {}
        }
        
        # Process labels
        if 'labels' in results and not results['labels'].get('error'):
            labels_data = results['labels'].get('labels', [])
            # Get top labels by confidence
            top_labels = sorted(labels_data, key=lambda x: x['confidence'], reverse=True)[:20]
            processed['labels'] = top_labels
        
        # Process celebrities
        if 'celebrities' in results and not results['celebrities'].get('error'):
            celebrities_data = results['celebrities'].get('celebrities', [])
            # Filter high-confidence celebrity detections
            high_conf_celebrities = [
                celeb for celeb in celebrities_data 
                if celeb['confidence'] > 80
            ]
            processed['celebrities'] = high_conf_celebrities
        
        # Process text
        if 'text' in results and not results['text'].get('error'):
            text_data = results['text'].get('text_detections', [])
            # Get unique text detections
            unique_texts = {}
            for text in text_data:
                text_content = text['text'].strip()
                if len(text_content) > 2 and text_content not in unique_texts:
                    unique_texts[text_content] = text
            processed['text'] = list(unique_texts.values())
        
        # Process moderation
        if 'moderation' in results and not results['moderation'].get('error'):
            moderation_data = results['moderation'].get('moderation_labels', [])
            # Filter high-confidence moderation flags
            high_conf_moderation = [
                mod for mod in moderation_data 
                if mod['confidence'] > 50
            ]
            processed['moderation_flags'] = high_conf_moderation
        
        # Create summary
        processed['summary'] = {
            'total_labels': len(processed['labels']),
            'total_celebrities': len(processed['celebrities']),
            'total_text_detections': len(processed['text']),
            'moderation_flags_count': len(processed['moderation_flags']),
            'top_categories': self._extract_top_categories(processed['labels'])
        }
        
        return processed
    
    def _extract_top_categories(self, labels: List[Dict[str, Any]]) -> List[str]:
        """Extract top categories from labels"""
        if not labels:
            return []
        
        # Simple categorization based on common label patterns
        categories = {}
        for label in labels[:10]:  # Top 10 labels
            name = label['name'].lower()
            confidence = label['confidence']
            
            # Map to broader categories
            if any(word in name for word in ['person', 'people', 'human', 'man', 'woman']):
                categories['People'] = categories.get('People', 0) + confidence
            elif any(word in name for word in ['animal', 'dog', 'cat', 'bird', 'wildlife']):
                categories['Animals'] = categories.get('Animals', 0) + confidence
            elif any(word in name for word in ['car', 'vehicle', 'transportation', 'road']):
                categories['Transportation'] = categories.get('Transportation', 0) + confidence
            elif any(word in name for word in ['nature', 'landscape', 'tree', 'water', 'sky']):
                categories['Nature'] = categories.get('Nature', 0) + confidence
            elif any(word in name for word in ['building', 'architecture', 'city', 'urban']):
                categories['Architecture'] = categories.get('Architecture', 0) + confidence
            else:
                categories['Other'] = categories.get('Other', 0) + confidence
        
        # Return sorted by total confidence
        return sorted(categories.keys(), key=lambda k: categories[k], reverse=True)[:5]