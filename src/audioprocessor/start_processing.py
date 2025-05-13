import boto3
import os
import json
import logging

sfn_client = boto3.client("stepfunctions")
STATE_MACHINE_ARN = os.environ["STATE_MACHINE_ARN"]

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
        logger.info(f"Starting state machine for audioId: {audio_id}")
        input_data = {"audioId": audio_id, "bucket": bucket, "key": key}

        response = sfn_client.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=f"audio-processing-{audio_id}",
            input=json.dumps(input_data),
        )

        return response["executionArn"]

    except Exception as e:
        logger.error(f"Error starting state machine: {str(e)}")
        raise
