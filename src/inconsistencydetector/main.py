"""
Inconsistency Detector Lambda Function
This function analyzes multiple transcriptions to identify contradictions
and inconsistencies between different interviews.
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
bedrock_runtime = boto3.client("bedrock-runtime")

# Environment variables
RESULTS_BUCKET = os.environ["RESULTS_BUCKET"]
TRANSCRIPTION_TABLE = os.environ["TRANSCRIPTION_TABLE"]
ANALYSIS_TABLE = os.environ["ANALYSIS_TABLE"]


def handler(event, context):
    """
    Lambda handler function that detects inconsistencies between different interviews.

    Args:
        event (dict): Event data containing audioId and transcription details
        context (object): Lambda context

    Returns:
        dict: Response with inconsistency detection status and details
    """
    # The current audio being processed
    current_audio_id = event.get("audioId", "unknown")

    try:
        logger.info(f"Processing inconsistency detection request: {json.dumps(event)}")

        # Get all transcriptions from DynamoDB
        transcriptions = get_all_transcriptions()
        
        # If we have fewer than 2 transcriptions, we can't detect inconsistencies
        if len(transcriptions) < 2:
            logger.info("Not enough transcriptions to detect inconsistencies")
            return {
                "audioId": current_audio_id,
                "status": "SKIPPED",
                "message": "Not enough transcriptions to detect inconsistencies",
                "inconsistencies": []
            }

        # Get transcription contents from S3
        transcription_contents = get_transcription_contents(transcriptions)
        
        # Detect inconsistencies using Bedrock
        inconsistencies = detect_inconsistencies(transcription_contents)
        
        # Save results
        result = save_inconsistencies(current_audio_id, inconsistencies, transcriptions)

        logger.info(f"Inconsistency detection completed successfully")
        return {
            "audioId": current_audio_id,
            "inconsistencyAnalysis": result,
            "status": "COMPLETED",
        }

    except KeyError as e:
        logger.error(f"Missing required parameter: {str(e)}")
        return create_error_response(
            current_audio_id, e, "INVALID_REQUEST", f"Missing required parameter: {str(e)}"
        )
    except ClientError as e:
        logger.error(f"AWS service error: {str(e)}")
        return create_error_response(
            current_audio_id,
            e,
            "SERVICE_ERROR",
            f"AWS service error: {e.response['Error']['Message']}",
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return create_error_response(
            current_audio_id, e, "FAILED", "Error detecting inconsistencies"
        )


def get_all_transcriptions():
    """
    Get all transcriptions from DynamoDB.

    Returns:
        list: List of transcription items
    """
    try:
        table = dynamodb.Table(TRANSCRIPTION_TABLE)
        response = table.scan()
        transcriptions = response.get("Items", [])
        
        # Continue scanning if we have more items (pagination)
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            transcriptions.extend(response.get("Items", []))
        
        return transcriptions
    except Exception as e:
        logger.error(f"Error getting transcriptions: {str(e)}")
        raise


def get_transcription_contents(transcriptions):
    """
    Get transcription contents from S3.

    Args:
        transcriptions (list): List of transcription items

    Returns:
        dict: Dictionary of transcription contents by audio ID
    """
    try:
        contents = {}
        
        for transcription in transcriptions:
            audio_id = transcription.get("audioId")
            script_s3_key = transcription.get("scriptS3Key")
            
            if not audio_id or not script_s3_key:
                continue
                
            # Get script content from S3
            response = s3_client.get_object(Bucket=RESULTS_BUCKET, Key=script_s3_key)
            content = response["Body"].read().decode("utf-8")
            
            contents[audio_id] = content
        
        return contents
    except Exception as e:
        logger.error(f"Error getting transcription contents: {str(e)}")
        raise


def detect_inconsistencies(transcription_contents):
    """
    Detect inconsistencies between different transcriptions using Bedrock.

    Args:
        transcription_contents (dict): Dictionary of transcription contents by audio ID

    Returns:
        list: List of detected inconsistencies
    """
    try:
        # Prepare data for analysis
        audio_ids = list(transcription_contents.keys())
        
        # For each pair of transcriptions, detect inconsistencies
        inconsistencies = []
        
        # Use Bedrock for more sophisticated analysis if available
        try:
            # Prepare all transcriptions for the model
            all_transcriptions = ""
            for audio_id, content in transcription_contents.items():
                # Limit content length to avoid exceeding token limits
                truncated_content = content[:5000] + "..." if len(content) > 5000 else content
                all_transcriptions += f"\n\nENTREVISTA {audio_id}:\n{truncated_content}"
            
            # Create prompt for Bedrock
            prompt = f"""
            Analiza las siguientes transcripciones de entrevistas relacionadas con un caso criminalístico.
            Identifica y enumera todas las contradicciones o inconsistencias entre las diferentes entrevistas.
            Para cada inconsistencia, proporciona:
            1. Una descripción clara de la contradicción
            2. Las declaraciones específicas que se contradicen
            3. Los IDs de audio involucrados
            4. La gravedad de la inconsistencia (Alta, Media, Baja)
            
            TRANSCRIPCIONES:
            {all_transcriptions}
            
            INCONSISTENCIAS DETECTADAS:
            """
            
            # Call Bedrock with Claude model
            response = bedrock_runtime.invoke_model(
                modelId="anthropic.claude-v2",  # Using Claude v2
                body=json.dumps({
                    "prompt": prompt,
                    "max_tokens_to_sample": 4000,
                    "temperature": 0.2,
                    "top_p": 0.9,
                })
            )
            
            # Parse response
            response_body = json.loads(response["body"].read())
            analysis_text = response_body.get("completion", "").strip()
            
            # Parse the analysis text into structured inconsistencies
            parsed_inconsistencies = parse_inconsistencies_from_text(analysis_text, audio_ids)
            inconsistencies.extend(parsed_inconsistencies)
            
        except Exception as bedrock_error:
            logger.error(f"Error using Bedrock for inconsistency detection: {str(bedrock_error)}")
            # Fall back to simpler pairwise comparison
            inconsistencies = fallback_inconsistency_detection(transcription_contents)
        
        return inconsistencies
    except Exception as e:
        logger.error(f"Error detecting inconsistencies: {str(e)}")
        raise


def parse_inconsistencies_from_text(analysis_text, audio_ids):
    """
    Parse inconsistencies from the Bedrock model's text output.

    Args:
        analysis_text (str): Text output from Bedrock
        audio_ids (list): List of audio IDs

    Returns:
        list: Structured inconsistencies
    """
    inconsistencies = []
    
    # Split by numbered items (1., 2., etc.)
    import re
    items = re.split(r'\n\d+\.', analysis_text)
    
    # Skip the first item if it's just an introduction
    if items and not re.search(r'inconsistencia|contradicción', items[0], re.IGNORECASE):
        items = items[1:]
    
    for item in items:
        if not item.strip():
            continue
            
        # Try to extract structured information
        inconsistency = {
            "description": item.strip(),
            "involved_audio_ids": [],
            "severity": "MEDIUM"  # Default severity
        }
        
        # Try to find audio IDs mentioned in the text
        for audio_id in audio_ids:
            if audio_id in item:
                inconsistency["involved_audio_ids"].append(audio_id)
        
        # Try to determine severity
        if re.search(r'gravedad.*alta|alta.*gravedad', item, re.IGNORECASE):
            inconsistency["severity"] = "HIGH"
        elif re.search(r'gravedad.*baja|baja.*gravedad', item, re.IGNORECASE):
            inconsistency["severity"] = "LOW"
        
        inconsistencies.append(inconsistency)
    
    return inconsistencies


def fallback_inconsistency_detection(transcription_contents):
    """
    Fallback method for inconsistency detection when Bedrock is unavailable.

    Args:
        transcription_contents (dict): Dictionary of transcription contents by audio ID

    Returns:
        list: List of detected inconsistencies
    """
    # This is a very simplified approach - in a real system, you would use NLP techniques
    inconsistencies = []
    audio_ids = list(transcription_contents.keys())
    
    # Look for common keywords that might indicate important facts
    keywords = ["hora", "lugar", "vio", "escuchó", "testigo", "arma", "víctima", "sospechoso"]
    
    # For each pair of transcriptions
    for i in range(len(audio_ids)):
        for j in range(i+1, len(audio_ids)):
            audio_id1 = audio_ids[i]
            audio_id2 = audio_ids[j]
            
            content1 = transcription_contents[audio_id1]
            content2 = transcription_contents[audio_id2]
            
            # Very simple check: look for sentences with keywords in both transcriptions
            for keyword in keywords:
                sentences1 = [s for s in content1.split('.') if keyword in s.lower()]
                sentences2 = [s for s in content2.split('.') if keyword in s.lower()]
                
                # If both mention the keyword, flag as potential inconsistency
                if sentences1 and sentences2:
                    inconsistencies.append({
                        "description": f"Posible inconsistencia sobre '{keyword}' entre las entrevistas {audio_id1} y {audio_id2}",
                        "involved_audio_ids": [audio_id1, audio_id2],
                        "severity": "MEDIUM",
                        "details": {
                            audio_id1: sentences1[0].strip(),
                            audio_id2: sentences2[0].strip()
                        }
                    })
    
    return inconsistencies


def save_inconsistencies(current_audio_id, inconsistencies, transcriptions):
    """
    Save the inconsistency analysis results to S3 and DynamoDB.

    Args:
        current_audio_id (str): Current audio ID
        inconsistencies (list): List of detected inconsistencies
        transcriptions (list): List of all transcriptions

    Returns:
        dict: Saved analysis details
    """
    try:
        # Create result object with metadata
        result = {
            "timestamp": int(time.time()),
            "analyzed_interviews": [t.get("audioId") for t in transcriptions],
            "total_interviews": len(transcriptions),
            "total_inconsistencies": len(inconsistencies),
            "inconsistencies": inconsistencies
        }

        # Save to S3
        inconsistency_key = f"analysis/inconsistencies/report_{int(time.time())}.json"
        s3_client.put_object(
            Bucket=RESULTS_BUCKET,
            Key=inconsistency_key,
            Body=json.dumps(result, indent=2),
            ContentType="application/json"
        )

        # Save to DynamoDB
        table = dynamodb.Table(ANALYSIS_TABLE)
        item = {
            "audioId": "global_inconsistency_report",  # Using a special ID for the global report
            "reportS3Key": inconsistency_key,
            "totalInconsistencies": len(inconsistencies),
            "analyzedInterviews": len(transcriptions),
            "status": "COMPLETED",
            "timestamp": int(time.time()),
            "type": "inconsistency",
            "triggeredBy": current_audio_id
        }
        table.put_item(Item=item)

        return {
            "reportS3Key": inconsistency_key,
            "totalInconsistencies": len(inconsistencies),
            "analyzedInterviews": len(transcriptions),
            "status": "COMPLETED"
        }

    except Exception as e:
        logger.error(f"Error saving inconsistency analysis: {str(e)}")
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