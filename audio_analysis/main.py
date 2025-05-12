"""
Main entry point for the Audio Interview Analysis System.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

from audio_analysis import config
from audio_analysis.transcription.transcriber import AudioTranscriber
from audio_analysis.transcription.diarization import SpeakerDiarizer
from audio_analysis.analysis.summarizer import InterviewSummarizer
from audio_analysis.analysis.sentiment import SentimentAnalyzer
from audio_analysis.analysis.inconsistency import InconsistencyDetector
from audio_analysis.utils.output_formatter import OutputFormatter
from audio_analysis.utils.s3_handler import S3Handler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def process_audio_files(input_dir: str, output_dir: str) -> Dict[str, Any]:
    """
    Process all audio files in the input directory.
    
    Args:
        input_dir: Directory containing audio files
        output_dir: Directory to save output files
        
    Returns:
        Dictionary with processing results
    """
    # Get all audio files
    audio_files = [
        f for f in Path(input_dir).glob('**/*') 
        if f.is_file() and f.suffix.lower() in ('.wav', '.mp3', '.m4a', '.flac')
    ]
    
    if not audio_files:
        logger.warning(f"No audio files found in {input_dir}")
        return {}
    
    logger.info(f"Found {len(audio_files)} audio files to process")
    
    # Initialize components
    transcriber = AudioTranscriber()
    diarizer = SpeakerDiarizer()
    summarizer = InterviewSummarizer()
    sentiment_analyzer = SentimentAnalyzer()
    formatter = OutputFormatter(output_dir)
    
    # Process each audio file
    results = {}
    transcriptions = {}
    
    for audio_file in audio_files:
        file_id = audio_file.stem
        logger.info(f"Processing {file_id}")
        
        # Step 1: Transcribe audio
        logger.info(f"Transcribing {file_id}")
        transcript = transcriber.transcribe(str(audio_file))
        
        # Step 2: Identify speakers
        logger.info(f"Identifying speakers in {file_id}")
        diarized_transcript = diarizer.diarize(str(audio_file), transcript)
        
        # Step 3: Generate summary and extract main ideas
        logger.info(f"Generating summary for {file_id}")
        summary = summarizer.summarize(diarized_transcript)
        
        # Step 4: Analyze sentiment and detect potential deception
        logger.info(f"Analyzing sentiment in {file_id}")
        sentiment_analysis = sentiment_analyzer.analyze(str(audio_file), diarized_transcript)
        
        # Step 5: Save formatted outputs
        logger.info(f"Saving outputs for {file_id}")
        formatter.save_transcript(file_id, diarized_transcript)
        formatter.save_summary(file_id, summary)
        formatter.save_sentiment_analysis(file_id, sentiment_analysis)
        
        # Store results for inconsistency detection
        results[file_id] = {
            'transcript': diarized_transcript,
            'summary': summary,
            'sentiment': sentiment_analysis
        }
        
        transcriptions[file_id] = diarized_transcript
    
    # Step 6: Detect inconsistencies across interviews
    if len(transcriptions) > 1:
        logger.info("Detecting inconsistencies across interviews")
        inconsistency_detector = InconsistencyDetector()
        inconsistencies = inconsistency_detector.detect_inconsistencies(transcriptions)
        formatter.save_inconsistencies(inconsistencies)
        results['inconsistencies'] = inconsistencies
    
    logger.info("Processing complete")
    return results


def handle_s3_operations(input_dir: str, output_dir: str) -> None:
    """
    Handle S3 operations for input and output.
    
    Args:
        input_dir: Local input directory
        output_dir: Local output directory
    """
    # Check if we're running in AWS Batch with S3 integration
    s3_bucket = os.environ.get('S3_BUCKET')
    s3_input_key = os.environ.get('S3_INPUT_KEY')
    
    if not s3_bucket:
        logger.info("No S3 bucket specified, skipping S3 operations")
        return
    
    s3_handler = S3Handler(s3_bucket)
    
    # Download input files from S3 if specified
    if s3_input_key:
        if s3_input_key.endswith('/'):
            # It's a directory
            logger.info(f"Downloading files from S3 prefix: {s3_input_key}")
            s3_handler.download_directory(s3_input_key, input_dir)
        else:
            # It's a single file
            filename = os.path.basename(s3_input_key)
            local_path = os.path.join(input_dir, filename)
            logger.info(f"Downloading file from S3: {s3_input_key}")
            s3_handler.download_file(s3_input_key, local_path)
    
    # Upload results to S3
    output_prefix = 'output/'
    if s3_input_key and not s3_input_key.startswith('input/'):
        # Preserve the directory structure
        parent_dir = os.path.dirname(s3_input_key)
        if parent_dir:
            output_prefix = f"output/{parent_dir}/"
    
    logger.info(f"Uploading results to S3 prefix: {output_prefix}")
    s3_handler.upload_directory(output_dir, output_prefix)


def main():
    """Main function to run the audio analysis system."""
    parser = argparse.ArgumentParser(description='Audio Interview Analysis System')
    parser.add_argument('--input_dir', type=str, default=config.DEFAULT_INPUT_DIR,
                        help='Directory containing audio files')
    parser.add_argument('--output_dir', type=str, default=config.DEFAULT_OUTPUT_DIR,
                        help='Directory to save output files')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    parser.add_argument('--s3_sync', action='store_true',
                        help='Enable S3 synchronization')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create necessary directories
    config.create_directories(args.input_dir, args.output_dir)
    
    # Handle S3 operations if running in AWS Batch or if explicitly enabled
    if args.s3_sync or os.environ.get('S3_BUCKET'):
        handle_s3_operations(args.input_dir, args.output_dir)
    
    # Process audio files
    process_audio_files(args.input_dir, args.output_dir)
    
    # Upload results to S3 if needed
    if args.s3_sync or os.environ.get('S3_BUCKET'):
        handle_s3_operations(args.input_dir, args.output_dir)


if __name__ == '__main__':
    main()