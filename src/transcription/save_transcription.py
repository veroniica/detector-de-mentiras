import boto3
import os
import logging
import time
import json

dynamodb = boto3.resource("dynamodb")

RESULTS_BUCKET = os.environ["RESULTS_BUCKET"]
TRANSCRIPTION_TABLE = os.environ["TRANSCRIPTION_TABLE"]

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def save_transcription(s3_client, audio_id, script, raw_result):
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
        logger.info(
            f"Saving transcription for {audio_id}: {json.dumps(script, raw_result)}"
        )
        # Save formatted script to S3
        script_key = f"transcriptions/{audio_id}/script.txt"
        s3_client.put_object(
            Bucket=RESULTS_BUCKET, Key=script_key, Body=script, ContentType="text/plain"
        )

        # Save to DynamoDB
        logger.info(f"Saving transcription to DynamoDB for {audio_id}")
        table = dynamodb.Table(TRANSCRIPTION_TABLE)
        item = {
            "audioId": audio_id,
            "scriptS3Key": script_key,
            "rawTranscriptionS3Key": f"transcriptions/{audio_id}/raw_transcription.json",
            "status": "COMPLETED",
            "timestamp": int(time.time()),
        }
        table.put_item(Item=item)

        return {"audioId": audio_id, "scriptS3Key": script_key, "status": "COMPLETED"}

    except Exception as e:
        logger.error(f"Error saving transcription: {str(e)}")
        raise
