#!/usr/bin/env python3
"""
Example script demonstrating the Audio Interview Analysis System.

This script shows how to use the system with sample data.
"""

import os
import logging
import argparse
from pathlib import Path

from audio_analysis import config
from audio_analysis.main import process_audio_files

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_directories():
    """Create sample input and output directories."""
    input_dir = os.path.join(os.getcwd(), "sample_input")
    output_dir = os.path.join(os.getcwd(), "sample_output")
    
    Path(input_dir).mkdir(exist_ok=True)
    Path(output_dir).mkdir(exist_ok=True)
    
    return input_dir, output_dir


def print_usage_instructions(input_dir):
    """Print instructions for using the example."""
    print("\n" + "=" * 80)
    print("Audio Interview Analysis System - Example Usage")
    print("=" * 80)
    print(f"\n1. Place your audio interview files in: {input_dir}")
    print("   Supported formats: .wav, .mp3, .m4a, .flac")
    print("\n2. Run the analysis with:")
    print(f"   python example.py")
    print("\n3. Results will be saved in the 'sample_output' directory")
    print("\nNote: For first-time use, you may need to download models and resources.")
    print("      This can take some time depending on your internet connection.")
    print("\nFor more options:")
    print("   python example.py --help")
    print("=" * 80 + "\n")


def main():
    """Main function to run the example."""
    parser = argparse.ArgumentParser(description='Audio Interview Analysis System Example')
    parser.add_argument('--input_dir', type=str, help='Directory containing audio files')
    parser.add_argument('--output_dir', type=str, help='Directory to save output files')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create sample directories if not specified
    input_dir = args.input_dir
    output_dir = args.output_dir
    
    if not input_dir or not output_dir:
        input_dir, output_dir = create_sample_directories()
    
    # Print usage instructions
    print_usage_instructions(input_dir)
    
    # Check if input directory has audio files
    audio_files = [
        f for f in Path(input_dir).glob('**/*') 
        if f.is_file() and f.suffix.lower() in ('.wav', '.mp3', '.m4a', '.flac')
    ]
    
    if not audio_files:
        logger.warning(f"No audio files found in {input_dir}")
        print(f"\nNo audio files found in {input_dir}")
        print("Please add some audio files and run the script again.")
        return
    
    # Process audio files
    logger.info(f"Processing {len(audio_files)} audio files")
    print(f"\nProcessing {len(audio_files)} audio files...")
    
    results = process_audio_files(input_dir, output_dir)
    
    print(f"\nProcessing complete! Results saved to: {output_dir}")
    print(f"Processed {len(results)} audio files")


if __name__ == '__main__':
    main()