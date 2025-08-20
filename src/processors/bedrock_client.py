"""
Amazon Bedrock Client for Description Generation
Uses Claude model to generate engaging video descriptions
"""
import json
import logging
import time
from typing import Dict, Any, List
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class BedrockClient:
    """Handles description generation using Amazon Bedrock"""
    
    def __init__(self, aws_services):
        self.aws_services = aws_services
        self.bedrock_runtime = boto3.client('bedrock-runtime')
        self.model_id = aws_services.bedrock_model_id
        
    def generate_description(
        self, 
        visual_analysis: Dict[str, Any], 
        audio_analysis: Dict[str, Any],
        video_url: str
    ) -> Dict[str, Any]:
        """
        Generate engaging video description using Claude
        
        Args:
            visual_analysis: Results from Rekognition
            audio_analysis: Results from Transcribe
            video_url: Original video URL for context
            
        Returns:
            dict: Generated description and metadata
        """
        try:
            logger.info("Generating description with Bedrock Claude")
            
            # Build dynamic prompt based on available data
            prompt = self._build_dynamic_prompt(visual_analysis, audio_analysis, video_url)
            
            # Prepare request for Claude
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 300,
                "temperature": 0.7,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            # Call Bedrock
            start_time = time.time()
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body)
            )
            
            # Process response
            response_body = json.loads(response['body'].read())
            description = response_body['content'][0]['text'].strip()
            
            processing_time = time.time() - start_time
            
            # Calculate token usage and costs
            input_tokens = response_body.get('usage', {}).get('input_tokens', 0)
            output_tokens = response_body.get('usage', {}).get('output_tokens', 0)
            
            return {
                'description': description,
                'metrics': {
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'processing_time_seconds': processing_time,
                    'model_id': self.model_id
                }
            }
            
        except ClientError as e:
            logger.error(f"Bedrock client error: {str(e)}")
            # Fallback to template-based description
            return self._generate_fallback_description(visual_analysis, audio_analysis)
        
        except Exception as e:
            logger.error(f"Description generation failed: {str(e)}")
            return self._generate_fallback_description(visual_analysis, audio_analysis)
    
    def _build_dynamic_prompt(
        self, 
        visual_analysis: Dict[str, Any], 
        audio_analysis: Dict[str, Any],
        video_url: str
    ) -> str:
        """
        Build a dynamic prompt based on available visual and audio data
        
        Args:
            visual_analysis: Visual analysis results
            audio_analysis: Audio analysis results
            video_url: Original video URL
            
        Returns:
            str: Formatted prompt for Claude
        """
        prompt_parts = [
            "You are an expert video content analyzer. Generate an engaging 2-3 sentence description for a video based on the analysis data below.",
            "",
            "**Instructions:**",
            "- Write in an engaging, descriptive style that would appeal to viewers",
            "- Focus on the most interesting and relevant elements",
            "- Be concise but informative",
            "- If the video has concerning content, mention it appropriately",
            "- Use active voice and vivid language",
            ""
        ]
        
        # Add visual analysis information
        if not visual_analysis.get('error'):
            prompt_parts.append("**Visual Elements Detected:**")
            
            # Add top labels
            labels = visual_analysis.get('labels', [])
            if labels:
                top_labels = [label['name'] for label in labels[:8]]
                prompt_parts.append(f"- Main subjects: {', '.join(top_labels)}")
            
            # Add celebrities if found
            celebrities = visual_analysis.get('celebrities', [])
            if celebrities:
                celeb_names = [celeb['name'] for celeb in celebrities[:3]]
                prompt_parts.append(f"- Notable people: {', '.join(celeb_names)}")
            
            # Add text if detected
            text_detections = visual_analysis.get('text', [])
            if text_detections:
                detected_text = [text['text'] for text in text_detections[:5]]
                prompt_parts.append(f"- Text visible: {', '.join(detected_text)}")
            
            # Add categories
            summary = visual_analysis.get('summary', {})
            top_categories = summary.get('top_categories', [])
            if top_categories:
                prompt_parts.append(f"- Primary categories: {', '.join(top_categories)}")
            
            # Add moderation flags if any
            moderation_flags = visual_analysis.get('moderation_flags', [])
            if moderation_flags:
                flag_names = [flag['name'] for flag in moderation_flags[:3]]
                prompt_parts.append(f"- Content warnings: {', '.join(flag_names)}")
            
            prompt_parts.append("")
        
        # Add audio analysis information
        if not audio_analysis.get('error') and audio_analysis.get('transcript'):
            prompt_parts.append("**Audio Content:**")
            
            transcript = audio_analysis.get('transcript', '')
            if transcript:
                # Truncate transcript if too long
                max_transcript_length = 500
                if len(transcript) > max_transcript_length:
                    transcript = transcript[:max_transcript_length] + "..."
                prompt_parts.append(f"- Transcript: \"{transcript}\"")
            
            # Add speaker information
            speaker_labels = audio_analysis.get('speaker_labels', [])
            if len(speaker_labels) > 1:
                prompt_parts.append(f"- Multiple speakers detected ({len(speaker_labels)} segments)")
            
            # Add language info
            language = audio_analysis.get('language_code', '')
            if language and language != 'en-US':
                prompt_parts.append(f"- Language: {language}")
            
            prompt_parts.append("")
        else:
            prompt_parts.append("**Audio Content:**")
            prompt_parts.append("- No clear audio/speech detected in this video")
            prompt_parts.append("")
        
        # Add context about video source
        if 'youtube.com' in video_url or 'youtu.be' in video_url:
            prompt_parts.append("**Context:** This is a YouTube video.")
        else:
            prompt_parts.append("**Context:** This is a directly uploaded video.")
        
        prompt_parts.extend([
            "",
            "**Task:** Based on the analysis above, write an engaging 2-3 sentence description that would make someone want to watch this video. Focus on the most interesting elements and create curiosity.",
            "",
            "Description:"
        ])
        
        return "\n".join(prompt_parts)
    
    def _generate_fallback_description(
        self, 
        visual_analysis: Dict[str, Any], 
        audio_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a basic description when Bedrock is not available
        
        Args:
            visual_analysis: Visual analysis results
            audio_analysis: Audio analysis results
            
        Returns:
            dict: Fallback description result
        """
        try:
            logger.info("Generating fallback description")
            
            description_parts = []
            
            # Start with visual elements
            if not visual_analysis.get('error'):
                labels = visual_analysis.get('labels', [])
                if labels:
                    top_label = labels[0]['name']
                    description_parts.append(f"This video features {top_label.lower()}")
                
                # Add categories for context
                summary = visual_analysis.get('summary', {})
                categories = summary.get('top_categories', [])
                if categories and len(categories) > 1:
                    description_parts.append(f"with elements of {categories[1].lower()}")
                
                # Add people if detected
                if any('people' in cat.lower() for cat in categories):
                    description_parts.append("and people")
            
            # Add audio context
            if not audio_analysis.get('error') and audio_analysis.get('transcript'):
                transcript = audio_analysis.get('transcript', '')
                if len(transcript) > 50:
                    description_parts.append("The video includes spoken content")
                    # Try to identify if it's educational, entertainment, etc.
                    if any(word in transcript.lower() for word in ['how to', 'tutorial', 'learn']):
                        description_parts.append("with educational content")
                    elif any(word in transcript.lower() for word in ['funny', 'laugh', 'joke']):
                        description_parts.append("with entertaining dialogue")
            else:
                description_parts.append("This appears to be a visual-focused video")
            
            # Create final description
            if description_parts:
                description = ". ".join(description_parts) + "."
                # Capitalize first letter
                description = description[0].upper() + description[1:] if description else "Video content detected."
            else:
                description = "This video contains visual content that may be of interest to viewers."
            
            return {
                'description': description,
                'metrics': {
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'processing_time_seconds': 0.1,
                    'model_id': 'fallback-template'
                }
            }
            
        except Exception as e:
            logger.error(f"Fallback description generation failed: {str(e)}")
            return {
                'description': "Video content available for viewing.",
                'metrics': {
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'processing_time_seconds': 0.1,
                    'model_id': 'fallback-minimal'
                }
            }