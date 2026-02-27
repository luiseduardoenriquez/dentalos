"""Analytics API routes — AN-01 through AN-07.

Endpoint map:
  GET /analytics/dashboard     — AN-01: KPI dashboard (5 parallel queries)
  GET /analytics/patients      — AN-02: Patient demographics & acquisition
  GET /analytics/appointments  — AN-03: Appointment utilization & peaks
  GET /analytics/revenue       — AN-04: Revenue trends & breakdowns
  GET /analytics/clinical      — AN-05: Clinical analytics (stub)
  GET /analytics/export        — AN-06: Export (stub, 501)
  GET /analytics/audit-trail   — AN-07: Audit trail (clinic_owner only)
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.schemas.analytics import (
    AppointmentAnalyticsResponse,
    AuditTrailResponse,
    DashboardResponse,
    PatientAnalyticsResponse,
    PeriodInfo,
    RevenueAnalyticsResponse,
)
from app.services.analytics_service import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ─── AN-01: Dashboard ────────────────────────────────────────────────────────


@router.get("/dashboard", response_model=DashboardResponse)
async def analytics_dashboard(
    period: str = Query(
        default="month",
        pattern=r"^(today|week|month|quarter|year|custom)$",
        description="Analytics period.",
    ),
    date_from: date | None = Query(default=None, description="Start date (custom period)."),
    date_to: date | None = Query(default=None, description="End date (custom period)."),
    doctor_id: UUID | None = Query(default=None, description="Filter by doctor (clinic_owner only)."),
    current_user: AuthenticatedUser = Depends(require_permission("analytics:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> DashboardResponse:
    """KPI dashboard: patients, appointments, revenue, procedures, occupancy."""
    return await analytics_service.get_dashboard(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
        current_user=current_user,
        period=period,
        date_from=date_from,
        date_to=date_to,
        doctor_id=doctor_id,
    )


# ─── AN-02: Patient analytics ────────────────────────────────────────────────


@router.get("/patients", response_model=PatientAnalyticsResponse)
async def patient_analytics(
    period: str = Query(
        default="month",
        pattern=r"^(today|week|month|quarter|year|custom)$",
        description="Analytics period.",
    ),
    date_from: date | None = Query(default=None, description="Start date (custom period)."),
    date_to: date | None = Query(default=None, description="End date (custom period)."),
    current_user: AuthenticatedUser = Depends(require_permission("analytics:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> PatientAnalyticsResponse:
    """Patient demographics, acquisition trend, and retention."""
    return await analytics_service.get_patient_analytics(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
        current_user=current_user,
        period=period,
        date_from=date_from,
        date_to=date_to,
    )


# ─── AN-03: Appointment analytics ────────────────────────────────────────────


@router.get("/appointments", response_model=AppointmentAnalyticsResponse)
async def appointment_analytics(
    period: str = Query(
        default="month",
        pattern=r"^(today|week|month|quarter|year|custom)$",
        description="Analytics period.",
    ),
    date_from: date | None = Query(default=None, description="Start date (custom period)."),
    date_to: date | None = Query(default=None, description="End date (custom period)."),
    doctor_id: UUID | None = Query(default=None, description="Filter by doctor (clinic_owner only)."),
    current_user: AuthenticatedUser = Depends(require_permission("analytics:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> AppointmentAnalyticsResponse:
    """Appointment utilization, peak hours, no-show trend."""
    return await analytics_service.get_appointment_analytics(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
        current_user=current_user,
        period=period,
        date_from=date_from,
        date_to=date_to,
        doctor_id=doctor_id,
    )


# ─── AN-04: Revenue analytics ────────────────────────────────────────────────


@router.get("/revenue", response_model=RevenueAnalyticsResponse)
async def revenue_analytics(
    period: str = Query(
        default="month",
        pattern=r"^(today|week|month|quarter|year|custom)$",
        description="Analytics period.",
    ),
    date_from: date | None = Query(default=None, description="Start date (custom period)."),
    date_to: date | None = Query(default=None, description="End date (custom period)."),
    doctor_id: UUID | None = Query(default=None, description="Filter by doctor (clinic_owner only)."),
    current_user: AuthenticatedUser = Depends(require_permission("analytics:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> RevenueAnalyticsResponse:
    """Revenue trend, by doctor, by procedure, payment methods, accounts receivable."""
    return await analytics_service.get_revenue_analytics(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
        current_user=current_user,
        period=period,
        date_from=date_from,
        date_to=date_to,
        doctor_id=doctor_id,
    )


# ─── AN-05: Clinical analytics (stub) ────────────────────────────────────────


@router.get("/clinical")
async def clinical_analytics(
    period: str = Query(
        default="month",
        pattern=r"^(today|week|month|quarter|year|custom)$",
        description="Analytics period.",
    ),
    date_from: date | None = Query(default=None, description="Start date (custom period)."),
    date_to: date | None = Query(default=None, description="End date (custom period)."),
    current_user: AuthenticatedUser = Depends(require_permission("analytics:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Clinical analytics (placeholder for future implementation)."""
    from app.services.analytics_service import AnalyticsService

    d_from, d_to = AnalyticsService.resolve_date_range(period, date_from, date_to)
    return {
        "period": PeriodInfo(
            date_from=d_from.isoformat(),
            date_to=d_to.isoformat(),
            period=period,
        ).model_dump(),
        "message": "Clinical analytics will be available in a future release.",
    }


# ─── AN-06: Export (stub, 501) ────────────────────────────────────────────────


@router.get("/export")
async def analytics_export(
    current_user: AuthenticatedUser = Depends(require_permission("analytics:read")),
) -> JSONResponse:
    """Analytics export (not yet implemented)."""
    return JSONResponse(
        status_code=501,
        content={"status": "not_implemented"},
    )


# ─── AN-07: Audit trail ──────────────────────────────────────────────────────


@router.get("/audit-trail", response_model=AuditTrailResponse)
async def audit_trail(
    cursor: str | None = Query(default=None, description="Pagination cursor (base64)."),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page."),
    user_id: UUID | None = Query(default=None, description="Filter by user ID."),
    resource_type: str | None = Query(default=None, description="Filter by resource type."),
    action: str | None = Query(default=None, description="Filter by action."),
    date_from: date | None = Query(default=None, description="Filter from date."),
    date_to: date | None = Query(default=None, description="Filter to date."),
    current_user: AuthenticatedUser = Depends(require_permission("analytics:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> AuditTrailResponse:
    """Audit trail with cursor-based pagination.  clinic_owner only."""
    return await analytics_service.get_audit_trail(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
        tenant_schema=current_user.tenant.schema_name,
        current_user=current_user,
        cursor=cursor,
        page_size=page_size,
        user_id=user_id,
        resource_type=resource_type,
        action=action,
        date_from=date_from,
        date_to=date_to,
    )
