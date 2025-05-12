"""
Unit tests for the transcription module.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

import numpy as np

from audio_analysis.transcription.transcriber import AudioTranscriber
from audio_analysis.transcription.diarization import SpeakerDiarizer


class TestAudioTranscriber(unittest.TestCase):
    """Test cases for the AudioTranscriber class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.transcriber = AudioTranscriber(language='es')
    
    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.transcriber.language, 'es')
        self.assertIsNotNone(self.transcriber.recognizer)
    
    def test_format_timestamp(self):
        """Test timestamp formatting."""
        self.assertEqual(self.transcriber._format_timestamp(65.5), "01:05")
        self.assertEqual(self.transcriber._format_timestamp(3661), "61:01")
        self.assertEqual(self.transcriber._format_timestamp(0), "00:00")
    
    @patch('speech_recognition.Recognizer.recognize_google')
    @patch('speech_recognition.AudioFile')
    @patch('pydub.AudioSegment.from_file')
    def test_transcribe_chunk(self, mock_from_file, mock_audio_file, mock_recognize):
        """Test transcribing a single chunk."""
        # Mock the audio segment
        mock_chunk = MagicMock()
        mock_chunk.__len__.return_value = 5000  # 5 seconds in milliseconds
        
        # Mock the recognition result
        mock_recognize.return_value = "This is a test transcription"
        
        # Call the method
        result = self.transcriber._transcribe_chunk(mock_chunk, 10.0)
        
        # Verify the result
        self.assertEqual(result["text"], "This is a test transcription")
        self.assertEqual(result["start_time"], 10.0)
        self.assertEqual(result["end_time"], 15.0)
        self.assertEqual(result["start_timestamp"], "00:10")
        self.assertEqual(result["end_timestamp"], "00:15")
    
    @patch('audio_analysis.transcription.transcriber.AudioTranscriber._transcribe_chunk')
    @patch('audio_analysis.transcription.transcriber.AudioTranscriber._split_audio')
    @patch('audio_analysis.transcription.transcriber.AudioTranscriber._preprocess_audio')
    def test_transcribe(self, mock_preprocess, mock_split, mock_transcribe_chunk):
        """Test the full transcription process."""
        # Mock preprocessing
        mock_audio = MagicMock()
        mock_preprocess.return_value = mock_audio
        
        # Mock splitting
        chunk1 = MagicMock()
        chunk2 = MagicMock()
        mock_split.return_value = [(chunk1, 0.0), (chunk2, 5.0)]
        
        # Mock chunk transcription
        mock_transcribe_chunk.side_effect = [
            {
                "text": "First segment",
                "start_time": 0.0,
                "end_time": 5.0,
                "start_timestamp": "00:00",
                "end_timestamp": "00:05"
            },
            {
                "text": "Second segment",
                "start_time": 5.0,
                "end_time": 10.0,
                "start_timestamp": "00:05",
                "end_timestamp": "00:10"
            }
        ]
        
        # Call the method
        result = self.transcriber.transcribe("test.wav")
        
        # Verify the result
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["text"], "First segment")
        self.assertEqual(result[1]["text"], "Second segment")
        
        # Verify method calls
        mock_preprocess.assert_called_once_with("test.wav")
        mock_split.assert_called_once_with(mock_audio)
        self.assertEqual(mock_transcribe_chunk.call_count, 2)


class TestSpeakerDiarizer(unittest.TestCase):
    """Test cases for the SpeakerDiarizer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the pipeline to avoid actual model loading
        with patch('pyannote.audio.Pipeline.from_pretrained') as mock_pipeline:
            self.diarizer = SpeakerDiarizer()
            self.diarizer.pipeline = None  # Force basic segmentation for tests
    
    def test_basic_speaker_segmentation(self):
        """Test basic speaker segmentation."""
        # Create test transcript
        transcript = [
            {
                "text": "Hello, how are you?",
                "start_time": 0.0,
                "end_time": 2.0,
                "start_timestamp": "00:00",
                "end_timestamp": "00:02"
            },
            {
                "text": "I'm fine, thank you.",
                "start_time": 3.0,
                "end_time": 5.0,
                "start_timestamp": "00:03",
                "end_timestamp": "00:05"
            },
            {
                "text": "What about you?",
                "start_time": 6.0,
                "end_time": 7.0,
                "start_timestamp": "00:06",
                "end_timestamp": "00:07"
            }
        ]
        
        # Call the method
        result = self.diarizer._basic_speaker_segmentation(transcript)
        
        # Verify the result
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["speaker"], "Speaker_1")
        self.assertEqual(result[1]["speaker"], "Speaker_2")
        self.assertEqual(result[2]["speaker"], "Speaker_1")
    
    def test_diarize_with_basic_segmentation(self):
        """Test diarization with basic segmentation."""
        # Create test transcript
        transcript = [
            {
                "text": "Hello, how are you?",
                "start_time": 0.0,
                "end_time": 2.0,
                "start_timestamp": "00:00",
                "end_timestamp": "00:02"
            },
            {
                "text": "I'm fine, thank you.",
                "start_time": 3.0,
                "end_time": 5.0,
                "start_timestamp": "00:03",
                "end_timestamp": "00:05"
            }
        ]
        
        # Call the method
        result = self.diarizer.diarize("test.wav", transcript)
        
        # Verify the result
        self.assertEqual(len(result), 2)
        self.assertIn("speaker", result[0])
        self.assertIn("speaker", result[1])
        self.assertNotEqual(result[0]["speaker"], result[1]["speaker"])


if __name__ == '__main__':
    unittest.main()