"""
Utility functions for audio preprocessing.
"""

import logging
import os
from typing import Tuple

import numpy as np
import librosa
import soundfile as sf
from pydub import AudioSegment

from audio_analysis import config

logger = logging.getLogger(__name__)


def load_audio(audio_path: str) -> Tuple[np.ndarray, int]:
    """
    Load audio file with librosa.
    
    Args:
        audio_path: Path to the audio file
        
    Returns:
        Tuple of (audio_data, sample_rate)
    """
    logger.debug(f"Loading audio: {audio_path}")
    try:
        y, sr = librosa.load(audio_path, sr=config.SAMPLE_RATE)
        return y, sr
    except Exception as e:
        logger.error(f"Error loading audio file {audio_path}: {e}")
        raise


def convert_audio_format(audio_path: str, output_format: str = 'wav') -> str:
    """
    Convert audio to a different format if needed.
    
    Args:
        audio_path: Path to the audio file
        output_format: Target format (default: wav)
        
    Returns:
        Path to the converted audio file
    """
    if audio_path.lower().endswith(f'.{output_format.lower()}'):
        return audio_path
    
    logger.debug(f"Converting {audio_path} to {output_format}")
    
    try:
        # Create output path
        output_path = os.path.join(
            config.DEFAULT_TEMP_DIR,
            f"{os.path.splitext(os.path.basename(audio_path))[0]}.{output_format}"
        )
        
        # Load and export with pydub
        audio = AudioSegment.from_file(audio_path)
        audio.export(output_path, format=output_format)
        
        return output_path
    except Exception as e:
        logger.error(f"Error converting audio format: {e}")
        return audio_path  # Return original path if conversion fails


def denoise_audio(audio_data: np.ndarray, sr: int) -> np.ndarray:
    """
    Apply basic noise reduction to audio.
    
    Args:
        audio_data: Audio data as numpy array
        sr: Sample rate
        
    Returns:
        Denoised audio data
    """
    logger.debug("Applying noise reduction")
    
    try:
        # Simple noise reduction using spectral gating
        # Calculate noise profile from the first 1 second (assumed to be noise/silence)
        noise_sample = audio_data[:min(len(audio_data), sr)]
        
        # Compute noise spectrum
        noise_stft = librosa.stft(noise_sample, n_fft=config.FRAME_SIZE, hop_length=config.HOP_LENGTH)
        noise_power = np.mean(np.abs(noise_stft)**2, axis=1)
        
        # Compute signal STFT
        signal_stft = librosa.stft(audio_data, n_fft=config.FRAME_SIZE, hop_length=config.HOP_LENGTH)
        signal_power = np.abs(signal_stft)**2
        
        # Compute gain mask
        gain_mask = 1 - np.minimum(noise_power[:, np.newaxis] / signal_power, 1)
        gain_mask = np.sqrt(gain_mask)  # Convert power to amplitude
        
        # Apply mask
        denoised_stft = signal_stft * gain_mask
        
        # Inverse STFT
        denoised_audio = librosa.istft(denoised_stft, hop_length=config.HOP_LENGTH)
        
        return denoised_audio
    except Exception as e:
        logger.error(f"Error in noise reduction: {e}")
        return audio_data  # Return original audio if denoising fails


def normalize_audio(audio_data: np.ndarray) -> np.ndarray:
    """
    Normalize audio volume.
    
    Args:
        audio_data: Audio data as numpy array
        
    Returns:
        Normalized audio data
    """
    logger.debug("Normalizing audio volume")
    
    try:
        # Peak normalization
        max_amplitude = np.max(np.abs(audio_data))
        if max_amplitude > 0:
            normalized_audio = audio_data / max_amplitude * 0.9  # Leave some headroom
            return normalized_audio
        return audio_data
    except Exception as e:
        logger.error(f"Error in audio normalization: {e}")
        return audio_data


def preprocess_audio(audio_path: str) -> str:
    """
    Preprocess audio file for better transcription.
    
    Args:
        audio_path: Path to the audio file
        
    Returns:
        Path to the preprocessed audio file
    """
    logger.info(f"Preprocessing audio: {audio_path}")
    
    try:
        # Convert to WAV if needed
        wav_path = convert_audio_format(audio_path, 'wav')
        
        # Load audio
        audio_data, sr = load_audio(wav_path)
        
        # Apply preprocessing
        audio_data = denoise_audio(audio_data, sr)
        audio_data = normalize_audio(audio_data)
        
        # Save preprocessed audio
        output_path = os.path.join(
            config.DEFAULT_TEMP_DIR,
            f"preprocessed_{os.path.basename(wav_path)}"
        )
        sf.write(output_path, audio_data, sr)
        
        logger.info(f"Preprocessing complete: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error preprocessing audio: {e}")
        return audio_path  # Return original path if preprocessing fails