"""Tooth photo API routes — P-16.

Endpoint map:
  POST   /patients/{patient_id}/teeth/{tooth_number}/photos  — Upload photo
  GET    /patients/{patient_id}/teeth/{tooth_number}/photos  — List photos
  DELETE /patients/{patient_id}/teeth/{tooth_number}/photos/{photo_id} — Delete photo
"""

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.schemas.tooth_photo import ToothPhotoListResponse, ToothPhotoResponse
from app.services.tooth_photo_service import tooth_photo_service

router = APIRouter(
    prefix="/patients/{patient_id}/teeth/{tooth_number}/photos",
    tags=["tooth-photos"],
)


@router.post("", response_model=ToothPhotoResponse, status_code=201)
async def upload_tooth_photo(
    patient_id: str,
    tooth_number: int,
    request: Request,
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(
        require_permission("photos:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ToothPhotoResponse:
    """Upload a photo for a specific tooth."""
    file_data = await file.read()

    result = await tooth_photo_service.upload_photo(
        db=db,
        tenant_id=current_user.tenant_id,
        patient_id=patient_id,
        tooth_number=tooth_number,
        uploaded_by=current_user.user_id,
        file_data=file_data,
        file_size=len(file_data),
        mime_type=file.content_type or "image/jpeg",
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="tooth_photo",
        resource_id=result["id"],
    )

    return ToothPhotoResponse(**result)


@router.get("", response_model=ToothPhotoListResponse)
async def list_tooth_photos(
    patient_id: str,
    tooth_number: int,
    current_user: AuthenticatedUser = Depends(
        require_permission("photos:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ToothPhotoListResponse:
    """List all photos for a specific tooth."""
    result = await tooth_photo_service.list_photos(
        db=db,
        tenant_id=current_user.tenant_id,
        patient_id=patient_id,
        tooth_number=tooth_number,
    )
    return ToothPhotoListResponse(
        items=[ToothPhotoResponse(**p) for p in result["items"]],
        total=result["total"],
    )


@router.delete("/{photo_id}", response_model=ToothPhotoResponse)
async def delete_tooth_photo(
    patient_id: str,
    tooth_number: int,
    photo_id: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("photos:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ToothPhotoResponse:
    """Soft-delete a tooth photo."""
    result = await tooth_photo_service.delete_photo(
        db=db,
        patient_id=patient_id,
        photo_id=photo_id,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="delete",
        resource_type="tooth_photo",
        resource_id=photo_id,
    )

    return ToothPhotoResponse(**result)
