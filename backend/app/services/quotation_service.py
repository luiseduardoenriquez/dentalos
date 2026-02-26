"""Quotation service — create, share, and approve price quotations.

Security invariants:
  - PHI is NEVER logged.
  - Clinical data is NEVER hard-deleted (Res. 1888).
  - All monetary values in COP cents.
  - Sequential quotation numbers per tenant.
"""

import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import QuotationErrors
from app.core.exceptions import DentalOSError, QuotationError, ResourceNotFoundError
from app.core.queue import publish_message
from app.models.tenant.patient import Patient
from app.models.tenant.quotation import Quotation, QuotationItem
from app.models.tenant.treatment_plan import TreatmentPlan
from app.schemas.queue import QueueMessage
from app.services.digital_signature_service import digital_signature_service

logger = logging.getLogger("dentalos.quotation")


def _item_to_dict(item: QuotationItem) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "quotation_id": str(item.quotation_id),
        "service_id": str(item.service_id) if item.service_id else None,
        "description": item.description,
        "cups_code": item.cups_code,
        "quantity": item.quantity,
        "unit_price": item.unit_price,
        "discount": item.discount,
        "line_total": item.line_total,
        "sort_order": item.sort_order,
        "tooth_number": item.tooth_number,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _quotation_to_dict(q: Quotation) -> dict[str, Any]:
    items = [_item_to_dict(i) for i in q.items] if q.items else []

    days_until_expiry = None
    if q.valid_until:
        delta = q.valid_until - date.today()
        days_until_expiry = max(delta.days, 0)

    return {
        "id": str(q.id),
        "quotation_number": q.quotation_number,
        "patient_id": str(q.patient_id),
        "created_by": str(q.created_by),
        "treatment_plan_id": str(q.treatment_plan_id) if q.treatment_plan_id else None,
        "subtotal": q.subtotal,
        "tax": q.tax,
        "total": q.total,
        "valid_until": q.valid_until,
        "status": q.status,
        "notes": q.notes,
        "signature_id": str(q.signature_id) if q.signature_id else None,
        "approved_at": q.approved_at,
        "invoice_id": str(q.invoice_id) if q.invoice_id else None,
        "items": items,
        "days_until_expiry": days_until_expiry,
        "is_active": q.is_active,
        "created_at": q.created_at,
        "updated_at": q.updated_at,
    }


class QuotationService:
    """Stateless quotation service."""

    async def create_quotation(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        created_by: str,
        treatment_plan_id: str | None = None,
        items: list[dict[str, Any]] | None = None,
        valid_until: date | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Create a new quotation. From treatment plan or manual items.

        Raises:
            DentalOSError (404) — patient not found.
            QuotationError (409) — duplicate quotation for same plan.
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

        # Check for duplicate if from treatment plan
        tp_id = None
        if treatment_plan_id:
            tp_id = uuid.UUID(treatment_plan_id)
            existing = await db.execute(
                select(Quotation.id).where(
                    Quotation.treatment_plan_id == tp_id,
                    Quotation.status.in_(["draft", "sent"]),
                    Quotation.is_active.is_(True),
                )
            )
            if existing.scalar_one_or_none() is not None:
                raise QuotationError(
                    error=QuotationErrors.DUPLICATE_FOR_PLAN,
                    message="Ya existe una cotización activa para este plan.",
                    status_code=409,
                )

        # Generate sequential number
        year = datetime.now(UTC).year
        count_result = await db.execute(
            select(func.count(Quotation.id)).where(
                Quotation.quotation_number.like(f"COT-{year}-%"),
            )
        )
        seq = (count_result.scalar_one() or 0) + 1
        quotation_number = f"COT-{year}-{seq:05d}"

        # Default validity: 30 days
        if valid_until is None:
            valid_until = date.today() + timedelta(days=30)

        # Build items from treatment plan or manual input
        quotation_items: list[dict[str, Any]] = []

        if treatment_plan_id and not items:
            plan_result = await db.execute(
                select(TreatmentPlan).where(
                    TreatmentPlan.id == tp_id,
                    TreatmentPlan.is_active.is_(True),
                )
            )
            plan = plan_result.scalar_one_or_none()
            if plan and plan.items:
                for idx, pi in enumerate(plan.items):
                    if pi.status != "cancelled":
                        quotation_items.append({
                            "description": pi.cups_description,
                            "cups_code": pi.cups_code,
                            "quantity": 1,
                            "unit_price": pi.estimated_cost,
                            "discount": 0,
                            "tooth_number": pi.tooth_number,
                            "sort_order": idx,
                        })
        elif items:
            for idx, item in enumerate(items):
                quotation_items.append({
                    "description": item["description"],
                    "cups_code": item.get("cups_code"),
                    "service_id": item.get("service_id"),
                    "quantity": item.get("quantity", 1),
                    "unit_price": item["unit_price"],
                    "discount": item.get("discount", 0),
                    "tooth_number": item.get("tooth_number"),
                    "sort_order": idx,
                })

        # Calculate totals
        subtotal = 0
        for qi in quotation_items:
            line_total = (qi["unit_price"] * qi["quantity"]) - qi["discount"]
            qi["line_total"] = max(line_total, 0)
            subtotal += qi["line_total"]

        # Tax: CO = 0%
        tax = 0
        total = subtotal + tax

        # Create quotation
        quotation = Quotation(
            quotation_number=quotation_number,
            patient_id=pid,
            created_by=uuid.UUID(created_by),
            treatment_plan_id=tp_id,
            subtotal=subtotal,
            tax=tax,
            total=total,
            valid_until=valid_until,
            status="draft",
            notes=notes,
            is_active=True,
        )
        db.add(quotation)
        await db.flush()

        # Create items
        for qi in quotation_items:
            item = QuotationItem(
                quotation_id=quotation.id,
                service_id=uuid.UUID(qi["service_id"]) if qi.get("service_id") else None,
                description=qi["description"],
                cups_code=qi.get("cups_code"),
                quantity=qi["quantity"],
                unit_price=qi["unit_price"],
                discount=qi["discount"],
                line_total=qi["line_total"],
                sort_order=qi["sort_order"],
                tooth_number=qi.get("tooth_number"),
            )
            db.add(item)

        await db.flush()
        await db.refresh(quotation)

        logger.info("Quotation created: number=%s patient=%s", quotation_number, patient_id[:8])

        return _quotation_to_dict(quotation)

    async def get_quotation(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        quotation_id: str,
    ) -> dict[str, Any] | None:
        """Fetch a single quotation with items."""
        result = await db.execute(
            select(Quotation).where(
                Quotation.id == uuid.UUID(quotation_id),
                Quotation.patient_id == uuid.UUID(patient_id),
                Quotation.is_active.is_(True),
            )
        )
        q = result.scalar_one_or_none()
        if q is None:
            return None
        return _quotation_to_dict(q)

    async def list_quotations(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Paginated list of quotations for a patient."""
        pid = uuid.UUID(patient_id)
        offset = (page - 1) * page_size

        total = (await db.execute(
            select(func.count(Quotation.id)).where(
                Quotation.patient_id == pid,
                Quotation.is_active.is_(True),
            )
        )).scalar_one()

        quotations = (await db.execute(
            select(Quotation)
            .where(Quotation.patient_id == pid, Quotation.is_active.is_(True))
            .order_by(Quotation.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )).scalars().all()

        return {
            "items": [_quotation_to_dict(q) for q in quotations],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def approve_quotation(
        self,
        *,
        db: AsyncSession,
        tenant_id: str,
        patient_id: str,
        quotation_id: str,
        signer_id: str,
        signature_image_b64: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Approve a quotation with a digital signature.

        Raises:
            ResourceNotFoundError (404) — quotation not found.
            QuotationError (409) — already approved or expired.
        """
        result = await db.execute(
            select(Quotation).where(
                Quotation.id == uuid.UUID(quotation_id),
                Quotation.patient_id == uuid.UUID(patient_id),
                Quotation.is_active.is_(True),
            )
        )
        quotation = result.scalar_one_or_none()

        if quotation is None:
            raise ResourceNotFoundError(
                error=QuotationErrors.NOT_FOUND,
                resource_name="Quotation",
            )

        if quotation.status == "approved":
            raise QuotationError(
                error=QuotationErrors.ALREADY_APPROVED,
                message="Esta cotización ya fue aprobada.",
                status_code=409,
            )

        if quotation.valid_until and quotation.valid_until < date.today():
            raise QuotationError(
                error=QuotationErrors.ALREADY_EXPIRED,
                message="Esta cotización ha expirado.",
                status_code=409,
            )

        # Create digital signature
        sig_result = await digital_signature_service.create_signature(
            db=db,
            tenant_id=tenant_id,
            signer_id=signer_id,
            document_type="quotation",
            document_id=str(quotation.id),
            signer_type="patient",
            signature_image_b64=signature_image_b64,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        quotation.signature_id = uuid.UUID(sig_result["id"])
        quotation.approved_at = datetime.now(UTC)
        quotation.status = "approved"
        # invoice_id = null (Sprint 11-12 TODO)

        await db.flush()
        await db.refresh(quotation)

        logger.info("Quotation approved: number=%s", quotation.quotation_number)

        return _quotation_to_dict(quotation)

    async def share_quotation(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        quotation_id: str,
        channel: str,
        recipient_email: str | None = None,
        recipient_phone: str | None = None,
        message: str | None = None,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Share a quotation via email or WhatsApp.

        Validates the quotation exists and enqueues a notification job.
        Actual delivery is handled by the notification worker (Sprint 11-12).

        Returns:
            {shared: True, channel, sent_to}

        Raises:
            ResourceNotFoundError -- quotation not found.
        """
        pid = uuid.UUID(patient_id)
        qid = uuid.UUID(quotation_id)

        # Verify quotation exists
        result = await db.execute(
            select(Quotation).where(
                Quotation.id == qid,
                Quotation.patient_id == pid,
                Quotation.is_active.is_(True),
            )
        )
        quotation = result.scalar_one_or_none()

        if quotation is None:
            raise ResourceNotFoundError(
                error="QUOTATION_not_found",
                resource_name="Quotation",
            )

        sent_to = recipient_email if channel == "email" else recipient_phone

        # Enqueue notification job
        await publish_message(
            "notifications",
            QueueMessage(
                tenant_id=tenant_id,
                job_type="quotation.share",
                payload={
                    "quotation_id": quotation_id,
                    "patient_id": patient_id,
                    "channel": channel,
                    "recipient": sent_to,
                    "message": message,
                },
            ),
        )

        logger.info(
            "Quotation share queued: quotation=%s channel=%s",
            quotation_id[:8],
            channel,
        )

        return {
            "shared": True,
            "channel": channel,
            "sent_to": sent_to,
        }


# Module-level singleton
quotation_service = QuotationService()
