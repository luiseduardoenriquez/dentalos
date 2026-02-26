"""Portal access management routes (P-11, registration).

Endpoint map:
  POST /portal/auth/register                     — Complete invitation registration
  POST /patients/{patient_id}/portal-access       — Grant/revoke portal access (staff only)

Note: The /patients/{patient_id}/portal-access endpoint is registered in the
patients router, not here. This file only contains the registration endpoint.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_tenant_db
from app.schemas.portal import PortalLoginResponse, PortalRegisterRequest
from app.services.portal_access_service import portal_access_service

router = APIRouter(prefix="/portal/auth", tags=["portal-auth"])


@router.post("/register", response_model=PortalLoginResponse)
async def complete_portal_registration(
    body: PortalRegisterRequest,
    db: AsyncSession = Depends(get_tenant_db),
) -> PortalLoginResponse:
    """Complete portal registration using invitation token.

    Sets the patient's password and issues portal JWT tokens.
    """
    result = await portal_access_service.complete_registration(
        db=db,
        tenant_id=body.tenant_id,
        token=body.token,
        password=body.password,
    )
    return PortalLoginResponse(**result)
