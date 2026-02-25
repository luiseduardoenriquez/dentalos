"""FastAPI authentication and authorization dependencies."""
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.permissions import get_permissions_for_role
from app.core.cache import get_cached
from app.core.database import get_db
from app.core.exceptions import AuthError, TenantError
from app.core.security import decode_access_token
from app.core.tenant import clear_current_tenant, set_current_tenant
from app.services.tenant_service import get_tenant_with_plan

logger = logging.getLogger("dentalos.auth")

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedUser:
    """Decode JWT, validate claims, resolve tenant, return AuthenticatedUser.

    1. Extracts and decodes the RS256 JWT
    2. Checks if the token JTI is blacklisted (Redis)
    3. Resolves the tenant via get_tenant_with_plan()
    4. Sets the TenantContext in ContextVar
    5. Returns an AuthenticatedUser with permissions
    """
    if credentials is None:
        raise AuthError(
            error="AUTH_missing_token",
            message="Authentication required.",
            status_code=401,
        )

    token = credentials.credentials

    try:
        payload = decode_access_token(token)
    except JWTError as e:
        raise AuthError(
            error="AUTH_invalid_token",
            message="Invalid or expired token.",
            status_code=401,
        ) from e

    # Extract claims
    sub: str | None = payload.get("sub")
    tid: str | None = payload.get("tid")
    role: str | None = payload.get("role")
    email: str | None = payload.get("email")
    name: str | None = payload.get("name")
    jti: str | None = payload.get("jti")
    token_version: int = payload.get("tver", 0)

    if not all([sub, tid, role, email, name, jti]):
        raise AuthError(
            error="AUTH_invalid_claims",
            message="Token missing required claims.",
            status_code=401,
        )

    # Extract IDs from prefixed format
    user_id = sub[4:] if sub.startswith("usr_") else sub  # type: ignore[union-attr]
    tenant_id = tid[3:] if tid.startswith("tn_") else tid  # type: ignore[union-attr]

    # Check Redis blacklist
    blacklist_key = f"dentalos:auth:blacklist:{jti}"
    is_blacklisted = await get_cached(blacklist_key)
    if is_blacklisted:
        raise AuthError(
            error="AUTH_token_revoked",
            message="Token has been revoked.",
            status_code=401,
        )

    # Resolve tenant
    try:
        tenant_ctx = await get_tenant_with_plan(tenant_id, db)
    except Exception:
        clear_current_tenant()
        raise AuthError(
            error="AUTH_tenant_not_found",
            message="Tenant not found or inactive.",
            status_code=401,
        ) from None

    # Set tenant context for downstream dependencies
    set_current_tenant(tenant_ctx)

    # Get permissions for role
    permissions = get_permissions_for_role(role)  # type: ignore[arg-type]

    return AuthenticatedUser(
        user_id=user_id,
        email=email,  # type: ignore[arg-type]
        name=name,  # type: ignore[arg-type]
        role=role,  # type: ignore[arg-type]
        permissions=permissions,
        tenant=tenant_ctx,
        token_jti=jti,  # type: ignore[arg-type]
        token_version=token_version,
    )


def require_role(
    allowed_roles: list[str],
) -> Callable[..., Coroutine[Any, Any, AuthenticatedUser]]:
    """Factory that returns a dependency checking the user's role."""

    async def _check_role(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if current_user.role not in allowed_roles:
            raise AuthError(
                error="AUTH_insufficient_role",
                message="You do not have the required role.",
                status_code=403,
            )
        return current_user

    return _check_role


def require_permission(
    permission: str,
) -> Callable[..., Coroutine[Any, Any, AuthenticatedUser]]:
    """Factory that returns a dependency checking a specific permission."""

    async def _check_permission(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if permission not in current_user.permissions:
            raise AuthError(
                error="AUTH_insufficient_permission",
                message=f"Missing required permission: {permission}",
                status_code=403,
            )
        return current_user

    return _check_permission


async def require_active_tenant(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Block write operations on suspended tenants."""
    if current_user.tenant.status == "suspended":
        raise TenantError(
            error="TENANT_suspended",
            message="This clinic is currently suspended. Read-only access.",
            status_code=403,
        )
    return current_user
