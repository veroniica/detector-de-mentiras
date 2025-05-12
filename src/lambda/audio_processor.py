"""
Audio Processor Lambda Function

This function is triggered when a new audio file is uploaded to the S3 bucket.
It extracts metadata from the audio file and starts the Step Functions state machine.
"""

import os
import json
import uuid
import boto3
import logging
from urllib.parse import unquote_plus

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sfn_client = boto3.client('stepfunctions')

# Get environment variables
AUDIO_BUCKET = os.environ['AUDIO_BUCKET']
RESULTS_BUCKET = os.environ['RESULTS_BUCKET']
METADATA_TABLE = os.environ['METADATA_TABLE']
STATE_MACHINE_ARN = os.environ['STATE_MACHINE_ARN']

def extract_audio_metadata(bucket, key):
    """
    Extract metadata from the audio file.
    
    Args:
        bucket (str): S3 bucket name
        key (str): S3 object key
        
    Returns:
        dict: Audio metadata
    """
    try:
        # Get object metadata from S3
        response = s3_client.head_object(Bucket=bucket, Key=key)
        
        # Extract basic metadata
        metadata = {
            'audioId': str(uuid.uuid4()),
            'fileName': key.split('/')[-1],
            'fileSize': response.get('ContentLength', 0),
            'contentType': response.get('ContentType', 'audio/mpeg'),
            'uploadTime': response.get('LastModified').isoformat(),
            'bucket': bucket,
            'key': key,
            'status': 'PROCESSING',
        }
        
        # Extract custom metadata if available
        if 'Metadata' in response:
            user_metadata = response['Metadata']
            if 'case_id' in user_metadata:
                metadata['caseId'] = user_metadata['case_id']
            if 'interview_date' in user_metadata:
                metadata['interviewDate'] = user_metadata['interview_date']
            if 'interviewer' in user_metadata:
                metadata['interviewer'] = user_metadata['interviewer']
            if 'interviewee' in user_metadata:
                metadata['interviewee'] = user_metadata['interviewee']
        
        return metadata
    
    except Exception as e:
        logger.error(f"Error extracting metadata: {str(e)}")
        raise

def save_metadata(metadata):
    """
    Save metadata to DynamoDB.
    
    Args:
        metadata (dict): Audio metadata
        
    Returns:
        str: Audio ID
    """
    try:
        table = dynamodb.Table(METADATA_TABLE)
        table.put_item(Item=metadata)
        return metadata['audioId']
    
    except Exception as e:
        logger.error(f"Error saving metadata: {str(e)}")
        raise

def start_processing(audio_id, bucket, key):
    """
    Start the Step Functions state machine.
    
    Args:
        audio_id (str): Audio ID
        bucket (str): S3 bucket name
        key (str): S3 object key
        
    Returns:
        str: Execution ARN
    """
    try:
        input_data = {
            'audioId': audio_id,
            'bucket': bucket,
            'key': key
        }
        
        response = sfn_client.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=f"audio-processing-{audio_id}",
            input=json.dumps(input_data)
        )
        
        return response['executionArn']
    
    except Exception as e:
        logger.error(f"Error starting state machine: {str(e)}")
        raise

def handler(event, context):
    """
    Lambda handler function.
    
    Args:
        event (dict): Event data
        context (object): Lambda context
        
    Returns:
        dict: Response
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Extract bucket and key from the event
        if 'detail' in event:
            # EventBridge event
            bucket = event['detail']['bucket']['name']
            key = unquote_plus(event['detail']['object']['key'])
        elif 'Records' in event:
            # S3 event
            record = event['Records'][0]
            bucket = record['s3']['bucket']['name']
            key = unquote_plus(record['s3']['object']['key'])
        else:
            raise ValueError("Unsupported event format")
        
        # Extract metadata from the audio file
        metadata = extract_audio_metadata(bucket, key)
        
        # Save metadata to DynamoDB
        audio_id = save_metadata(metadata)
        
        # Start the Step Functions state machine
        execution_arn = start_processing(audio_id, bucket, key)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Audio processing started',
                'audioId': audio_id,
                'executionArn': execution_arn
            })
        }
    
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f"Error processing audio: {str(e)}"
            })
        }