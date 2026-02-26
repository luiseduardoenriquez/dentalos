"""Consent service — templates, CRUD, signing, PDF, and voiding.

Security invariants:
  - PHI is NEVER logged.
  - Clinical data is NEVER hard-deleted (Res. 1888).
  - Content hash (SHA-256) is computed at signing for immutability.
  - Voiding is irreversible and requires clinic_owner role.
"""

import hashlib
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ConsentErrors
from app.core.exceptions import ConsentError, DentalOSError, ResourceNotFoundError
from app.core.pdf import render_pdf
from app.models.public.consent_template import PublicConsentTemplate
from app.models.tenant.consent import Consent, ConsentTemplate
from app.models.tenant.patient import Patient
from app.services.digital_signature_service import digital_signature_service

logger = logging.getLogger("dentalos.consent")


def _template_to_dict(t: ConsentTemplate | PublicConsentTemplate, *, is_builtin: bool = False) -> dict[str, Any]:
    return {
        "id": str(t.id),
        "name": t.name,
        "category": t.category,
        "description": t.description,
        "content": t.content,
        "signature_positions": t.signature_positions,
        "version": t.version,
        "is_active": t.is_active,
        "is_builtin": is_builtin or (hasattr(t, "builtin") and t.builtin),
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }


def _consent_to_dict(c: Consent) -> dict[str, Any]:
    return {
        "id": str(c.id),
        "patient_id": str(c.patient_id),
        "doctor_id": str(c.doctor_id),
        "template_id": str(c.template_id) if c.template_id else None,
        "title": c.title,
        "content_rendered": c.content_rendered,
        "content_hash": c.content_hash,
        "status": c.status,
        "signed_at": c.signed_at,
        "locked_at": c.locked_at,
        "voided_at": c.voided_at,
        "voided_by": str(c.voided_by) if c.voided_by else None,
        "void_reason": c.void_reason,
        "is_active": c.is_active,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }


class ConsentService:
    """Stateless consent service."""

    # ─── Templates ────────────────────────────────────────────────────────

    async def list_templates(
        self,
        *,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """List all consent templates (public builtin + tenant custom)."""
        # Tenant templates
        tenant_result = await db.execute(
            select(ConsentTemplate).where(ConsentTemplate.is_active.is_(True))
        )
        tenant_templates = tenant_result.scalars().all()

        # Public builtin templates
        public_result = await db.execute(
            select(PublicConsentTemplate).where(
                PublicConsentTemplate.is_active.is_(True),
                PublicConsentTemplate.builtin.is_(True),
            )
        )
        public_templates = public_result.scalars().all()

        items = [_template_to_dict(t, is_builtin=True) for t in public_templates]
        items.extend([_template_to_dict(t) for t in tenant_templates])

        return {"items": items, "total": len(items)}

    async def create_template(
        self,
        *,
        db: AsyncSession,
        name: str,
        category: str,
        content: str,
        description: str | None = None,
        signature_positions: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Create a tenant consent template."""
        template = ConsentTemplate(
            name=name,
            category=category,
            description=description,
            content=content,
            signature_positions=signature_positions,
            version=1,
            is_active=True,
        )
        db.add(template)
        await db.flush()

        logger.info("Template created: name=%s category=%s", name[:20], category)

        return _template_to_dict(template)

    async def get_template(
        self,
        *,
        db: AsyncSession,
        template_id: str,
    ) -> dict[str, Any] | None:
        """Fetch a single template (tenant or public)."""
        # Try tenant first
        result = await db.execute(
            select(ConsentTemplate).where(
                ConsentTemplate.id == uuid.UUID(template_id),
                ConsentTemplate.is_active.is_(True),
            )
        )
        template = result.scalar_one_or_none()
        if template is not None:
            return _template_to_dict(template)

        # Try public
        result = await db.execute(
            select(PublicConsentTemplate).where(
                PublicConsentTemplate.id == uuid.UUID(template_id),
                PublicConsentTemplate.is_active.is_(True),
            )
        )
        public_template = result.scalar_one_or_none()
        if public_template is not None:
            return _template_to_dict(public_template, is_builtin=True)

        return None

    # ─── Consents ─────────────────────────────────────────────────────────

    async def create_consent(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        doctor_id: str,
        title: str,
        template_id: str | None = None,
        content_rendered: str | None = None,
    ) -> dict[str, Any]:
        """Create a new consent document.

        If template_id is provided and content_rendered is not, the template
        content is used as-is (variable substitution is a future enhancement).
        """
        pid = uuid.UUID(patient_id)

        # Validate patient
        patient_result = await db.execute(
            select(Patient.id).where(Patient.id == pid, Patient.is_active.is_(True))
        )
        if patient_result.scalar_one_or_none() is None:
            raise DentalOSError(
                error="PATIENT_not_found",
                message="El paciente no existe o está inactivo.",
                status_code=404,
            )

        # Resolve content from template if needed
        if content_rendered is None and template_id:
            template_data = await self.get_template(db=db, template_id=template_id)
            if template_data is None:
                raise ResourceNotFoundError(
                    error=ConsentErrors.TEMPLATE_NOT_FOUND,
                    resource_name="ConsentTemplate",
                )
            content_rendered = template_data["content"]

        if not content_rendered:
            raise DentalOSError(
                error="VALIDATION_failed",
                message="Debe proporcionar contenido o un template_id.",
                status_code=422,
            )

        consent = Consent(
            patient_id=pid,
            doctor_id=uuid.UUID(doctor_id),
            template_id=uuid.UUID(template_id) if template_id else None,
            title=title,
            content_rendered=content_rendered,
            content_snapshot=content_rendered,
            status="draft",
            is_active=True,
        )
        db.add(consent)
        await db.flush()

        logger.info("Consent created: patient=%s title_len=%d", patient_id[:8], len(title))

        return _consent_to_dict(consent)

    async def get_consent(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        consent_id: str,
    ) -> dict[str, Any] | None:
        """Fetch a single consent."""
        result = await db.execute(
            select(Consent).where(
                Consent.id == uuid.UUID(consent_id),
                Consent.patient_id == uuid.UUID(patient_id),
                Consent.is_active.is_(True),
            )
        )
        c = result.scalar_one_or_none()
        if c is None:
            return None
        return _consent_to_dict(c)

    async def list_consents(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Paginated list of consents for a patient."""
        pid = uuid.UUID(patient_id)
        offset = (page - 1) * page_size

        total = (await db.execute(
            select(func.count(Consent.id)).where(
                Consent.patient_id == pid,
                Consent.is_active.is_(True),
            )
        )).scalar_one()

        consents = (await db.execute(
            select(Consent)
            .where(Consent.patient_id == pid, Consent.is_active.is_(True))
            .order_by(Consent.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )).scalars().all()

        return {
            "items": [_consent_to_dict(c) for c in consents],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def sign_consent(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        patient_id: str,
        consent_id: str,
        signer_id: str,
        signer_type: str,
        signature_image_b64: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Sign a consent document.

        Status transitions: draft → pending_signatures → signed.
        Computes content_hash and sets locked_at.

        Raises:
            ResourceNotFoundError (404) — consent not found.
            ConsentError (409) — already signed.
        """
        result = await db.execute(
            select(Consent).where(
                Consent.id == uuid.UUID(consent_id),
                Consent.patient_id == uuid.UUID(patient_id),
                Consent.is_active.is_(True),
            )
        )
        consent = result.scalar_one_or_none()

        if consent is None:
            raise ResourceNotFoundError(
                error=ConsentErrors.NOT_FOUND,
                resource_name="Consent",
            )

        if consent.status == "signed":
            raise ConsentError(
                error=ConsentErrors.ALREADY_SIGNED,
                message="Este consentimiento ya fue firmado.",
                status_code=409,
            )

        if consent.status == "voided":
            raise ConsentError(
                error=ConsentErrors.ALREADY_REVOKED,
                message="Este consentimiento fue anulado.",
                status_code=409,
            )

        # Create digital signature
        await digital_signature_service.create_signature(
            db=db,
            tenant_id=tenant_id,
            signer_id=signer_id,
            document_type="consent",
            document_id=str(consent.id),
            signer_type=signer_type,
            signature_image_b64=signature_image_b64,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Compute content hash
        content_hash = hashlib.sha256(
            consent.content_rendered.encode("utf-8")
        ).hexdigest()

        now = datetime.now(UTC)
        consent.content_hash = content_hash
        consent.signed_at = now
        consent.locked_at = now
        consent.status = "signed"
        await db.flush()

        logger.info("Consent signed: consent=%s", consent_id[:8])

        return _consent_to_dict(consent)

    async def generate_pdf(
        self,
        *,
        consent_data: dict[str, Any],
        clinic_name: str = "DentalOS",
        watermark: str | None = None,
    ) -> bytes:
        """Generate a PDF for a consent document."""
        return await render_pdf(
            template_name="consent_es.html",
            context={
                "consent": consent_data,
                "clinic_name": clinic_name,
            },
            watermark=watermark,
        )

    async def void_consent(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        consent_id: str,
        voided_by: str,
        reason: str,
    ) -> dict[str, Any]:
        """Void a consent. Irreversible. Requires clinic_owner role.

        Raises:
            ResourceNotFoundError (404) — consent not found.
            ConsentError (409) — already voided.
        """
        result = await db.execute(
            select(Consent).where(
                Consent.id == uuid.UUID(consent_id),
                Consent.patient_id == uuid.UUID(patient_id),
                Consent.is_active.is_(True),
            )
        )
        consent = result.scalar_one_or_none()

        if consent is None:
            raise ResourceNotFoundError(
                error=ConsentErrors.NOT_FOUND,
                resource_name="Consent",
            )

        if consent.status == "voided":
            raise ConsentError(
                error=ConsentErrors.ALREADY_REVOKED,
                message="Este consentimiento ya fue anulado.",
                status_code=409,
            )

        consent.status = "voided"
        consent.voided_at = datetime.now(UTC)
        consent.voided_by = uuid.UUID(voided_by)
        consent.void_reason = reason
        await db.flush()

        logger.info("Consent voided: consent=%s", consent_id[:8])

        return _consent_to_dict(consent)


# Module-level singleton
consent_service = ConsentService()
