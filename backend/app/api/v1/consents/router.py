"""Consent API routes — IC-04 through IC-09.

Endpoint map:
  POST /patients/{patient_id}/consents                     — Create consent
  GET  /patients/{patient_id}/consents                     — List consents
  GET  /patients/{patient_id}/consents/{consent_id}        — Get consent detail
  POST /patients/{patient_id}/consents/{consent_id}/sign   — Sign consent
  GET  /patients/{patient_id}/consents/{consent_id}/pdf    — Generate PDF
  POST /patients/{patient_id}/consents/{consent_id}/void   — Void consent
"""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_permission
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.core.exceptions import ResourceNotFoundError
from app.schemas.consent import (
    ConsentCreate,
    ConsentListResponse,
    ConsentResponse,
    SignConsentRequest,
    VoidConsentRequest,
)
from app.services.consent_service import consent_service

router = APIRouter(
    prefix="/patients/{patient_id}/consents",
    tags=["consents"],
)


@router.post("", response_model=ConsentResponse, status_code=201)
async def create_consent(
    patient_id: str,
    body: ConsentCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("consents:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ConsentResponse:
    """Create a new consent document."""
    result = await consent_service.create_consent(
        db=db,
        patient_id=patient_id,
        doctor_id=current_user.user_id,
        title=body.title,
        template_id=body.template_id,
        content_rendered=body.content_rendered,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="consent",
        resource_id=result["id"],
    )

    return ConsentResponse(**result)


@router.get("", response_model=ConsentListResponse)
async def list_consents(
    patient_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(
        require_permission("consents:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ConsentListResponse:
    """List consents for a patient."""
    result = await consent_service.list_consents(
        db=db,
        patient_id=patient_id,
        page=page,
        page_size=page_size,
    )
    return ConsentListResponse(**result)


@router.get("/{consent_id}", response_model=ConsentResponse)
async def get_consent(
    patient_id: str,
    consent_id: str,
    current_user: AuthenticatedUser = Depends(
        require_permission("consents:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ConsentResponse:
    """Get consent detail."""
    result = await consent_service.get_consent(
        db=db,
        patient_id=patient_id,
        consent_id=consent_id,
    )
    if result is None:
        raise ResourceNotFoundError(
            error="CONSENT_not_found",
            resource_name="Consent",
        )
    return ConsentResponse(**result)


@router.post("/{consent_id}/sign", response_model=ConsentResponse)
async def sign_consent(
    patient_id: str,
    consent_id: str,
    body: SignConsentRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("consents:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ConsentResponse:
    """Sign a consent document."""
    result = await consent_service.sign_consent(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
        patient_id=patient_id,
        consent_id=consent_id,
        signer_id=current_user.user_id,
        signer_type=body.signer_type,
        signature_image_b64=body.signature_image,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="sign",
        resource_type="consent",
        resource_id=consent_id,
    )

    return ConsentResponse(**result)


@router.get("/{consent_id}/pdf")
async def get_consent_pdf(
    patient_id: str,
    consent_id: str,
    current_user: AuthenticatedUser = Depends(
        require_permission("consents:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> Response:
    """Generate and return a PDF for a consent."""
    result = await consent_service.get_consent(
        db=db,
        patient_id=patient_id,
        consent_id=consent_id,
    )
    if result is None:
        raise ResourceNotFoundError(
            error="CONSENT_not_found",
            resource_name="Consent",
        )

    watermark = None
    if result["status"] == "draft":
        watermark = "BORRADOR"
    elif result["status"] == "voided":
        watermark = "ANULADO"

    pdf_bytes = consent_service.generate_pdf(
        consent_data=result,
        watermark=watermark,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="consent-{consent_id[:8]}.pdf"'},
    )


@router.post("/{consent_id}/void", response_model=ConsentResponse)
async def void_consent(
    patient_id: str,
    consent_id: str,
    body: VoidConsentRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(
        require_permission("consents:write")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ConsentResponse:
    """Void a consent. Irreversible."""
    result = await consent_service.void_consent(
        db=db,
        patient_id=patient_id,
        consent_id=consent_id,
        voided_by=current_user.user_id,
        reason=body.reason,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="void",
        resource_type="consent",
        resource_id=consent_id,
    )

    return ConsentResponse(**result)
