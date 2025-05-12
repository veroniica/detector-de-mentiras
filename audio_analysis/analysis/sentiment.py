"""
Module for sentiment analysis and deception detection in audio interviews.
"""

import logging
import os
from typing import Dict, List, Any, Tuple

import numpy as np
import librosa
import torch
from transformers import pipeline
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from audio_analysis import config

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """
    Class for analyzing sentiment and detecting potential deception in interviews.
    """
    
    def __init__(self):
        """Initialize the sentiment analyzer."""
        # Text-based sentiment analysis
        self.vader = SentimentIntensityAnalyzer()
        
        # Audio-based emotion recognition
        try:
            self.emotion_classifier = pipeline(
                "audio-classification", 
                model="ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition"
            )
            logger.debug("Initialized audio emotion classifier")
        except Exception as e:
            logger.error(f"Failed to initialize audio emotion classifier: {e}")
            self.emotion_classifier = None
    
    def _analyze_text_sentiment(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of text using multiple methods.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with sentiment scores
        """
        # VADER sentiment analysis
        vader_scores = self.vader.polarity_scores(text)
        
        # TextBlob sentiment analysis
        blob = TextBlob(text)
        textblob_polarity = blob.sentiment.polarity
        textblob_subjectivity = blob.sentiment.subjectivity
        
        return {
            "compound": vader_scores["compound"],
            "positive": vader_scores["pos"],
            "negative": vader_scores["neg"],
            "neutral": vader_scores["neu"],
            "polarity": textblob_polarity,
            "subjectivity": textblob_subjectivity
        }
    
    def _analyze_audio_emotion(self, audio_path: str, start_time: float, end_time: float) -> Dict[str, Any]:
        """
        Analyze emotion in audio segment.
        
        Args:
            audio_path: Path to audio file
            start_time: Start time in seconds
            end_time: End time in seconds
            
        Returns:
            Dictionary with emotion analysis results
        """
        if not self.emotion_classifier:
            return {"error": "Audio emotion classifier not available"}
        
        try:
            # Load audio segment
            y, sr = librosa.load(
                audio_path, 
                offset=start_time, 
                duration=(end_time - start_time),
                sr=16000
            )
            
            # Save temporary file for the emotion classifier
            temp_path = os.path.join(config.DEFAULT_TEMP_DIR, "temp_segment.wav")
            librosa.output.write_wav(temp_path, y, sr)
            
            # Classify emotion
            emotion_result = self.emotion_classifier(temp_path)
            
            # Extract audio features for deception indicators
            # Higher pitch variation and speech rate can indicate stress/deception
            pitch = librosa.yin(y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'))
            pitch_std = np.std(pitch[pitch > 0])  # Pitch variation
            
            # Energy/volume features
            rms = librosa.feature.rms(y=y)[0]
            energy_mean = np.mean(rms)
            energy_std = np.std(rms)
            
            # Speech rate approximation (zero crossings)
            zero_crossings = librosa.feature.zero_crossing_rate(y)[0]
            speech_rate = np.mean(zero_crossings)
            
            return {
                "emotions": emotion_result,
                "acoustic_features": {
                    "pitch_variation": float(pitch_std),
                    "energy_mean": float(energy_mean),
                    "energy_std": float(energy_std),
                    "speech_rate": float(speech_rate)
                }
            }
        except Exception as e:
            logger.error(f"Error in audio emotion analysis: {e}")
            return {"error": str(e)}
    
    def _detect_potential_deception(self, text_sentiment: Dict[str, float], 
                                   audio_emotion: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect potential deception based on combined text and audio analysis.
        
        Args:
            text_sentiment: Text sentiment analysis results
            audio_emotion: Audio emotion analysis results
            
        Returns:
            Dictionary with deception indicators
        """
        deception_indicators = {}
        deception_score = 0.0
        confidence = 0.5  # Base confidence
        
        # Check for emotional inconsistency
        if "emotions" in audio_emotion and not "error" in audio_emotion:
            # Get top emotion
            top_emotion = audio_emotion["emotions"][0]["label"]
            
            # Negative sentiment but positive emotion or vice versa can indicate deception
            sentiment_emotion_mismatch = False
            if (text_sentiment["compound"] < -0.2 and top_emotion in ["happy", "calm"]) or \
               (text_sentiment["compound"] > 0.2 and top_emotion in ["angry", "sad", "fearful"]):
                sentiment_emotion_mismatch = True
                deception_score += 0.2
                confidence += 0.1
            
            deception_indicators["sentiment_emotion_mismatch"] = sentiment_emotion_mismatch
        
        # Check acoustic features if available
        if "acoustic_features" in audio_emotion:
            features = audio_emotion["acoustic_features"]
            
            # High pitch variation can indicate stress/deception
            high_pitch_variation = features["pitch_variation"] > 0.15
            if high_pitch_variation:
                deception_score += 0.15
                confidence += 0.05
            
            # High energy variation can indicate stress
            high_energy_variation = features["energy_std"] / features["energy_mean"] > 0.5
            if high_energy_variation:
                deception_score += 0.15
                confidence += 0.05
            
            # Unusual speech rate can indicate deception
            unusual_speech_rate = features["speech_rate"] > 0.12 or features["speech_rate"] < 0.04
            if unusual_speech_rate:
                deception_score += 0.1
                confidence += 0.05
            
            deception_indicators["high_pitch_variation"] = high_pitch_variation
            deception_indicators["high_energy_variation"] = high_energy_variation
            deception_indicators["unusual_speech_rate"] = unusual_speech_rate
        
        # Check text features
        high_subjectivity = text_sentiment["subjectivity"] > 0.8
        if high_subjectivity:
            deception_score += 0.1
            confidence += 0.05
        
        extreme_sentiment = abs(text_sentiment["compound"]) > 0.8
        if extreme_sentiment:
            deception_score += 0.1
            confidence += 0.05
        
        deception_indicators["high_subjectivity"] = high_subjectivity
        deception_indicators["extreme_sentiment"] = extreme_sentiment
        
        # Cap the scores
        deception_score = min(1.0, deception_score)
        confidence = min(0.9, confidence)
        
        return {
            "deception_score": deception_score,
            "confidence": confidence,
            "indicators": deception_indicators
        }
    
    def analyze(self, audio_path: str, transcript: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze sentiment and detect potential deception in the interview.
        
        Args:
            audio_path: Path to the audio file
            transcript: List of transcript segments with speaker information
            
        Returns:
            List of segments with sentiment and deception analysis
        """
        logger.info(f"Analyzing sentiment in: {audio_path}")
        
        results = []
        
        for segment in transcript:
            # Skip segments without text
            if "text" not in segment or not segment["text"]:
                continue
            
            # Analyze text sentiment
            text_sentiment = self._analyze_text_sentiment(segment["text"])
            
            # Analyze audio emotion
            audio_emotion = self._analyze_audio_emotion(
                audio_path, 
                segment["start_time"], 
                segment["end_time"]
            )
            
            # Detect potential deception
            deception_analysis = self._detect_potential_deception(text_sentiment, audio_emotion)
            
            # Combine results
            analysis = {
                "segment": {
                    "text": segment["text"],
                    "start_time": segment["start_time"],
                    "end_time": segment["end_time"],
                    "start_timestamp": segment["start_timestamp"],
                    "end_timestamp": segment["end_timestamp"],
                    "speaker": segment.get("speaker", "Unknown")
                },
                "sentiment": text_sentiment,
                "emotion": audio_emotion,
                "deception": deception_analysis
            }
            
            results.append(analysis)
        
        logger.info(f"Sentiment analysis complete: {len(results)} segments analyzed")
        return results