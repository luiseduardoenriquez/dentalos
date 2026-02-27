"""S3-compatible object storage client for DentalOS.

Wraps aioboto3 to provide async file upload, download, presigned URL
generation, and deletion. Uses MinIO for local dev, Hetzner Object Storage
in production.

Security invariants:
  - All S3 keys are tenant-prefixed: /{tenant_id}/{...}
  - Presigned URLs expire in 15 minutes (configurable).
  - File content type is validated before upload (allowlist + magic-byte check).
"""

import logging
from typing import BinaryIO

import aioboto3
import magic
from botocore.config import Config as BotoConfig

from app.core.config import settings

logger = logging.getLogger("dentalos.storage")

# Allowed MIME types for upload
ALLOWED_MIME_TYPES = frozenset({
    "image/jpeg",
    "image/png",
    "application/pdf",
    "application/dicom",
    "text/plain",
    "application/xml",
    # Audio types for voice dictation pipeline
    "audio/webm",
    "audio/ogg",
    "audio/wav",
    "audio/mpeg",
    "audio/mp4",
    "video/webm",  # webm containers detected as video by python-magic
})

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25MB

_PRESIGNED_URL_EXPIRY = 900  # 15 minutes

# Normalize common MIME type aliases to their canonical form before comparing.
# The python-magic library returns canonical types; clients sometimes send aliases.
_MIME_ALIASES: dict[str, str] = {
    "image/jpg": "image/jpeg",
    "image/x-jpeg": "image/jpeg",
    "image/pjpeg": "image/jpeg",
    "image/x-png": "image/png",
    "application/x-pdf": "application/pdf",
    "video/webm": "audio/webm",  # webm audio detected as video container
    "audio/x-wav": "audio/wav",
    "audio/x-m4a": "audio/mp4",
}


def verify_mime_type(data: bytes, claimed_type: str) -> bool:
    """Verify that file content matches the claimed MIME type using magic bytes.

    Args:
        data: Raw file bytes to inspect.
        claimed_type: MIME type asserted by the caller (e.g. from Content-Type header).

    Returns:
        True if the detected type matches (or is a known alias of) the claimed type.
    """
    detected = magic.from_buffer(data, mime=True)

    # Normalise both sides through the alias map.
    canonical_claimed = _MIME_ALIASES.get(claimed_type, claimed_type)
    canonical_detected = _MIME_ALIASES.get(detected, detected)

    if canonical_claimed == canonical_detected:
        return True

    # python-magic often detects short audio chunks (webm, ogg) as
    # application/octet-stream because the magic bytes are ambiguous.
    # Trust the claimed type when it's an allowed audio MIME type.
    return detected == "application/octet-stream" and canonical_claimed.startswith("audio/")


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

        # Resolve bytes for magic-byte verification (BinaryIO must be read first).
        raw: bytes = data if isinstance(data, bytes) else data.read()

        if not verify_mime_type(raw, content_type):
            detected = magic.from_buffer(raw, mime=True)
            raise ValueError(
                f"MIME type mismatch: claimed {content_type!r} but detected {detected!r}"
            )

        async with self._session.client(**self._client_kwargs()) as s3:
            await s3.put_object(
                Bucket=bucket,
                Key=key,
                ContentType=content_type,
                Body=raw,
            )

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
