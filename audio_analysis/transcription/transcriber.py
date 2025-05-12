"""
Audio transcription module that converts speech to text with timestamps.
"""

import logging
import os
from typing import Dict, List, Tuple, Any

import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import split_on_silence

from audio_analysis import config

logger = logging.getLogger(__name__)


class AudioTranscriber:
    """
    Class for transcribing audio files to text with timestamps.
    """
    
    def __init__(self, language: str = config.LANGUAGE):
        """
        Initialize the transcriber.
        
        Args:
            language: Language code for transcription (default: from config)
        """
        self.language = language
        self.recognizer = sr.Recognizer()
        logger.debug(f"Initialized AudioTranscriber with language: {language}")
    
    def _preprocess_audio(self, audio_path: str) -> AudioSegment:
        """
        Preprocess audio file for better transcription.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Preprocessed AudioSegment
        """
        logger.debug(f"Preprocessing audio: {audio_path}")
        
        # Load audio file
        audio = AudioSegment.from_file(audio_path)
        
        # Convert to mono if stereo
        if audio.channels > 1:
            audio = audio.set_channels(config.CHANNELS)
        
        # Normalize audio
        audio = audio.normalize()
        
        return audio
    
    def _split_audio(self, audio: AudioSegment) -> List[Tuple[AudioSegment, float]]:
        """
        Split audio into chunks based on silence.
        
        Args:
            audio: AudioSegment to split
            
        Returns:
            List of tuples containing (audio_chunk, start_time_in_seconds)
        """
        logger.debug("Splitting audio into chunks")
        
        # Split audio on silence
        chunks = split_on_silence(
            audio,
            min_silence_len=int(config.MIN_SILENCE_DURATION * 1000),
            silence_thresh=audio.dBFS - 16,
            keep_silence=500  # Keep 500ms of silence at the beginning and end
        )
        
        # If no chunks were found, use the whole audio
        if not chunks:
            logger.warning("No silence detected, using entire audio as one chunk")
            chunks = [audio]
        
        # Calculate start time for each chunk
        result = []
        current_pos = 0
        
        for chunk in chunks:
            result.append((chunk, current_pos / 1000.0))  # Convert to seconds
            current_pos += len(chunk)
        
        logger.debug(f"Split audio into {len(result)} chunks")
        return result
    
    def _transcribe_chunk(self, chunk: AudioSegment, start_time: float) -> Dict[str, Any]:
        """
        Transcribe a single audio chunk.
        
        Args:
            chunk: Audio chunk to transcribe
            start_time: Start time of the chunk in seconds
            
        Returns:
            Dictionary with transcription and timing information
        """
        # Export chunk to a temporary WAV file
        temp_path = os.path.join(config.DEFAULT_TEMP_DIR, "temp_chunk.wav")
        chunk.export(temp_path, format="wav")
        
        # Transcribe the chunk
        with sr.AudioFile(temp_path) as source:
            audio_data = self.recognizer.record(source)
            try:
                text = self.recognizer.recognize_google(audio_data, language=self.language)
                end_time = start_time + len(chunk) / 1000.0
                
                # Format timestamps
                start_timestamp = self._format_timestamp(start_time)
                end_timestamp = self._format_timestamp(end_time)
                
                return {
                    "text": text,
                    "start_time": start_time,
                    "end_time": end_time,
                    "start_timestamp": start_timestamp,
                    "end_timestamp": end_timestamp
                }
            except sr.UnknownValueError:
                logger.debug(f"Could not understand audio at {start_time:.2f}s")
                return None
            except sr.RequestError as e:
                logger.error(f"Error with speech recognition service: {e}")
                return None
    
    def _format_timestamp(self, seconds: float) -> str:
        """
        Format seconds into a timestamp string.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp string
        """
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def transcribe(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        Transcribe an audio file with timestamps.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            List of dictionaries with transcribed text and timing information
        """
        logger.info(f"Transcribing audio file: {audio_path}")
        
        # Preprocess audio
        audio = self._preprocess_audio(audio_path)
        
        # Split audio into chunks
        chunks = self._split_audio(audio)
        
        # Transcribe each chunk
        transcriptions = []
        for chunk, start_time in chunks:
            result = self._transcribe_chunk(chunk, start_time)
            if result:
                transcriptions.append(result)
        
        logger.info(f"Transcription complete: {len(transcriptions)} segments")
        return transcriptions