"""Billing summary API routes — B-11, B-12, B-12b, B-13.

Endpoint map:
  GET /billing/summary       — B-11: Billing summary (totals for dashboard)
  GET /billing/aging-report  — B-12: Aging report (overdue invoices by age)
  GET /billing/commissions   — B-12b: Doctor commissions report
  GET /billing/revenue       — B-13: Revenue report (collected by period)
"""

from datetime import date, datetime as dt, timedelta
from uuid import UUID as PyUUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import Date, String, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.core.exceptions import BusinessValidationError
from app.models.tenant.invoice import Invoice, InvoiceItem
from app.models.tenant.patient import Patient
from app.models.tenant.payment import Payment
from app.models.tenant.user import User

router = APIRouter(prefix="/billing", tags=["billing"])


# ─── Response schemas (colocated — small, endpoint-specific) ────────────────


class BillingSummaryResponse(BaseModel):
    total_pending: int  # cents
    total_overdue: int  # cents
    collected_month: int  # cents
    collected_year: int  # cents
    invoice_count: int
    overdue_count: int


class AgingBucket(BaseModel):
    label: str
    count: int
    total: int  # cents


class AgingReportResponse(BaseModel):
    buckets: list[AgingBucket]
    total_overdue: int  # cents


class RevenueResponse(BaseModel):
    period: str
    collected: int  # cents
    invoice_count: int
    payment_count: int


class InvoiceSummaryItem(BaseModel):
    id: str
    invoice_number: str
    patient_id: str
    patient_name: str
    total: int  # cents
    balance: int  # cents
    status: str
    due_date: str | None
    created_at: str


class InvoiceSummaryListResponse(BaseModel):
    items: list[InvoiceSummaryItem]
    total: int
    page: int
    page_size: int


# ─── Global invoice list (cross-patient) ────────────────────────────────────


@router.get("/invoices", response_model=InvoiceSummaryListResponse)
async def list_all_invoices(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(
        require_permission("billing:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> InvoiceSummaryListResponse:
    """List invoices across all patients for the billing dashboard."""
    conditions = [Invoice.is_active.is_(True)]
    if status:
        conditions.append(Invoice.status == status)

    # Count
    count_result = await db.execute(
        select(func.count(Invoice.id)).where(*conditions)
    )
    total = count_result.scalar_one()

    # Paginated list with patient name join
    offset = (page - 1) * page_size
    rows_result = await db.execute(
        select(
            Invoice.id,
            Invoice.invoice_number,
            Invoice.patient_id,
            (Patient.first_name + " " + Patient.last_name).label("patient_name"),
            Invoice.total,
            Invoice.balance,
            Invoice.status,
            Invoice.due_date,
            Invoice.created_at,
        )
        .outerjoin(Patient, Patient.id == Invoice.patient_id)
        .where(*conditions)
        .order_by(Invoice.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    rows = rows_result.all()

    items = [
        InvoiceSummaryItem(
            id=str(row.id),
            invoice_number=row.invoice_number,
            patient_id=str(row.patient_id),
            patient_name=row.patient_name or "—",
            total=row.total,
            balance=row.balance,
            status=row.status,
            due_date=row.due_date.isoformat() if row.due_date else None,
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]

    return InvoiceSummaryListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# ─── B-11: Billing summary ──────────────────────────────────────────────────


@router.get("/summary", response_model=BillingSummaryResponse)
async def billing_summary(
    current_user: AuthenticatedUser = Depends(
        require_permission("billing:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> BillingSummaryResponse:
    """Dashboard billing summary: pending, overdue, collected this month/year."""
    today = date.today()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    # Pending invoices (sent + partial + overdue)
    pending_result = await db.execute(
        select(
            func.coalesce(func.sum(Invoice.balance), 0),
            func.count(Invoice.id),
        ).where(
            Invoice.status.in_(["sent", "partial", "overdue"]),
            Invoice.is_active.is_(True),
        )
    )
    pending_row = pending_result.one()
    total_pending = pending_row[0]
    invoice_count = pending_row[1]

    # Overdue invoices
    overdue_result = await db.execute(
        select(
            func.coalesce(func.sum(Invoice.balance), 0),
            func.count(Invoice.id),
        ).where(
            Invoice.status == "overdue",
            Invoice.is_active.is_(True),
        )
    )
    overdue_row = overdue_result.one()
    total_overdue = overdue_row[0]
    overdue_count = overdue_row[1]

    # Collected this month
    month_result = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.payment_date >= month_start,
        )
    )
    collected_month = month_result.scalar_one()

    # Collected this year
    year_result = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.payment_date >= year_start,
        )
    )
    collected_year = year_result.scalar_one()

    return BillingSummaryResponse(
        total_pending=total_pending,
        total_overdue=total_overdue,
        collected_month=collected_month,
        collected_year=collected_year,
        invoice_count=invoice_count,
        overdue_count=overdue_count,
    )


# ─── B-12: Aging report ─────────────────────────────────────────────────────


@router.get("/aging-report", response_model=AgingReportResponse)
async def aging_report(
    current_user: AuthenticatedUser = Depends(
        require_permission("billing:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> AgingReportResponse:
    """Aging report: overdue invoices grouped by age buckets."""
    today = date.today()

    # Define buckets: 1-30 days, 31-60 days, 61-90 days, 90+ days
    bucket_expr = case(
        (Invoice.due_date >= today - timedelta(days=30), "1-30 días"),
        (Invoice.due_date >= today - timedelta(days=60), "31-60 días"),
        (Invoice.due_date >= today - timedelta(days=90), "61-90 días"),
        else_="90+ días",
    )

    result = await db.execute(
        select(
            bucket_expr.label("bucket"),
            func.count(Invoice.id).label("count"),
            func.coalesce(func.sum(Invoice.balance), 0).label("total"),
        )
        .where(
            Invoice.status.in_(["overdue", "sent"]),
            Invoice.due_date < today,
            Invoice.balance > 0,
            Invoice.is_active.is_(True),
        )
        .group_by(bucket_expr)
    )
    rows = result.all()

    buckets = [
        AgingBucket(label=row.bucket, count=row.count, total=row.total)
        for row in rows
    ]
    total_overdue = sum(b.total for b in buckets)

    return AgingReportResponse(buckets=buckets, total_overdue=total_overdue)


# ─── B-13: Revenue report ───────────────────────────────────────────────────


@router.get("/revenue", response_model=RevenueResponse)
async def revenue_report(
    period: str = Query(
        default="month",
        pattern=r"^(month|year)$",
        description="Report period: 'month' or 'year'",
    ),
    current_user: AuthenticatedUser = Depends(
        require_permission("billing:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> RevenueResponse:
    """Revenue report: total collected for the current month or year."""
    today = date.today()

    if period == "month":
        start_date = today.replace(day=1)
    else:
        start_date = today.replace(month=1, day=1)

    # Total collected
    collected_result = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.payment_date >= start_date,
        )
    )
    collected = collected_result.scalar_one()

    # Invoice count (paid in period)
    invoice_count_result = await db.execute(
        select(func.count(Invoice.id)).where(
            Invoice.status == "paid",
            Invoice.paid_at >= start_date,
            Invoice.is_active.is_(True),
        )
    )
    invoice_count = invoice_count_result.scalar_one()

    # Payment count
    payment_count_result = await db.execute(
        select(func.count(Payment.id)).where(
            Payment.payment_date >= start_date,
        )
    )
    payment_count = payment_count_result.scalar_one()

    return RevenueResponse(
        period=period,
        collected=collected,
        invoice_count=invoice_count,
        payment_count=payment_count,
    )


# ─── Commissions schemas ─────────────────────────────────────────────────────


class CommissionDoctor(BaseModel):
    id: str
    name: str
    specialty: str | None


class CommissionEntry(BaseModel):
    doctor: CommissionDoctor
    procedure_count: int
    total_revenue: int  # cents
    commission_percentage: float
    commission_amount: int  # cents


class CommissionTotals(BaseModel):
    total_revenue: int  # cents
    total_commission: int  # cents


class CommissionPeriod(BaseModel):
    date_from: str
    date_to: str


class CommissionsReportResponse(BaseModel):
    period: CommissionPeriod
    currency: str
    commissions: list[CommissionEntry]
    totals: CommissionTotals
    generated_at: str


# ─── B-12b: Commissions report ──────────────────────────────────────────────


@router.get("/commissions", response_model=CommissionsReportResponse)
async def commissions_report(
    date_from: date = Query(..., description="Start date (inclusive)"),
    date_to: date = Query(..., description="End date (inclusive)"),
    doctor_id: PyUUID | None = Query(default=None, description="Filter to single doctor"),
    status: str = Query(
        default="paid",
        pattern=r"^(paid|all)$",
        description="Invoice status filter: 'paid' or 'all'",
    ),
    current_user: AuthenticatedUser = Depends(
        require_permission("billing:read")
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> CommissionsReportResponse:
    """Doctor commission report for a date range.

    Calculates per-doctor: procedure count, total revenue, commission amount.
    Uses invoice.created_by as the doctor reference. Commission percentage
    is configured per doctor on their user profile.
    """
    today = date.today()

    # Validate date range
    if date_from > date_to:
        raise BusinessValidationError(
            "Rango de fechas inválido.",
            field_errors={"date_from": ["La fecha de inicio debe ser anterior a la fecha de fin."]},
        )
    if date_to > today:
        raise BusinessValidationError(
            "Rango de fechas inválido.",
            field_errors={"date_to": ["La fecha de fin no puede ser futura."]},
        )
    if (date_to - date_from).days > 366:
        raise BusinessValidationError(
            "Rango de fechas inválido.",
            field_errors={"date_range": ["El rango de fechas no puede superar 366 días."]},
        )

    # Build status filter
    if status == "paid":
        status_filter = ["paid"]
    else:
        status_filter = ["draft", "sent", "partial", "paid", "overdue"]

    # Doctor filter
    doctor_filter = []
    if doctor_id is not None:
        doctor_filter.append(User.id == doctor_id)

    # Main aggregation query
    # Join: users LEFT JOIN invoices (filtered by date/status) LEFT JOIN invoice_items
    stmt = (
        select(
            User.id,
            User.name,
            User.specialties,
            User.commission_percentage,
            func.coalesce(func.count(InvoiceItem.id), 0).label("procedure_count"),
            func.coalesce(func.sum(InvoiceItem.line_total), 0).label("total_revenue"),
        )
        .outerjoin(
            Invoice,
            (Invoice.created_by == User.id)
            & (Invoice.status.in_(status_filter))
            & (func.cast(Invoice.created_at, Date) >= date_from)
            & (func.cast(Invoice.created_at, Date) <= date_to)
            & (Invoice.is_active.is_(True)),
        )
        .outerjoin(InvoiceItem, InvoiceItem.invoice_id == Invoice.id)
        .where(
            User.role == "doctor",
            User.is_active.is_(True),
            *doctor_filter,
        )
        .group_by(User.id, User.name, User.specialties, User.commission_percentage)
        .order_by(func.coalesce(func.sum(InvoiceItem.line_total), 0).desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    commissions = []
    total_rev = 0
    total_comm = 0

    for row in rows:
        pct = float(row.commission_percentage) if row.commission_percentage is not None else 0.0
        revenue = int(row.total_revenue)
        comm_amount = int(revenue * pct / 100)  # floor via int()
        specialty = row.specialties[0] if row.specialties else None

        commissions.append(
            CommissionEntry(
                doctor=CommissionDoctor(
                    id=str(row.id),
                    name=row.name,
                    specialty=specialty,
                ),
                procedure_count=int(row.procedure_count),
                total_revenue=revenue,
                commission_percentage=pct,
                commission_amount=comm_amount,
            )
        )
        total_rev += revenue
        total_comm += comm_amount

    return CommissionsReportResponse(
        period=CommissionPeriod(
            date_from=date_from.isoformat(),
            date_to=date_to.isoformat(),
        ),
        currency="COP",
        commissions=commissions,
        totals=CommissionTotals(
            total_revenue=total_rev,
            total_commission=total_comm,
        ),
        generated_at=dt.now().isoformat(),
    )
