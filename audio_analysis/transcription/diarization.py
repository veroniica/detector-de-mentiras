"""
Speaker diarization module for identifying different speakers in audio.
"""

import logging
import os
from typing import Dict, List, Any, Tuple

import numpy as np
import torch
from pyannote.audio import Pipeline
from pyannote.core import Segment

from audio_analysis import config

logger = logging.getLogger(__name__)


class SpeakerDiarizer:
    """
    Class for identifying and separating different speakers in audio.
    """
    
    def __init__(self):
        """Initialize the speaker diarizer."""
        try:
            # Initialize the pyannote.audio diarization pipeline
            # Note: This requires authentication with HuggingFace
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization",
                use_auth_token=os.environ.get("HF_TOKEN")
            )
            
            # Move to GPU if available
            if torch.cuda.is_available():
                self.pipeline = self.pipeline.to(torch.device("cuda"))
                
            logger.debug("Initialized SpeakerDiarizer with pyannote.audio")
        except Exception as e:
            logger.error(f"Failed to initialize diarization pipeline: {e}")
            logger.warning("Falling back to basic speaker segmentation")
            self.pipeline = None
    
    def _map_speakers_to_segments(self, diarization, transcription: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Map identified speakers to transcription segments.
        
        Args:
            diarization: Diarization result from pyannote.audio
            transcription: List of transcription segments
            
        Returns:
            Transcription with speaker information added
        """
        result = []
        
        # Create a mapping of speaker IDs to more readable names
        speakers = {}
        for segment, _, speaker in diarization.itertracks(yield_label=True):
            if speaker not in speakers:
                speakers[speaker] = f"Speaker_{len(speakers) + 1}"
        
        # Map speakers to transcription segments
        for segment in transcription:
            start_time = segment["start_time"]
            end_time = segment["end_time"]
            
            # Find the dominant speaker for this segment
            speaker_times = {}
            for track, _, speaker in diarization.itertracks(yield_label=True):
                # Check for overlap between diarization segment and transcription segment
                overlap_start = max(track.start, start_time)
                overlap_end = min(track.end, end_time)
                
                if overlap_end > overlap_start:
                    overlap_duration = overlap_end - overlap_start
                    if speaker not in speaker_times:
                        speaker_times[speaker] = 0
                    speaker_times[speaker] += overlap_duration
            
            # Assign the speaker with the most speaking time in this segment
            if speaker_times:
                dominant_speaker = max(speaker_times, key=speaker_times.get)
                segment["speaker"] = speakers[dominant_speaker]
            else:
                segment["speaker"] = "Unknown"
            
            result.append(segment)
        
        return result
    
    def _basic_speaker_segmentation(self, transcription: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Basic speaker segmentation based on timing when pyannote is not available.
        
        Args:
            transcription: List of transcription segments
            
        Returns:
            Transcription with estimated speaker information
        """
        result = []
        
        # Sort segments by start time
        sorted_segments = sorted(transcription, key=lambda x: x["start_time"])
        
        # Initialize with two speakers alternating
        current_speaker = 1
        last_end_time = 0
        
        for segment in sorted_segments:
            # If there's a significant gap, might be a new speaker
            if segment["start_time"] - last_end_time > config.SPEAKER_MIN_ACTIVITY:
                current_speaker = 3 - current_speaker  # Toggle between 1 and 2
            
            segment["speaker"] = f"Speaker_{current_speaker}"
            result.append(segment)
            last_end_time = segment["end_time"]
        
        return result
    
    def diarize(self, audio_path: str, transcription: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify speakers in the audio and map them to transcription segments.
        
        Args:
            audio_path: Path to the audio file
            transcription: List of transcription segments
            
        Returns:
            Transcription with speaker information added
        """
        logger.info(f"Diarizing speakers in: {audio_path}")
        
        if not transcription:
            logger.warning("No transcription provided for diarization")
            return []
        
        try:
            if self.pipeline:
                # Use pyannote.audio for diarization
                diarization = self.pipeline(audio_path)
                return self._map_speakers_to_segments(diarization, transcription)
            else:
                # Fall back to basic speaker segmentation
                logger.warning("Using basic speaker segmentation")
                return self._basic_speaker_segmentation(transcription)
        except Exception as e:
            logger.error(f"Error during diarization: {e}")
            logger.warning("Falling back to basic speaker segmentation")
            return self._basic_speaker_segmentation(transcription)