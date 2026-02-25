"""Tooth photo service — upload, list, and delete tooth photos.

Security invariants:
  - PHI is NEVER logged.
  - Clinical data is NEVER hard-deleted (Res. 1888).
  - Files stored in S3 with tenant-scoped paths.
  - Max 20 photos per tooth.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.core.storage import storage_client
from app.models.tenant.tooth_photo import ToothPhoto

logger = logging.getLogger("dentalos.tooth_photo")

_MAX_PHOTOS_PER_TOOTH = 20


def _photo_to_dict(photo: ToothPhoto) -> dict[str, Any]:
    """Serialize a ToothPhoto ORM instance to a plain dict."""
    return {
        "id": str(photo.id),
        "patient_id": str(photo.patient_id),
        "tooth_number": photo.tooth_number,
        "s3_key": photo.s3_key,
        "thumbnail_s3_key": photo.thumbnail_s3_key,
        "file_size_bytes": photo.file_size_bytes,
        "mime_type": photo.mime_type,
        "uploaded_by": str(photo.uploaded_by),
        "photo_url": None,
        "thumbnail_url": None,
        "is_active": photo.is_active,
        "created_at": photo.created_at,
        "updated_at": photo.updated_at,
    }


class ToothPhotoService:
    """Stateless tooth photo service."""

    async def upload_photo(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        patient_id: str,
        tooth_number: int,
        uploaded_by: str,
        file_data: bytes,
        file_size: int,
        mime_type: str,
    ) -> dict[str, Any]:
        """Upload a tooth photo to S3 and create DB record.

        Raises:
            DentalOSError (422) — max photos per tooth exceeded.
            DentalOSError (422) — invalid file type.
        """
        pid = uuid.UUID(patient_id)

        # Check photo count limit
        count_result = await db.execute(
            select(func.count(ToothPhoto.id)).where(
                ToothPhoto.patient_id == pid,
                ToothPhoto.tooth_number == tooth_number,
                ToothPhoto.is_active.is_(True),
            )
        )
        count = count_result.scalar_one()
        if count >= _MAX_PHOTOS_PER_TOOTH:
            raise DentalOSError(
                error="SYSTEM_file_upload_failed",
                message=f"Máximo {_MAX_PHOTOS_PER_TOOTH} fotos por diente.",
                status_code=422,
            )

        # Validate mime type
        allowed = {"image/jpeg", "image/png"}
        if mime_type not in allowed:
            raise DentalOSError(
                error="SYSTEM_file_type_not_allowed",
                message="Solo se permiten archivos JPEG y PNG.",
                status_code=422,
            )

        # Generate S3 key
        photo_id = uuid.uuid4()
        ext = "jpg" if "jpeg" in mime_type else "png"
        s3_key = f"{tenant_id}/{patient_id}/teeth/{tooth_number}/{photo_id}.{ext}"

        # Upload to S3
        await storage_client.upload_file(
            key=s3_key,
            data=file_data,
            content_type=mime_type,
        )

        # Create DB record
        photo = ToothPhoto(
            id=photo_id,
            patient_id=pid,
            tooth_number=tooth_number,
            s3_key=s3_key,
            thumbnail_s3_key=None,
            file_size_bytes=file_size,
            mime_type=mime_type,
            uploaded_by=uuid.UUID(uploaded_by),
            is_active=True,
        )
        db.add(photo)
        await db.flush()

        logger.info(
            "Photo uploaded: patient=%s tooth=%d",
            patient_id[:8],
            tooth_number,
        )

        result = _photo_to_dict(photo)

        # Generate presigned URL
        try:
            result["photo_url"] = await storage_client.get_presigned_url(key=s3_key)
        except Exception:
            pass

        return result

    async def list_photos(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        patient_id: str,
        tooth_number: int,
    ) -> dict[str, Any]:
        """List all active photos for a specific tooth."""
        pid = uuid.UUID(patient_id)

        result = await db.execute(
            select(ToothPhoto)
            .where(
                ToothPhoto.patient_id == pid,
                ToothPhoto.tooth_number == tooth_number,
                ToothPhoto.is_active.is_(True),
            )
            .order_by(ToothPhoto.created_at.desc())
        )
        photos = result.scalars().all()

        items = []
        for photo in photos:
            d = _photo_to_dict(photo)
            try:
                d["photo_url"] = await storage_client.get_presigned_url(key=photo.s3_key)
                if photo.thumbnail_s3_key:
                    d["thumbnail_url"] = await storage_client.get_presigned_url(
                        key=photo.thumbnail_s3_key
                    )
            except Exception:
                pass
            items.append(d)

        return {"items": items, "total": len(items)}

    async def delete_photo(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        photo_id: str,
    ) -> dict[str, Any]:
        """Soft-delete a tooth photo.

        Raises:
            ResourceNotFoundError (404) — photo not found.
        """
        result = await db.execute(
            select(ToothPhoto).where(
                ToothPhoto.id == uuid.UUID(photo_id),
                ToothPhoto.patient_id == uuid.UUID(patient_id),
                ToothPhoto.is_active.is_(True),
            )
        )
        photo = result.scalar_one_or_none()

        if photo is None:
            raise ResourceNotFoundError(
                error="SYSTEM_not_found",
                resource_name="ToothPhoto",
            )

        photo.is_active = False
        photo.deleted_at = datetime.now(UTC)
        await db.flush()

        logger.info("Photo deleted: patient=%s photo=%s", patient_id[:8], photo_id[:8])

        return _photo_to_dict(photo)


# Module-level singleton
tooth_photo_service = ToothPhotoService()
