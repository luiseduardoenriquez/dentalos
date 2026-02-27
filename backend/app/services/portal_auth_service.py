"""Portal authentication service — login, magic link, token refresh, logout.

Security invariants:
  - PHI is NEVER logged (no patient names, emails, phones in log output)
  - Timing-attack prevention: always run bcrypt verify even if user not found
  - Rate limiting via Redis counters for failed login attempts
  - Magic link tokens are one-time use (deleted from Redis after verification)
"""

import hashlib
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete_pattern, get_cached, set_cached
from app.core.config import settings
from app.core.exceptions import AuthError, DentalOSError, RateLimitError
from app.core.security import (
    create_portal_access_token,
    create_portal_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.tenant.patient import Patient
from app.models.tenant.portal import PortalCredentials

logger = logging.getLogger("dentalos.portal_auth")

# Dummy hash for timing-attack prevention (cost matches production bcrypt rounds)
_DUMMY_HASH = bcrypt.hashpw(b"dummy_password_timing_prevention", bcrypt.gensalt(rounds=12)).decode()

# Rate limit settings
_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT_MINUTES = 15
_RATE_LIMIT_WINDOW = 900  # 15 minutes in seconds


class PortalAuthService:
    """Stateless portal authentication service."""

    async def login_password(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        identifier: str,
        password: str,
    ) -> dict[str, Any]:
        """Authenticate a portal patient via email/phone + password.

        Returns tokens + patient summary on success.
        Raises AuthError on invalid credentials.
        """
        # Rate limit check
        rate_key = f"dentalos:portal:failed:{tenant_id[:12]}:{hashlib.sha256(identifier.encode()).hexdigest()[:16]}"
        attempts_str = await get_cached(rate_key)
        attempts = int(attempts_str) if attempts_str else 0

        if attempts >= _MAX_FAILED_ATTEMPTS:
            raise RateLimitError(
                message="Demasiados intentos fallidos. Intenta de nuevo más tarde.",
                retry_after=_LOCKOUT_MINUTES * 60,
            )

        # Find patient by email or phone
        patient = await self._find_patient_by_identifier(db, identifier)

        if patient is None:
            # Timing attack prevention: verify against dummy hash
            verify_password("dummy", _DUMMY_HASH)
            await self._increment_failed_attempts(rate_key)
            raise AuthError(
                error="AUTH_invalid_credentials",
                message="Credenciales inválidas.",
                status_code=401,
            )

        # Check portal access enabled
        if not patient.portal_access:
            verify_password("dummy", _DUMMY_HASH)
            await self._increment_failed_attempts(rate_key)
            raise AuthError(
                error="AUTH_portal_not_enabled",
                message="Credenciales inválidas.",
                status_code=401,
            )

        # Load credentials
        result = await db.execute(
            select(PortalCredentials).where(
                PortalCredentials.patient_id == patient.id,
                PortalCredentials.is_active.is_(True),
            )
        )
        creds = result.scalar_one_or_none()

        if creds is None or creds.password_hash is None:
            verify_password("dummy", _DUMMY_HASH)
            await self._increment_failed_attempts(rate_key)
            raise AuthError(
                error="AUTH_invalid_credentials",
                message="Credenciales inválidas.",
                status_code=401,
            )

        # Check lockout
        if creds.locked_until and creds.locked_until > datetime.now(UTC):
            raise RateLimitError(
                message="Cuenta bloqueada temporalmente. Intenta de nuevo más tarde.",
                retry_after=int((creds.locked_until - datetime.now(UTC)).total_seconds()),
            )

        # Verify password
        if not verify_password(password, creds.password_hash):
            creds.failed_attempts += 1
            if creds.failed_attempts >= _MAX_FAILED_ATTEMPTS:
                creds.locked_until = datetime.now(UTC) + timedelta(minutes=_LOCKOUT_MINUTES)
            await db.flush()
            await self._increment_failed_attempts(rate_key)
            raise AuthError(
                error="AUTH_invalid_credentials",
                message="Credenciales inválidas.",
                status_code=401,
            )

        # Success — reset counters
        creds.failed_attempts = 0
        creds.locked_until = None
        creds.last_login_at = datetime.now(UTC)
        await db.flush()

        # Clear rate limit
        await set_cached(rate_key, 0, ttl_seconds=1)

        # Generate tokens
        patient_id_str = str(patient.id)
        access_token = create_portal_access_token(
            patient_id=patient_id_str,
            tenant_id=tenant_id,
            email=patient.email or "",
            name=f"{patient.first_name} {patient.last_name}",
        )
        raw_refresh, refresh_hash = create_portal_refresh_token()

        # Store refresh token in Redis (30 days)
        refresh_key = f"dentalos:portal:refresh:{refresh_hash}"
        await set_cached(
            refresh_key,
            f"{patient_id_str}:{tenant_id}",
            ttl_seconds=settings.refresh_token_expire_days * 86400,
        )

        logger.info("Portal login success: tenant=%s", tenant_id[:8])

        return {
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "token_type": "bearer",
            "expires_in": 1800,  # 30 minutes
            "must_change_password": creds.must_change_password,
            "patient": {
                "id": patient_id_str,
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "email": patient.email,
                "phone": patient.phone,
            },
        }

    async def request_magic_link(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        identifier: str,
        channel: str,
    ) -> dict[str, Any]:
        """Request a magic link for portal login.

        Always returns success to prevent user enumeration.
        """
        patient = await self._find_patient_by_identifier(db, identifier)

        if patient and patient.portal_access:
            # Generate magic link token
            raw_token = str(uuid.uuid4())
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

            # Store in Redis with 15-minute TTL
            magic_key = f"dentalos:portal:magic:{token_hash}"
            await set_cached(
                magic_key,
                f"{patient.id}:{tenant_id}",
                ttl_seconds=900,
            )

            # TODO: Dispatch via RabbitMQ to send email/WhatsApp
            logger.info(
                "Magic link requested: tenant=%s channel=%s",
                tenant_id[:8],
                channel,
            )

        return {
            "status": "sent",
            "message": "Si la cuenta existe, se ha enviado un enlace de acceso.",
            "expires_in_minutes": 15,
            "channel": channel,
        }

    async def verify_magic_link(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        token: str,
    ) -> dict[str, Any]:
        """Verify and redeem a magic link token. One-time use."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        magic_key = f"dentalos:portal:magic:{token_hash}"

        stored = await get_cached(magic_key)
        if not stored:
            raise AuthError(
                error="AUTH_invalid_magic_link",
                message="Enlace de acceso inválido o expirado.",
                status_code=401,
            )

        # Delete immediately (one-time use)
        await set_cached(magic_key, "", ttl_seconds=1)

        # Parse stored data
        parts = stored.split(":")
        if len(parts) != 2:
            raise AuthError(
                error="AUTH_invalid_magic_link",
                message="Enlace de acceso inválido.",
                status_code=401,
            )

        patient_id_str, stored_tenant_id = parts

        # Load patient
        patient_uuid = uuid.UUID(patient_id_str)
        result = await db.execute(
            select(Patient).where(
                Patient.id == patient_uuid,
                Patient.is_active.is_(True),
                Patient.portal_access.is_(True),
            )
        )
        patient = result.scalar_one_or_none()

        if patient is None:
            raise AuthError(
                error="AUTH_patient_not_found",
                message="Enlace de acceso inválido.",
                status_code=401,
            )

        # Update last login
        creds_result = await db.execute(
            select(PortalCredentials).where(
                PortalCredentials.patient_id == patient.id,
                PortalCredentials.is_active.is_(True),
            )
        )
        creds = creds_result.scalar_one_or_none()
        if creds:
            creds.last_login_at = datetime.now(UTC)
            await db.flush()

        # Generate tokens
        access_token = create_portal_access_token(
            patient_id=patient_id_str,
            tenant_id=tenant_id,
            email=patient.email or "",
            name=f"{patient.first_name} {patient.last_name}",
        )
        raw_refresh, refresh_hash = create_portal_refresh_token()

        refresh_key = f"dentalos:portal:refresh:{refresh_hash}"
        await set_cached(
            refresh_key,
            f"{patient_id_str}:{tenant_id}",
            ttl_seconds=settings.refresh_token_expire_days * 86400,
        )

        return {
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "token_type": "bearer",
            "expires_in": 1800,
            "patient": {
                "id": patient_id_str,
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "email": patient.email,
                "phone": patient.phone,
            },
        }

    async def refresh_portal_token(
        self,
        *,
        db: AsyncSession,
        raw_refresh_token: str,
    ) -> dict[str, Any]:
        """Refresh a portal access token using the refresh token."""
        refresh_hash = hash_refresh_token(raw_refresh_token)
        refresh_key = f"dentalos:portal:refresh:{refresh_hash}"

        stored = await get_cached(refresh_key)
        if not stored:
            raise AuthError(
                error="AUTH_invalid_refresh",
                message="Token de refresco inválido o expirado.",
                status_code=401,
            )

        parts = stored.split(":")
        if len(parts) != 2:
            raise AuthError(
                error="AUTH_invalid_refresh",
                message="Token de refresco inválido.",
                status_code=401,
            )

        patient_id_str, tenant_id = parts

        # Load patient for fresh claims
        patient_uuid = uuid.UUID(patient_id_str)
        result = await db.execute(
            select(Patient).where(
                Patient.id == patient_uuid,
                Patient.is_active.is_(True),
                Patient.portal_access.is_(True),
            )
        )
        patient = result.scalar_one_or_none()

        if patient is None:
            # Revoke refresh token
            await set_cached(refresh_key, "", ttl_seconds=1)
            raise AuthError(
                error="AUTH_patient_not_found",
                message="Cuenta de portal no disponible.",
                status_code=401,
            )

        # Rotate refresh token
        await set_cached(refresh_key, "", ttl_seconds=1)
        new_raw_refresh, new_refresh_hash = create_portal_refresh_token()
        new_refresh_key = f"dentalos:portal:refresh:{new_refresh_hash}"
        await set_cached(
            new_refresh_key,
            f"{patient_id_str}:{tenant_id}",
            ttl_seconds=settings.refresh_token_expire_days * 86400,
        )

        access_token = create_portal_access_token(
            patient_id=patient_id_str,
            tenant_id=tenant_id,
            email=patient.email or "",
            name=f"{patient.first_name} {patient.last_name}",
        )

        return {
            "access_token": access_token,
            "refresh_token": new_raw_refresh,
            "token_type": "bearer",
            "expires_in": 1800,
        }

    async def logout_portal(
        self,
        *,
        patient_id: str,
        token_jti: str,
    ) -> dict[str, Any]:
        """Logout a portal patient by blacklisting the current JTI."""
        blacklist_key = f"dentalos:auth:blacklist:{token_jti}"
        await set_cached(blacklist_key, "1", ttl_seconds=1800)  # 30 min (matches token TTL)

        logger.info("Portal logout: jti=%s", token_jti[:8])

        return {"message": "Sesión cerrada exitosamente."}

    async def change_password(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        new_password: str,
    ) -> dict[str, Any]:
        """Change portal password and clear must_change_password flag."""
        pid = uuid.UUID(patient_id)

        result = await db.execute(
            select(PortalCredentials).where(
                PortalCredentials.patient_id == pid,
                PortalCredentials.is_active.is_(True),
            )
        )
        creds = result.scalar_one_or_none()

        if creds is None:
            raise AuthError(
                error="AUTH_credentials_not_found",
                message="No se encontraron credenciales de portal.",
                status_code=400,
            )

        creds.password_hash = hash_password(new_password)
        creds.must_change_password = False
        await db.flush()

        logger.info("Portal password changed: patient=%s", patient_id[:8])

        return {"message": "Contraseña actualizada exitosamente."}

    # ── Private helpers ──

    async def _find_patient_by_identifier(
        self, db: AsyncSession, identifier: str
    ) -> Patient | None:
        """Find a patient by email or phone. Returns None if not found."""
        identifier = identifier.strip().lower()

        # Try email first
        result = await db.execute(
            select(Patient).where(
                Patient.email == identifier,
                Patient.is_active.is_(True),
            )
        )
        patient = result.scalar_one_or_none()

        if patient is None:
            # Try phone
            result = await db.execute(
                select(Patient).where(
                    Patient.phone == identifier,
                    Patient.is_active.is_(True),
                )
            )
            patient = result.scalar_one_or_none()

        return patient

    async def _increment_failed_attempts(self, rate_key: str) -> None:
        """Increment the failed attempts counter in Redis."""
        current = await get_cached(rate_key)
        count = int(current) + 1 if current else 1
        await set_cached(rate_key, count, ttl_seconds=_RATE_LIMIT_WINDOW)


# Module-level singleton
portal_auth_service = PortalAuthService()
