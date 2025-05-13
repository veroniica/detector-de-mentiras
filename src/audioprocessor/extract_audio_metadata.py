import logging
import boto3
import json
import uuid

from logger_serialize import logger_serialize

s3_client = boto3.client("s3")


# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
        logger.info(f"Extracting metadata from {bucket}/{key}")
        response = s3_client.head_object(Bucket=bucket, Key=key)
        logger.info(f"Object metadata: {json.dumps(logger_serialize(response))}")

        # Extract basic metadata
        metadata = {
            "audioId": str(uuid.uuid4()),
            "fileName": key.split("/")[-1],
            "fileSize": response.get("ContentLength", 0),
            "contentType": response.get("ContentType", "audio/mpeg"),
            "uploadTime": response.get("LastModified").isoformat(),
            "bucket": bucket,
            "key": key,
            "status": "PROCESSING",
        }

        # Extract custom metadata if available
        # ToDo: Add this metadata to the audio file at the end
        # if 'Metadata' in response:
        #     user_metadata = response['Metadata']
        #     if 'case_id' in user_metadata:
        #         metadata['caseId'] = user_metadata['case_id']
        #     if 'interview_date' in user_metadata:
        #         metadata['interviewDate'] = user_metadata['interview_date']
        #     if 'interviewer' in user_metadata:
        #         metadata['interviewer'] = user_metadata['interviewer']
        #     if 'interviewee' in user_metadata:
        #         metadata['interviewee'] = user_metadata['interviewee']

        return metadata

    except Exception as e:
        logger.error(f"Error extracting metadata: {str(e)}", exc_info=True)

        raise
