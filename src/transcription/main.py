"""
Transcription Lambda Function
This function uses Amazon Transcribe to convert audio to text with
speaker identification and formats the transcription as a script with timestamps.
"""

import json
import boto3
import logging
from botocore.exceptions import ClientError
import traceback

from start_transcription_job import start_transcription_job
from wait_for_transcription_job import wait_for_transcription_job
from get_transcription_result import get_transcription_result
from format_as_script import format_as_script
from save_transcription import save_transcription

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients once outside the handler for better performance
s3_client = boto3.client("s3")
transcribe_client = boto3.client("transcribe")


def handler(event, context):
    """
    Lambda handler function that processes audio transcription workflow.

    Args:
        event (dict): Event data containing audioId, bucket and key
        context (object): Lambda context

    Returns:
        dict: Response with transcription status and details
    """
    audio_id = event.get("audioId", "unknown")

    try:
        logger.info(f"Processing transcription request: {json.dumps(event)}")

        # Extract required parameters
        bucket = event["bucket"]
        key = event["key"]

        # Execute transcription workflow
        job_name = start_transcription_job(transcribe_client, audio_id, bucket, key)
        job = wait_for_transcription_job(transcribe_client, job_name)
        result = get_transcription_result(s3_client, job)
        script = format_as_script(result)
        transcription = save_transcription(s3_client, audio_id, script, result)

        logger.info(f"Transcription completed successfully for audio: {audio_id}")
        return {
            "audioId": audio_id,
            "transcription": transcription,
            "status": "COMPLETED",
        }

    except KeyError as e:
        logger.error(f"Missing required parameter: {str(e)}")
        return create_error_response(
            audio_id, e, "INVALID_REQUEST", f"Missing required parameter: {str(e)}"
        )
    except ClientError as e:
        logger.error(f"AWS service error: {str(e)}")
        return create_error_response(
            audio_id,
            e,
            "SERVICE_ERROR",
            f"AWS service error: {e.response['Error']['Message']}",
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return create_error_response(
            audio_id, e, "FAILED", "Error processing audio transcription"
        )


def create_error_response(audio_id, exception, status, message):
    """Helper function to create standardized error responses"""
    return {
        "audioId": audio_id,
        "error": str(exception),
        "status": status,
        "message": message,
        "error_type": type(exception).__name__,
    }
