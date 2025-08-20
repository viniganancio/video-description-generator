"""
API Handler Lambda Function
Handles REST API endpoints for the video description service
"""
import json
import logging
import os
import traceback
import uuid
from datetime import datetime
from typing import Dict, Any

import boto3
from api_handler import APIHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize API handler
api_handler = APIHandler()


def lambda_handler(event, context):
    """
    Lambda handler for API requests
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        dict: HTTP response
    """
    try:
        logger.info(f"API request: {json.dumps(event, default=str)}")
        
        # Extract HTTP method and path
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '/')
        path_parameters = event.get('pathParameters') or {}
        query_parameters = event.get('queryStringParameters') or {}
        
        # Parse request body
        body = {}
        if event.get('body'):
            try:
                body = json.loads(event['body'])
            except json.JSONDecodeError:
                return api_handler.error_response(400, "Invalid JSON in request body")
        
        # Route the request
        if http_method == 'POST' and path == '/analyze':
            return api_handler.handle_analyze(body)
        elif http_method == 'GET' and path.startswith('/status/'):
            job_id = path_parameters.get('job_id')
            return api_handler.handle_status(job_id, query_parameters)
        elif http_method == 'GET' and path.startswith('/result/'):
            job_id = path_parameters.get('job_id')
            return api_handler.handle_result(job_id, query_parameters)
        elif http_method == 'OPTIONS':
            return api_handler.handle_options()
        else:
            return api_handler.error_response(404, f"Endpoint not found: {http_method} {path}")
            
    except Exception as e:
        error_message = str(e)
        error_traceback = traceback.format_exc()
        logger.error(f"Unhandled error in API handler: {error_message}")
        logger.error(f"Traceback: {error_traceback}")
        
        return api_handler.error_response(
            500, 
            "Internal server error",
            {"error_id": str(uuid.uuid4())[:8]}
        )