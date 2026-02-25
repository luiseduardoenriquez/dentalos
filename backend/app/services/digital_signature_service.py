"""Digital signature service — create, verify, and manage signatures.

Security invariants:
  - PNG images are validated (magic bytes, not blank, size limit).
  - Canonical hash is deterministic and immutable.
  - Signatures are NEVER deleted (regulatory requirement).
  - S3 keys are tenant-prefixed for isolation.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import SignatureErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError, SignatureError
from app.core.signature_utils import (
    compute_canonical_hash,
    is_blank_signature,
    sha256_digest,
    validate_png_base64,
)
from app.core.storage import storage_client
from app.models.tenant.digital_signature import DigitalSignature, SignatureVerification

logger = logging.getLogger("dentalos.signature")

_VALID_DOCUMENT_TYPES = frozenset({"consent", "treatment_plan", "quotation", "prescription"})
_VALID_SIGNER_TYPES = frozenset({"patient", "doctor", "clinic_owner", "witness"})


def _signature_to_dict(sig: DigitalSignature) -> dict[str, Any]:
    """Serialize a DigitalSignature ORM instance to a plain dict."""
    return {
        "id": str(sig.id),
        "document_type": sig.document_type,
        "document_id": str(sig.document_id),
        "signer_type": sig.signer_type,
        "signer_id": str(sig.signer_id),
        "s3_key": sig.s3_key,
        "signature_hash": sig.signature_hash,
        "image_hash": sig.image_hash,
        "signed_at": sig.signed_at,
        "ip_address": sig.ip_address,
        "created_at": sig.created_at,
        "updated_at": sig.updated_at,
    }


def _verification_to_dict(ver: SignatureVerification) -> dict[str, Any]:
    """Serialize a SignatureVerification ORM instance to a plain dict."""
    return {
        "signature_id": str(ver.signature_id),
        "is_valid": ver.is_valid,
        "computed_hash": ver.computed_hash,
        "stored_hash": ver.stored_hash,
        "verified_at": ver.verified_at,
        "created_at": ver.created_at,
        "updated_at": ver.updated_at,
    }


class DigitalSignatureService:
    """Stateless digital signature service."""

    async def create_signature(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        signer_id: str,
        document_type: str,
        document_id: str,
        signer_type: str,
        signature_image_b64: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Create a new digital signature.

        Validates the PNG image, checks for blank signatures, computes
        the canonical hash, uploads to S3, and creates the DB record.

        Raises:
            SignatureError (422) — blank signature or invalid image.
            DentalOSError (409) — signature already exists for this document+signer.
        """
        # 1. Validate document_type and signer_type
        if document_type not in _VALID_DOCUMENT_TYPES:
            raise DentalOSError(
                error=SignatureErrors.INVALID_IMAGE,
                message=f"Tipo de documento inválido: {document_type}.",
                status_code=422,
            )
        if signer_type not in _VALID_SIGNER_TYPES:
            raise DentalOSError(
                error=SignatureErrors.INVALID_IMAGE,
                message=f"Tipo de firmante inválido: {signer_type}.",
                status_code=422,
            )

        # 2. Validate and decode PNG
        try:
            png_bytes = validate_png_base64(signature_image_b64)
        except ValueError as e:
            raise SignatureError(
                error=SignatureErrors.INVALID_IMAGE,
                message=str(e),
                status_code=422,
            )

        # 3. Blank detection
        if is_blank_signature(png_bytes):
            raise SignatureError(
                error=SignatureErrors.BLANK_SIGNATURE,
                message="La imagen de firma está en blanco. Por favor firme nuevamente.",
                status_code=422,
            )

        # 4. Check for existing signature (UNIQUE constraint)
        existing = await db.execute(
            select(DigitalSignature).where(
                DigitalSignature.document_type == document_type,
                DigitalSignature.document_id == uuid.UUID(document_id),
                DigitalSignature.signer_type == signer_type,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise DentalOSError(
                error=SignatureErrors.ALREADY_SIGNED,
                message="Este documento ya fue firmado por este tipo de firmante.",
                status_code=409,
            )

        # 5. Compute image hash
        image_hash = sha256_digest(png_bytes)

        # 6. Create DB record (flush to get ID)
        now = datetime.now(UTC)
        timestamp_us = int(now.timestamp() * 1_000_000)

        sig = DigitalSignature(
            document_type=document_type,
            document_id=uuid.UUID(document_id),
            signer_type=signer_type,
            signer_id=uuid.UUID(signer_id),
            s3_key="",  # Placeholder — set after S3 upload
            canonical_payload="",  # Placeholder — set after hash computation
            signature_hash="",  # Placeholder
            image_hash=image_hash,
            signed_at=now,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(sig)
        await db.flush()  # Get sig.id

        # 7. Compute canonical hash
        canonical_hash = compute_canonical_hash(
            signature_id=str(sig.id),
            document_type=document_type,
            document_id=document_id,
            signer_id=signer_id,
            timestamp_us=timestamp_us,
            image_sha256=image_hash,
        )

        canonical_payload = (
            f"{sig.id}|{document_type}|{document_id}|"
            f"{signer_id}|{timestamp_us}|{image_hash}"
        )

        # 8. Upload to S3
        s3_key = f"{tenant_id}/signatures/{sig.id}.png"
        await storage_client.upload_file(
            key=s3_key,
            data=png_bytes,
            content_type="image/png",
        )

        # 9. Update record with final values
        sig.s3_key = s3_key
        sig.canonical_payload = canonical_payload
        sig.signature_hash = canonical_hash
        await db.flush()

        logger.info(
            "Signature created: doc_type=%s doc_id=%s signer=%s",
            document_type,
            document_id[:8],
            signer_type,
        )

        return _signature_to_dict(sig)

    async def verify_signature(
        self,
        *,
        db: AsyncSession,
        signature_id: str,
        verified_by: str | None = None,
    ) -> dict[str, Any]:
        """Verify a signature by recomputing the canonical hash.

        Creates an immutable verification audit record.

        Raises:
            ResourceNotFoundError (404) — signature not found.
        """
        result = await db.execute(
            select(DigitalSignature).where(
                DigitalSignature.id == uuid.UUID(signature_id),
            )
        )
        sig = result.scalar_one_or_none()

        if sig is None:
            raise ResourceNotFoundError(
                error=SignatureErrors.NOT_FOUND,
                resource_name="DigitalSignature",
            )

        # Parse canonical payload to extract components
        parts = sig.canonical_payload.split("|")
        if len(parts) != 6:
            # Corrupted payload
            computed_hash = "CORRUPTED_PAYLOAD"
            is_valid = False
        else:
            computed_hash = compute_canonical_hash(
                signature_id=parts[0],
                document_type=parts[1],
                document_id=parts[2],
                signer_id=parts[3],
                timestamp_us=int(parts[4]),
                image_sha256=parts[5],
            )
            is_valid = computed_hash == sig.signature_hash

        # Create verification record
        now = datetime.now(UTC)
        verification = SignatureVerification(
            signature_id=sig.id,
            is_valid=is_valid,
            computed_hash=computed_hash,
            stored_hash=sig.signature_hash,
            verified_by=uuid.UUID(verified_by) if verified_by else None,
            verified_at=now,
        )
        db.add(verification)
        await db.flush()

        logger.info(
            "Signature verified: sig=%s valid=%s",
            signature_id[:8],
            is_valid,
        )

        return _verification_to_dict(verification)

    async def get_signature(
        self,
        *,
        db: AsyncSession,
        signature_id: str,
    ) -> dict[str, Any] | None:
        """Fetch a single signature by ID."""
        result = await db.execute(
            select(DigitalSignature).where(
                DigitalSignature.id == uuid.UUID(signature_id),
            )
        )
        sig = result.scalar_one_or_none()
        if sig is None:
            return None
        return _signature_to_dict(sig)

    async def get_signatures_for_document(
        self,
        *,
        db: AsyncSession,
        document_type: str,
        document_id: str,
    ) -> list[dict[str, Any]]:
        """Fetch all signatures for a specific document."""
        result = await db.execute(
            select(DigitalSignature).where(
                DigitalSignature.document_type == document_type,
                DigitalSignature.document_id == uuid.UUID(document_id),
            )
        )
        sigs = result.scalars().all()
        return [_signature_to_dict(s) for s in sigs]


# Module-level singleton
digital_signature_service = DigitalSignatureService()
