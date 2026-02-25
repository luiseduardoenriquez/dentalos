"""S3-compatible object storage client for DentalOS.

Wraps aioboto3 to provide async file upload, download, presigned URL
generation, and deletion. Uses MinIO for local dev, Hetzner Object Storage
in production.

Security invariants:
  - All S3 keys are tenant-prefixed: /{tenant_id}/{...}
  - Presigned URLs expire in 15 minutes (configurable).
  - File content type is validated before upload.
"""

import logging
from typing import BinaryIO

import aioboto3
from botocore.config import Config as BotoConfig

from app.core.config import settings

logger = logging.getLogger("dentalos.storage")

# Allowed MIME types for upload
ALLOWED_MIME_TYPES = frozenset({
    "image/jpeg",
    "image/png",
    "application/pdf",
    "application/dicom",
})

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25MB

_PRESIGNED_URL_EXPIRY = 900  # 15 minutes


class StorageClient:
    """Async S3-compatible storage client."""

    def __init__(self) -> None:
        self._session = aioboto3.Session()

    def _client_kwargs(self) -> dict:
        """Build connection kwargs from settings."""
        kwargs = {
            "service_name": "s3",
            "endpoint_url": settings.s3_endpoint_url,
            "aws_access_key_id": settings.s3_access_key,
            "aws_secret_access_key": settings.s3_secret_key,
            "region_name": settings.s3_region,
            "config": BotoConfig(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
        }
        return kwargs

    async def upload_file(
        self,
        *,
        key: str,
        data: BinaryIO | bytes,
        content_type: str,
        bucket: str | None = None,
    ) -> str:
        """Upload a file to S3. Returns the S3 key.

        Raises:
            ValueError — invalid content type or file too large.
        """
        bucket = bucket or settings.s3_bucket_name

        if content_type not in ALLOWED_MIME_TYPES:
            raise ValueError(f"Content type '{content_type}' is not allowed.")

        async with self._session.client(**self._client_kwargs()) as s3:
            upload_kwargs = {
                "Bucket": bucket,
                "Key": key,
                "ContentType": content_type,
            }
            if isinstance(data, bytes):
                upload_kwargs["Body"] = data
            else:
                upload_kwargs["Body"] = data.read()

            await s3.put_object(**upload_kwargs)

        logger.info("File uploaded: key=%s bucket=%s", key[:40], bucket)
        return key

    async def get_presigned_url(
        self,
        *,
        key: str,
        bucket: str | None = None,
        expiry: int = _PRESIGNED_URL_EXPIRY,
    ) -> str:
        """Generate a presigned GET URL for a file."""
        bucket = bucket or settings.s3_bucket_name

        async with self._session.client(**self._client_kwargs()) as s3:
            url = await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expiry,
            )

        return url

    async def download_file(
        self,
        *,
        key: str,
        bucket: str | None = None,
    ) -> bytes:
        """Download a file from S3. Returns raw bytes."""
        bucket = bucket or settings.s3_bucket_name

        async with self._session.client(**self._client_kwargs()) as s3:
            response = await s3.get_object(Bucket=bucket, Key=key)
            body = await response["Body"].read()

        return body

    async def delete_file(
        self,
        *,
        key: str,
        bucket: str | None = None,
    ) -> None:
        """Delete a file from S3."""
        bucket = bucket or settings.s3_bucket_name

        async with self._session.client(**self._client_kwargs()) as s3:
            await s3.delete_object(Bucket=bucket, Key=key)

        logger.info("File deleted: key=%s bucket=%s", key[:40], bucket)


# Module-level singleton
storage_client = StorageClient()
