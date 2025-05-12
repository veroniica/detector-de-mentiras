"""
Unit tests for utility modules.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from audio_analysis.utils.s3_handler import S3Handler
from audio_analysis.utils.output_formatter import OutputFormatter


class TestS3Handler(unittest.TestCase):
    """Test cases for the S3Handler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bucket_name = "test-bucket"
        self.s3_handler = S3Handler(self.bucket_name)
    
    @patch('boto3.client')
    def test_download_file(self, mock_boto_client):
        """Test downloading a file from S3."""
        # Set up mock
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        
        # Call the method
        result = self.s3_handler.download_file("test/file.mp3", "/tmp/file.mp3")
        
        # Verify the result
        self.assertTrue(result)
        mock_s3.download_file.assert_called_once_with(
            self.bucket_name, "test/file.mp3", "/tmp/file.mp3"
        )
    
    @patch('boto3.client')
    def test_upload_file(self, mock_boto_client):
        """Test uploading a file to S3."""
        # Set up mock
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        
        # Call the method
        result = self.s3_handler.upload_file("/tmp/file.mp3", "test/file.mp3")
        
        # Verify the result
        self.assertTrue(result)
        mock_s3.upload_file.assert_called_once_with(
            "/tmp/file.mp3", self.bucket_name, "test/file.mp3"
        )
    
    @patch('boto3.client')
    def test_download_directory(self, mock_boto_client):
        """Test downloading a directory from S3."""
        # Set up mock
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        
        # Mock paginator
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        
        # Mock pages
        mock_pages = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                'Contents': [
                    {'Key': 'input/file1.mp3'},
                    {'Key': 'input/file2.mp3'},
                    {'Key': 'input/subdir/'},
                    {'Key': 'input/subdir/file3.mp3'}
                ]
            }
        ]
        
        # Call the method
        result = self.s3_handler.download_directory("input/", "/tmp/input")
        
        # Verify the result
        self.assertEqual(len(result), 3)  # 3 files, excluding the directory
        mock_s3.download_file.assert_any_call(
            self.bucket_name, "input/file1.mp3", "/tmp/input/file1.mp3"
        )
        mock_s3.download_file.assert_any_call(
            self.bucket_name, "input/file2.mp3", "/tmp/input/file2.mp3"
        )
        mock_s3.download_file.assert_any_call(
            self.bucket_name, "input/subdir/file3.mp3", "/tmp/input/subdir/file3.mp3"
        )
    
    @patch('boto3.client')
    @patch('os.walk')
    def test_upload_directory(self, mock_walk, mock_boto_client):
        """Test uploading a directory to S3."""
        # Set up mock
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        
        # Mock os.walk
        mock_walk.return_value = [
            ("/tmp/output", [], ["file1.txt", "file2.txt"]),
            ("/tmp/output/subdir", [], ["file3.txt"])
        ]
        
        # Call the method
        result = self.s3_handler.upload_directory("/tmp/output", "output/")
        
        # Verify the result
        self.assertEqual(len(result), 3)  # 3 files
        mock_s3.upload_file.assert_any_call(
            "/tmp/output/file1.txt", self.bucket_name, "output/file1.txt"
        )
        mock_s3.upload_file.assert_any_call(
            "/tmp/output/file2.txt", self.bucket_name, "output/file2.txt"
        )
        mock_s3.upload_file.assert_any_call(
            "/tmp/output/subdir/file3.txt", self.bucket_name, "output/subdir/file3.txt"
        )


class TestOutputFormatter(unittest.TestCase):
    """Test cases for the OutputFormatter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.output_dir = "/tmp/test_output"
        self.formatter = OutputFormatter(self.output_dir)
    
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('os.path.join')
    @patch('pathlib.Path.mkdir')
    def test_save_transcript(self, mock_mkdir, mock_join, mock_open):
        """Test saving a transcript."""
        # Set up mocks
        mock_join.side_effect = lambda *args: '/'.join(args)
        
        # Create test data
        transcript = [
            {
                "text": "Hello, how are you?",
                "start_time": 0.0,
                "end_time": 2.0,
                "start_timestamp": "00:00",
                "end_timestamp": "00:02",
                "speaker": "Speaker_1"
            },
            {
                "text": "I'm fine, thank you.",
                "start_time": 3.0,
                "end_time": 5.0,
                "start_timestamp": "00:03",
                "end_timestamp": "00:05",
                "speaker": "Speaker_2"
            }
        ]
        
        # Call the method
        self.formatter.save_transcript("test_file", transcript)
        
        # Verify the result
        mock_open.assert_any_call(f"{self.output_dir}/transcripts/test_file_script.txt", 'w', encoding='utf-8')
        mock_open.assert_any_call(f"{self.output_dir}/transcripts/test_file_transcript.json", 'w', encoding='utf-8')
        
        # Check that the write method was called
        handle = mock_open()
        self.assertTrue(handle.write.called)


if __name__ == '__main__':
    unittest.main()