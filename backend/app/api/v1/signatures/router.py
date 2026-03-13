"""Digital signature API routes — DS-01.

Endpoint map:
  POST /signatures              — Create a new signature
  GET  /signatures/{id}         — Get signature detail
  GET  /signatures/{id}/verify  — Verify a signature
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_permission
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.core.exceptions import ResourceNotFoundError
from app.schemas.digital_signature import (
    SignatureCreate,
    SignatureResponse,
    SignatureVerifyResponse,
)
from app.services.digital_signature_service import digital_signature_service

router = APIRouter(prefix="/signatures", tags=["signatures"])


@router.post("", response_model=SignatureResponse, status_code=201)
async def create_signature(
    body: SignatureCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("signatures:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> SignatureResponse:
    """Create a new digital signature for a document."""
    result = await digital_signature_service.create_signature(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
        signer_id=current_user.user_id,
        document_type=body.document_type,
        document_id=body.document_id,
        signer_type=body.signer_type,
        signature_image_b64=body.signature_image,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="digital_signature",
        resource_id=result["id"],
    )

    return SignatureResponse(**result)


@router.get("/{signature_id}", response_model=SignatureResponse)
async def get_signature(
    signature_id: str,
    current_user: AuthenticatedUser = Depends(
        require_permission("signatures:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> SignatureResponse:
    """Get signature detail by ID."""
    result = await digital_signature_service.get_signature(
        db=db,
        signature_id=signature_id,
    )
    if result is None:
        raise ResourceNotFoundError(
            error="SIGNATURE_not_found",
            resource_name="DigitalSignature",
        )
    return SignatureResponse(**result)


@router.get("/{signature_id}/verify", response_model=SignatureVerifyResponse)
async def verify_signature(
    signature_id: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("signatures:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> SignatureVerifyResponse:
    """Verify a signature by recomputing its canonical hash."""
    result = await digital_signature_service.verify_signature(
        db=db,
        signature_id=signature_id,
        verified_by=current_user.user_id,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="verify",
        resource_type="digital_signature",
        resource_id=signature_id,
    )

    return SignatureVerifyResponse(**result)
