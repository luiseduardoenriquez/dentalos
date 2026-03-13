"""Portal access management — grant/revoke portal access for patients.

Used by staff (clinic_owner, receptionist) to control which patients
can log in to the patient portal.
"""

import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete_pattern, get_cached, set_cached
from app.core.config import settings
from app.core.email import email_service
from app.core.exceptions import (
    DentalOSError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.core.security import hash_password
from app.models.public.tenant import Tenant
from app.models.tenant.patient import Patient
from app.models.tenant.portal import PortalCredentials, PortalInvitation

logger = logging.getLogger("dentalos.portal_access")


class PortalAccessService:
    """Stateless portal access management service."""

    async def grant_access(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        invitation_channel: str | None,
        created_by: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Grant portal access to a patient and send invitation."""
        pid = uuid.UUID(patient_id)

        # Load patient
        result = await db.execute(
            select(Patient).where(Patient.id == pid, Patient.is_active.is_(True))
        )
        patient = result.scalar_one_or_none()

        if patient is None:
            raise ResourceNotFoundError(
                error="PATIENT_not_found",
                resource_name="Patient",
            )

        if patient.portal_access:
            raise ResourceConflictError(
                error="PORTAL_already_granted",
                message="El paciente ya tiene acceso al portal.",
            )

        # Determine channel
        channel = invitation_channel or "email"
        if channel == "email" and not patient.email:
            raise DentalOSError(
                error="VALIDATION_missing_email",
                message="El paciente no tiene email registrado. Necesario para invitación por email.",
                status_code=422,
            )
        if channel == "whatsapp" and not patient.phone:
            raise DentalOSError(
                error="VALIDATION_missing_phone",
                message="El paciente no tiene teléfono registrado. Necesario para invitación por WhatsApp.",
                status_code=422,
            )

        # Generate a temporary password for the patient
        temp_password = secrets.token_urlsafe(8)[:10]

        # Check if credentials already exist
        existing_creds = await db.execute(
            select(PortalCredentials).where(PortalCredentials.patient_id == pid)
        )
        creds = existing_creds.scalar_one_or_none()

        if creds is not None:
            # Reactivate existing credentials with new password
            creds.password_hash = hash_password(temp_password)
            creds.is_active = True
            creds.must_change_password = True
        else:
            # Create new credentials row
            creds = PortalCredentials(
                patient_id=pid,
                password_hash=hash_password(temp_password),
                is_active=True,
                must_change_password=True,
            )
            db.add(creds)

        # Update patient
        patient.portal_access = True

        # Generate invitation token (kept for audit trail)
        raw_token = str(uuid.uuid4())
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(days=7)

        invitation = PortalInvitation(
            patient_id=pid,
            token_hash=token_hash,
            channel=channel,
            status="pending",
            expires_at=expires_at,
            created_by=uuid.UUID(created_by),
        )
        db.add(invitation)
        await db.flush()

        # Store invitation token in Redis for quick lookup
        invite_key = f"dentalos:portal:invite:{token_hash}"
        await set_cached(
            invite_key,
            f"{patient_id}:{tenant_id}",
            ttl_seconds=7 * 86400,  # 7 days
        )

        # Send welcome email with temp credentials
        if channel == "email" and patient.email:
            await self._send_portal_welcome_email(
                db=db,
                patient=patient,
                tenant_id=tenant_id,
                temp_password=temp_password,
            )

        logger.info(
            "Portal access granted: tenant=%s channel=%s",
            tenant_id[:8],
            channel,
        )

        return {
            "message": f"Acceso al portal concedido. Invitación enviada por {channel}.",
            "patient_id": patient_id,
            "portal_access": True,
            "invitation_sent_via": channel,
            "invitation_expires_at": expires_at,
        }

    async def _send_portal_welcome_email(
        self,
        *,
        db: AsyncSession,
        patient: Patient,
        tenant_id: str,
        temp_password: str,
    ) -> None:
        """Send portal welcome email with temporary credentials."""
        # Resolve clinic name and slug from public.tenants
        tenant_result = await db.execute(
            select(Tenant).where(Tenant.id == uuid.UUID(tenant_id))
        )
        tenant = tenant_result.scalar_one_or_none()
        clinic_name = tenant.name if tenant else "Tu clínica"
        clinic_slug = tenant.slug if tenant else tenant_id

        portal_url = settings.frontend_url

        try:
            await email_service.send_email(
                to_email=patient.email,
                to_name=f"{patient.first_name} {patient.last_name}",
                subject=f"Bienvenido al Portal del Paciente — {clinic_name}",
                template_name="portal_welcome_es.html",
                context={
                    "patient_name": patient.first_name,
                    "clinic_name": clinic_name,
                    "email": patient.email,
                    "temp_password": temp_password,
                    "portal_url": portal_url,
                    "clinic_slug": clinic_slug,
                    "current_year": "2026",
                },
            )
        except Exception:
            logger.warning(
                "Failed to send portal welcome email: tenant=%s",
                tenant_id[:8],
                exc_info=True,
            )

    async def revoke_access(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Revoke portal access for a patient."""
        pid = uuid.UUID(patient_id)

        result = await db.execute(
            select(Patient).where(Patient.id == pid, Patient.is_active.is_(True))
        )
        patient = result.scalar_one_or_none()

        if patient is None:
            raise ResourceNotFoundError(
                error="PATIENT_not_found",
                resource_name="Patient",
            )

        if not patient.portal_access:
            raise ResourceConflictError(
                error="PORTAL_not_granted",
                message="El paciente no tiene acceso al portal.",
            )

        # Deactivate credentials
        await db.execute(
            update(PortalCredentials)
            .where(PortalCredentials.patient_id == pid)
            .values(is_active=False)
        )

        # Expire pending invitations
        await db.execute(
            update(PortalInvitation)
            .where(
                PortalInvitation.patient_id == pid,
                PortalInvitation.status == "pending",
            )
            .values(status="expired")
        )

        # Update patient
        patient.portal_access = False
        await db.flush()

        # Invalidate portal caches for this patient
        tid_short = tenant_id[:12]
        await cache_delete_pattern(f"dentalos:portal:refresh:*")

        logger.info("Portal access revoked: tenant=%s", tenant_id[:8])

        return {
            "message": "Acceso al portal revocado.",
            "patient_id": patient_id,
            "portal_access": False,
            "tokens_revoked": 1,
        }

    async def complete_registration(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        token: str,
        password: str,
    ) -> dict[str, Any]:
        """Complete portal registration using invitation token."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        invite_key = f"dentalos:portal:invite:{token_hash}"

        stored = await get_cached(invite_key)
        if not stored:
            # Also check DB for the invitation
            result = await db.execute(
                select(PortalInvitation).where(
                    PortalInvitation.token_hash == token_hash,
                    PortalInvitation.status == "pending",
                    PortalInvitation.expires_at > datetime.now(UTC),
                )
            )
            invitation = result.scalar_one_or_none()

            if invitation is None:
                raise DentalOSError(
                    error="PORTAL_invalid_invitation",
                    message="Invitación inválida o expirada.",
                    status_code=400,
                )

            patient_id_str = str(invitation.patient_id)
        else:
            parts = stored.split(":")
            patient_id_str = parts[0]

            result = await db.execute(
                select(PortalInvitation).where(
                    PortalInvitation.token_hash == token_hash,
                    PortalInvitation.status == "pending",
                )
            )
            invitation = result.scalar_one_or_none()

        if invitation is None:
            raise DentalOSError(
                error="PORTAL_invalid_invitation",
                message="Invitación inválida o expirada.",
                status_code=400,
            )

        # Mark invitation as accepted
        invitation.status = "accepted"
        invitation.accepted_at = datetime.now(UTC)

        # Set password on credentials
        pid = uuid.UUID(patient_id_str)
        creds_result = await db.execute(
            select(PortalCredentials).where(
                PortalCredentials.patient_id == pid,
                PortalCredentials.is_active.is_(True),
            )
        )
        creds = creds_result.scalar_one_or_none()

        if creds is None:
            raise DentalOSError(
                error="PORTAL_credentials_not_found",
                message="No se encontraron credenciales de portal.",
                status_code=400,
            )

        creds.password_hash = hash_password(password)
        creds.last_login_at = datetime.now(UTC)
        await db.flush()

        # Clear invite from Redis
        await set_cached(invite_key, "", ttl_seconds=1)

        # Load patient for token generation
        patient_result = await db.execute(
            select(Patient).where(Patient.id == pid)
        )
        patient = patient_result.scalar_one()

        # Issue tokens
        from app.core.security import create_portal_access_token, create_portal_refresh_token

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

        logger.info("Portal registration completed: tenant=%s", tenant_id[:8])

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


# Module-level singleton
portal_access_service = PortalAccessService()
