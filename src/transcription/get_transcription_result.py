import logging
import os
import json
from urllib.parse import urlparse

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

RESULTS_BUCKET = os.environ["RESULTS_BUCKET"]


def get_transcription_result(s3_client, job):
    """
    Get the transcription result from S3.

    Args:
        job (dict): Transcription job details

    Returns:
        dict: Transcription result
    """
    try:
        print(job)
        logger.info(f"Getting transcription result for {job['TranscriptionJobName']}")
        transcript_uri = job["Transcript"]["TranscriptFileUri"]
        print(transcript_uri)

        if transcript_uri.startswith("s3://"):
            # Parse S3 URI
            parsed_uri = urlparse(transcript_uri)
            bucket = parsed_uri.netloc
            key = parsed_uri.path.lstrip("/")
        else:
            # Handle HTTPS URL to S3
            output_location = job.get("OutputLocation", {})
            bucket = RESULTS_BUCKET
            key = output_location.get(
                "Key", f"transcriptions/{job['TranscriptionJobName']}/raw_transcription.json"
            )

        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response["Body"].read().decode("utf-8")

        return json.loads(content)

    except Exception as e:
        logger.error(f"Error getting transcription result: {str(e)}")
        raise
