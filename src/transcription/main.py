# """
# Transcription Lambda Function
# This function uses Amazon Transcribe to convert audio to text with
# speaker identification.
# It formats the transcription as a script with timestamps.
# """

import json
import boto3
import logging
import traceback

from start_transcription_job import start_transcription_job
from wait_for_transcription_job import wait_for_transcription_job
from get_transcription_result import get_transcription_result
from format_as_script import format_as_script
from save_transcription import save_transcription

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")
transcribe_client = boto3.client("transcribe")


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
        logger.info(f"Begin: {json.dumps(event)}")
        audio_id = event["audioId"]
        bucket = event["bucket"]
        key = event["key"]

        # Start transcription job
        job_name = start_transcription_job(transcribe_client, audio_id, bucket, key)
        logger.info(f"Started transcription job: {job_name}")

        # Wait for job to complete
        job = wait_for_transcription_job(transcribe_client, job_name)
        logger.info(f"Transcription job completed: {job_name}")

        # Get transcription result
        result = get_transcription_result(s3_client, job)
        logger.info(f"Transcription result: {result}")

        # Format as script
        script = format_as_script(result)
        logger.info(f"Formatted as script: {script}")

        # Save transcription
        transcription = save_transcription(s3_client, audio_id, script, result)

        return {
            "audioId": audio_id,
            "transcription": transcription,
            "status": "COMPLETED",
        }

    except Exception as e:
        logger.error(f"Error processing transcription: {str(e)}")
        error_traceback = traceback.format_exc()
        raise {
            "audioId": event.get("audioId", "unknown"),
            "error": str(e),
            "status": "FAILED",
            "message": f"Error processing audio: {str(e)}",
            "error_type": type(e).__name__,
            "error_details": str(e),
            "error_traceback": error_traceback,
            "error_location": str(traceback.extract_tb(e.__traceback__)[-1]),
        }

