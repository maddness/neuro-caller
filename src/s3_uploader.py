"""
S3 Uploader Module

Module for uploading files to S3-compatible storage
(Yandex Object Storage, AWS S3, MinIO, etc.)

Features:
- File upload to S3
- File existence check
- Temporary download links (presigned URLs)
- Retry on errors
- Detailed logging
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

import boto3
from botocore.config import Config
from botocore.exceptions import (
    ClientError,
    BotoCoreError,
    ConnectTimeoutError,
    ReadTimeoutError,
    EndpointConnectionError
)

logger = logging.getLogger(__name__)


class S3Uploader:
    """
    Class for uploading files to S3-compatible storage

    Supports:
    - Yandex Object Storage
    - AWS S3
    - MinIO
    - Other S3-compatible storages
    """

    # Short connect timeout for quick failure detection (hardcoded)
    CONNECT_TIMEOUT = 10

    def __init__(
        self,
        endpoint_url: str,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str,
        region_name: str = "ru-central1",
        retry_attempts: int = 3,
        timeout: int = 300
    ):
        """
        Initialize S3 client

        Args:
            endpoint_url: S3 endpoint URL (e.g., https://storage.yandexcloud.net)
            access_key_id: Access Key ID for authentication
            secret_access_key: Secret Access Key for authentication
            bucket_name: Bucket name for file storage
            region_name: Region (for Yandex usually ru-central1)
            retry_attempts: Number of retry attempts on error
            timeout: Read timeout in seconds (for large file uploads)
        """
        self.endpoint_url = endpoint_url
        self.bucket_name = bucket_name

        # Configuration without boto3 retry - we handle retry via recovery mechanism
        # connect_timeout is short (10s) for quick failure detection
        # read_timeout is longer for large file uploads
        config = Config(
            retries={'max_attempts': 0},
            connect_timeout=self.CONNECT_TIMEOUT,
            read_timeout=timeout
        )

        # Create S3 client
        try:
            self.s3_client = boto3.client(
                service_name='s3',
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                region_name=region_name,
                config=config
            )

            logger.info(
                f"S3 client initialized: {endpoint_url}, "
                f"bucket: {bucket_name}, "
                f"connect_timeout: {self.CONNECT_TIMEOUT}s, read_timeout: {timeout}s"
            )

            # Verify bucket access
            self._verify_bucket_access()

        except (ConnectTimeoutError, EndpointConnectionError) as e:
            logger.error(f"S3 connection timeout: {e}")
            raise
        except (ClientError, BotoCoreError) as e:
            logger.error(f"S3 client initialization error: {e}")
            raise

    def _verify_bucket_access(self) -> bool:
        """
        Verify bucket access

        Returns:
            True if access is available
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket {self.bucket_name} access confirmed")
            return True
        except (ConnectTimeoutError, EndpointConnectionError) as e:
            logger.error(f"S3 connection timeout during bucket check: {e}")
            return False
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == '404':
                logger.error(f"Bucket {self.bucket_name} not found")
            elif error_code == '403':
                logger.error(f"No access to bucket {self.bucket_name}")
            else:
                logger.error(f"Bucket access error: {e}")
            return False

    def upload_file(
        self,
        file_path: Path,
        s3_key: str,
        storage_class: str = "STANDARD",
        acl: str = "private",
        metadata: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Upload file to S3

        Args:
            file_path: Path to local file
            s3_key: Key (path) in S3 (e.g., 2025_11_20/PERU_003/file.wav)
            storage_class: Storage class (STANDARD, COLD, ICE)
            acl: Access Control List (private, public-read, etc)
            metadata: Additional file metadata

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False, "File not found"

        # File size for logging
        file_size = file_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)

        # Build upload parameters
        extra_args = {
            'StorageClass': storage_class,
            'ACL': acl
        }

        # Add metadata if provided
        if metadata:
            extra_args['Metadata'] = metadata

        # Set Content-Type for WAV files
        if file_path.suffix.lower() in ['.wav', '.wave']:
            extra_args['ContentType'] = 'audio/wav'

        try:
            logger.info(
                f"Uploading to S3: {file_path.name} ({file_size_mb:.1f} MB) "
                f"-> s3://{self.bucket_name}/{s3_key}"
            )

            # Upload file
            self.s3_client.upload_file(
                str(file_path),
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )

            logger.info(f"File uploaded to S3: {s3_key}")
            return True, None

        except ConnectTimeoutError as e:
            error_msg = "Connection timeout"
            logger.error(f"S3 connection timeout: {e}")
            return False, error_msg
        except ReadTimeoutError as e:
            error_msg = "Read timeout (file too large or slow connection)"
            logger.error(f"S3 read timeout: {e}")
            return False, error_msg
        except EndpointConnectionError as e:
            error_msg = "Cannot connect to S3"
            logger.error(f"S3 endpoint connection error: {e}")
            return False, error_msg
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = f"S3 error: {error_code}"
            logger.error(f"S3 upload error (code {error_code}): {e}")
            return False, error_msg
        except BotoCoreError as e:
            error_msg = "Network error"
            logger.error(f"S3 network error: {e}")
            return False, error_msg
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Unexpected upload error: {e}")
            return False, error_msg

    def file_exists(self, s3_key: str) -> Tuple[bool, Optional[str]]:
        """
        Check if file exists in S3

        Args:
            s3_key: File key in S3

        Returns:
            Tuple of (exists: bool, error_message: Optional[str])
            If error occurs, returns (False, error_message)
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True, None
        except ConnectTimeoutError as e:
            logger.error(f"S3 connection timeout checking file: {e}")
            return False, "Connection timeout"
        except EndpointConnectionError as e:
            logger.error(f"S3 endpoint connection error: {e}")
            return False, "Cannot connect to S3"
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == '404':
                return False, None  # File doesn't exist, not an error
            logger.error(f"S3 file check error: {e}")
            return False, f"S3 error: {error_code}"
        except BotoCoreError as e:
            logger.error(f"S3 network error checking file: {e}")
            return False, "Network error"

    def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 604800
    ) -> Optional[str]:
        """
        Generate temporary download link (presigned URL)

        Args:
            s3_key: File key in S3
            expiration: URL lifetime in seconds (default 7 days)

        Returns:
            Presigned URL or None on error
        """
        try:
            # Generate presigned URL (no file_exists check - file was just uploaded)
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )

            # Calculate expiry date for logging
            expiry_date = datetime.now() + timedelta(seconds=expiration)
            logger.info(
                f"Presigned URL created for {s3_key} "
                f"(valid until {expiry_date.strftime('%Y-%m-%d %H:%M')})"
            )

            return url

        except (ConnectTimeoutError, EndpointConnectionError) as e:
            logger.error(f"S3 connection error generating URL: {e}")
            return None
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating URL: {e}")
            return None

    def get_file_info(self, s3_key: str) -> Optional[Dict[str, Any]]:
        """
        Get file info from S3

        Args:
            s3_key: File key in S3

        Returns:
            Dictionary with file info or None
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            return {
                'size': response.get('ContentLength', 0),
                'last_modified': response.get('LastModified'),
                'content_type': response.get('ContentType', 'unknown'),
                'metadata': response.get('Metadata', {})
            }

        except ClientError as e:
            logger.error(f"Error getting file info: {e}")
            return None

    def delete_file(self, s3_key: str) -> bool:
        """
        Delete file from S3

        Args:
            s3_key: File key in S3

        Returns:
            True if deletion successful
        """
        try:
            logger.info(f"Deleting from S3: {s3_key}")
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"File deleted from S3: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting file: {e}")
            return False

    def list_files(self, prefix: str = "", max_keys: int = 1000) -> list:
        """
        Get list of files in bucket

        Args:
            prefix: Prefix for filtering (e.g., "2025_11_20/")
            max_keys: Maximum number of files

        Returns:
            List of file keys
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )

            if 'Contents' not in response:
                return []

            files = [obj['Key'] for obj in response['Contents']]
            logger.info(f"Found files in S3: {len(files)} (prefix: {prefix or 'all'})")
            return files

        except ClientError as e:
            logger.error(f"Error listing files: {e}")
            return []


# Usage example
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    load_dotenv()

    if not all([
        os.getenv("S3_ENDPOINT_URL"),
        os.getenv("S3_ACCESS_KEY_ID"),
        os.getenv("S3_SECRET_ACCESS_KEY"),
        os.getenv("S3_BUCKET_NAME")
    ]):
        logger.error("Not all S3 variables set in .env")
        exit(1)

    uploader = S3Uploader(
        endpoint_url=os.getenv("S3_ENDPOINT_URL"),
        access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
        secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
        bucket_name=os.getenv("S3_BUCKET_NAME"),
        region_name=os.getenv("S3_REGION_NAME", "ru-central1"),
        retry_attempts=int(os.getenv("S3_RETRY_ATTEMPTS", "3")),
        timeout=int(os.getenv("S3_UPLOAD_TIMEOUT", "300"))
    )

    test_file = Path("test.wav")
    if test_file.exists():
        s3_key = "2025_11_20/TEST_DEVICE/test.wav"

        metadata = {
            'device': 'TEST_DEVICE',
            'original_filename': test_file.name,
            'upload_date': datetime.now().isoformat()
        }

        success, error = uploader.upload_file(
            file_path=test_file,
            s3_key=s3_key,
            metadata=metadata
        )

        if success:
            url = uploader.generate_presigned_url(s3_key, expiration=604800)
            if url:
                logger.info(f"Download link: {url}")
    else:
        logger.info("Test file not found. Skipping example.")
