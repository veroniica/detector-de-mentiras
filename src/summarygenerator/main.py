"""
Summary Generator Lambda Function
This function analyzes transcription data to extract key ideas and generate a summary
of the audio content using AWS Comprehend and Bedrock services.
"""

import json
import boto3
import logging
import os
import time
import traceback
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients once outside the handler for better performance
s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
comprehend_client = boto3.client("comprehend")
bedrock_runtime = boto3.client("bedrock-runtime")

# Environment variables
RESULTS_BUCKET = os.environ["RESULTS_BUCKET"]
ANALYSIS_TABLE = os.environ["ANALYSIS_TABLE"]


def handler(event, context):
    """
    Lambda handler function that generates a summary from transcription data.

    Args:
        event (dict): Event data containing audioId and transcription details
        context (object): Lambda context

    Returns:
        dict: Response with summary generation status and details
    """
    audio_id = event.get("audioId", "unknown")

    try:
        logger.info(f"Processing summary generation request: {json.dumps(event)}")

        # Get transcription data
        transcription = event.get("transcription", {})
        script_s3_key = transcription.get("scriptS3Key")

        if not script_s3_key:
            raise KeyError("Missing required parameter: scriptS3Key")

        # Get the transcription script from S3
        script_content = get_script_from_s3(script_s3_key)

        # Extract key phrases using Amazon Comprehend
        key_phrases = extract_key_phrases(script_content)

        # Generate summary using Amazon Bedrock
        summary = generate_summary(script_content)

        # Save results
        result = save_summary(audio_id, key_phrases, summary)

        logger.info(f"Summary generation completed successfully for audio: {audio_id}")
        return {
            "audioId": audio_id,
            "summary": result,
            "status": "COMPLETED",
        }

    except KeyError as e:
        logger.error(f"Missing required parameter: {str(e)}")
        return create_error_response(
            audio_id, e, "INVALID_REQUEST", f"Missing required parameter: {str(e)}"
        )
    except ClientError as e:
        logger.error(f"AWS service error: {str(e)}")
        return create_error_response(
            audio_id,
            e,
            "SERVICE_ERROR",
            f"AWS service error: {e.response['Error']['Message']}",
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return create_error_response(
            audio_id, e, "FAILED", "Error generating summary"
        )


def get_script_from_s3(script_s3_key):
    """
    Get the transcription script from S3.

    Args:
        script_s3_key (str): S3 key for the script file

    Returns:
        str: Script content
    """
    try:
        response = s3_client.get_object(Bucket=RESULTS_BUCKET, Key=script_s3_key)
        script_content = response["Body"].read().decode("utf-8")
        return script_content
    except Exception as e:
        logger.error(f"Error retrieving script from S3: {str(e)}")
        raise


def extract_key_phrases(text):
    """
    Extract key phrases from the text using Amazon Comprehend.

    Args:
        text (str): Text to analyze

    Returns:
        list: List of key phrases
    """
    try:
        # Ensure text is within Comprehend's limits (100KB)
        if len(text.encode('utf-8')) > 100000:
            # Split text into chunks if needed
            text = text[:100000]
            logger.warning("Text truncated to 100KB for Comprehend analysis")

        response = comprehend_client.detect_key_phrases(
            Text=text,
            LanguageCode="es"  # Assuming Spanish based on the request
        )

        # Sort key phrases by score and get top phrases
        key_phrases = sorted(
            response["KeyPhrases"],
            key=lambda x: x["Score"],
            reverse=True
        )[:10]  # Get top 10 key phrases

        return [phrase["Text"] for phrase in key_phrases]
    except Exception as e:
        logger.error(f"Error extracting key phrases: {str(e)}")
        raise


def generate_summary(text):
    """
    Generate a summary of the text using Amazon Bedrock.

    Args:
        text (str): Text to summarize

    Returns:
        str: Generated summary
    """
    try:
        # Prepare prompt for the model
        prompt = f"""
        Por favor, genera un resumen conciso del siguiente texto de una entrevista relacionada con un caso criminalístico.
        Identifica las ideas principales y organiza el resumen de manera coherente.
        
        TEXTO:
        {text[:8000]}  # Limiting text length for Bedrock
        
        RESUMEN:
        """

        # Call Bedrock with Claude model
        response = bedrock_runtime.invoke_model(
            modelId="anthropic.claude-v2",  # Using Claude v2
            body=json.dumps({
                "prompt": prompt,
                "max_tokens_to_sample": 2000,
                "temperature": 0.5,
                "top_p": 0.9,
            })
        )

        # Parse response
        response_body = json.loads(response["body"].read())
        summary = response_body.get("completion", "").strip()

        return summary
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        # Fallback to a simpler summary method if Bedrock fails
        return generate_fallback_summary(text)


def generate_fallback_summary(text):
    """
    Generate a simple summary when Bedrock is unavailable.

    Args:
        text (str): Text to summarize

    Returns:
        str: Simple summary
    """
    # Simple fallback: use first few sentences as summary
    sentences = text.split('.')
    summary = '. '.join(sentences[:5]) + '.'
    return f"Resumen (generado por método alternativo): {summary}"


def save_summary(audio_id, key_phrases, summary):
    """
    Save the summary and key phrases to S3 and DynamoDB.

    Args:
        audio_id (str): Audio ID
        key_phrases (list): List of key phrases
        summary (str): Generated summary

    Returns:
        dict: Saved summary details
    """
    try:
        # Create result object
        result = {
            "keyPhrases": key_phrases,
            "summary": summary
        }

        # Save to S3
        summary_key = f"analysis/{audio_id}/summary.json"
        s3_client.put_object(
            Bucket=RESULTS_BUCKET,
            Key=summary_key,
            Body=json.dumps(result, indent=2),
            ContentType="application/json"
        )

        # Save to DynamoDB
        table = dynamodb.Table(ANALYSIS_TABLE)
        item = {
            "audioId": audio_id,
            "summaryS3Key": summary_key,
            "keyPhrases": key_phrases,
            "status": "COMPLETED",
            "timestamp": int(time.time()),
            "type": "summary"
        }
        table.put_item(Item=item)

        return {
            "audioId": audio_id,
            "summaryS3Key": summary_key,
            "keyPhrases": key_phrases,
            "status": "COMPLETED"
        }

    except Exception as e:
        logger.error(f"Error saving summary: {str(e)}")
        raise


def create_error_response(audio_id, exception, status, message):
    """Helper function to create standardized error responses"""
    return {
        "audioId": audio_id,
        "error": str(exception),
        "status": status,
        "message": message,
        "error_type": type(exception).__name__,
    }