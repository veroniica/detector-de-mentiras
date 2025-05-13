# """
# Audio Processor Lambda Function

# This function is triggered when a new audio file is uploaded to the S3 bucket.
# It extracts metadata from the audio file and starts the Step Functions state machine.
# """

import json
import logging
import traceback
from urllib.parse import unquote_plus
from save_metadata import save_metadata
from extract_audio_metadata import extract_audio_metadata
from start_processing import start_processing

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


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

        # Extract bucket and key from the event
        if "detail" in event:
            # EventBridge event
            bucket = event["detail"]["bucket"]["name"]
            key = unquote_plus(event["detail"]["object"]["key"])
        elif "Records" in event:
            # S3 event
            record = event["Records"][0]
            bucket = record["s3"]["bucket"]["name"]
            key = unquote_plus(record["s3"]["object"]["key"])
        else:
            raise ValueError("Unsupported event format")

        logger.info(f"Record, Bucket, Key: {bucket}, {key}")

        # Extract metadata from the audio file
        metadata = extract_audio_metadata(bucket, key)

        # Save metadata to DynamoDB
        audio_id = save_metadata(metadata)

        # Start the Step Functions state machine
        execution_arn = start_processing(audio_id, bucket, key)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Audio processing started",
                    "audioId": audio_id,
                    "executionArn": execution_arn,
                }
            ),
        }

    except Exception as e:
        # Obtener el traceback completo como string
        error_traceback = traceback.format_exc()
        logger.error(f"Error processing audio: {str(e)}", exc_info=True)
        raise {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "message": f"Error processing audio: {str(e)}",
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                    "error_traceback": error_traceback,
                    "error_location": str(traceback.extract_tb(e.__traceback__)[-1]),
                }
            ),
        }
