import boto3
import os
import logging

RESULTS_BUCKET = os.environ["RESULTS_BUCKET"]

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def start_transcription_job(transcribe_client, audio_id, bucket, key):
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
        logger.info(f"Starting transcription job for {audio_id}")
        job_name = f"transcription-{audio_id}"
        media_uri = f"s3://{bucket}/{key}"

        response = transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": media_uri},
            MediaFormat=key.split(".")[-1].lower(),
            LanguageCode="es-ES",  # Spanish language code, change as needed
            OutputBucketName=RESULTS_BUCKET,
            OutputKey=f"transcriptions/{audio_id}/raw_transcription.json",
            Settings={
                "ShowSpeakerLabels": True,
                "MaxSpeakerLabels": 10,  # Adjust based on expected number of speakers
                "ShowAlternatives": False,
            },
        )
        logger.info(f"Transcription job response: {response}")
        return job_name

    except Exception as e:
        logger.error(f"Error starting transcription job: {str(e)}")
        raise
