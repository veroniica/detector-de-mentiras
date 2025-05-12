"""
Sentiment Analysis Lambda Function

This function analyzes the transcription to detect emotions and potential deception.
It uses Amazon Comprehend for sentiment analysis and Amazon Bedrock for advanced analysis.
"""

import os
import json
import time
import boto3
import logging
import re

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
comprehend_client = boto3.client('comprehend')
bedrock_runtime = boto3.client('bedrock-runtime')
dynamodb = boto3.resource('dynamodb')

# Get environment variables
RESULTS_BUCKET = os.environ['RESULTS_BUCKET']
ANALYSIS_TABLE = os.environ['ANALYSIS_TABLE']

# Constants
MAX_SEGMENT_LENGTH = 5000  # Maximum length for Comprehend API
CLAUDE_MODEL_ID = "anthropic.claude-v2"  # Bedrock model ID

def get_transcription(event):
    """
    Get the transcription from S3.
    
    Args:
        event (dict): Event data
        
    Returns:
        tuple: Script content and raw transcription
    """
    try:
        audio_id = event['audioId']
        transcription = event.get('transcription', {})
        script_key = transcription.get('scriptS3Key', f"transcriptions/{audio_id}/script.txt")
        raw_key = f"transcriptions/{audio_id}/raw_transcription.json"
        
        # Get script
        script_response = s3_client.get_object(Bucket=RESULTS_BUCKET, Key=script_key)
        script_content = script_response['Body'].read().decode('utf-8')
        
        # Get raw transcription
        try:
            raw_response = s3_client.get_object(Bucket=RESULTS_BUCKET, Key=raw_key)
            raw_content = raw_response['Body'].read().decode('utf-8')
            raw_transcription = json.loads(raw_content)
        except Exception as e:
            logger.warning(f"Could not get raw transcription: {str(e)}")
            raw_transcription = {}
        
        return script_content, raw_transcription
    
    except Exception as e:
        logger.error(f"Error getting transcription: {str(e)}")
        raise

def parse_script(script_content):
    """
    Parse the script into segments by speaker.
    
    Args:
        script_content (str): Script content
        
    Returns:
        list: List of segments with speaker, text, and timestamp
    """
    try:
        segments = []
        pattern = r'\[(\d+:\d+)\] (.*?): (.*)'
        
        for line in script_content.split('\n'):
            match = re.match(pattern, line)
            if match:
                timestamp, speaker, text = match.groups()
                segments.append({
                    'timestamp': timestamp,
                    'speaker': speaker,
                    'text': text
                })
        
        return segments
    
    except Exception as e:
        logger.error(f"Error parsing script: {str(e)}")
        raise

def analyze_sentiment_by_speaker(segments):
    """
    Analyze sentiment for each speaker's segments.
    
    Args:
        segments (list): List of segments
        
    Returns:
        dict: Sentiment analysis by speaker
    """
    try:
        # Group segments by speaker
        speakers = {}
        for segment in segments:
            speaker = segment['speaker']
            if speaker not in speakers:
                speakers[speaker] = []
            speakers[speaker].append(segment)
        
        # Analyze sentiment for each speaker
        sentiment_by_speaker = {}
        for speaker, speaker_segments in speakers.items():
            # Combine text for each speaker, respecting API limits
            combined_text = ""
            segment_sentiments = []
            
            for segment in speaker_segments:
                text = segment['text']
                
                # If adding this segment would exceed the limit, analyze the current batch
                if len(combined_text) + len(text) > MAX_SEGMENT_LENGTH and combined_text:
                    response = comprehend_client.detect_sentiment(
                        Text=combined_text,
                        LanguageCode='es'  # Spanish language code, change as needed
                    )
                    segment_sentiments.append(response)
                    combined_text = text
                else:
                    combined_text += " " + text if combined_text else text
            
            # Analyze any remaining text
            if combined_text:
                response = comprehend_client.detect_sentiment(
                    Text=combined_text,
                    LanguageCode='es'  # Spanish language code, change as needed
                )
                segment_sentiments.append(response)
            
            # Aggregate sentiment scores
            sentiment_counts = {'POSITIVE': 0, 'NEGATIVE': 0, 'NEUTRAL': 0, 'MIXED': 0}
            sentiment_scores = {'Positive': 0, 'Negative': 0, 'Neutral': 0, 'Mixed': 0}
            total_segments = len(segment_sentiments)
            
            for sentiment in segment_sentiments:
                sentiment_type = sentiment.get('Sentiment', 'NEUTRAL')
                sentiment_counts[sentiment_type] += 1
                
                scores = sentiment.get('SentimentScore', {})
                sentiment_scores['Positive'] += scores.get('Positive', 0)
                sentiment_scores['Negative'] += scores.get('Negative', 0)
                sentiment_scores['Neutral'] += scores.get('Neutral', 0)
                sentiment_scores['Mixed'] += scores.get('Mixed', 0)
            
            # Calculate average scores
            if total_segments > 0:
                sentiment_scores = {k: v / total_segments for k, v in sentiment_scores.items()}
            
            # Determine dominant sentiment
            dominant_sentiment = max(sentiment_counts, key=sentiment_counts.get)
            
            sentiment_by_speaker[speaker] = {
                'dominantSentiment': dominant_sentiment,
                'sentimentCounts': sentiment_counts,
                'averageScores': sentiment_scores,
                'segmentCount': total_segments
            }
        
        return sentiment_by_speaker
    
    except Exception as e:
        logger.error(f"Error analyzing sentiment by speaker: {str(e)}")
        raise

def analyze_sentiment_by_segment(segments):
    """
    Analyze sentiment for each individual segment.
    
    Args:
        segments (list): List of segments
        
    Returns:
        list: Segments with sentiment analysis
    """
    try:
        segments_with_sentiment = []
        
        for segment in segments:
            text = segment['text']
            
            # Skip very short segments
            if len(text) < 5:
                segment['sentiment'] = 'NEUTRAL'
                segment['sentimentScore'] = {'Positive': 0, 'Negative': 0, 'Neutral': 1, 'Mixed': 0}
                segments_with_sentiment.append(segment)
                continue
            
            # Analyze sentiment
            response = comprehend_client.detect_sentiment(
                Text=text,
                LanguageCode='es'  # Spanish language code, change as needed
            )
            
            segment['sentiment'] = response.get('Sentiment', 'NEUTRAL')
            segment['sentimentScore'] = response.get('SentimentScore', {})
            segments_with_sentiment.append(segment)
        
        return segments_with_sentiment
    
    except Exception as e:
        logger.error(f"Error analyzing sentiment by segment: {str(e)}")
        raise

def detect_deception(audio_id, segments_with_sentiment, sentiment_by_speaker):
    """
    Use Amazon Bedrock to analyze potential deception.
    
    Args:
        audio_id (str): Audio ID
        segments_with_sentiment (list): Segments with sentiment analysis
        sentiment_by_speaker (dict): Sentiment analysis by speaker
        
    Returns:
        dict: Deception analysis
    """
    try:
        # Prepare data for analysis
        speakers_data = []
        for speaker, analysis in sentiment_by_speaker.items():
            speaker_segments = [s for s in segments_with_sentiment if s['speaker'] == speaker]
            speaker_text = "\n".join([f"{s['timestamp']}: {s['text']}" for s in speaker_segments])
            
            speakers_data.append({
                'speaker': speaker,
                'dominantSentiment': analysis['dominantSentiment'],
                'sentimentScores': analysis['averageScores'],
                'text': speaker_text[:1000]  # Limit text length
            })
        
        # Prepare prompt for Bedrock
        prompt = f"""
Human: You are a forensic psychologist analyzing interview transcripts for potential deception. 
I'll provide you with transcript segments and sentiment analysis for each speaker.
For each speaker, analyze their language patterns, sentiment shifts, and potential indicators of deception.

Here's the data:
{json.dumps(speakers_data, indent=2)}

For each speaker, please provide:
1. A deception probability score (0-100%)
2. Key indicators of potential deception (if any)
3. Justification for your assessment
4. Segments that contain potential contradictions or inconsistencies

Format your response as JSON with the following structure:
{{
  "speakers": [
    {{
      "speaker": "Speaker1",
      "deceptionProbability": 75,
      "indicators": ["inconsistent details", "sentiment shifts when discussing key events"],
      "justification": "The speaker shows significant emotional variation...",
      "suspiciousSegments": ["timestamp: suspicious text"]
    }}
  ],
  "overallAssessment": "Brief overall assessment of all speakers"
}}