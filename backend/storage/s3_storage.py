"""
CineCloud Cloud Storage Adapter (AWS S3 / Cloudflare R2 / MinIO / Backblaze B2)
Allows offloading high-bitrate 4K/1080p video files to cloud object storage.
"""
from typing import Generator, Optional
from backend.storage.base import BaseStorage
from backend.config import (
    S3_BUCKET_NAME, S3_ENDPOINT_URL, S3_ACCESS_KEY, S3_SECRET_KEY, S3_REGION
)

class S3CloudStorage(BaseStorage):
    def __init__(self):
        self.bucket_name = S3_BUCKET_NAME
        self.endpoint_url = S3_ENDPOINT_URL
        self.access_key = S3_ACCESS_KEY
        self.secret_key = S3_SECRET_KEY
        self.region = S3_REGION
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import boto3
                from botocore.config import Config
                self._client = boto3.client(
                    's3',
                    endpoint_url=self.endpoint_url or None,
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    region_name=self.region,
                    config=Config(signature_version='s3v4')
                )
            except ImportError:
                raise RuntimeError("boto3 is required for S3CloudStorage. Install with 'pip install boto3'")
        return self._client

    def save_file(self, filename: str, content: bytes, folder: str = "movies") -> str:
        client = self._get_client()
        key = f"{folder}/{filename}"
        client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=content
        )
        return f"s3://{self.bucket_name}/{key}"

    def delete_file(self, filepath: str) -> bool:
        client = self._get_client()
        key = filepath.replace(f"s3://{self.bucket_name}/", "")
        try:
            client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    def file_exists(self, filepath: str) -> bool:
        client = self._get_client()
        key = filepath.replace(f"s3://{self.bucket_name}/", "")
        try:
            client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    def get_file_size(self, filepath: str) -> int:
        client = self._get_client()
        key = filepath.replace(f"s3://{self.bucket_name}/", "")
        resp = client.head_object(Bucket=self.bucket_name, Key=key)
        return resp.get('ContentLength', 0)

    def get_presigned_streaming_url(self, filepath: str, expires_in: int = 3600) -> str:
        client = self._get_client()
        key = filepath.replace(f"s3://{self.bucket_name}/", "")
        return client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket_name, 'Key': key},
            ExpiresIn=expires_in
        )

    def get_byte_range(self, filepath: str, start: int, end: int) -> Generator[bytes, None, None]:
        client = self._get_client()
        key = filepath.replace(f"s3://{self.bucket_name}/", "")
        range_header = f"bytes={start}-{end}"
        resp = client.get_object(Bucket=self.bucket_name, Key=key, Range=range_header)
        body = resp['Body']
        while True:
            chunk = body.read(128 * 1024)
            if not chunk:
                break
            yield chunk
