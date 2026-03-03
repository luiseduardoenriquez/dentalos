"""Invoice service — create, manage, and track invoices.

Security invariants:
  - PHI is NEVER logged.
  - Clinical/financial data is NEVER hard-deleted (Res. 1888).
  - All monetary values in COP cents.
  - Sequential invoice numbers per tenant.
"""

import logging
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import BillingErrors
from app.core.exceptions import BillingError, DentalOSError, ResourceNotFoundError
from app.core.queue import publish_message
from app.models.tenant.invoice import Invoice, InvoiceItem
from app.models.tenant.patient import Patient
from app.models.tenant.payment import Payment
from app.models.tenant.quotation import Quotation
from app.schemas.queue import QueueMessage

logger = logging.getLogger("dentalos.invoice")


def _item_to_dict(item: InvoiceItem) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "invoice_id": str(item.invoice_id),
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


def _invoice_to_dict(inv: Invoice) -> dict[str, Any]:
    items = [_item_to_dict(i) for i in inv.items] if inv.items else []

    days_until_due = None
    if inv.due_date:
        delta = inv.due_date - date.today()
        days_until_due = delta.days  # Can be negative if overdue

    return {
        "id": str(inv.id),
        "invoice_number": inv.invoice_number,
        "patient_id": str(inv.patient_id),
        "created_by": str(inv.created_by),
        "quotation_id": str(inv.quotation_id) if inv.quotation_id else None,
        "subtotal": inv.subtotal,
        "tax": inv.tax,
        "total": inv.total,
        "amount_paid": inv.amount_paid,
        "balance": inv.balance,
        "status": inv.status,
        "due_date": inv.due_date,
        "paid_at": inv.paid_at,
        "notes": inv.notes,
        "items": items,
        "days_until_due": days_until_due,
        "currency_code": getattr(inv, "currency_code", "COP"),
        "exchange_rate": float(inv.exchange_rate) if getattr(inv, "exchange_rate", None) else None,
        "exchange_rate_date": inv.exchange_rate_date if getattr(inv, "exchange_rate_date", None) else None,
        "is_active": inv.is_active,
        "created_at": inv.created_at,
        "updated_at": inv.updated_at,
    }


class InvoiceService:
    """Stateless invoice service."""

    async def create_invoice(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        created_by: str,
        quotation_id: str | None = None,
        items: list[dict[str, Any]] | None = None,
        due_date: date | None = None,
        notes: str | None = None,
        currency_code: str = "COP",
    ) -> dict[str, Any]:
        """Create a new invoice from a quotation or manual items.

        If quotation_id is provided and items is None, copies items from the
        quotation and links the invoice to it.

        Raises:
            DentalOSError (404) — patient not found.
            BillingError (404) — quotation not found.
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

        # Generate sequential number
        year = datetime.now(UTC).year
        count_result = await db.execute(
            select(func.count(Invoice.id)).where(
                Invoice.invoice_number.like(f"FAC-{year}-%"),
            )
        )
        seq = (count_result.scalar_one() or 0) + 1
        invoice_number = f"FAC-{year}-{seq:05d}"

        # Build items from quotation or manual input
        invoice_items: list[dict[str, Any]] = []
        q_id = None

        if quotation_id:
            q_id = uuid.UUID(quotation_id)
            q_result = await db.execute(
                select(Quotation).where(
                    Quotation.id == q_id,
                    Quotation.patient_id == pid,
                    Quotation.is_active.is_(True),
                )
            )
            quotation = q_result.scalar_one_or_none()
            if quotation is None:
                raise BillingError(
                    error=BillingErrors.QUOTATION_NOT_FOUND,
                    message="La cotización no existe o no pertenece a este paciente.",
                    status_code=404,
                )

            # Copy items from quotation if no manual items provided
            if not items and quotation.items:
                for idx, qi in enumerate(quotation.items):
                    invoice_items.append({
                        "description": qi.description,
                        "cups_code": qi.cups_code,
                        "service_id": str(qi.service_id) if qi.service_id else None,
                        "quantity": qi.quantity,
                        "unit_price": qi.unit_price,
                        "discount": qi.discount,
                        "tooth_number": qi.tooth_number,
                        "sort_order": idx,
                    })

        if items and not invoice_items:
            for idx, item in enumerate(items):
                invoice_items.append({
                    "description": item["description"],
                    "cups_code": item.get("cups_code"),
                    "service_id": item.get("service_id"),
                    "quantity": item.get("quantity", 1),
                    "unit_price": item["unit_price"],
                    "discount": item.get("discount", 0),
                    "tooth_number": item.get("tooth_number"),
                    "sort_order": idx,
                })

        # Sprint 21-22: Apply membership discount if patient has active membership
        from app.services.membership_service import membership_service

        membership_discount_pct, membership_sub_id = (
            await membership_service.get_active_membership_discount(db=db, patient_id=pid)
        )

        # Sprint 25-26: Get convenio discount for per-item application (step 2b)
        from app.services.convenio_service import convenio_service

        convenio_discount_pct, convenio_id = (
            await convenio_service.get_active_convenio_discount(db=db, patient_id=pid)
        )

        # Calculate totals (step 2a: membership, step 2b: convenio)
        subtotal = 0
        total_membership_discount_cents = 0
        total_convenio_discount_cents = 0
        for ii in invoice_items:
            base = ii["unit_price"] * ii["quantity"]
            # Step 2a: Apply membership discount first
            if membership_discount_pct > 0:
                membership_disc = base * membership_discount_pct // 100
                ii["discount"] = ii["discount"] + membership_disc
                total_membership_discount_cents += membership_disc
            # Step 2b: Apply convenio discount on remaining (after membership)
            if convenio_discount_pct > 0:
                remaining = base - ii["discount"]
                convenio_disc = remaining * convenio_discount_pct // 100
                ii["discount"] = ii["discount"] + convenio_disc
                total_convenio_discount_cents += convenio_disc
            line_total = (ii["unit_price"] * ii["quantity"]) - ii["discount"]
            ii["line_total"] = max(line_total, 0)
            subtotal += ii["line_total"]

        # Tax: CO = 0% for dental
        tax = 0
        total = subtotal + tax

        # Sprint 25-26: Fetch exchange rate for multi-currency invoices (step 3)
        exchange_rate_val = None
        exchange_rate_date_val = None
        if currency_code != "COP":
            from app.services.exchange_rate_service import exchange_rate_service

            rate_info = await exchange_rate_service.get_rate_for_invoice(currency_code)
            if rate_info:
                exchange_rate_val = rate_info["rate"]
                exchange_rate_date_val = rate_info["rate_date"]

        # Create invoice
        invoice = Invoice(
            invoice_number=invoice_number,
            patient_id=pid,
            created_by=uuid.UUID(created_by),
            quotation_id=q_id,
            subtotal=subtotal,
            tax=tax,
            total=total,
            amount_paid=0,
            balance=total,
            status="draft",
            due_date=due_date,
            notes=notes,
            is_active=True,
            currency_code=currency_code,
            exchange_rate=exchange_rate_val,
            exchange_rate_date=exchange_rate_date_val,
        )
        db.add(invoice)
        await db.flush()

        # Create items
        for ii in invoice_items:
            item = InvoiceItem(
                invoice_id=invoice.id,
                service_id=uuid.UUID(ii["service_id"]) if ii.get("service_id") else None,
                description=ii["description"],
                cups_code=ii.get("cups_code"),
                quantity=ii["quantity"],
                unit_price=ii["unit_price"],
                discount=ii["discount"],
                line_total=ii["line_total"],
                sort_order=ii["sort_order"],
                tooth_number=ii.get("tooth_number"),
            )
            db.add(item)

        # Link quotation to this invoice
        if q_id:
            q_update = await db.execute(
                select(Quotation).where(Quotation.id == q_id)
            )
            quotation_obj = q_update.scalar_one_or_none()
            if quotation_obj:
                quotation_obj.invoice_id = invoice.id

        await db.flush()
        await db.refresh(invoice)

        # Log membership usage if a discount was applied
        if membership_sub_id and total_membership_discount_cents > 0:
            await membership_service.log_usage(
                db=db,
                subscription_id=membership_sub_id,
                invoice_id=invoice.id,
                discount_applied_cents=total_membership_discount_cents,
            )

        # Sprint 23-24: Apply referral program discount (VP-08)
        from app.services.referral_program_service import referral_program_service

        referral_discount = await referral_program_service.apply_referral_discount(
            db=db,
            patient_id=patient_id,
            invoice_id=invoice.id,
            max_discount_cents=invoice.balance,
        )
        if referral_discount > 0:
            invoice.total = max(invoice.total - referral_discount, 0)
            invoice.balance = max(invoice.balance - referral_discount, 0)
            if invoice.balance == 0:
                invoice.status = "paid"
            await db.flush()
            await db.refresh(invoice)

        # Sprint 25-26: Apply loyalty points redemption (step 4b — VP-15)
        # Only applies if loyalty is enabled and patient has redeemable points
        try:
            from app.services.loyalty_service import loyalty_service

            if invoice.balance > 0:
                loyalty_balance = await loyalty_service.get_balance(
                    db=db, patient_id=pid,
                )
                if loyalty_balance and loyalty_balance["points_balance"] > 0:
                    ratio = await loyalty_service.get_points_to_currency_ratio(db=db)
                    max_points = invoice.balance // ratio  # Max points that make sense
                    redeemable = min(loyalty_balance["points_balance"], max_points)
                    if redeemable > 0:
                        result = await loyalty_service.redeem_points(
                            db=db,
                            patient_id=pid,
                            points=redeemable,
                            reason="Auto-redeem on invoice creation",
                            performed_by=None,
                        )
                        loyalty_discount = result.get("discount_cents", 0)
                        if loyalty_discount > 0:
                            invoice.total = max(invoice.total - loyalty_discount, 0)
                            invoice.balance = max(invoice.balance - loyalty_discount, 0)
                            if invoice.balance == 0:
                                invoice.status = "paid"
                            await db.flush()
                            await db.refresh(invoice)
        except Exception:
            logger.debug("Loyalty redemption skipped — service unavailable or disabled")

        logger.info("Invoice created: number=%s patient=%s", invoice_number, patient_id[:8])

        return _invoice_to_dict(invoice)

    async def get_invoice(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        invoice_id: str,
    ) -> dict[str, Any] | None:
        """Fetch a single invoice with items.

        Performs lazy overdue detection: if status=sent + due_date < today + balance > 0,
        flips status to 'overdue'.
        """
        result = await db.execute(
            select(Invoice).where(
                Invoice.id == uuid.UUID(invoice_id),
                Invoice.patient_id == uuid.UUID(patient_id),
                Invoice.is_active.is_(True),
            )
        )
        inv = result.scalar_one_or_none()
        if inv is None:
            return None

        # Lazy overdue detection
        if (
            inv.status == "sent"
            and inv.due_date is not None
            and inv.due_date < date.today()
            and inv.balance > 0
        ):
            inv.status = "overdue"
            await db.flush()

        return _invoice_to_dict(inv)

    async def list_invoices(
        self,
        *,
        db: AsyncSession,
        patient_id: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Paginated list of invoices, optionally filtered by patient and/or status."""
        offset = (page - 1) * page_size

        # Build base conditions
        conditions = [Invoice.is_active.is_(True)]
        if patient_id:
            conditions.append(Invoice.patient_id == uuid.UUID(patient_id))
        if status:
            conditions.append(Invoice.status == status)

        total = (await db.execute(
            select(func.count(Invoice.id)).where(*conditions)
        )).scalar_one()

        invoices = (await db.execute(
            select(Invoice)
            .where(*conditions)
            .order_by(Invoice.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )).scalars().all()

        # Lazy overdue detection on list results
        today = date.today()
        for inv in invoices:
            if (
                inv.status == "sent"
                and inv.due_date is not None
                and inv.due_date < today
                and inv.balance > 0
            ):
                inv.status = "overdue"
        await db.flush()

        return {
            "items": [_invoice_to_dict(inv) for inv in invoices],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def cancel_invoice(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        invoice_id: str,
    ) -> dict[str, Any]:
        """Cancel an invoice. Only allowed if status is draft, sent, or overdue.

        Raises:
            ResourceNotFoundError (404) — invoice not found.
            BillingError (409) — invoice cannot be cancelled.
        """
        result = await db.execute(
            select(Invoice).where(
                Invoice.id == uuid.UUID(invoice_id),
                Invoice.patient_id == uuid.UUID(patient_id),
                Invoice.is_active.is_(True),
            )
        )
        inv = result.scalar_one_or_none()

        if inv is None:
            raise ResourceNotFoundError(
                error=BillingErrors.INVOICE_NOT_FOUND,
                resource_name="Invoice",
            )

        if inv.status not in ("draft", "sent", "overdue"):
            raise BillingError(
                error=BillingErrors.INVOICE_ALREADY_CANCELLED,
                message=f"No se puede cancelar una factura con estado '{inv.status}'.",
                status_code=409,
            )

        inv.status = "cancelled"
        await db.flush()
        await db.refresh(inv)

        logger.info("Invoice cancelled: number=%s", inv.invoice_number)

        return _invoice_to_dict(inv)

    async def send_invoice(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        invoice_id: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Mark an invoice as sent and enqueue notification.

        Raises:
            ResourceNotFoundError (404) — invoice not found.
            BillingError (409) — invoice is not in draft status.
        """
        result = await db.execute(
            select(Invoice).where(
                Invoice.id == uuid.UUID(invoice_id),
                Invoice.patient_id == uuid.UUID(patient_id),
                Invoice.is_active.is_(True),
            )
        )
        inv = result.scalar_one_or_none()

        if inv is None:
            raise ResourceNotFoundError(
                error=BillingErrors.INVOICE_NOT_FOUND,
                resource_name="Invoice",
            )

        if inv.status != "draft":
            raise BillingError(
                error=BillingErrors.INVOICE_NOT_PAYABLE,
                message="Solo se pueden enviar facturas en estado 'draft'.",
                status_code=409,
            )

        inv.status = "sent"
        await db.flush()
        await db.refresh(inv)

        # Enqueue email notification
        await publish_message(
            "notifications",
            QueueMessage(
                tenant_id=tenant_id,
                job_type="invoice.sent",
                payload={
                    "invoice_id": invoice_id,
                    "patient_id": patient_id,
                    "invoice_number": inv.invoice_number,
                    "total": inv.total,
                    "due_date": str(inv.due_date) if inv.due_date else None,
                },
            ),
        )

        logger.info("Invoice sent: number=%s", inv.invoice_number)

        return _invoice_to_dict(inv)

    async def recalculate_balance(
        self,
        *,
        db: AsyncSession,
        invoice_id: uuid.UUID,
    ) -> Invoice:
        """Recalculate amount_paid, balance, and status for an invoice.

        Called after a payment is recorded. Updates:
          - amount_paid = SUM(payments.amount)
          - balance = total - amount_paid
          - status = 'paid' if balance == 0, 'partial' if balance > 0 and amount_paid > 0
        """
        inv_result = await db.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        inv = inv_result.scalar_one()

        # Sum all payments for this invoice
        paid_result = await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.invoice_id == invoice_id,
            )
        )
        total_paid = paid_result.scalar_one()

        inv.amount_paid = total_paid
        inv.balance = inv.total - total_paid

        if inv.balance <= 0:
            inv.status = "paid"
            inv.paid_at = datetime.now(UTC)
            inv.balance = 0
        elif total_paid > 0 and inv.status not in ("cancelled",):
            inv.status = "partial"

        await db.flush()
        return inv


# Module-level singleton
invoice_service = InvoiceService()
