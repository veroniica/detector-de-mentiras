"""
Unit tests for the analysis module.
"""

import unittest
from unittest.mock import patch, MagicMock

import numpy as np

from audio_analysis.analysis.summarizer import InterviewSummarizer
from audio_analysis.analysis.sentiment import SentimentAnalyzer
from audio_analysis.analysis.inconsistency import InconsistencyDetector


class TestInterviewSummarizer(unittest.TestCase):
    """Test cases for the InterviewSummarizer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the transformer pipeline to avoid actual model loading
        with patch('transformers.pipeline') as mock_pipeline:
            self.summarizer = InterviewSummarizer(language='es')
            self.summarizer.summarizer = None  # Avoid actual model inference
    
    def test_extract_text_from_transcript(self):
        """Test extracting text from transcript."""
        transcript = [
            {"text": "Hello, ", "speaker": "Speaker_1"},
            {"text": "how are you?", "speaker": "Speaker_1"},
            {"text": "I'm fine, thank you.", "speaker": "Speaker_2"}
        ]
        
        result = self.summarizer._extract_text_from_transcript(transcript)
        self.assertEqual(result, "Hello, how are you? I'm fine, thank you.")
    
    def test_extract_main_ideas(self):
        """Test extracting main ideas."""
        text = "This is the first sentence. This is the second sentence. " \
               "This is the third sentence. This is the fourth sentence."
        
        result = self.summarizer._extract_main_ideas(text)
        
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        self.assertTrue(all(isinstance(idea, str) for idea in result))
    
    def test_sentence_similarity(self):
        """Test sentence similarity calculation."""
        sent1 = "This is a test sentence."
        sent2 = "This is another test sentence."
        sent3 = "Something completely different."
        
        sim1 = self.summarizer._sentence_similarity(sent1, sent2)
        sim2 = self.summarizer._sentence_similarity(sent1, sent3)
        
        self.assertGreater(sim1, sim2)  # First pair should be more similar
    
    def test_summarize(self):
        """Test the full summarization process."""
        transcript = [
            {"text": "This is a test sentence.", "speaker": "Speaker_1"},
            {"text": "This is another test sentence.", "speaker": "Speaker_1"},
            {"text": "Something completely different.", "speaker": "Speaker_2"}
        ]
        
        # Mock the abstractive summarization
        self.summarizer._generate_abstractive_summary = MagicMock(
            return_value="This is a mock summary."
        )
        
        result = self.summarizer.summarize(transcript)
        
        self.assertIn("summary", result)
        self.assertIn("main_ideas", result)
        self.assertEqual(result["summary"], "This is a mock summary.")
        self.assertIsInstance(result["main_ideas"], list)


class TestSentimentAnalyzer(unittest.TestCase):
    """Test cases for the SentimentAnalyzer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the emotion classifier to avoid actual model loading
        with patch('transformers.pipeline') as mock_pipeline:
            self.analyzer = SentimentAnalyzer()
            self.analyzer.emotion_classifier = None  # Avoid actual model inference
    
    def test_analyze_text_sentiment(self):
        """Test text sentiment analysis."""
        # Test positive text
        positive_result = self.analyzer._analyze_text_sentiment("I love this! It's amazing.")
        self.assertGreater(positive_result["compound"], 0)
        self.assertGreater(positive_result["positive"], positive_result["negative"])
        
        # Test negative text
        negative_result = self.analyzer._analyze_text_sentiment("I hate this. It's terrible.")
        self.assertLess(negative_result["compound"], 0)
        self.assertGreater(negative_result["negative"], negative_result["positive"])
    
    def test_detect_potential_deception(self):
        """Test deception detection."""
        # Test case with deception indicators
        text_sentiment = {
            "compound": -0.5,
            "positive": 0.1,
            "negative": 0.6,
            "neutral": 0.3,
            "polarity": -0.4,
            "subjectivity": 0.9
        }
        
        audio_emotion = {
            "emotions": [{"label": "happy", "score": 0.8}],
            "acoustic_features": {
                "pitch_variation": 0.2,
                "energy_mean": 0.5,
                "energy_std": 0.3,
                "speech_rate": 0.15
            }
        }
        
        result = self.analyzer._detect_potential_deception(text_sentiment, audio_emotion)
        
        self.assertIn("deception_score", result)
        self.assertIn("confidence", result)
        self.assertIn("indicators", result)
        self.assertGreater(result["deception_score"], 0.3)  # Should detect some deception
    
    def test_analyze(self):
        """Test the full sentiment analysis process."""
        # Mock audio_emotion analysis to avoid actual audio processing
        self.analyzer._analyze_audio_emotion = MagicMock(
            return_value={
                "emotions": [{"label": "neutral", "score": 0.7}],
                "acoustic_features": {
                    "pitch_variation": 0.1,
                    "energy_mean": 0.5,
                    "energy_std": 0.2,
                    "speech_rate": 0.1
                }
            }
        )
        
        transcript = [
            {
                "text": "This is a test sentence.",
                "speaker": "Speaker_1",
                "start_time": 0.0,
                "end_time": 2.0,
                "start_timestamp": "00:00",
                "end_timestamp": "00:02"
            }
        ]
        
        result = self.analyzer.analyze("test.wav", transcript)
        
        self.assertEqual(len(result), 1)
        self.assertIn("segment", result[0])
        self.assertIn("sentiment", result[0])
        self.assertIn("emotion", result[0])
        self.assertIn("deception", result[0])


class TestInconsistencyDetector(unittest.TestCase):
    """Test cases for the InconsistencyDetector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = InconsistencyDetector(language='es')
    
    def test_extract_statements_by_speaker(self):
        """Test extracting statements by speaker."""
        transcript = [
            {
                "text": "I was at home all day.",
                "speaker": "Speaker_1",
                "start_time": 0.0,
                "end_time": 2.0,
                "start_timestamp": "00:00",
                "end_timestamp": "00:02"
            },
            {
                "text": "I saw him at the store.",
                "speaker": "Speaker_2",
                "start_time": 3.0,
                "end_time": 5.0,
                "start_timestamp": "00:03",
                "end_timestamp": "00:05"
            }
        ]
        
        result = self.detector._extract_statements_by_speaker(transcript)
        
        self.assertIn("Speaker_1", result)
        self.assertIn("Speaker_2", result)
        self.assertEqual(len(result["Speaker_1"]), 1)
        self.assertEqual(len(result["Speaker_2"]), 1)
        self.assertEqual(result["Speaker_1"][0]["text"], "I was at home all day.")
    
    def test_find_similar_statements_simple(self):
        """Test finding similar statements with the simple approach."""
        statements = [
            {"text": "I was at home all day yesterday."},
            {"text": "I stayed at home the entire day yesterday."},
            {"text": "I went to the store in the morning."}
        ]
        
        result = self.detector._find_similar_statements_simple(statements)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)  # Should find one similar pair
        self.assertEqual(result[0][0], 0)
        self.assertEqual(result[0][1], 1)
        self.assertGreater(result[0][2], 0.3)  # Should have reasonable similarity
    
    def test_detect_contradictions(self):
        """Test detecting contradictions."""
        similar_statements = [
            (
                {"text": "I was at home all day."},
                {"text": "I was not at home all day."},
                0.8
            ),
            (
                {"text": "I saw him at the store."},
                {"text": "I also saw him at the store."},
                0.9
            )
        ]
        
        result = self.detector._detect_contradictions(similar_statements)
        
        self.assertEqual(len(result), 1)  # Should find one contradiction
        self.assertEqual(result[0]["contradiction_type"], "negation")
    
    def test_detect_inconsistencies(self):
        """Test the full inconsistency detection process."""
        transcriptions = {
            "interview1": [
                {
                    "text": "I was at home all day.",
                    "speaker": "Suspect",
                    "start_time": 0.0,
                    "end_time": 2.0,
                    "start_timestamp": "00:00",
                    "end_timestamp": "00:02"
                }
            ],
            "interview2": [
                {
                    "text": "I was not at home yesterday.",
                    "speaker": "Suspect",
                    "start_time": 0.0,
                    "end_time": 2.0,
                    "start_timestamp": "00:00",
                    "end_timestamp": "00:02"
                }
            ]
        }
        
        # Mock the find_similar_statements method to ensure we get a result
        self.detector._find_similar_statements = MagicMock(
            return_value=[(0, 0, 0.8)]
        )
        
        result = self.detector.detect_inconsistencies(transcriptions)
        
        self.assertIn("total_inconsistencies", result)
        self.assertIn("contradictions", result)
        self.assertIn("similar_statements", result)


if __name__ == '__main__':
    unittest.main()