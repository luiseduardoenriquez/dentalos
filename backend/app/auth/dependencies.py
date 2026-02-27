"""FastAPI authentication and authorization dependencies."""
import contextlib
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.permissions import get_permissions_for_role
from app.core.cache import get_cached, set_cached
from app.core.database import get_db
from app.core.exceptions import AuthError, TenantError
from app.core.security import decode_access_token
from app.core.tenant import TenantContext, clear_current_tenant, set_current_tenant
from app.models.tenant.user import User
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
    raw_tver: int | None = payload.get("tver")
    token_version: int = raw_tver if raw_tver is not None else 0

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

    # Validate token_version (skip if tver claim was absent for backwards compat)
    if raw_tver is not None:
        await _validate_token_version(
            token_version=token_version,
            user_id=user_id,
            tenant_ctx=tenant_ctx,
            db=db,
        )

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


async def _validate_token_version(
    *,
    token_version: int,
    user_id: str,
    tenant_ctx: TenantContext,
    db: AsyncSession,
) -> None:
    """Validate that the JWT token_version matches the current DB value.

    Fast path: check Redis cache first.
    Slow path: on cache miss, query the tenant DB and cache the result.
    Resilient: if both Redis and DB fail, log a warning and allow the
    request through (don't block auth on transient infrastructure errors).
    """
    tenant_id = tenant_ctx.tenant_id
    cache_key = f"dentalos:{tenant_id}:auth:tver:{user_id}"

    # Try Redis cache first (returns None on miss or Redis error)
    cached_version = await get_cached(cache_key)
    if cached_version is not None:
        if token_version < cached_version:
            raise AuthError(
                error="AUTH_token_version_mismatch",
                message="Token has been revoked. Please log in again.",
                status_code=401,
            )
        return

    # Cache miss: query the tenant DB
    db_version: int | None = None
    try:
        await db.execute(text(f"SET search_path TO {tenant_ctx.schema_name}, public"))
        result = await db.execute(
            select(User.token_version).where(User.id == user_id)
        )
        row = result.scalar_one_or_none()
        if row is not None:
            db_version = row
    except Exception:
        logger.warning(
            "Failed to query token_version from DB for user in tenant %s",
            tenant_id[:8],
        )
    finally:
        # Always restore search_path to public
        with contextlib.suppress(Exception):
            await db.execute(text("SET search_path TO public"))

    if db_version is None:
        # User not found or DB error — allow through to avoid blocking on
        # transient failures. The user will be rejected downstream if they
        # truly don't exist.
        logger.warning(
            "token_version lookup returned None for user in tenant %s — allowing request",
            tenant_id[:8],
        )
        return

    # Cache the DB result for 5 minutes
    await set_cached(cache_key, db_version, ttl_seconds=300)

    if token_version < db_version:
        raise AuthError(
            error="AUTH_token_version_mismatch",
            message="Token has been revoked. Please log in again.",
            status_code=401,
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
