"""Portal authentication routes (PP-01).

Endpoint map:
  POST /portal/auth/login     — Password login or magic link request
  POST /portal/auth/magic     — Magic link verification/redemption
  POST /portal/auth/refresh   — Refresh portal access token
  POST /portal/auth/logout    — Logout (blacklist current JTI)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.portal_context import PortalUser
from app.auth.portal_dependencies import get_current_portal_user, resolve_portal_tenant_from_body
from app.core.database import get_db, get_tenant_db
from app.core.tenant import TenantContext
from app.schemas.portal import (
    MagicLinkResponse,
    MagicLinkVerifyRequest,
    PortalChangePasswordRequest,
    PortalLoginRequest,
    PortalLoginResponse,
    PortalTokenResponse,
)
from app.services.portal_auth_service import portal_auth_service

router = APIRouter(prefix="/portal/auth", tags=["portal-auth"])


@router.post("/login", response_model=PortalLoginResponse | MagicLinkResponse)
async def portal_login(
    body: PortalLoginRequest,
    _tenant: TenantContext = Depends(resolve_portal_tenant_from_body),
    db: AsyncSession = Depends(get_tenant_db),
) -> PortalLoginResponse | MagicLinkResponse:
    """Portal login — password or magic link request.

    For password login: validates credentials, returns tokens.
    For magic link: dispatches link to email/WhatsApp, returns confirmation.
    """
    if body.login_method == "password":
        if not body.password:
            from app.core.exceptions import DentalOSError

            raise DentalOSError(
                error="VALIDATION_missing_password",
                message="Se requiere contraseña para login con password.",
                status_code=422,
            )
        result = await portal_auth_service.login_password(
            db=db,
            tenant_id=body.tenant_id,
            identifier=body.identifier,
            password=body.password,
        )
        return PortalLoginResponse(**result)
    else:
        channel = body.magic_link_channel or "email"
        result = await portal_auth_service.request_magic_link(
            db=db,
            tenant_id=body.tenant_id,
            identifier=body.identifier,
            channel=channel,
        )
        return MagicLinkResponse(**result)


@router.post("/magic", response_model=PortalLoginResponse)
async def verify_magic_link(
    body: MagicLinkVerifyRequest,
    _tenant: TenantContext = Depends(resolve_portal_tenant_from_body),
    db: AsyncSession = Depends(get_tenant_db),
) -> PortalLoginResponse:
    """Verify and redeem a magic link token."""
    result = await portal_auth_service.verify_magic_link(
        db=db,
        tenant_id=body.tenant_id,
        token=body.token,
    )
    return PortalLoginResponse(**result)


@router.post("/refresh", response_model=PortalTokenResponse)
async def refresh_portal_token(
    body: dict,
    db: AsyncSession = Depends(get_db),
) -> PortalTokenResponse:
    """Refresh a portal access token using the refresh token.

    Uses get_db (public schema) because there is no JWT or tenant_id in
    the request body.  The service resolves the tenant from the Redis-stored
    refresh token data and sets the search path internally.
    """
    refresh_token = body.get("refresh_token") if body else None
    if not refresh_token:
        from app.core.exceptions import DentalOSError

        raise DentalOSError(
            error="VALIDATION_missing_refresh_token",
            message="Se requiere refresh_token.",
            status_code=422,
        )
    result = await portal_auth_service.refresh_portal_token(
        db=db,
        raw_refresh_token=refresh_token,
    )
    return PortalTokenResponse(**result)


@router.post("/change-password")
async def change_portal_password(
    body: PortalChangePasswordRequest,
    portal_user: PortalUser = Depends(get_current_portal_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Change portal password (used on first login with temp password)."""
    result = await portal_auth_service.change_password(
        db=db,
        patient_id=portal_user.patient_id,
        new_password=body.new_password,
    )
    return result


@router.post("/logout")
async def portal_logout(
    portal_user: PortalUser = Depends(get_current_portal_user),
) -> dict:
    """Logout the current portal session."""
    result = await portal_auth_service.logout_portal(
        patient_id=portal_user.patient_id,
        token_jti=portal_user.token_jti,
    )
    return result
