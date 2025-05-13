import json
import logging
import boto3
import os

dynamodb = boto3.resource("dynamodb")
METADATA_TABLE = os.environ["METADATA_TABLE"]


# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def save_metadata(metadata):
    """
    Save metadata to DynamoDB.

    Args:
        metadata (dict): Audio metadata

    Returns:
        str: Audio ID
    """
    try:
        logger.info(f"Saving metadata: {json.dumps(metadata)}")
        table = dynamodb.Table(METADATA_TABLE)
        table.put_item(Item=metadata)
        return metadata["audioId"]

    except Exception as e:
        logger.error(f"Error saving metadata: {str(e)}")
        raise
