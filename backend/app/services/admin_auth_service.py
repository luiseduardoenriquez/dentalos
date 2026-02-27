"""Admin authentication service — superadmin login, TOTP, and JWT issuance.

Handles the separate authentication flow for platform superadmins.
Admin tokens use aud="dentalos-admin" and have no tenant claim (tid).
TOTP (Time-based One-Time Password) is optional but recommended.

Security invariants:
  - Rate limited: 3 login attempts per 15 minutes per IP.
  - IP allowlist enforced when configured on the admin account.
  - Admin JWT expiry: 1 hour (longer than staff 15min since admin
    sessions are infrequent but interactive).
  - TOTP verified before token issuance when enabled.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pyotp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthError, RateLimitError
from app.core.redis import redis_client
from app.core.security import _load_private_key, verify_password
from app.models.public.superadmin import AdminSession, Superadmin
from app.schemas.admin import AdminLoginResponse, AdminTOTPSetupResponse

logger = logging.getLogger("dentalos.admin_auth")

# Admin JWT TTL: 1 hour
_ADMIN_TOKEN_EXPIRE_MINUTES = 60

# Rate limit: 3 attempts per 15 minutes per IP
_RATE_LIMIT_MAX_ATTEMPTS = 3
_RATE_LIMIT_WINDOW_SECONDS = 900  # 15 min


class AdminAuthService:
    """Stateless admin auth service — all state flows through the DB session."""

    # ─── Login ──────────────────────────────────────────

    async def authenticate_admin(
        self,
        *,
        db: AsyncSession,
        email: str,
        password: str,
        totp_code: str | None = None,
        ip_address: str,
        user_agent: str | None = None,
    ) -> AdminLoginResponse:
        """Authenticate a superadmin and issue an admin JWT.

        Flow:
          1. Check rate limit (3 attempts / 15 min per IP)
          2. Load Superadmin by email
          3. Verify bcrypt password
          4. If TOTP enabled and code missing, return totp_required=True
          5. If TOTP enabled, verify the TOTP code
          6. Enforce IP allowlist
          7. Create AdminSession, update last_login
          8. Issue admin JWT and return response
        """
        email = email.strip().lower()

        # 1. Rate limit
        await self._check_rate_limit(ip_address)

        # 2. Load admin by email
        result = await db.execute(
            select(Superadmin).where(
                Superadmin.email == email,
                Superadmin.is_active.is_(True),
            )
        )
        admin = result.scalar_one_or_none()

        if admin is None:
            logger.info("Admin login attempt for unknown email")
            raise AuthError(
                error="AUTH_invalid_credentials",
                message="Invalid credentials.",
            )

        # 3. Verify password
        if not verify_password(password, admin.password_hash):
            logger.info("Admin login failed: bad password")
            raise AuthError(
                error="AUTH_invalid_credentials",
                message="Invalid credentials.",
            )

        # 4. TOTP check: if enabled but code not provided, signal client
        if admin.totp_enabled and not totp_code:
            return AdminLoginResponse(
                access_token="",
                token_type="bearer",
                admin_id=str(admin.id),
                name=admin.name,
                totp_required=True,
            )

        # 5. Verify TOTP code if enabled
        if admin.totp_enabled:
            if not admin.totp_secret:
                raise AuthError(
                    error="AUTH_totp_misconfigured",
                    message="TOTP is enabled but not configured. Contact support.",
                    status_code=500,
                )
            totp = pyotp.TOTP(admin.totp_secret)
            if not totp.verify(totp_code, valid_window=1):
                logger.info("Admin login failed: invalid TOTP code")
                raise AuthError(
                    error="AUTH_invalid_totp",
                    message="Invalid TOTP code.",
                )

        # 6. IP allowlist enforcement
        if admin.ip_allowlist and len(admin.ip_allowlist) > 0:
            if ip_address not in admin.ip_allowlist:
                logger.warning(
                    "Admin login blocked: IP %s not in allowlist", ip_address
                )
                raise AuthError(
                    error="AUTH_ip_not_allowed",
                    message="Access denied from this IP address.",
                    status_code=403,
                )

        # 7. Create session and update audit fields
        now = datetime.now(UTC)
        session = AdminSession(
            admin_id=admin.id,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now,
            expires_at=now + timedelta(minutes=_ADMIN_TOKEN_EXPIRE_MINUTES),
        )
        db.add(session)

        admin.last_login_at = now
        admin.last_login_ip = ip_address
        await db.flush()

        # 8. Generate admin JWT
        access_token = self._generate_admin_jwt(
            admin_id=str(admin.id),
            admin_name=admin.name,
        )

        logger.info("Admin login successful for admin_id=%s...", str(admin.id)[:8])

        return AdminLoginResponse(
            access_token=access_token,
            token_type="bearer",
            admin_id=str(admin.id),
            name=admin.name,
            totp_required=False,
        )

    # ─── TOTP Setup ─────────────────────────────────────

    async def setup_totp(
        self,
        *,
        db: AsyncSession,
        admin_id: uuid.UUID,
    ) -> AdminTOTPSetupResponse:
        """Generate a TOTP secret for initial setup.

        The secret is saved to the admin record but totp_enabled
        remains False until verify_totp_setup() confirms the code.
        """
        result = await db.execute(
            select(Superadmin).where(Superadmin.id == admin_id)
        )
        admin = result.scalar_one_or_none()

        if admin is None:
            raise AuthError(
                error="AUTH_admin_not_found",
                message="Admin account not found.",
                status_code=404,
            )

        secret = pyotp.random_base32()
        admin.totp_secret = secret
        await db.flush()

        provisioning_uri = pyotp.TOTP(secret).provisioning_uri(
            name=admin.email,
            issuer_name="DentalOS Admin",
        )

        logger.info("TOTP setup initiated for admin_id=%s...", str(admin.id)[:8])

        return AdminTOTPSetupResponse(
            secret=secret,
            provisioning_uri=provisioning_uri,
            qr_code_base64=None,
        )

    # ─── TOTP Verify ────────────────────────────────────

    async def verify_totp_setup(
        self,
        *,
        db: AsyncSession,
        admin_id: uuid.UUID,
        totp_code: str,
    ) -> None:
        """Confirm TOTP setup by verifying a code against the stored secret.

        On success, totp_enabled is set to True. On failure, raises
        AuthenticationError so the client can retry.
        """
        result = await db.execute(
            select(Superadmin).where(Superadmin.id == admin_id)
        )
        admin = result.scalar_one_or_none()

        if admin is None:
            raise AuthError(
                error="AUTH_admin_not_found",
                message="Admin account not found.",
                status_code=404,
            )

        if not admin.totp_secret:
            raise AuthError(
                error="AUTH_totp_not_setup",
                message="TOTP has not been set up. Call setup first.",
                status_code=400,
            )

        totp = pyotp.TOTP(admin.totp_secret)
        if not totp.verify(totp_code, valid_window=1):
            raise AuthError(
                error="AUTH_invalid_totp",
                message="Invalid TOTP code. Please try again.",
            )

        admin.totp_enabled = True
        await db.flush()

        logger.info("TOTP enabled for admin_id=%s...", str(admin.id)[:8])

    # ─── Rate Limiting ──────────────────────────────────

    async def _check_rate_limit(self, ip_address: str) -> None:
        """Enforce admin login rate limit: 3 attempts per 15 minutes per IP.

        Uses a simple Redis INCR + EXPIRE pattern. If Redis is down,
        allows the request (graceful degradation).
        """
        key = f"dentalos:admin:login:ratelimit:{ip_address}"
        try:
            current = await redis_client.incr(key)
            if current == 1:
                await redis_client.expire(key, _RATE_LIMIT_WINDOW_SECONDS)
            if current > _RATE_LIMIT_MAX_ATTEMPTS:
                raise RateLimitError(
                    message="Too many login attempts. Please try again later.",
                    retry_after=_RATE_LIMIT_WINDOW_SECONDS,
                )
        except RateLimitError:
            raise
        except Exception:
            logger.warning(
                "Admin rate limit check failed (Redis unavailable), allowing request"
            )

    # ─── JWT Generation ─────────────────────────────────

    def _generate_admin_jwt(
        self,
        admin_id: str,
        admin_name: str,
    ) -> str:
        """Create an RS256 JWT for admin authentication.

        Admin tokens differ from regular tenant tokens:
          - No tid (tenant ID) claim
          - aud = "dentalos-admin" (separate audience)
          - role = "superadmin"
          - Expiry: 1 hour
        """
        from jose import jwt as jose_jwt

        now = datetime.now(UTC)
        jti = f"adtok_{uuid.uuid4().hex}"

        payload: dict[str, Any] = {
            "sub": f"admin_{admin_id}",
            "role": "superadmin",
            "name": admin_name,
            "iat": now,
            "exp": now + timedelta(minutes=_ADMIN_TOKEN_EXPIRE_MINUTES),
            "iss": settings.jwt_issuer,
            "aud": "dentalos-admin",
            "jti": jti,
        }
        headers = {"kid": settings.jwt_key_id}
        return jose_jwt.encode(
            payload,
            _load_private_key(),
            algorithm=settings.jwt_algorithm,
            headers=headers,
        )


# Module-level singleton
admin_auth_service = AdminAuthService()
