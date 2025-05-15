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
        print("job")
        print(job)
        logger.info(f"Getting transcription result for {job['TranscriptionJobName']}")
        transcript_uri = job["Transcript"]["TranscriptFileUri"]
        print("transcript_uri")
        print(transcript_uri)

        assert transcript_uri.startswith("https://s3."), "Invalid S3 URL"
        # Parse HTTPS S3 URL
        logger.info("Parse HTTPS S3 URL")
        parsed_uri = urlparse(transcript_uri)
        print("parsed_uri")
        print(parsed_uri)

        # Extract the bucket name from the path
        path_parts = parsed_uri.path.lstrip("/").split("/", 1)
        bucket = path_parts[0]
        key = path_parts[1] if len(path_parts) > 1 else ""

        logger.info(f"Extracted from HTTPS URL - Bucket: {bucket}, Key: {key}")

        logger.info(f"Bucket: {bucket}, Key: {key}")
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response["Body"].read().decode("utf-8")

        return json.loads(content)

    except Exception as e:
        logger.error(f"Error getting transcription result: {str(e)}")
        raise
