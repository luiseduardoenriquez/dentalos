"""Digital signature utility functions for DentalOS.

Provides canonical hash computation, blank signature detection, and
base64 PNG validation used by the digital signature service.

Security invariants:
  - Canonical hash is deterministic: same inputs always produce same hash.
  - Blank detection prevents signing with empty/white canvas images.
  - PNG magic bytes are checked before processing.
"""

import base64
import hashlib
import io
import logging

from PIL import Image

logger = logging.getLogger("dentalos.signature")

# PNG file magic bytes
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

# Blank detection: if < 5% of pixels are non-white, the image is blank
_BLANK_THRESHOLD = 0.05

# Maximum signature image size (500KB)
MAX_SIGNATURE_SIZE_BYTES = 500 * 1024


def validate_png_base64(data: str) -> bytes:
    """Validate and decode a base64-encoded PNG image.

    Args:
        data: Base64-encoded string (with or without data URI prefix).

    Returns:
        Raw PNG bytes.

    Raises:
        ValueError — invalid base64, not a PNG, or exceeds size limit.
    """
    # Strip data URI prefix if present
    if data.startswith("data:image/png;base64,"):
        data = data[len("data:image/png;base64,"):]

    try:
        raw = base64.b64decode(data, validate=True)
    except Exception:
        raise ValueError("Invalid base64 encoding.")

    if len(raw) > MAX_SIGNATURE_SIZE_BYTES:
        raise ValueError(
            f"Signature image exceeds {MAX_SIGNATURE_SIZE_BYTES // 1024}KB limit."
        )

    if not raw.startswith(_PNG_MAGIC):
        raise ValueError("File is not a valid PNG image.")

    return raw


def is_blank_signature(png_bytes: bytes) -> bool:
    """Detect if a signature image is effectively blank.

    Converts to grayscale and checks if fewer than 5% of pixels
    are non-white (value < 250). This catches empty canvas submissions.

    Args:
        png_bytes: Raw PNG image bytes.

    Returns:
        True if the image is blank (should be rejected).
    """
    try:
        img = Image.open(io.BytesIO(png_bytes)).convert("L")  # Grayscale
        pixels = list(img.getdata())
        total = len(pixels)
        if total == 0:
            return True

        # Count non-white pixels (threshold: pixel value < 250)
        non_white = sum(1 for p in pixels if p < 250)
        ratio = non_white / total

        return ratio < _BLANK_THRESHOLD
    except Exception:
        logger.warning("Blank detection failed — treating as blank.")
        return True


def compute_canonical_hash(
    *,
    signature_id: str,
    document_type: str,
    document_id: str,
    signer_id: str,
    timestamp_us: int,
    image_sha256: str,
) -> str:
    """Compute the canonical SHA-256 hash for a digital signature.

    The hash is deterministic: the same inputs always produce the same
    output. The canonical format is:
        {sig_id}|{doc_type}|{doc_id}|{signer_id}|{timestamp_us}|{image_sha256}

    Args:
        signature_id: UUID of the signature record.
        document_type: Type of document being signed.
        document_id: UUID of the document being signed.
        signer_id: UUID of the signer.
        timestamp_us: Signing timestamp in microseconds since epoch.
        image_sha256: SHA-256 hex digest of the raw signature image.

    Returns:
        SHA-256 hex digest of the canonical string.
    """
    canonical = (
        f"{signature_id}|{document_type}|{document_id}|"
        f"{signer_id}|{timestamp_us}|{image_sha256}"
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sha256_digest(data: bytes) -> str:
    """Compute SHA-256 hex digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()
