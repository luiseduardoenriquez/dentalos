"""Auth service — registration, login, token lifecycle, and team invites.

Handles all authentication and authorization flows for DentalOS multi-tenant
dental SaaS. Every method operates across the public schema (tenants,
memberships) and individual tenant schemas (users, sessions, invites).

Security invariants:
  - Generic error messages on all credential failures (no user enumeration).
  - PHI (emails, names, phones) is NEVER logged.
  - Refresh tokens stored as SHA-256 hashes; raw values never persisted.
  - Replay detection: a reused refresh token revokes ALL sessions for that user.
  - Account lockout after configurable failed login attempts.
"""

import contextlib
import hashlib
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import get_permissions_for_role
from app.core.cache import cache_delete, get_cached, set_cached
from app.core.config import settings
from app.core.exceptions import (
    AuthError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.core.rate_limit import check_rate_limit
from app.core.security import (
    create_access_token,
    create_pre_auth_token,
    create_refresh_token,
    decode_pre_auth_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.public.plan import Plan
from app.models.public.tenant import Tenant
from app.models.public.user_tenant_membership import UserTenantMembership
from app.models.tenant.user import User
from app.models.tenant.user_invite import UserInvite
from app.models.tenant.user_session import UserSession
from app.core.queue import publish_message
from app.schemas.queue import QueueMessage
from app.services.tenant_service import (
    generate_schema_name,
    generate_slug,
    get_tenant_with_plan,
    provision_tenant_schema,
)

logger = logging.getLogger("dentalos.auth")

# ─── Constants ──────────────────────────────────────────────

COUNTRY_DEFAULTS: dict[str, dict[str, str]] = {
    "CO": {"timezone": "America/Bogota", "currency_code": "COP", "locale": "es-CO"},
    "MX": {"timezone": "America/Mexico_City", "currency_code": "MXN", "locale": "es-MX"},
    "CL": {"timezone": "America/Santiago", "currency_code": "CLP", "locale": "es-CL"},
    "AR": {"timezone": "America/Argentina/Buenos_Aires", "currency_code": "ARS", "locale": "es-AR"},
    "PE": {"timezone": "America/Lima", "currency_code": "PEN", "locale": "es-PE"},
    "EC": {"timezone": "America/Guayaquil", "currency_code": "USD", "locale": "es-EC"},
}

_GENERIC_CREDENTIALS_ERROR = "Invalid credentials."
_ACCOUNT_LOCKED_ERROR = "Account temporarily locked. Please try again later."
_INVALID_TOKEN_ERROR = "Invalid or expired token."  # noqa: S105

# Redis key prefixes for password reset and email verification tokens
_RESET_TOKEN_PREFIX = "dentalos:auth:reset:"  # noqa: S105
_VERIFY_EMAIL_PREFIX = "dentalos:auth:verify_email:"
_JTI_BLACKLIST_PREFIX = "dentalos:auth:jti_blacklist:"

_RESET_TOKEN_TTL = 3600  # 1 hour
_VERIFY_EMAIL_TTL = 86400  # 24 hours


# ─── Auth Service ───────────────────────────────────────────


class AuthService:
    """Stateless auth service — all state flows through the DB session.

    Each public method corresponds to one API endpoint. Methods accept
    primitive arguments (not Pydantic models) so they can be called from
    any context (API routes, CLI, workers, tests).
    """

    # ─── Registration ───────────────────────────────────

    async def register(
        self,
        *,
        email: str,
        password: str,
        name: str,
        clinic_name: str,
        country: str,
        phone: str | None,
        ip_address: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Register a new clinic owner and provision their tenant.

        Creates the tenant in the public schema, provisions a dedicated
        PostgreSQL schema, creates the owner user inside it, and issues
        initial JWT + refresh tokens.

        Returns a dict with access_token, refresh_token, user, and tenant data.
        On failure after schema creation, performs cleanup (DROP SCHEMA).
        """
        await check_rate_limit(f"rl:register:{ip_address}", limit=3, window_seconds=3600)

        email = email.strip().lower()
        name = name.strip()
        clinic_name = clinic_name.strip()

        # Check if email is already registered as a tenant owner
        existing = await db.execute(
            select(Tenant.id).where(
                func.lower(Tenant.owner_email) == email,
                Tenant.status.in_(["pending", "active", "suspended"]),
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ResourceConflictError(
                error="AUTH_email_already_registered",
                message="An account with this email already exists.",
            )

        # Find the free plan
        plan_result = await db.execute(
            select(Plan).where(Plan.slug == "free", Plan.is_active.is_(True))
        )
        plan = plan_result.scalar_one_or_none()
        if plan is None:
            logger.error("Default 'free' plan not found in database")
            raise AuthError(
                error="SYSTEM_configuration_error",
                message="Registration is temporarily unavailable.",
                status_code=500,
            )

        # Resolve country defaults
        defaults = COUNTRY_DEFAULTS.get(country, COUNTRY_DEFAULTS["CO"])

        schema_name = generate_schema_name()
        slug = generate_slug(clinic_name)

        # Create tenant in public schema
        tenant = Tenant(
            slug=slug,
            schema_name=schema_name,
            name=clinic_name,
            country_code=country,
            timezone=defaults["timezone"],
            currency_code=defaults["currency_code"],
            locale=defaults["locale"],
            plan_id=plan.id,
            owner_email=email,
            phone=phone,
            status="pending",
            onboarding_step=0,
            settings={},
        )
        db.add(tenant)
        await db.flush()  # Generate tenant.id without committing
        tenant_id = tenant.id

        try:
            # Provision the schema (CREATE SCHEMA + Alembic migrations)
            await provision_tenant_schema(schema_name, db)

            # Switch to the new tenant schema
            await db.execute(text(f"SET search_path TO {schema_name}, public"))

            # Create the owner user in the tenant schema
            password_hash = hash_password(password)
            user = User(
                email=email,
                password_hash=password_hash,
                name=name,
                phone=phone,
                role="clinic_owner",
                is_active=True,
                email_verified=False,
                failed_login_attempts=0,
                token_version=0,
            )
            db.add(user)
            await db.flush()  # Generate user.id

            # Update tenant with owner reference and activate
            tenant.owner_user_id = user.id
            tenant.status = "active"

            # Create membership in public schema
            membership = UserTenantMembership(
                user_id=user.id,
                tenant_id=tenant_id,
                role="clinic_owner",
                status="active",
                is_primary=True,
            )
            db.add(membership)

            # Create refresh token + session
            raw_refresh, refresh_hash = create_refresh_token()
            session = UserSession(
                user_id=user.id,
                refresh_token_hash=refresh_hash,
                ip_address=ip_address,
                expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
                is_revoked=False,
            )
            db.add(session)

            await db.commit()

            # Issue access token
            permissions = list(get_permissions_for_role("clinic_owner"))
            access_token = create_access_token(
                user_id=str(user.id),
                tenant_id=str(tenant_id),
                role="clinic_owner",
                permissions=permissions,
                email=email,
                name=name,
                token_version=0,
            )

            logger.info(
                "Registration completed for tenant %s (schema=%s)",
                str(tenant_id)[:8],
                schema_name,
            )

            return {
                "access_token": access_token,
                "refresh_token": raw_refresh,
                "token_type": "bearer",
                "expires_in": settings.access_token_expire_minutes * 60,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                    "phone": user.phone,
                    "avatar_url": user.avatar_url,
                    "professional_license": user.professional_license,
                    "specialties": user.specialties,
                    "is_active": user.is_active,
                    "email_verified": user.email_verified,
                },
                "tenant": {
                    "id": str(tenant_id),
                    "slug": tenant.slug,
                    "name": tenant.name,
                    "country_code": tenant.country_code,
                    "timezone": tenant.timezone,
                    "currency_code": tenant.currency_code,
                    "status": tenant.status,
                    "plan_name": plan.name,
                    "logo_url": tenant.logo_url,
                },
            }

        except Exception:
            await db.rollback()
            # Cleanup: drop the provisioned schema if it was created
            try:
                await db.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
                await db.execute(
                    text("DELETE FROM public.tenants WHERE id = :tid"),
                    {"tid": tenant_id},
                )
                await db.commit()
            except Exception:
                logger.error("Cleanup failed for schema %s after registration error", schema_name)
            raise

        finally:
            # Always reset search_path back to public
            with contextlib.suppress(Exception):
                await db.execute(text("SET search_path TO public"))

    # ─── Login ──────────────────────────────────────────

    async def login(
        self,
        *,
        email: str,
        password: str,
        ip_address: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Authenticate a user by email and password.

        For single-tenant users, returns access + refresh tokens directly.
        For multi-tenant users, returns a pre-auth token and a list of
        tenants for the client to select from.
        """
        await check_rate_limit(f"rl:login:{ip_address}", limit=15, window_seconds=900)

        email = email.strip().lower()

        # Find all active tenants and scan each for a user with this email.
        # UserTenantMembership stores user_id (not email), so we must check
        # each tenant schema for the user, then cross-reference memberships.
        tenants_result = await db.execute(
            select(Tenant).where(Tenant.status == "active")
        )
        active_tenants = tenants_result.scalars().all()

        user = None
        user_tenant = None
        rows: list[tuple[Any, Any]] = []

        for tenant in active_tenants:
            found_user = await self._load_user_from_tenant(
                email=email,
                schema_name=tenant.schema_name,
                db=db,
            )
            if found_user is not None:
                user = found_user
                user_tenant = tenant
                # Now find all memberships for this user
                membership_stmt = (
                    select(Tenant, UserTenantMembership)
                    .join(
                        UserTenantMembership,
                        UserTenantMembership.tenant_id == Tenant.id,
                    )
                    .where(
                        UserTenantMembership.user_id == user.id,
                        Tenant.status == "active",
                        UserTenantMembership.status == "active",
                    )
                    .order_by(UserTenantMembership.is_primary.desc())
                )
                membership_result = await db.execute(membership_stmt)
                rows = membership_result.all()
                break

        if not rows or user is None or user_tenant is None:
            # Don't reveal whether the email exists
            logger.info("Login attempt for unknown email (no tenants found)")
            raise AuthError(
                error="AUTH_invalid_credentials",
                message=_GENERIC_CREDENTIALS_ERROR,
            )

        # Use the primary (or first) tenant to verify the password
        primary_tenant, primary_membership = rows[0]

        # Check account lockout
        self._check_lockout(user)

        # Verify password
        if not verify_password(password, user.password_hash):
            await self._handle_failed_login(user, primary_tenant.schema_name, db)
            raise AuthError(
                error="AUTH_invalid_credentials",
                message=_GENERIC_CREDENTIALS_ERROR,
            )

        # Password correct: reset failed attempts and update last_login_at
        await self._reset_failed_attempts(user, primary_tenant.schema_name, db)

        # Single tenant: issue tokens directly
        if len(rows) == 1:
            return await self._issue_login_tokens(
                user=user,
                tenant=primary_tenant,
                membership=primary_membership,
                ip_address=ip_address,
                db=db,
            )

        # Multiple tenants: issue pre-auth token for tenant selection
        pre_auth_token = create_pre_auth_token(
            user_id=str(user.id),
            email=email,
        )

        tenants_list = [
            {
                "tenant_id": str(t.id),
                "tenant_name": t.name,
                "tenant_slug": t.slug,
                "role": m.role,
                "is_primary": m.is_primary,
            }
            for t, m in rows
        ]

        logger.info(
            "Multi-tenant login: user has %d tenants, issuing pre-auth token",
            len(rows),
        )

        return {
            "requires_tenant_selection": True,
            "pre_auth_token": pre_auth_token,
            "tenants": tenants_list,
            "message": "Please select a clinic to continue.",
        }

    # ─── Tenant Selection (multi-clinic) ────────────────

    async def select_tenant(
        self,
        *,
        pre_auth_token: str,
        tenant_id: str,
        ip_address: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Complete login by selecting a specific tenant after multi-tenant auth.

        Validates the pre-auth token, verifies the user has a membership for
        the requested tenant, and issues full JWT + refresh tokens.
        """
        try:
            payload = decode_pre_auth_token(pre_auth_token)
        except JWTError:
            raise AuthError(
                error="AUTH_invalid_token",
                message=_INVALID_TOKEN_ERROR,
            ) from None

        # Extract user ID (strip the "usr_" prefix)
        raw_user_id = payload["sub"]
        user_id = raw_user_id.removeprefix("usr_")
        user_email = payload["email"]

        await check_rate_limit(f"rl:switch:{user_id}", limit=100, window_seconds=3600)

        # Verify membership exists for this tenant
        membership_result = await db.execute(
            select(UserTenantMembership, Tenant)
            .join(Tenant, Tenant.id == UserTenantMembership.tenant_id)
            .where(
                UserTenantMembership.user_id == uuid.UUID(user_id),
                UserTenantMembership.tenant_id == uuid.UUID(tenant_id),
                UserTenantMembership.status == "active",
                Tenant.status == "active",
            )
        )
        row = membership_result.one_or_none()
        if row is None:
            raise AuthError(
                error="AUTH_invalid_tenant",
                message="You do not have access to this clinic.",
                status_code=403,
            )

        membership, tenant = row

        # Load user from the target tenant schema
        user = await self._load_user_from_tenant(
            email=user_email,
            schema_name=tenant.schema_name,
            db=db,
        )
        if user is None:
            raise AuthError(
                error="AUTH_invalid_credentials",
                message=_GENERIC_CREDENTIALS_ERROR,
            )

        return await self._issue_login_tokens(
            user=user,
            tenant=tenant,
            membership=membership,
            ip_address=ip_address,
            db=db,
        )

    # ─── Token Refresh ──────────────────────────────────

    async def refresh_token(
        self,
        *,
        raw_refresh_token: str,
        ip_address: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Rotate a refresh token and issue a new access token.

        Implements replay detection: if the presented refresh token has
        already been revoked (reuse), ALL sessions for that user are
        immediately revoked as a security measure.
        """
        token_hash = hash_refresh_token(raw_refresh_token)

        # Find the session across all tenant schemas via brute approach:
        # Sessions live in tenant schemas, so we need the tenant context.
        # Strategy: look up all active memberships, then check each tenant
        # schema for this session. For MVP, we scan active tenants.
        session_data = await self._find_session_by_refresh_hash(token_hash, db)

        if session_data is None:
            raise AuthError(
                error="AUTH_invalid_token",
                message=_INVALID_TOKEN_ERROR,
            )

        session_record, tenant, schema_name = session_data

        # Replay detection: if session is already revoked, someone reused a token
        if session_record.is_revoked:
            logger.warning(
                "Refresh token replay detected for session %s — revoking all sessions",
                str(session_record.id)[:8],
            )
            await self._revoke_all_sessions(
                user_id=session_record.user_id,
                schema_name=schema_name,
                db=db,
            )
            raise AuthError(
                error="AUTH_token_reuse_detected",
                message="Security violation detected. All sessions have been revoked.",
            )

        # Check expiry
        if session_record.expires_at < datetime.now(UTC):
            raise AuthError(
                error="AUTH_token_expired",
                message="Refresh token has expired. Please log in again.",
            )

        # Load user from tenant schema
        await db.execute(text(f"SET search_path TO {schema_name}, public"))
        try:
            user_result = await db.execute(
                select(User).where(
                    User.id == session_record.user_id,
                    User.is_active.is_(True),
                )
            )
            user = user_result.scalar_one_or_none()

            if user is None:
                raise AuthError(
                    error="AUTH_invalid_credentials",
                    message=_GENERIC_CREDENTIALS_ERROR,
                )

            # Rotate: revoke old session and create new one
            session_record.is_revoked = True

            raw_new, new_hash = create_refresh_token()
            new_session = UserSession(
                user_id=user.id,
                refresh_token_hash=new_hash,
                ip_address=ip_address,
                expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
                is_revoked=False,
            )
            db.add(new_session)
            await db.flush()

            # Link old session to the replacement
            session_record.replaced_by = new_session.id

            await db.commit()

            # Load membership to get role
            membership_result = await db.execute(
                select(UserTenantMembership).where(
                    UserTenantMembership.user_id == user.id,
                    UserTenantMembership.tenant_id == tenant.id,
                    UserTenantMembership.status == "active",
                )
            )
            membership = membership_result.scalar_one_or_none()
            role = membership.role if membership else user.role

            # Issue new access token
            permissions = list(get_permissions_for_role(role))
            access_token = create_access_token(
                user_id=str(user.id),
                tenant_id=str(tenant.id),
                role=role,
                permissions=permissions,
                email=user.email,
                name=user.name,
                token_version=user.token_version,
            )

            return {
                "access_token": access_token,
                "refresh_token": raw_new,
                "token_type": "bearer",
                "expires_in": settings.access_token_expire_minutes * 60,
            }

        finally:
            with contextlib.suppress(Exception):
                await db.execute(text("SET search_path TO public"))

    # ─── Logout ─────────────────────────────────────────

    async def logout(
        self,
        *,
        jti: str,
        user_id: str,
        raw_refresh_token: str | None,
        tenant_schema: str,
        db: AsyncSession,
    ) -> None:
        """Invalidate the current session.

        Blacklists the JWT ID (jti) in Redis for the remaining token
        lifetime and revokes the refresh token session.
        """
        # Blacklist the JTI in Redis (TTL = access token lifetime)
        jti_key = f"{_JTI_BLACKLIST_PREFIX}{jti}"
        await set_cached(jti_key, True, ttl_seconds=settings.access_token_expire_minutes * 60)

        if raw_refresh_token:
            token_hash = hash_refresh_token(raw_refresh_token)
            await db.execute(text(f"SET search_path TO {tenant_schema}, public"))
            try:
                result = await db.execute(
                    select(UserSession).where(
                        UserSession.refresh_token_hash == token_hash,
                        UserSession.user_id == uuid.UUID(user_id),
                    )
                )
                session_record = result.scalar_one_or_none()
                if session_record and not session_record.is_revoked:
                    session_record.is_revoked = True
                    await db.commit()
            finally:
                with contextlib.suppress(Exception):
                    await db.execute(text("SET search_path TO public"))

        logger.info("User logged out (jti=%s...)", jti[:8] if jti else "none")

    # ─── Get Me ─────────────────────────────────────────

    async def get_me(
        self,
        *,
        user_id: str,
        tenant_id: str,
        tenant_schema: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Return the current user's profile, tenant, permissions, and plan limits."""
        await db.execute(text(f"SET search_path TO {tenant_schema}, public"))
        try:
            user_result = await db.execute(
                select(User).where(
                    User.id == uuid.UUID(user_id),
                    User.is_active.is_(True),
                )
            )
            user = user_result.scalar_one_or_none()

            if user is None:
                raise ResourceNotFoundError(
                    error="AUTH_user_not_found",
                    resource_name="User",
                )

            # Load tenant context with plan info (uses cache)
            tenant_ctx = await get_tenant_with_plan(tenant_id, db)

            permissions = sorted(get_permissions_for_role(user.role))

            return {
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                    "phone": user.phone,
                    "avatar_url": user.avatar_url,
                    "professional_license": user.professional_license,
                    "specialties": user.specialties,
                    "is_active": user.is_active,
                    "email_verified": user.email_verified,
                },
                "tenant": {
                    "id": tenant_ctx.tenant_id,
                    "slug": "",  # Not available in TenantContext; fetched below
                    "name": "",
                    "country_code": tenant_ctx.country_code,
                    "timezone": tenant_ctx.timezone,
                    "currency_code": tenant_ctx.currency_code,
                    "status": tenant_ctx.status,
                    "plan_name": tenant_ctx.plan_name,
                    "logo_url": None,
                },
                "permissions": permissions,
                "feature_flags": tenant_ctx.features,
                "plan_limits": tenant_ctx.limits,
            }

        finally:
            with contextlib.suppress(Exception):
                await db.execute(text("SET search_path TO public"))

    # ─── Forgot Password ────────────────────────────────

    async def forgot_password(
        self,
        *,
        email: str,
        ip_address: str,
        db: AsyncSession,
    ) -> None:
        """Initiate a password reset flow.

        Always returns successfully to prevent email enumeration. If the
        email exists, a reset token is stored in Redis and an email job
        is enqueued (currently logged).
        """
        await check_rate_limit(f"rl:forgot:{ip_address}", limit=3, window_seconds=3600)

        email = email.strip().lower()

        # Find tenant for this email
        tenant_result = await db.execute(
            select(Tenant).where(
                func.lower(Tenant.owner_email) == email,
                Tenant.status == "active",
            )
        )
        tenant = tenant_result.scalar_one_or_none()

        if tenant is None:
            # Don't reveal whether the email exists
            logger.info("Password reset requested for non-existent account")
            return

        # Load user from tenant schema
        user = await self._load_user_from_tenant(
            email=email,
            schema_name=tenant.schema_name,
            db=db,
        )
        if user is None:
            return

        # Generate reset token and store hash in Redis
        raw_token = uuid.uuid4().hex
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        redis_key = f"{_RESET_TOKEN_PREFIX}{token_hash}"

        await set_cached(
            redis_key,
            {
                "user_id": str(user.id),
                "tenant_id": str(tenant.id),
                "schema_name": tenant.schema_name,
            },
            ttl_seconds=_RESET_TOKEN_TTL,
        )

        # Enqueue password reset email
        await publish_message(
            "notifications",
            QueueMessage(
                tenant_id=str(tenant.id),
                job_type="email.send",
                payload={
                    "to_email": user.email,
                    "to_name": user.name or "",
                    "subject": "Restablecer contraseña — DentalOS",
                    "template_name": "password_reset_es.html",
                    "context": {
                        "user_name": user.name or user.email,
                        "clinic_name": tenant.name,
                        "expiry_minutes": str(_RESET_TOKEN_TTL // 60),
                        "reset_link": f"{settings.frontend_url}/auth/reset-password?token={raw_token}",
                        "current_year": "2026",
                    },
                },
            ),
        )
        logger.info(
            "Password reset token generated for tenant %s (token=%s...)",
            str(tenant.id)[:8],
            raw_token[:8],
        )

    # ─── Reset Password ────────────────────────────────

    async def reset_password(
        self,
        *,
        token: str,
        new_password: str,
        db: AsyncSession,
    ) -> None:
        """Complete a password reset using a valid reset token.

        Updates the password, increments token_version to force-logout all
        existing sessions, and revokes every active session.
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        redis_key = f"{_RESET_TOKEN_PREFIX}{token_hash}"

        token_data = await get_cached(redis_key)
        if token_data is None:
            raise AuthError(
                error="AUTH_invalid_token",
                message=_INVALID_TOKEN_ERROR,
            )

        user_id = token_data["user_id"]
        schema_name = token_data["schema_name"]

        await db.execute(text(f"SET search_path TO {schema_name}, public"))
        try:
            user_result = await db.execute(
                select(User).where(User.id == uuid.UUID(user_id))
            )
            user = user_result.scalar_one_or_none()

            if user is None:
                raise AuthError(
                    error="AUTH_invalid_token",
                    message=_INVALID_TOKEN_ERROR,
                )

            # Update password and force-logout all sessions
            user.password_hash = hash_password(new_password)
            user.token_version += 1
            user.failed_login_attempts = 0
            user.locked_until = None

            # Revoke all sessions
            await db.execute(
                update(UserSession)
                .where(
                    UserSession.user_id == user.id,
                    UserSession.is_revoked.is_(False),
                )
                .values(is_revoked=True)
            )

            await db.commit()

            # Delete the reset token from Redis
            await cache_delete(redis_key)

            # Invalidate token_version cache so auth checks fetch the new version
            tenant_id = token_data["tenant_id"]
            tver_key = f"dentalos:{tenant_id}:auth:tver:{user_id}"
            await cache_delete(tver_key)

            logger.info("Password reset completed for user in schema %s", schema_name)

        finally:
            with contextlib.suppress(Exception):
                await db.execute(text("SET search_path TO public"))

    # ─── Change Password ────────────────────────────────

    async def change_password(
        self,
        *,
        user_id: str,
        current_password: str,
        new_password: str,
        current_session_token_hash: str | None,
        tenant_id: str,
        tenant_schema: str,
        db: AsyncSession,
    ) -> None:
        """Change password for an authenticated user.

        Verifies the current password, updates the hash, and revokes all
        OTHER sessions (keeps the current one active).
        """
        await db.execute(text(f"SET search_path TO {tenant_schema}, public"))
        try:
            user_result = await db.execute(
                select(User).where(
                    User.id == uuid.UUID(user_id),
                    User.is_active.is_(True),
                )
            )
            user = user_result.scalar_one_or_none()

            if user is None:
                raise ResourceNotFoundError(
                    error="AUTH_user_not_found",
                    resource_name="User",
                )

            if not verify_password(current_password, user.password_hash):
                raise AuthError(
                    error="AUTH_invalid_credentials",
                    message="Current password is incorrect.",
                )

            user.password_hash = hash_password(new_password)
            user.token_version += 1

            # Revoke all OTHER sessions (keep the current one)
            revoke_filter = [
                UserSession.user_id == user.id,
                UserSession.is_revoked.is_(False),
            ]
            if current_session_token_hash:
                revoke_filter.append(
                    UserSession.refresh_token_hash != current_session_token_hash
                )

            await db.execute(
                update(UserSession)
                .where(*revoke_filter)
                .values(is_revoked=True)
            )

            await db.commit()

            # Invalidate token_version cache so auth checks fetch the new version
            tver_key = f"dentalos:{tenant_id}:auth:tver:{user_id}"
            await cache_delete(tver_key)

            logger.info("Password changed for user in schema %s", tenant_schema)

        finally:
            with contextlib.suppress(Exception):
                await db.execute(text("SET search_path TO public"))

    # ─── Invite User ────────────────────────────────────

    async def invite_user(
        self,
        *,
        inviter_user_id: str,
        email: str,
        role: str,
        tenant_id: str,
        tenant_schema: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Invite a new team member to the clinic.

        Validates plan limits, checks for duplicate email, creates an
        invite record with a hashed token, and enqueues an email.
        """
        email = email.strip().lower()

        await db.execute(text(f"SET search_path TO {tenant_schema}, public"))
        try:
            # Verify inviter is clinic_owner
            inviter_result = await db.execute(
                select(User).where(
                    User.id == uuid.UUID(inviter_user_id),
                    User.is_active.is_(True),
                )
            )
            inviter = inviter_result.scalar_one_or_none()

            if inviter is None or inviter.role != "clinic_owner":
                raise AuthError(
                    error="AUTH_insufficient_permissions",
                    message="Only clinic owners can invite team members.",
                    status_code=403,
                )

            # Check plan limits (max_users)
            tenant_ctx = await get_tenant_with_plan(tenant_id, db)
            max_users = tenant_ctx.limits.get("max_users", 1)

            current_members_result = await db.execute(
                select(func.count(UserTenantMembership.id)).where(
                    UserTenantMembership.tenant_id == uuid.UUID(tenant_id),
                    UserTenantMembership.status == "active",
                )
            )
            current_count = current_members_result.scalar() or 0

            if current_count >= max_users:
                raise AuthError(
                    error="TENANT_plan_limit_reached",
                    message="Your plan's user limit has been reached. Please upgrade.",
                    status_code=403,
                )

            # Check if email already exists in this tenant
            existing_user_result = await db.execute(
                select(User.id).where(func.lower(User.email) == email)
            )
            if existing_user_result.scalar_one_or_none() is not None:
                raise ResourceConflictError(
                    error="AUTH_user_already_exists",
                    message="A user with this email already exists in this clinic.",
                )

            # Check for pending invites to the same email
            pending_invite_result = await db.execute(
                select(UserInvite.id).where(
                    func.lower(UserInvite.email) == email,
                    UserInvite.status == "pending",
                )
            )
            if pending_invite_result.scalar_one_or_none() is not None:
                raise ResourceConflictError(
                    error="AUTH_invite_already_pending",
                    message="An invitation has already been sent to this email.",
                )

            # Generate invite token
            raw_token = uuid.uuid4().hex
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

            invite = UserInvite(
                email=email,
                role=role,
                invited_by=uuid.UUID(inviter_user_id),
                token_hash=token_hash,
                status="pending",
                expires_at=datetime.now(UTC) + timedelta(days=7),
            )
            db.add(invite)
            await db.commit()

            # Resolve names for the invite email
            inviter_name = inviter.name or inviter.email
            tenant_record = await db.execute(
                select(Tenant).where(Tenant.id == uuid.UUID(tenant_id))
            )
            tenant_obj = tenant_record.scalar_one_or_none()
            clinic_name = tenant_obj.name if tenant_obj else ""

            # Enqueue invite email
            await publish_message(
                "notifications",
                QueueMessage(
                    tenant_id=str(tenant_id),
                    job_type="email.send",
                    payload={
                        "to_email": email,
                        "to_name": "",
                        "subject": f"Te invitaron a unirte a DentalOS",
                        "template_name": "team_invite_es.html",
                        "context": {
                            "inviter_name": inviter_name,
                            "clinic_name": clinic_name,
                            "role_label": role,
                            "invite_link": f"{settings.frontend_url}/auth/accept-invite?token={raw_token}",
                            "current_year": "2026",
                        },
                    },
                ),
            )
            logger.info(
                "Invite created in tenant %s for role=%s (token=%s...)",
                str(tenant_id)[:8],
                role,
                raw_token[:8],
            )

            return {
                "invite_id": str(invite.id),
                "email": email,
                "role": role,
                "expires_at": invite.expires_at.isoformat(),
                "token": raw_token,  # Returned to be sent in the invite email
            }

        finally:
            with contextlib.suppress(Exception):
                await db.execute(text("SET search_path TO public"))

    # ─── Accept Invite ──────────────────────────────────

    async def accept_invite(
        self,
        *,
        token: str,
        password: str,
        name: str,
        phone: str | None,
        ip_address: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Accept a team invite, creating a user account and issuing tokens.

        The invite token is looked up across all tenant schemas. Once found,
        a user is created in the tenant schema and a membership is added to
        the public schema.
        """
        name = name.strip()
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Find the invite across tenant schemas
        invite_data = await self._find_invite_by_token_hash(token_hash, db)
        if invite_data is None:
            raise AuthError(
                error="AUTH_invalid_token",
                message=_INVALID_TOKEN_ERROR,
            )

        invite, tenant, schema_name = invite_data

        # Check invite status and expiry
        if invite.status != "pending":
            raise AuthError(
                error="AUTH_invite_already_used",
                message="This invitation has already been used or cancelled.",
            )

        if invite.expires_at < datetime.now(UTC):
            invite.status = "expired"
            await db.commit()
            raise AuthError(
                error="AUTH_invite_expired",
                message="This invitation has expired. Please request a new one.",
            )

        # Create user in tenant schema
        await db.execute(text(f"SET search_path TO {schema_name}, public"))
        try:
            password_hash_val = hash_password(password)
            user = User(
                email=invite.email,
                password_hash=password_hash_val,
                name=name,
                phone=phone,
                role=invite.role,
                is_active=True,
                email_verified=False,
                failed_login_attempts=0,
                token_version=0,
            )
            db.add(user)
            await db.flush()

            # Create membership in public schema
            membership = UserTenantMembership(
                user_id=user.id,
                tenant_id=tenant.id,
                role=invite.role,
                status="active",
                is_primary=True,
                invited_by=invite.invited_by,
            )
            db.add(membership)

            # Mark invite as accepted
            invite.status = "accepted"
            invite.accepted_at = datetime.now(UTC)

            # Create session
            raw_refresh, refresh_hash = create_refresh_token()
            session = UserSession(
                user_id=user.id,
                refresh_token_hash=refresh_hash,
                ip_address=ip_address,
                expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
                is_revoked=False,
            )
            db.add(session)

            await db.commit()

            # Issue access token
            permissions = list(get_permissions_for_role(invite.role))
            plan = tenant.plan

            access_token = create_access_token(
                user_id=str(user.id),
                tenant_id=str(tenant.id),
                role=invite.role,
                permissions=permissions,
                email=user.email,
                name=user.name,
                token_version=0,
            )

            logger.info(
                "Invite accepted in tenant %s: new %s user created",
                str(tenant.id)[:8],
                invite.role,
            )

            return {
                "access_token": access_token,
                "refresh_token": raw_refresh,
                "token_type": "bearer",
                "expires_in": settings.access_token_expire_minutes * 60,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                    "phone": user.phone,
                    "avatar_url": user.avatar_url,
                    "professional_license": user.professional_license,
                    "specialties": user.specialties,
                    "is_active": user.is_active,
                    "email_verified": user.email_verified,
                },
                "tenant": {
                    "id": str(tenant.id),
                    "slug": tenant.slug,
                    "name": tenant.name,
                    "country_code": tenant.country_code,
                    "timezone": tenant.timezone,
                    "currency_code": tenant.currency_code,
                    "status": tenant.status,
                    "plan_name": plan.name if plan else "unknown",
                    "logo_url": tenant.logo_url,
                },
            }

        finally:
            with contextlib.suppress(Exception):
                await db.execute(text("SET search_path TO public"))

    # ─── Verify Email ───────────────────────────────────

    async def verify_email(
        self,
        *,
        token: str,
        db: AsyncSession,
    ) -> None:
        """Mark a user's email as verified using a verification token."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        redis_key = f"{_VERIFY_EMAIL_PREFIX}{token_hash}"

        token_data = await get_cached(redis_key)
        if token_data is None:
            raise AuthError(
                error="AUTH_invalid_token",
                message=_INVALID_TOKEN_ERROR,
            )

        user_id = token_data["user_id"]
        schema_name = token_data["schema_name"]

        await db.execute(text(f"SET search_path TO {schema_name}, public"))
        try:
            user_result = await db.execute(
                select(User).where(User.id == uuid.UUID(user_id))
            )
            user = user_result.scalar_one_or_none()

            if user is None:
                raise AuthError(
                    error="AUTH_invalid_token",
                    message=_INVALID_TOKEN_ERROR,
                )

            user.email_verified = True
            await db.commit()

            await cache_delete(redis_key)

            logger.info("Email verified for user in schema %s", schema_name)

        finally:
            with contextlib.suppress(Exception):
                await db.execute(text("SET search_path TO public"))

    # ─── Private Helpers ────────────────────────────────

    async def _load_user_from_tenant(
        self,
        *,
        email: str,
        schema_name: str,
        db: AsyncSession,
    ) -> User | None:
        """Load an active user by email from a specific tenant schema."""
        await db.execute(text(f"SET search_path TO {schema_name}, public"))
        try:
            result = await db.execute(
                select(User).where(
                    func.lower(User.email) == email.lower(),
                    User.is_active.is_(True),
                )
            )
            return result.scalar_one_or_none()
        finally:
            with contextlib.suppress(Exception):
                await db.execute(text("SET search_path TO public"))

    def _check_lockout(self, user: User) -> None:
        """Raise AuthError if the user's account is currently locked."""
        if user.locked_until and user.locked_until > datetime.now(UTC):
            raise AuthError(
                error="AUTH_account_locked",
                message=_ACCOUNT_LOCKED_ERROR,
            )

    async def _handle_failed_login(
        self,
        user: User,
        schema_name: str,
        db: AsyncSession,
    ) -> None:
        """Increment failed login attempts and lock account if threshold reached."""
        await db.execute(text(f"SET search_path TO {schema_name}, public"))
        try:
            user.failed_login_attempts += 1

            if user.failed_login_attempts >= settings.lockout_threshold:
                user.locked_until = datetime.now(UTC) + timedelta(
                    minutes=settings.lockout_duration_minutes
                )
                logger.warning(
                    "Account locked after %d failed attempts (lockout=%d min)",
                    user.failed_login_attempts,
                    settings.lockout_duration_minutes,
                )

            await db.commit()
        finally:
            with contextlib.suppress(Exception):
                await db.execute(text("SET search_path TO public"))

    async def _reset_failed_attempts(
        self,
        user: User,
        schema_name: str,
        db: AsyncSession,
    ) -> None:
        """Clear failed login counter and lockout on successful authentication."""
        await db.execute(text(f"SET search_path TO {schema_name}, public"))
        try:
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login_at = datetime.now(UTC)
            await db.flush()
        finally:
            with contextlib.suppress(Exception):
                await db.execute(text("SET search_path TO public"))

    async def _issue_login_tokens(
        self,
        *,
        user: User,
        tenant: Tenant,
        membership: UserTenantMembership,
        ip_address: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Create a refresh session and issue JWT + refresh tokens."""
        await db.execute(text(f"SET search_path TO {tenant.schema_name}, public"))
        try:
            raw_refresh, refresh_hash = create_refresh_token()
            session = UserSession(
                user_id=user.id,
                refresh_token_hash=refresh_hash,
                ip_address=ip_address,
                expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
                is_revoked=False,
            )
            db.add(session)
            await db.commit()

            permissions = list(get_permissions_for_role(membership.role))
            plan = tenant.plan  # Eagerly loaded via relationship

            access_token = create_access_token(
                user_id=str(user.id),
                tenant_id=str(tenant.id),
                role=membership.role,
                permissions=permissions,
                email=user.email,
                name=user.name,
                token_version=user.token_version,
            )

            return {
                "access_token": access_token,
                "refresh_token": raw_refresh,
                "token_type": "bearer",
                "expires_in": settings.access_token_expire_minutes * 60,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                    "phone": user.phone,
                    "avatar_url": user.avatar_url,
                    "professional_license": user.professional_license,
                    "specialties": user.specialties,
                    "is_active": user.is_active,
                    "email_verified": user.email_verified,
                },
                "tenant": {
                    "id": str(tenant.id),
                    "slug": tenant.slug,
                    "name": tenant.name,
                    "country_code": tenant.country_code,
                    "timezone": tenant.timezone,
                    "currency_code": tenant.currency_code,
                    "status": tenant.status,
                    "plan_name": plan.name if plan else "unknown",
                    "logo_url": tenant.logo_url,
                },
            }

        finally:
            with contextlib.suppress(Exception):
                await db.execute(text("SET search_path TO public"))

    async def _revoke_all_sessions(
        self,
        *,
        user_id: uuid.UUID,
        schema_name: str,
        db: AsyncSession,
    ) -> None:
        """Revoke every active session for a user (security response)."""
        await db.execute(text(f"SET search_path TO {schema_name}, public"))
        try:
            await db.execute(
                update(UserSession)
                .where(
                    UserSession.user_id == user_id,
                    UserSession.is_revoked.is_(False),
                )
                .values(is_revoked=True)
            )
            await db.commit()
            logger.warning("All sessions revoked for user in schema %s", schema_name)
        finally:
            with contextlib.suppress(Exception):
                await db.execute(text("SET search_path TO public"))

    async def _find_session_by_refresh_hash(
        self,
        token_hash: str,
        db: AsyncSession,
    ) -> tuple[UserSession, Tenant, str] | None:
        """Find a refresh token session across all active tenant schemas.

        Iterates active tenants and checks each schema for the session.
        For a production system at scale, this would be optimized with
        a lookup table in the public schema. For MVP, the number of
        active tenants is small enough for sequential scanning.
        """
        tenants_result = await db.execute(
            select(Tenant).where(Tenant.status == "active")
        )
        tenants = tenants_result.scalars().all()

        for tenant in tenants:
            schema = tenant.schema_name
            await db.execute(text(f"SET search_path TO {schema}, public"))
            try:
                result = await db.execute(
                    select(UserSession).where(
                        UserSession.refresh_token_hash == token_hash,
                    )
                )
                session_record = result.scalar_one_or_none()
                if session_record is not None:
                    return session_record, tenant, schema
            finally:
                with contextlib.suppress(Exception):
                    await db.execute(text("SET search_path TO public"))

        return None

    async def _find_invite_by_token_hash(
        self,
        token_hash: str,
        db: AsyncSession,
    ) -> tuple[UserInvite, Tenant, str] | None:
        """Find an invite token across all active tenant schemas.

        Similar scanning approach to _find_session_by_refresh_hash.
        """
        tenants_result = await db.execute(
            select(Tenant).where(Tenant.status == "active")
        )
        tenants = tenants_result.scalars().all()

        for tenant in tenants:
            schema = tenant.schema_name
            await db.execute(text(f"SET search_path TO {schema}, public"))
            try:
                result = await db.execute(
                    select(UserInvite).where(
                        UserInvite.token_hash == token_hash,
                    )
                )
                invite = result.scalar_one_or_none()
                if invite is not None:
                    return invite, tenant, schema
            finally:
                with contextlib.suppress(Exception):
                    await db.execute(text("SET search_path TO public"))

        return None


# Module-level singleton for dependency injection
auth_service = AuthService()
