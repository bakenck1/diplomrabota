"""Object Storage Service for audio files.

Validates: Requirements 5.1, 10.2
"""

import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from src.config import get_settings


# Local storage directory
LOCAL_STORAGE_DIR = Path("audio_storage")


class StorageService:
    """Service for storing and retrieving audio files from S3/MinIO or local storage.
    
    Validates: Requirements 5.1, 10.2
    """

    def __init__(self):
        """Initialize storage service."""
        self.settings = get_settings()
        self.client = None
        self.bucket = self.settings.s3_bucket_name
        self.use_local = True  # Default to local storage
        
        # Ensure local storage directory exists
        LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Try to initialize S3 client
        try:
            import boto3
            from botocore.config import Config
            self.client = boto3.client(
                "s3",
                endpoint_url=self.settings.s3_endpoint_url,
                aws_access_key_id=self.settings.s3_access_key,
                aws_secret_access_key=self.settings.s3_secret_key,
                config=Config(signature_version="s3v4"),
            )
            # Test connection
            self.client.head_bucket(Bucket=self.bucket)
            self.use_local = False
        except Exception:
            print("Info: Using local storage for audio files")

    def _generate_path(
        self,
        user_id,
        conversation_id,
        turn_id,
        file_type: str,
    ) -> str:
        """Generate storage path for audio file."""
        return f"users/{user_id}/conversations/{conversation_id}/turns/{turn_id}/{file_type}"

    async def upload_audio(
        self,
        audio: bytes,
        user_id,
        conversation_id,
        turn_id,
        file_type: str = "input.wav",
        content_type: str = "audio/wav",
    ) -> str:
        """Upload audio file to storage."""
        key = self._generate_path(user_id, conversation_id, turn_id, file_type)
        
        if self.use_local:
            # Save to local storage
            local_path = LOCAL_STORAGE_DIR / key
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(audio)
        elif self.client:
            try:
                self.client.put_object(
                    Bucket=self.bucket,
                    Key=key,
                    Body=audio,
                    ContentType=content_type,
                )
            except Exception as e:
                print(f"Warning: Failed to upload to S3: {e}")
                # Fallback to local
                local_path = LOCAL_STORAGE_DIR / key
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_bytes(audio)
        
        return key

    def generate_signed_url(
        self,
        key: str,
        expiration_seconds: Optional[int] = None,
    ) -> str:
        """Generate a URL for accessing audio file."""
        if self.use_local:
            # Return API endpoint URL for local files
            return f"/api/audio/{key}"
            
        if not self.client:
            return f"/api/audio/{key}"
            
        if expiration_seconds is None:
            expiration_seconds = self.settings.s3_url_expiration_seconds

        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expiration_seconds,
            )
            return url
        except Exception:
            return f"/api/audio/{key}"
    
    def get_local_file(self, key: str) -> Optional[bytes]:
        """Get file from local storage."""
        local_path = LOCAL_STORAGE_DIR / key
        if local_path.exists():
            return local_path.read_bytes()
        return None

    async def delete_audio(self, key: str) -> None:
        """Delete audio file from storage."""
        if self.client:
            try:
                self.client.delete_object(Bucket=self.bucket, Key=key)
            except Exception:
                pass

    async def list_old_files(self, older_than_days: int) -> list[str]:
        """List files older than specified days."""
        if not self.client:
            return []
            
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        old_keys = []

        try:
            paginator = self.client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket, Prefix="users/"):
                for obj in page.get("Contents", []):
                    if obj["LastModified"].replace(tzinfo=None) < cutoff_date:
                        old_keys.append(obj["Key"])
        except Exception:
            pass

        return old_keys
