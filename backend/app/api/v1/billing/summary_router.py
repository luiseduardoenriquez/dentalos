"""Billing summary API routes — B-11, B-12, B-13.

Endpoint map:
  GET /billing/summary       — B-11: Billing summary (totals for dashboard)
  GET /billing/aging-report  — B-12: Aging report (overdue invoices by age)
  GET /billing/revenue       — B-13: Revenue report (collected by period)
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.models.tenant.invoice import Invoice
from app.models.tenant.payment import Payment

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
