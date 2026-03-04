"""Analytics API routes — AN-01 through AN-07 + VP-04 Huddle.

Endpoint map:
  GET /analytics/dashboard     — AN-01: KPI dashboard (5 parallel queries)
  GET /analytics/patients      — AN-02: Patient demographics & acquisition
  GET /analytics/appointments  — AN-03: Appointment utilization & peaks
  GET /analytics/revenue       — AN-04: Revenue trends & breakdowns
  GET /analytics/clinical      — AN-05: Clinical analytics (stub)
  GET /analytics/export        — AN-06: CSV export (sync <=1000 rows, 202 >1000)
  GET /analytics/audit-trail   — AN-07: Audit trail (clinic_owner only)
  GET /analytics/huddle        — VP-04: Morning Huddle daily briefing
"""

import csv
import io
import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
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
from app.services.audit_service import write_audit_log

logger = logging.getLogger("dentalos.analytics")

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


# ─── AN-06: Export ───────────────────────────────────────────────────────────

# Threshold above which export is deferred asynchronously.
_EXPORT_SYNC_LIMIT = 1_000

# Column definitions per report type — order matters for CSV header row.
_REPORT_COLUMNS: dict[str, list[str]] = {
    "patients": [
        "patient_id",
        "full_name",
        "date_of_birth",
        "gender",
        "phone",
        "email",
        "document_type",
        "document_number",
        "city",
        "created_at",
        "total_visits",
        "last_visit_date",
    ],
    "appointments": [
        "appointment_id",
        "patient_name",
        "doctor_name",
        "appointment_type",
        "scheduled_at",
        "status",
        "duration_scheduled_min",
    ],
    "revenue": [
        "invoice_id",
        "patient_name",
        "doctor_name",
        "issue_date",
        "total_amount",
        "status",
        "payment_method",
    ],
    "clinical": [
        "record_id",
        "doctor_name",
        "record_date",
        "diagnoses_cie10",
        "procedures_cups",
        "has_notes",
    ],
}


def _build_csv_bytes(columns: list[str], rows: list[dict]) -> bytes:
    """Render rows to a UTF-8 BOM CSV byte string (Excel-compatible)."""
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=columns,
        extrasaction="ignore",
        lineterminator="\r\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    # Prepend UTF-8 BOM so Excel auto-detects encoding.
    return "\ufeff".encode("utf-8") + buf.getvalue().encode("utf-8")


@router.get("/export", response_model=None)
async def analytics_export(
    request: Request,
    report_type: str = Query(
        ...,
        pattern=r"^(patients|appointments|revenue|clinical)$",
        description="Tipo de reporte a exportar.",
    ),
    period: str = Query(
        default="month",
        pattern=r"^(today|week|month|quarter|year|custom)$",
        description="Periodo de analisis.",
    ),
    date_from: date | None = Query(
        default=None,
        description="Fecha de inicio (requerida cuando period='custom').",
    ),
    date_to: date | None = Query(
        default=None,
        description="Fecha de fin (requerida cuando period='custom').",
    ),
    format: str = Query(
        default="csv",
        pattern=r"^csv$",
        description="Formato de exportacion (solo 'csv' en MVP).",
    ),
    current_user: AuthenticatedUser = Depends(require_permission("analytics:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> StreamingResponse | JSONResponse:
    """Export analytics data as CSV.

    - Datasets <= 1000 rows: returns synchronous StreamingResponse (200).
    - Datasets > 1000 rows: returns 202 with a deferral message
      (async export not yet implemented).

    Response headers:
      Content-Disposition: attachment; filename="..."
      X-Row-Count: <number of rows>
      X-Export-Mode: sync | async
    """
    rows, row_count = await analytics_service.export_analytics_data(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
        tenant_schema=current_user.tenant.schema_name,
        current_user=current_user,
        report_type=report_type,
        period=period,
        date_from=date_from,
        date_to=date_to,
    )

    # Write audit log — always, regardless of sync/async path.
    try:
        await write_audit_log(
            db=db,
            tenant_schema=current_user.tenant.schema_name,
            user_id=current_user.user_id,
            action="export",
            resource_type=f"analytics_{report_type}",
            resource_id=None,
            changes={
                "report_type": report_type,
                "period": period,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
                "row_count": row_count,
                "export_mode": "sync" if row_count <= _EXPORT_SYNC_LIMIT else "async",
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except Exception:
        logger.warning(
            "Failed to write audit log for analytics export: report_type=%s user=%s",
            report_type,
            current_user.user_id,
        )

    # Async path — dataset too large for synchronous delivery.
    if row_count > _EXPORT_SYNC_LIMIT:
        return JSONResponse(
            status_code=202,
            content={
                "message": (
                    "El reporte contiene mas de 1000 filas. "
                    "La exportacion asincrona estara disponible en una proxima version."
                ),
                "row_count": row_count,
                "report_type": report_type,
            },
            headers={
                "X-Row-Count": str(row_count),
                "X-Export-Mode": "async",
            },
        )

    # Sync path — build CSV and stream.
    columns = _REPORT_COLUMNS[report_type]
    csv_bytes = _build_csv_bytes(columns, rows)

    filename = f"dentalos_{report_type}_{date.today().isoformat()}.csv"

    return StreamingResponse(
        content=iter([csv_bytes]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Row-Count": str(row_count),
            "X-Export-Mode": "sync",
        },
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


# ─── VP-04: Morning Huddle ─────────────────────────────────────────────────


@router.get("/huddle")
async def morning_huddle(
    current_user: AuthenticatedUser = Depends(require_permission("analytics:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Morning Huddle — daily briefing aggregating 8 data sections."""
    from app.services.huddle_service import huddle_service

    return await huddle_service.get_huddle(
        db=db,
        tenant_id=current_user.tenant.tenant_id,
    )


# ─── GAP-06: Acceptance rate analytics ──────────────────────────────────────


@router.get("/acceptance-rate")
async def acceptance_rate(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(require_permission("analytics:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Quotation acceptance rate analytics (GAP-06).

    Returns total, accepted, pending, expired counts plus the acceptance
    rate ratio and average days-to-accept for approved quotations.
    """
    from app.services.staff_task_service import staff_task_service

    return await staff_task_service.get_acceptance_rate(
        db=db,
        date_from=date_from,
        date_to=date_to,
    )


# ─── GAP-03: Profit & Loss ─────────────────────────────────────────────────


@router.get("/profit-loss")
async def profit_loss(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(require_permission("analytics:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Profit and loss report (GAP-03).

    Aggregates revenue from invoices against expenses for the period,
    returning net profit, gross revenue, total expenses, and a breakdown
    by expense category.
    """
    from app.services.expense_service import expense_service

    # Default to current month if no dates provided
    if date_from is None:
        from datetime import date as dt_date
        today = dt_date.today()
        date_from = today.replace(day=1)
    if date_to is None:
        from datetime import date as dt_date
        date_to = dt_date.today()

    return await expense_service.get_profit_loss(
        db=db,
        date_from=date_from,
        date_to=date_to,
    )


# ─── NPS Analytics ─────────────────────────────────────────────────────────


def _parse_range_to_dates(range_param: str) -> tuple[date | None, date | None]:
    """Convert '7d', '30d', '90d' range strings to (start_date, end_date)."""
    import re
    from datetime import timedelta

    today = date.today()
    match = re.match(r"^(\d+)d$", range_param)
    if match:
        days = int(match.group(1))
        return today - timedelta(days=days), today
    return None, today


@router.get("/nps")
async def nps_dashboard(
    range: str = Query(default="30d", description="Date range: 7d, 30d, 90d"),
    current_user: AuthenticatedUser = Depends(require_permission("analytics:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """NPS dashboard with score, breakdown, and monthly trend."""
    from app.services.nps_survey_service import nps_survey_service

    start_date, end_date = _parse_range_to_dates(range)
    data = await nps_survey_service.get_nps_dashboard(
        db=db, start_date=start_date, end_date=end_date,
    )

    # Total surveys sent (including unanswered) for response rate
    total_sent = data.get("total_sent", 0)
    total_responses = data.get("total_responses", 0)
    response_rate = (total_responses / total_sent * 100) if total_sent > 0 else 0.0

    return {
        "nps_score": data.get("nps_score", 0),
        "total_responses": total_responses,
        "promoters_count": data.get("promoters", 0),
        "passives_count": data.get("passives", 0),
        "detractors_count": data.get("detractors", 0),
        "response_rate": round(response_rate, 1),
        "trend": data.get("trend", []),
    }


@router.get("/nps/by-doctor")
async def nps_by_doctor(
    range: str = Query(default="30d", description="Date range: 7d, 30d, 90d"),
    current_user: AuthenticatedUser = Depends(require_permission("analytics:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """NPS breakdown per doctor."""
    from app.services.nps_survey_service import nps_survey_service

    start_date, end_date = _parse_range_to_dates(range)
    data = await nps_survey_service.get_nps_by_doctor(
        db=db, start_date=start_date, end_date=end_date,
    )

    # Map field names to match frontend expectations
    items = []
    for row in data.get("items", []):
        items.append({
            "doctor_id": row.get("doctor_id", ""),
            "doctor_name": row.get("doctor_name", "Desconocido"),
            "nps_score": row.get("nps_score", 0),
            "total_responses": row.get("total", 0),
            "promoters": row.get("promoters", 0),
            "detractors": row.get("detractors", 0),
        })

    return {"items": items}
