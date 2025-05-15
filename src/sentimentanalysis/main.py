"""
Sentiment Analysis Lambda Function
This function analyzes the sentiment in different parts of the audio transcription
to help determine if the interviewee might be lying based on tone variations.
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
transcribe_client = boto3.client("transcribe")

# Environment variables
RESULTS_BUCKET = os.environ["RESULTS_BUCKET"]
TRANSCRIPTION_TABLE = os.environ["TRANSCRIPTION_TABLE"]
ANALYSIS_TABLE = os.environ["ANALYSIS_TABLE"]


def handler(event, context):
    """
    Lambda handler function that analyzes sentiment in audio transcription.

    Args:
        event (dict): Event data containing audioId and transcription details
        context (object): Lambda context

    Returns:
        dict: Response with sentiment analysis status and details
    """
    audio_id = event.get("audioId", "unknown")

    try:
        logger.info(f"Processing sentiment analysis request: {json.dumps(event)}")

        # Get transcription data
        transcription = event.get("transcription", {})
        script_s3_key = transcription.get("scriptS3Key")

        if not script_s3_key:
            raise KeyError("Missing required parameter: scriptS3Key")

        # Get the transcription script from S3
        script_content = get_script_from_s3(script_s3_key)

        # Parse the script into segments by speaker
        segments = parse_script_by_speaker(script_content)

        # Analyze sentiment for each segment
        sentiment_results = analyze_segments_sentiment(segments)

        # Analyze tone variations and detect potential deception
        deception_analysis = analyze_deception(sentiment_results)

        # Save results
        result = save_sentiment_analysis(audio_id, sentiment_results, deception_analysis)

        logger.info(f"Sentiment analysis completed successfully for audio: {audio_id}")
        return {
            "audioId": audio_id,
            "sentimentAnalysis": result,
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
            audio_id, e, "FAILED", "Error analyzing sentiment"
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


def parse_script_by_speaker(script_content):
    """
    Parse the script into segments by speaker.

    Args:
        script_content (str): Script content

    Returns:
        dict: Dictionary of segments by speaker
    """
    try:
        segments = {}
        lines = script_content.strip().split('\n')
        
        for line in lines:
            # Parse timestamp and speaker from line
            # Format: [MM:SS] Speaker: Text
            if not line or ']' not in line or ':' not in line:
                continue
                
            timestamp_end = line.find(']')
            timestamp = line[1:timestamp_end].strip()
            
            rest = line[timestamp_end+1:].strip()
            speaker_end = rest.find(':')
            
            if speaker_end == -1:
                continue
                
            speaker = rest[:speaker_end].strip()
            text = rest[speaker_end+1:].strip()
            
            # Add to segments
            if speaker not in segments:
                segments[speaker] = []
                
            segments[speaker].append({
                "timestamp": timestamp,
                "text": text
            })
        
        return segments
    except Exception as e:
        logger.error(f"Error parsing script: {str(e)}")
        raise


def analyze_segments_sentiment(segments):
    """
    Analyze sentiment for each segment.

    Args:
        segments (dict): Dictionary of segments by speaker

    Returns:
        dict: Sentiment analysis results by speaker
    """
    try:
        sentiment_results = {}
        
        for speaker, utterances in segments.items():
            speaker_sentiments = []
            
            # Group utterances into chunks for batch processing
            # (to avoid too many API calls)
            chunk_size = 5
            for i in range(0, len(utterances), chunk_size):
                chunk = utterances[i:i+chunk_size]
                chunk_text = " ".join([u["text"] for u in chunk])
                
                # Skip empty chunks
                if not chunk_text.strip():
                    continue
                
                # Analyze sentiment
                response = comprehend_client.detect_sentiment(
                    Text=chunk_text,
                    LanguageCode="es"  # Assuming Spanish based on the request
                )
                
                # Get sentiment and confidence scores
                sentiment = response["Sentiment"]
                sentiment_scores = response["SentimentScore"]
                
                # Add to results
                speaker_sentiments.append({
                    "timestamp_range": f"{chunk[0]['timestamp']} - {chunk[-1]['timestamp']}",
                    "text": chunk_text,
                    "sentiment": sentiment,
                    "scores": {
                        "positive": sentiment_scores["Positive"],
                        "negative": sentiment_scores["Negative"],
                        "neutral": sentiment_scores["Neutral"],
                        "mixed": sentiment_scores["Mixed"]
                    }
                })
            
            sentiment_results[speaker] = speaker_sentiments
        
        return sentiment_results
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {str(e)}")
        raise


def analyze_deception(sentiment_results):
    """
    Analyze tone variations and detect potential deception.

    Args:
        sentiment_results (dict): Sentiment analysis results by speaker

    Returns:
        dict: Deception analysis results
    """
    try:
        deception_analysis = {}
        
        for speaker, sentiments in sentiment_results.items():
            # Skip if not enough data
            if len(sentiments) < 2:
                deception_analysis[speaker] = {
                    "deception_likelihood": "INSUFFICIENT_DATA",
                    "confidence": 0.0,
                    "explanation": "Insufficient data to analyze deception"
                }
                continue
            
            # Calculate sentiment variations
            sentiment_changes = []
            mixed_sentiments = 0
            negative_sentiments = 0
            
            for i in range(len(sentiments)):
                sentiment = sentiments[i]
                
                # Count mixed and negative sentiments
                if sentiment["sentiment"] == "MIXED":
                    mixed_sentiments += 1
                elif sentiment["sentiment"] == "NEGATIVE":
                    negative_sentiments += 1
                
                # Calculate sentiment changes between consecutive segments
                if i > 0:
                    prev_sentiment = sentiments[i-1]
                    change = {
                        "from_timestamp": prev_sentiment["timestamp_range"],
                        "to_timestamp": sentiment["timestamp_range"],
                        "sentiment_change": abs(sentiment["scores"]["positive"] - prev_sentiment["scores"]["positive"]) +
                                           abs(sentiment["scores"]["negative"] - prev_sentiment["scores"]["negative"])
                    }
                    sentiment_changes.append(change)
            
            # Calculate metrics
            total_segments = len(sentiments)
            mixed_ratio = mixed_sentiments / total_segments if total_segments > 0 else 0
            negative_ratio = negative_sentiments / total_segments if total_segments > 0 else 0
            
            # Calculate average sentiment change
            avg_sentiment_change = sum(c["sentiment_change"] for c in sentiment_changes) / len(sentiment_changes) if sentiment_changes else 0
            
            # Determine deception likelihood
            # This is a simplified model - in a real system, you would use more sophisticated analysis
            deception_score = (mixed_ratio * 0.4) + (negative_ratio * 0.3) + (avg_sentiment_change * 0.3)
            
            if deception_score < 0.2:
                likelihood = "LOW"
                confidence = 0.7
                explanation = "Consistent sentiment patterns suggest truthfulness"
            elif deception_score < 0.4:
                likelihood = "MEDIUM_LOW"
                confidence = 0.6
                explanation = "Some minor inconsistencies in sentiment patterns"
            elif deception_score < 0.6:
                likelihood = "MEDIUM"
                confidence = 0.5
                explanation = "Moderate sentiment variations detected"
            elif deception_score < 0.8:
                likelihood = "MEDIUM_HIGH"
                confidence = 0.6
                explanation = "Significant sentiment variations and mixed emotions detected"
            else:
                likelihood = "HIGH"
                confidence = 0.7
                explanation = "Strong indicators of deception in sentiment patterns"
            
            # Add significant sentiment changes
            significant_changes = [c for c in sentiment_changes if c["sentiment_change"] > 0.5]
            
            deception_analysis[speaker] = {
                "deception_likelihood": likelihood,
                "confidence": confidence,
                "explanation": explanation,
                "metrics": {
                    "mixed_sentiment_ratio": mixed_ratio,
                    "negative_sentiment_ratio": negative_ratio,
                    "average_sentiment_change": avg_sentiment_change
                },
                "significant_changes": significant_changes
            }
        
        return deception_analysis
    except Exception as e:
        logger.error(f"Error analyzing deception: {str(e)}")
        raise


def save_sentiment_analysis(audio_id, sentiment_results, deception_analysis):
    """
    Save the sentiment analysis results to S3 and DynamoDB.

    Args:
        audio_id (str): Audio ID
        sentiment_results (dict): Sentiment analysis results
        deception_analysis (dict): Deception analysis results

    Returns:
        dict: Saved analysis details
    """
    try:
        # Create result object
        result = {
            "sentimentAnalysis": sentiment_results,
            "deceptionAnalysis": deception_analysis
        }

        # Save to S3
        sentiment_key = f"analysis/{audio_id}/sentiment_analysis.json"
        s3_client.put_object(
            Bucket=RESULTS_BUCKET,
            Key=sentiment_key,
            Body=json.dumps(result, indent=2),
            ContentType="application/json"
        )

        # Save to DynamoDB
        table = dynamodb.Table(ANALYSIS_TABLE)
        
        # Create a simplified version for DynamoDB (avoiding nested structures)
        simplified_result = {
            "audioId": audio_id,
            "sentimentS3Key": sentiment_key,
            "status": "COMPLETED",
            "timestamp": int(time.time()),
            "type": "sentiment"
        }
        
        # Add deception likelihood for each speaker
        for speaker, analysis in deception_analysis.items():
            simplified_result[f"deception_{speaker}"] = analysis["deception_likelihood"]
            simplified_result[f"confidence_{speaker}"] = analysis["confidence"]
        
        table.put_item(Item=simplified_result)

        return {
            "audioId": audio_id,
            "sentimentS3Key": sentiment_key,
            "deceptionAnalysis": {
                speaker: {
                    "likelihood": analysis["deception_likelihood"],
                    "confidence": analysis["confidence"]
                } for speaker, analysis in deception_analysis.items()
            },
            "status": "COMPLETED"
        }

    except Exception as e:
        logger.error(f"Error saving sentiment analysis: {str(e)}")
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