"""Patient document service — upload, list, and delete patient documents.

Security invariants:
  - PHI is NEVER logged.
  - Clinical data is NEVER hard-deleted (Res. 1888).
  - Files stored in S3 with tenant-scoped paths.
"""
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.core.storage import storage_client
from app.models.tenant.patient_document import PatientDocument

logger = logging.getLogger("dentalos.patient_document")

# Allowed MIME types for patient documents
_ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf",
    "application/dicom",
}

_MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


def _document_to_dict(doc: PatientDocument) -> dict[str, Any]:
    """Serialize a PatientDocument ORM instance to a plain dict."""
    return {
        "id": str(doc.id),
        "patient_id": str(doc.patient_id),
        "document_type": doc.document_type,
        "file_name": doc.file_name,
        "file_size_bytes": doc.file_size_bytes,
        "mime_type": doc.mime_type,
        "description": doc.description,
        "tooth_number": doc.tooth_number,
        "uploaded_by": str(doc.uploaded_by),
        "download_url": None,
        "is_active": doc.is_active,
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
    }


class PatientDocumentService:
    """Stateless patient document service."""

    async def list_documents(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        document_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List active documents for a patient with optional type filter."""
        pid = uuid.UUID(patient_id)

        conditions = [
            PatientDocument.patient_id == pid,
            PatientDocument.is_active.is_(True),
        ]
        if document_type:
            conditions.append(PatientDocument.document_type == document_type)

        # Count
        count_result = await db.execute(
            select(func.count(PatientDocument.id)).where(*conditions)
        )
        total = count_result.scalar_one()

        # Fetch page
        offset = (page - 1) * page_size
        result = await db.execute(
            select(PatientDocument)
            .where(*conditions)
            .order_by(PatientDocument.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        documents = result.scalars().all()

        items = []
        for doc in documents:
            d = _document_to_dict(doc)
            try:
                d["download_url"] = await storage_client.get_presigned_url(
                    key=doc.s3_key
                )
            except Exception:
                pass
            items.append(d)

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def upload_document(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        patient_id: str,
        uploaded_by: str,
        file_data: bytes,
        file_name: str,
        file_size: int,
        mime_type: str,
        document_type: str,
        description: str | None = None,
        tooth_number: int | None = None,
    ) -> dict[str, Any]:
        """Upload a patient document to S3 and create DB record.

        Raises:
            DentalOSError (422) — invalid file type.
            DentalOSError (422) — file too large.
        """
        # Validate MIME type
        if mime_type not in _ALLOWED_MIME_TYPES:
            raise DentalOSError(
                error="SYSTEM_file_type_not_allowed",
                message="Tipo de archivo no permitido. Se aceptan: JPEG, PNG, PDF, DICOM.",
                status_code=422,
            )

        # Validate file size
        if file_size > _MAX_FILE_SIZE_BYTES:
            raise DentalOSError(
                error="SYSTEM_file_too_large",
                message="El archivo excede el tamaño máximo de 25 MB.",
                status_code=422,
            )

        pid = uuid.UUID(patient_id)
        doc_id = uuid.uuid4()

        # Determine extension from mime type
        ext_map = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "application/pdf": "pdf",
            "application/dicom": "dcm",
        }
        ext = ext_map.get(mime_type, "bin")
        s3_key = f"{tenant_id}/{patient_id}/documents/{document_type}/{doc_id}.{ext}"

        # Upload to S3
        await storage_client.upload_file(
            key=s3_key,
            data=file_data,
            content_type=mime_type,
        )

        # Create DB record
        doc = PatientDocument(
            id=doc_id,
            patient_id=pid,
            document_type=document_type,
            file_name=file_name,
            s3_key=s3_key,
            file_size_bytes=file_size,
            mime_type=mime_type,
            description=description,
            tooth_number=tooth_number,
            uploaded_by=uuid.UUID(uploaded_by),
            is_active=True,
        )
        db.add(doc)
        await db.flush()

        logger.info(
            "Document uploaded: patient=%s type=%s",
            patient_id[:8],
            document_type,
        )

        result = _document_to_dict(doc)

        # Generate presigned URL
        try:
            result["download_url"] = await storage_client.get_presigned_url(key=s3_key)
        except Exception:
            pass

        return result

    async def delete_document(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        document_id: str,
    ) -> dict[str, Any]:
        """Soft-delete a patient document.

        Never deletes from S3 — regulatory requirement.

        Raises:
            ResourceNotFoundError (404) — document not found.
        """
        result = await db.execute(
            select(PatientDocument).where(
                PatientDocument.id == uuid.UUID(document_id),
                PatientDocument.patient_id == uuid.UUID(patient_id),
                PatientDocument.is_active.is_(True),
            )
        )
        doc = result.scalar_one_or_none()

        if doc is None:
            raise ResourceNotFoundError(
                error="SYSTEM_not_found",
                resource_name="PatientDocument",
            )

        doc.is_active = False
        doc.deleted_at = datetime.now(UTC)
        await db.flush()

        logger.info(
            "Document deleted: patient=%s doc=%s",
            patient_id[:8],
            document_id[:8],
        )

        return _document_to_dict(doc)


# Module-level singleton
patient_document_service = PatientDocumentService()
