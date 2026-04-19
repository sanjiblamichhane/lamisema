"""
S3/Minio storage implementation for LamiSema.

Requires: boto3 (pip install boto3)
Environment Variables:
  - LAMI_S3_ENDPOINT: http://minio:9000
  - LAMI_S3_ACCESS_KEY: minioadmin
  - LAMI_S3_SECRET_KEY: minioadmin
  - LAMI_S3_BUCKET: lamisema-vault
"""

import json
import logging
import os
from typing import Optional
from urllib.parse import quote, unquote

from lamisema.models import ExtractionResult
from lamisema.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class S3Storage(StorageBackend):
    """
    Persistent storage using S3-compatible service (AWS S3 or Minio).
    """

    def __init__(self):
        try:
            import boto3
            from botocore.exceptions import ClientError  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "boto3 is required for S3 storage. Run: pip install boto3"
            ) from exc

        self.endpoint = os.getenv("LAMI_S3_ENDPOINT")
        self.access_key = os.getenv("LAMI_S3_ACCESS_KEY")
        self.secret_key = os.getenv("LAMI_S3_SECRET_KEY")
        self.bucket_name = os.getenv("LAMI_S3_BUCKET", "lamisema-vault")

        # Custom session/client
        self.s3 = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )
        self._ensure_bucket()
        logger.info(f"Initialized S3Storage at {self.endpoint or 'AWS S3'} (bucket: {self.bucket_name})")

    def _ensure_bucket(self):
        """Create the bucket if it doesn't exist."""
        try:
            self.s3.head_bucket(Bucket=self.bucket_name)
        except Exception:
            logger.info(f"Creating S3 bucket: {self.bucket_name}")
            self.s3.create_bucket(Bucket=self.bucket_name)

    def store_pdf(self, doc_id: str, filename: str, pdf_bytes: bytes) -> None:
        key = f"uploads/{doc_id}.pdf"
        # S3 Metadata MUST be ASCII. We URL-encode the Nepali filename.
        safe_filename = quote(filename)
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=pdf_bytes,
            Metadata={"filename": safe_filename},
        )
        logger.debug(f"Stored PDF to S3: {key} (orig: {filename})")

    def get_pdf(self, doc_id: str) -> Optional[bytes]:
        key = f"uploads/{doc_id}.pdf"
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
            return response["Body"].read()
        except Exception:
            return None

    def get_filename(self, doc_id: str) -> Optional[str]:
        key = f"uploads/{doc_id}.pdf"
        try:
            response = self.s3.head_object(Bucket=self.bucket_name, Key=key)
            safe_filename = response.get("Metadata", {}).get("filename")
            return unquote(safe_filename) if safe_filename else None
        except Exception:
            return None

    def store_result(self, doc_id: str, result: ExtractionResult) -> None:
        key = f"results/{doc_id}.json"
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=result.model_dump_json(),
            ContentType="application/json",
        )
        logger.debug(f"Stored result to S3: {key}")

    def get_result(self, doc_id: str) -> Optional[ExtractionResult]:
        key = f"results/{doc_id}.json"
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
            data = json.loads(response["Body"].read())
            return ExtractionResult.model_validate(data)
        except Exception:
            return None
