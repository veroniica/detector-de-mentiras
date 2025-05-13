import time
import logging


# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def wait_for_transcription_job(transcribe_client, job_name):
    """
    Wait for the transcription job to complete.

    Args:
        job_name (str): Transcription job name

    Returns:
        dict: Transcription job details
    """
    try:
        logger.info(f"Waiting for transcription job {job_name} to complete")
        while True:
            response = transcribe_client.get_transcription_job(
                TranscriptionJobName=job_name
            )

            status = response["TranscriptionJob"]["TranscriptionJobStatus"]

            if status in ["COMPLETED", "FAILED"]:
                return response["TranscriptionJob"]

            time.sleep(5)  # Wait for 5 seconds before checking again

    except Exception as e:
        logger.error(f"Error waiting for transcription job: {str(e)}")
        raise
