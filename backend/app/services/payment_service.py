"""Payment service — record payments and manage payment plans.

Security invariants:
  - PHI is NEVER logged.
  - Payments are IMMUTABLE (financial audit trail).
  - All monetary values in COP cents.
"""

import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import BillingErrors
from app.core.exceptions import BillingError, ResourceNotFoundError
from app.core.queue import publish_message
from app.models.tenant.cash_register import CashMovement, CashRegister
from app.models.tenant.invoice import Invoice, InvoiceItem
from app.models.tenant.ortho import OrthoVisit
from app.models.tenant.payment import Payment
from app.models.tenant.payment_plan import PaymentPlan, PaymentPlanInstallment
from app.schemas.queue import QueueMessage
from app.services.invoice_service import invoice_service

logger = logging.getLogger("dentalos.payment")


def _payment_to_dict(p: Payment) -> dict[str, Any]:
    return {
        "id": str(p.id),
        "invoice_id": str(p.invoice_id),
        "patient_id": str(p.patient_id),
        "amount": p.amount,
        "currency": getattr(p, "currency", "COP") or "COP",
        "payment_method": p.payment_method,
        "reference_number": p.reference_number,
        "received_by": str(p.received_by),
        "notes": p.notes,
        "payment_date": p.payment_date,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


def _installment_to_dict(inst: PaymentPlanInstallment) -> dict[str, Any]:
    return {
        "id": str(inst.id),
        "plan_id": str(inst.plan_id),
        "installment_number": inst.installment_number,
        "amount": inst.amount,
        "due_date": inst.due_date,
        "status": inst.status,
        "paid_at": inst.paid_at,
        "payment_id": str(inst.payment_id) if inst.payment_id else None,
        "created_at": inst.created_at,
        "updated_at": inst.updated_at,
    }


def _plan_to_dict(plan: PaymentPlan) -> dict[str, Any]:
    installments = (
        [_installment_to_dict(i) for i in plan.installments]
        if plan.installments
        else []
    )
    return {
        "id": str(plan.id),
        "invoice_id": str(plan.invoice_id),
        "patient_id": str(plan.patient_id),
        "total_amount": plan.total_amount,
        "num_installments": plan.num_installments,
        "status": plan.status,
        "created_by": str(plan.created_by),
        "is_active": plan.is_active,
        "installments": installments,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }


class PaymentService:
    """Stateless payment service."""

    async def record_payment(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        invoice_id: str,
        amount: int,
        payment_method: str,
        currency: str = "COP",
        received_by: str,
        reference_number: str | None = None,
        notes: str | None = None,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Record a payment against an invoice.

        Validates amount <= invoice.balance. After recording, recalculates
        the invoice balance. If fully paid, enqueues receipt notification.

        Raises:
            ResourceNotFoundError (404) — invoice not found.
            BillingError (409) — invoice not payable or payment exceeds balance.
        """
        iid = uuid.UUID(invoice_id)
        pid = uuid.UUID(patient_id)

        # Fetch invoice
        inv_result = await db.execute(
            select(Invoice).where(
                Invoice.id == iid,
                Invoice.patient_id == pid,
                Invoice.is_active.is_(True),
            )
        )
        inv = inv_result.scalar_one_or_none()

        if inv is None:
            raise ResourceNotFoundError(
                error=BillingErrors.INVOICE_NOT_FOUND,
                resource_name="Invoice",
            )

        if inv.status in ("cancelled", "draft"):
            raise BillingError(
                error=BillingErrors.INVOICE_NOT_PAYABLE,
                message=f"No se puede registrar un pago en una factura con estado '{inv.status}'.",
                status_code=409,
            )

        if amount > inv.balance:
            raise BillingError(
                error=BillingErrors.PAYMENT_EXCEEDS_BALANCE,
                message=f"El monto ({amount}) excede el saldo pendiente ({inv.balance}).",
                status_code=409,
            )

        # Create payment — store currency alongside amount for multi-currency support
        payment = Payment(
            invoice_id=iid,
            patient_id=pid,
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            reference_number=reference_number,
            received_by=uuid.UUID(received_by),
            notes=notes,
        )
        db.add(payment)
        await db.flush()

        # Bridge: create cash movement if there is an open cash register
        register_result = await db.execute(
            select(CashRegister).where(CashRegister.status == "open").limit(1)
        )
        open_register = register_result.scalar_one_or_none()
        if open_register is not None:
            movement = CashMovement(
                register_id=open_register.id,
                type="income",
                amount_cents=amount,
                payment_method=payment_method,
                reference_id=payment.id,
                reference_type="payment",
                description=f"Pago factura {inv.invoice_number}",
                recorded_by=uuid.UUID(received_by),
            )
            db.add(movement)
            await db.flush()

        # Recalculate invoice balance
        inv = await invoice_service.recalculate_balance(db=db, invoice_id=iid)

        # Bridge: sync OrthoVisit payment_status when invoice is fully paid
        if inv.status == "paid":
            ortho_items_result = await db.execute(
                select(InvoiceItem.ortho_visit_id).where(
                    InvoiceItem.invoice_id == iid,
                    InvoiceItem.ortho_visit_id.isnot(None),
                )
            )
            ortho_visit_ids = [row[0] for row in ortho_items_result.all()]
            if ortho_visit_ids:
                visits_result = await db.execute(
                    select(OrthoVisit).where(OrthoVisit.id.in_(ortho_visit_ids))
                )
                for visit in visits_result.scalars().all():
                    visit.payment_status = "paid"
                    visit.payment_id = payment.id
                await db.flush()

        # Enqueue payment receipt notification
        await publish_message(
            "notifications",
            QueueMessage(
                tenant_id=tenant_id,
                job_type="payment.receipt",
                payload={
                    "payment_id": str(payment.id),
                    "invoice_id": invoice_id,
                    "patient_id": patient_id,
                    "amount": amount,
                    "currency": currency,
                    "payment_method": payment_method,
                    "invoice_number": inv.invoice_number,
                    "balance": inv.balance,
                },
            ),
        )

        logger.info(
            "Payment recorded: invoice=%s amount=%d method=%s",
            invoice_id[:8],
            amount,
            payment_method,
        )

        return _payment_to_dict(payment)

    async def list_payments(
        self,
        *,
        db: AsyncSession,
        invoice_id: str | None = None,
        patient_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Paginated list of payments, filtered by invoice or patient."""
        offset = (page - 1) * page_size

        conditions = []
        if invoice_id:
            conditions.append(Payment.invoice_id == uuid.UUID(invoice_id))
        if patient_id:
            conditions.append(Payment.patient_id == uuid.UUID(patient_id))

        total = (await db.execute(
            select(func.count(Payment.id)).where(*conditions)
        )).scalar_one()

        payments = (await db.execute(
            select(Payment)
            .where(*conditions)
            .order_by(Payment.payment_date.desc())
            .offset(offset)
            .limit(page_size)
        )).scalars().all()

        return {
            "items": [_payment_to_dict(p) for p in payments],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def create_payment_plan(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        invoice_id: str,
        num_installments: int,
        first_due_date: date,
        created_by: str,
    ) -> dict[str, Any]:
        """Create a payment plan for an invoice.

        Splits the invoice balance into N equal installments with monthly due dates.
        Only one active plan per invoice.

        Raises:
            ResourceNotFoundError (404) — invoice not found.
            BillingError (409) — active plan already exists.
        """
        iid = uuid.UUID(invoice_id)
        pid = uuid.UUID(patient_id)

        # Fetch invoice
        inv_result = await db.execute(
            select(Invoice).where(
                Invoice.id == iid,
                Invoice.patient_id == pid,
                Invoice.is_active.is_(True),
            )
        )
        inv = inv_result.scalar_one_or_none()

        if inv is None:
            raise ResourceNotFoundError(
                error=BillingErrors.INVOICE_NOT_FOUND,
                resource_name="Invoice",
            )

        # Check for existing active plan
        existing = await db.execute(
            select(PaymentPlan.id).where(
                PaymentPlan.invoice_id == iid,
                PaymentPlan.status == "active",
                PaymentPlan.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise BillingError(
                error=BillingErrors.PLAN_ALREADY_EXISTS,
                message="Ya existe un plan de pagos activo para esta factura.",
                status_code=409,
            )

        # Create plan
        plan = PaymentPlan(
            invoice_id=iid,
            patient_id=pid,
            total_amount=inv.balance,
            num_installments=num_installments,
            status="active",
            created_by=uuid.UUID(created_by),
            is_active=True,
        )
        db.add(plan)
        await db.flush()

        # Split balance into installments
        base_amount = inv.balance // num_installments
        remainder = inv.balance % num_installments

        for i in range(num_installments):
            # First installment gets the remainder
            inst_amount = base_amount + (remainder if i == 0 else 0)
            inst_due_date = first_due_date + timedelta(days=30 * i)

            installment = PaymentPlanInstallment(
                plan_id=plan.id,
                installment_number=i + 1,
                amount=inst_amount,
                due_date=inst_due_date,
                status="pending",
            )
            db.add(installment)

        await db.flush()
        await db.refresh(plan)

        logger.info(
            "Payment plan created: invoice=%s installments=%d",
            invoice_id[:8],
            num_installments,
        )

        return _plan_to_dict(plan)

    async def get_payment_plan(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        invoice_id: str,
    ) -> dict[str, Any] | None:
        """Fetch the active payment plan for an invoice.

        Performs lazy overdue detection on installments.
        """
        result = await db.execute(
            select(PaymentPlan).where(
                PaymentPlan.invoice_id == uuid.UUID(invoice_id),
                PaymentPlan.patient_id == uuid.UUID(patient_id),
                PaymentPlan.status == "active",
                PaymentPlan.is_active.is_(True),
            )
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            return None

        # Lazy overdue detection on installments
        today = date.today()
        for inst in plan.installments:
            if inst.status == "pending" and inst.due_date < today:
                inst.status = "overdue"
        await db.flush()

        return _plan_to_dict(plan)

    async def pay_installment(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        invoice_id: str,
        installment_number: int,
        payment_method: str,
        received_by: str,
        reference_number: str | None = None,
        notes: str | None = None,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Pay a specific installment.

        Records a payment linked to the installment, marks it as paid.
        If all installments are paid, marks the plan as completed.

        Raises:
            ResourceNotFoundError (404) — plan or installment not found.
            BillingError (409) — installment already paid.
        """
        iid = uuid.UUID(invoice_id)
        pid = uuid.UUID(patient_id)

        # Fetch plan
        plan_result = await db.execute(
            select(PaymentPlan).where(
                PaymentPlan.invoice_id == iid,
                PaymentPlan.patient_id == pid,
                PaymentPlan.status == "active",
                PaymentPlan.is_active.is_(True),
            )
        )
        plan = plan_result.scalar_one_or_none()

        if plan is None:
            raise ResourceNotFoundError(
                error=BillingErrors.INVOICE_NOT_FOUND,
                resource_name="PaymentPlan",
            )

        # Find installment
        installment = None
        for inst in plan.installments:
            if inst.installment_number == installment_number:
                installment = inst
                break

        if installment is None:
            raise ResourceNotFoundError(
                error=BillingErrors.INSTALLMENT_NOT_FOUND,
                resource_name="Installment",
            )

        if installment.status == "paid":
            raise BillingError(
                error=BillingErrors.INVOICE_ALREADY_PAID,
                message=f"La cuota #{installment_number} ya fue pagada.",
                status_code=409,
            )

        # Record payment via the payment service
        payment_dict = await self.record_payment(
            db=db,
            patient_id=patient_id,
            invoice_id=invoice_id,
            amount=installment.amount,
            payment_method=payment_method,
            received_by=received_by,
            reference_number=reference_number,
            notes=notes or f"Pago cuota #{installment_number}",
            tenant_id=tenant_id,
        )

        # Mark installment as paid
        installment.status = "paid"
        installment.paid_at = datetime.now(UTC)
        installment.payment_id = uuid.UUID(payment_dict["id"])

        # Check if all installments are paid → complete plan
        all_paid = all(i.status == "paid" for i in plan.installments)
        if all_paid:
            plan.status = "completed"

        await db.flush()

        logger.info(
            "Installment paid: plan=%s installment=#%d",
            str(plan.id)[:8],
            installment_number,
        )

        return payment_dict


# Module-level singleton
payment_service = PaymentService()
