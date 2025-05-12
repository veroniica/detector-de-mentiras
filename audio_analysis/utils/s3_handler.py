"""
Utility functions for handling S3 operations.
"""

import os
import logging
import boto3
from botocore.exceptions import ClientError
from pathlib import Path

logger = logging.getLogger(__name__)

class S3Handler:
    """
    Class for handling S3 operations.
    """
    
    def __init__(self, bucket_name=None):
        """
        Initialize the S3 handler.
        
        Args:
            bucket_name: Name of the S3 bucket (optional, can be set from environment)
        """
        self.s3_client = boto3.client('s3')
        self.bucket_name = bucket_name or os.environ.get('S3_BUCKET')
        
        if not self.bucket_name:
            logger.warning("No S3 bucket specified, S3 operations will not work")
    
    def download_file(self, s3_key, local_path):
        """
        Download a file from S3.
        
        Args:
            s3_key: S3 object key
            local_path: Local path to save the file
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.bucket_name:
            logger.error("No S3 bucket specified")
            return False
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            logger.info(f"Downloading {s3_key} from S3 bucket {self.bucket_name} to {local_path}")
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            return True
        except ClientError as e:
            logger.error(f"Error downloading file from S3: {e}")
            return False
    
    def upload_file(self, local_path, s3_key):
        """
        Upload a file to S3.
        
        Args:
            local_path: Local path of the file
            s3_key: S3 object key
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.bucket_name:
            logger.error("No S3 bucket specified")
            return False
        
        try:
            logger.info(f"Uploading {local_path} to S3 bucket {self.bucket_name} as {s3_key}")
            self.s3_client.upload_file(local_path, self.bucket_name, s3_key)
            return True
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            return False
    
    def download_directory(self, s3_prefix, local_dir):
        """
        Download all files from an S3 prefix to a local directory.
        
        Args:
            s3_prefix: S3 prefix (directory)
            local_dir: Local directory to save files
            
        Returns:
            list: List of downloaded file paths
        """
        if not self.bucket_name:
            logger.error("No S3 bucket specified")
            return []
        
        downloaded_files = []
        
        try:
            # Ensure local directory exists
            os.makedirs(local_dir, exist_ok=True)
            
            # List objects in the prefix
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=s3_prefix)
            
            for page in pages:
                if 'Contents' not in page:
                    continue
                
                for obj in page['Contents']:
                    key = obj['Key']
                    
                    # Skip if it's a directory
                    if key.endswith('/'):
                        continue
                    
                    # Determine local file path
                    rel_path = key[len(s3_prefix):].lstrip('/')
                    local_path = os.path.join(local_dir, rel_path)
                    
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    
                    # Download file
                    logger.info(f"Downloading {key} to {local_path}")
                    self.s3_client.download_file(self.bucket_name, key, local_path)
                    downloaded_files.append(local_path)
            
            logger.info(f"Downloaded {len(downloaded_files)} files from S3")
            return downloaded_files
        except ClientError as e:
            logger.error(f"Error downloading directory from S3: {e}")
            return downloaded_files
    
    def upload_directory(self, local_dir, s3_prefix):
        """
        Upload all files from a local directory to an S3 prefix.
        
        Args:
            local_dir: Local directory containing files
            s3_prefix: S3 prefix (directory)
            
        Returns:
            list: List of uploaded S3 keys
        """
        if not self.bucket_name:
            logger.error("No S3 bucket specified")
            return []
        
        uploaded_keys = []
        
        try:
            # Walk through the directory
            for root, _, files in os.walk(local_dir):
                for file in files:
                    local_path = os.path.join(root, file)
                    
                    # Determine S3 key
                    rel_path = os.path.relpath(local_path, local_dir)
                    s3_key = f"{s3_prefix.rstrip('/')}/{rel_path}"
                    
                    # Upload file
                    logger.info(f"Uploading {local_path} to {s3_key}")
                    self.s3_client.upload_file(local_path, self.bucket_name, s3_key)
                    uploaded_keys.append(s3_key)
            
            logger.info(f"Uploaded {len(uploaded_keys)} files to S3")
            return uploaded_keys
        except ClientError as e:
            logger.error(f"Error uploading directory to S3: {e}")
            return uploaded_keys