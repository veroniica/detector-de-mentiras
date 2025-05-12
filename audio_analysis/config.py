"""
Configuration settings for the Audio Interview Analysis System.
"""

import os
from pathlib import Path

# Default paths
DEFAULT_INPUT_DIR = os.environ.get('AUDIO_ANALYSIS_INPUT_DIR', './input')
DEFAULT_OUTPUT_DIR = os.environ.get('AUDIO_ANALYSIS_OUTPUT_DIR', './output')
DEFAULT_TEMP_DIR = os.environ.get('AUDIO_ANALYSIS_TEMP_DIR', './temp')

# Audio processing settings
SAMPLE_RATE = 16000
CHANNELS = 1
FRAME_SIZE = 1024
HOP_LENGTH = 512

# Transcription settings
LANGUAGE = 'es'  # Spanish for the interviews
MIN_SILENCE_DURATION = 0.5  # seconds
SPEAKER_MIN_ACTIVITY = 1.0  # seconds

# Analysis settings
SENTIMENT_WINDOW_SIZE = 10  # seconds
INCONSISTENCY_SIMILARITY_THRESHOLD = 0.7

# Output settings
TIMESTAMP_FORMAT = '%M:%S'  # Minutes:Seconds format

# Create necessary directories
def create_directories(input_dir=None, output_dir=None):
    """Create necessary directories if they don't exist."""
    dirs = [
        input_dir or DEFAULT_INPUT_DIR,
        output_dir or DEFAULT_OUTPUT_DIR,
        DEFAULT_TEMP_DIR
    ]
    
    for directory in dirs:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    return dirs