"""
Transcription Lambda Function

This function uses Amazon Transcribe to convert audio to text with speaker identification.
It formats the transcription as a script with timestamps.
"""

import os
import json
import time
import uuid
import boto3
import logging
from urllib.parse import urlparse

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
transcribe_client = boto3.client('transcribe')
dynamodb = boto3.resource('dynamodb')

# Get environment variables
AUDIO_BUCKET = os.environ['AUDIO_BUCKET']
RESULTS_BUCKET = os.environ['RESULTS_BUCKET']
TRANSCRIPTION_TABLE = os.environ['TRANSCRIPTION_TABLE']

def start_transcription_job(audio_id, bucket, key):
    """
    Start an Amazon Transcribe job with speaker identification.
    
    Args:
        audio_id (str): Audio ID
        bucket (str): S3 bucket name
        key (str): S3 object key
        
    Returns:
        str: Transcription job name
    """
    try:
        job_name = f"transcription-{audio_id}"
        media_uri = f"s3://{bucket}/{key}"
        
        response = transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': media_uri},
            MediaFormat=key.split('.')[-1].lower(),
            LanguageCode='es-ES',  # Spanish language code, change as needed
            OutputBucketName=RESULTS_BUCKET,
            OutputKey=f"transcriptions/{audio_id}/raw_transcription.json",
            Settings={
                'ShowSpeakerLabels': True,
                'MaxSpeakerLabels': 10,  # Adjust based on expected number of speakers
                'ShowAlternatives': False
            }
        )
        
        return job_name
    
    except Exception as e:
        logger.error(f"Error starting transcription job: {str(e)}")
        raise

def wait_for_transcription_job(job_name):
    """
    Wait for the transcription job to complete.
    
    Args:
        job_name (str): Transcription job name
        
    Returns:
        dict: Transcription job details
    """
    try:
        while True:
            response = transcribe_client.get_transcription_job(
                TranscriptionJobName=job_name
            )
            
            status = response['TranscriptionJob']['TranscriptionJobStatus']
            
            if status in ['COMPLETED', 'FAILED']:
                return response['TranscriptionJob']
            
            time.sleep(5)  # Wait for 5 seconds before checking again
    
    except Exception as e:
        logger.error(f"Error waiting for transcription job: {str(e)}")
        raise

def get_transcription_result(job):
    """
    Get the transcription result from S3.
    
    Args:
        job (dict): Transcription job details
        
    Returns:
        dict: Transcription result
    """
    try:
        transcript_uri = job['Transcript']['TranscriptFileUri']
        
        if transcript_uri.startswith('s3://'):
            # Parse S3 URI
            parsed_uri = urlparse(transcript_uri)
            bucket = parsed_uri.netloc
            key = parsed_uri.path.lstrip('/')
        else:
            # Handle HTTPS URL to S3
            output_location = job.get('OutputLocation', {})
            bucket = RESULTS_BUCKET
            key = output_location.get('Key', f"transcriptions/{job['TranscriptionJobName']}.json")
        
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')
        
        return json.loads(content)
    
    except Exception as e:
        logger.error(f"Error getting transcription result: {str(e)}")
        raise

def format_as_script(result):
    """
    Format the transcription result as a script with timestamps.
    
    Args:
        result (dict): Transcription result
        
    Returns:
        str: Formatted script
    """
    try:
        transcript = result.get('results', {})
        items = transcript.get('items', [])
        speaker_labels = transcript.get('speaker_labels', {})
        segments = speaker_labels.get('segments', [])
        
        # Create a mapping of item IDs to speaker labels
        speaker_mapping = {}
        for segment in segments:
            speaker_label = segment.get('speaker_label', 'Unknown')
            for item in segment.get('items', []):
                speaker_mapping[item.get('start_time')] = speaker_label
        
        # Format the transcript as a script
        script_lines = []
        current_speaker = None
        current_line = ""
        current_start_time = None
        
        for item in items:
            # Skip non-pronunciation items (like punctuation)
            if item.get('type') != 'pronunciation':
                continue
                
            start_time = item.get('start_time')
            end_time = item.get('end_time')
            content = item.get('alternatives', [{}])[0].get('content', '')
            speaker = speaker_mapping.get(start_time, 'Unknown')
            
            # Format timestamp as MM:SS
            timestamp = format_timestamp(float(start_time))
            
            # If speaker changes or significant time gap, start a new line
            if speaker != current_speaker or current_line == "":
                if current_line:
                    script_lines.append(f"[{format_timestamp(float(current_start_time))}] {current_speaker}: {current_line}")
                current_speaker = speaker
                current_line = content
                current_start_time = start_time
            else:
                current_line += " " + content
        
        # Add the last line
        if current_line:
            script_lines.append(f"[{format_timestamp(float(current_start_time))}] {current_speaker}: {current_line}")
        
        return "\n".join(script_lines)
    
    except Exception as e:
        logger.error(f"Error formatting script: {str(e)}")
        raise

def format_timestamp(seconds):
    """
    Format seconds as MM:SS.
    
    Args:
        seconds (float): Time in seconds
        
    Returns:
        str: Formatted timestamp
    """
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

def save_transcription(audio_id, script, raw_result):
    """
    Save the transcription to S3 and DynamoDB.
    
    Args:
        audio_id (str): Audio ID
        script (str): Formatted script
        raw_result (dict): Raw transcription result
        
    Returns:
        dict: Saved transcription details
    """
    try:
        # Save formatted script to S3
        script_key = f"transcriptions/{audio_id}/script.txt"
        s3_client.put_object(
            Bucket=RESULTS_BUCKET,
            Key=script_key,
            Body=script,
            ContentType='text/plain'
        )
        
        # Save to DynamoDB
        table = dynamodb.Table(TRANSCRIPTION_TABLE)
        item = {
            'audioId': audio_id,
            'scriptS3Key': script_key,
            'rawTranscriptionS3Key': f"transcriptions/{audio_id}/raw_transcription.json",
            'status': 'COMPLETED',
            'timestamp': int(time.time())
        }
        table.put_item(Item=item)
        
        return {
            'audioId': audio_id,
            'scriptS3Key': script_key,
            'status': 'COMPLETED'
        }
    
    except Exception as e:
        logger.error(f"Error saving transcription: {str(e)}")
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
        
        audio_id = event['audioId']
        bucket = event['bucket']
        key = event['key']
        
        # Start transcription job
        job_name = start_transcription_job(audio_id, bucket, key)
        logger.info(f"Started transcription job: {job_name}")
        
        # Wait for job to complete
        job = wait_for_transcription_job(job_name)
        logger.info(f"Transcription job completed: {job_name}")
        
        # Get transcription result
        result = get_transcription_result(job)
        
        # Format as script
        script = format_as_script(result)
        
        # Save transcription
        transcription = save_transcription(audio_id, script, result)
        
        return {
            'audioId': audio_id,
            'transcription': transcription,
            'status': 'COMPLETED'
        }
    
    except Exception as e:
        logger.error(f"Error processing transcription: {str(e)}")
        return {
            'audioId': event.get('audioId', 'unknown'),
            'error': str(e),
            'status': 'FAILED'
        }