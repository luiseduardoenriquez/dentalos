"""FastAPI dependencies for portal authentication.

Security invariants:
  - Portal JWT must have scope='portal' — staff tokens are REJECTED
  - Staff JWT must NOT have scope='portal' — prevents portal tokens on staff endpoints
  - sub must start with 'pat_' — extra validation layer
  - Tenant resolution uses the same path as staff (Redis cache -> DB lookup)
"""
import logging

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.portal_context import PortalUser
from app.core.cache import get_cached
from app.core.database import get_db
from app.core.exceptions import AuthError
from app.core.security import decode_access_token
from app.core.tenant import TenantContext, set_current_tenant
from app.services.tenant_service import get_tenant_with_plan

logger = logging.getLogger("dentalos.portal_auth")

portal_bearer_scheme = HTTPBearer(auto_error=False)


async def resolve_portal_tenant_from_body(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TenantContext:
    """Resolve tenant from the request body's tenant_id field.

    Used by portal endpoints (login, magic link, refresh) that receive
    tenant_id in the JSON body rather than in a JWT. Sets the ContextVar
    so get_tenant_db() works downstream.
    """
    body = await request.json()
    tenant_id = body.get("tenant_id")

    if not tenant_id:
        raise AuthError(
            error="AUTH_missing_tenant",
            message="Se requiere el ID de la clínica.",
            status_code=422,
        )

    try:
        tenant_ctx = await get_tenant_with_plan(tenant_id, db)
    except Exception:
        raise AuthError(
            error="AUTH_tenant_not_found",
            message="Clínica no encontrada o inactiva.",
            status_code=401,
        ) from None

    set_current_tenant(tenant_ctx)
    return tenant_ctx


async def get_current_portal_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(portal_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> PortalUser:
    """Decode portal JWT, validate scope, resolve tenant, return PortalUser.

    1. Extracts and decodes the RS256 JWT
    2. Verifies scope == 'portal' (REJECTS staff tokens)
    3. Verifies sub starts with 'pat_' (extra safety)
    4. Checks if the token JTI is blacklisted (Redis)
    5. Resolves the tenant via get_tenant_with_plan()
    6. Sets the TenantContext in ContextVar
    7. Returns a PortalUser
    """
    if credentials is None:
        raise AuthError(
            error="AUTH_missing_token",
            message="Se requiere autenticación del portal.",
            status_code=401,
        )

    token = credentials.credentials

    try:
        payload = decode_access_token(token)
    except JWTError as e:
        raise AuthError(
            error="AUTH_invalid_token",
            message="Token inválido o expirado.",
            status_code=401,
        ) from e

    # ── Scope isolation: MUST be a portal token ──
    scope = payload.get("scope")
    if scope != "portal":
        raise AuthError(
            error="AUTH_invalid_scope",
            message="Este endpoint requiere autenticación del portal.",
            status_code=403,
        )

    # ── Extract claims ──
    sub: str | None = payload.get("sub")
    tid: str | None = payload.get("tid")
    pid: str | None = payload.get("pid")
    email: str | None = payload.get("email")
    name: str | None = payload.get("name")
    jti: str | None = payload.get("jti")

    if not all([sub, tid, pid, email, name, jti]):
        raise AuthError(
            error="AUTH_invalid_claims",
            message="Token del portal con claims incompletos.",
            status_code=401,
        )

    # ── Validate sub prefix ──
    if not sub.startswith("pat_"):
        raise AuthError(
            error="AUTH_invalid_subject",
            message="Token de tipo incorrecto.",
            status_code=403,
        )

    tenant_id = tid[3:] if tid.startswith("tn_") else tid

    # ── Check Redis blacklist ──
    blacklist_key = f"dentalos:auth:blacklist:{jti}"
    is_blacklisted = await get_cached(blacklist_key)
    if is_blacklisted:
        raise AuthError(
            error="AUTH_token_revoked",
            message="El token ha sido revocado.",
            status_code=401,
        )

    # ── Resolve tenant ──
    try:
        tenant_ctx = await get_tenant_with_plan(tenant_id, db)
    except Exception:
        raise AuthError(
            error="AUTH_tenant_not_found",
            message="Clínica no encontrada o inactiva.",
            status_code=401,
        ) from None

    set_current_tenant(tenant_ctx)

    return PortalUser(
        patient_id=pid,
        email=email,
        name=name,
        tenant=tenant_ctx,
        token_jti=jti,
    )
