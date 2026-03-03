"""GAP-14: Natural Language Analytics Reports service.

Security architecture:
    Claude does NOT generate SQL. It receives a catalogue of pre-defined query
    templates (key + description + parameter schema) and returns a structured
    JSON response selecting which template to execute and with which parameters.
    The server validates the query_key, validates parameter types, and executes
    a pre-validated SQLAlchemy ORM query. No raw SQL, no direct table access,
    no PHI in responses.

Flow:
    1. User asks a natural language question.
    2. System prompt lists all available templates.
    3. Claude selects a query_key + parameters + chart_type + explanation.
    4. Server validates and executes the ORM query.
    5. Results returned as aggregated data (never individual patient records).
"""

import logging
from collections.abc import Callable, Coroutine
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import case, cast, func, select, Date, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import DentalOSError
from app.core.error_codes import AIReportErrors
from app.models.tenant.appointment import Appointment
from app.models.tenant.invoice import Invoice, InvoiceItem
from app.models.tenant.patient import Patient
from app.models.tenant.payment import Payment
from app.models.tenant.procedure import Procedure
from app.models.tenant.treatment_plan import TreatmentPlan, TreatmentPlanItem
from app.models.tenant.user import User
from app.services.ai_claude_client import call_claude, extract_json_object

logger = logging.getLogger("dentalos.ai.report")


# ---------------------------------------------------------------------------
# Type alias for executor functions
# ---------------------------------------------------------------------------
ExecutorFunc = Callable[..., Coroutine[Any, Any, list[dict]]]


# ---------------------------------------------------------------------------
# Query template registry
# ---------------------------------------------------------------------------

class QueryTemplate:
    """Describes a pre-validated analytics query template."""

    __slots__ = ("key", "description", "params_schema", "executor", "default_chart")

    def __init__(
        self,
        *,
        key: str,
        description: str,
        params_schema: dict[str, str],
        executor: ExecutorFunc,
        default_chart: str,
    ) -> None:
        self.key = key
        self.description = description
        self.params_schema = params_schema
        self.executor = executor
        self.default_chart = default_chart


# ---------------------------------------------------------------------------
# Executor functions — each returns list[dict] with human-readable columns.
# Money values are converted from cents to display (divided by 100).
# Never exposes internal IDs or PHI.
# ---------------------------------------------------------------------------

def _parse_date(value: str | None, default: date | None = None) -> date | None:
    """Safely parse an ISO date string, returning a fallback on failure."""
    if not value:
        return default
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return default


def _default_date_from() -> date:
    """Default start date: first day of current month."""
    today = date.today()
    return today.replace(day=1)


def _default_date_to() -> date:
    """Default end date: today."""
    return date.today()


async def _execute_revenue_by_period(
    db: AsyncSession, **params: Any
) -> list[dict]:
    """Revenue breakdown by month or week for paid/sent/partial invoices."""
    date_from = _parse_date(params.get("date_from"), _default_date_from())
    date_to = _parse_date(params.get("date_to"), _default_date_to())
    group_by = params.get("group_by", "month")

    if group_by not in ("month", "week"):
        group_by = "month"

    trunc_expr = func.date_trunc(group_by, Invoice.created_at)

    stmt = (
        select(
            trunc_expr.label("periodo"),
            func.sum(Invoice.total).label("total_cents"),
            func.count(Invoice.id).label("cantidad_facturas"),
        )
        .where(
            Invoice.is_active.is_(True),
            Invoice.status.in_(["paid", "sent", "partial"]),
            cast(Invoice.created_at, Date) >= date_from,
            cast(Invoice.created_at, Date) <= date_to,
        )
        .group_by(trunc_expr)
        .order_by(trunc_expr)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "periodo": row.periodo.strftime("%Y-%m-%d") if row.periodo else "",
            "ingresos": round(row.total_cents / 100, 2) if row.total_cents else 0,
            "cantidad_facturas": row.cantidad_facturas or 0,
        }
        for row in rows
    ]


async def _execute_top_procedures(
    db: AsyncSession, **params: Any
) -> list[dict]:
    """Most performed procedures with counts."""
    date_from = _parse_date(params.get("date_from"), _default_date_from())
    date_to = _parse_date(params.get("date_to"), _default_date_to())
    limit = min(int(params.get("limit", 10)), 50)

    stmt = (
        select(
            Procedure.cups_code,
            Procedure.cups_description.label("procedimiento"),
            func.count(Procedure.id).label("cantidad"),
        )
        .where(
            Procedure.is_active.is_(True),
            cast(Procedure.created_at, Date) >= date_from,
            cast(Procedure.created_at, Date) <= date_to,
        )
        .group_by(Procedure.cups_code, Procedure.cups_description)
        .order_by(func.count(Procedure.id).desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "codigo_cups": row.cups_code,
            "procedimiento": row.procedimiento,
            "cantidad": row.cantidad or 0,
        }
        for row in rows
    ]


async def _execute_appointment_no_show_rate(
    db: AsyncSession, **params: Any
) -> list[dict]:
    """No-show rate for appointments, optionally filtered by doctor."""
    date_from = _parse_date(params.get("date_from"), _default_date_from())
    date_to = _parse_date(params.get("date_to"), _default_date_to())
    doctor_id = params.get("doctor_id")

    filters = [
        Appointment.is_active.is_(True),
        Appointment.status.in_(["completed", "no_show", "cancelled"]),
        cast(Appointment.start_time, Date) >= date_from,
        cast(Appointment.start_time, Date) <= date_to,
    ]
    if doctor_id:
        filters.append(Appointment.doctor_id == doctor_id)

    total_stmt = select(func.count(Appointment.id)).where(*filters)
    no_show_stmt = select(func.count(Appointment.id)).where(
        *filters,
        Appointment.status == "no_show",
    )

    total_result = await db.execute(total_stmt)
    no_show_result = await db.execute(no_show_stmt)

    total = total_result.scalar() or 0
    no_shows = no_show_result.scalar() or 0
    rate = round((no_shows / total * 100), 1) if total > 0 else 0.0

    return [
        {
            "total_citas": total,
            "inasistencias": no_shows,
            "tasa_inasistencia_porcentaje": rate,
        }
    ]


async def _execute_patient_retention_rate(
    db: AsyncSession, **params: Any
) -> list[dict]:
    """Patient retention: percentage of patients who had more than one visit."""
    date_from = _parse_date(params.get("date_from"), _default_date_from())
    date_to = _parse_date(params.get("date_to"), _default_date_to())

    # Subquery: patients with at least one completed appointment in range
    patients_with_visits = (
        select(
            Appointment.patient_id,
            func.count(Appointment.id).label("visit_count"),
        )
        .where(
            Appointment.is_active.is_(True),
            Appointment.status == "completed",
            cast(Appointment.start_time, Date) >= date_from,
            cast(Appointment.start_time, Date) <= date_to,
        )
        .group_by(Appointment.patient_id)
        .subquery()
    )

    total_stmt = select(func.count()).select_from(patients_with_visits)
    returning_stmt = select(func.count()).select_from(
        select(patients_with_visits.c.patient_id)
        .where(patients_with_visits.c.visit_count > 1)
        .subquery()
    )

    total_result = await db.execute(total_stmt)
    returning_result = await db.execute(returning_stmt)

    total_patients = total_result.scalar() or 0
    returning_patients = returning_result.scalar() or 0
    rate = round((returning_patients / total_patients * 100), 1) if total_patients > 0 else 0.0

    return [
        {
            "pacientes_con_visita": total_patients,
            "pacientes_recurrentes": returning_patients,
            "tasa_retencion_porcentaje": rate,
        }
    ]


async def _execute_revenue_by_doctor(
    db: AsyncSession, **params: Any
) -> list[dict]:
    """Revenue per doctor for paid/sent/partial invoices."""
    date_from = _parse_date(params.get("date_from"), _default_date_from())
    date_to = _parse_date(params.get("date_to"), _default_date_to())

    stmt = (
        select(
            User.name.label("doctor"),
            func.sum(Invoice.total).label("total_cents"),
            func.count(Invoice.id).label("cantidad_facturas"),
        )
        .join(User, User.id == Invoice.created_by)
        .where(
            Invoice.is_active.is_(True),
            Invoice.status.in_(["paid", "sent", "partial"]),
            cast(Invoice.created_at, Date) >= date_from,
            cast(Invoice.created_at, Date) <= date_to,
        )
        .group_by(User.name)
        .order_by(func.sum(Invoice.total).desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "doctor": row.doctor,
            "ingresos": round(row.total_cents / 100, 2) if row.total_cents else 0,
            "cantidad_facturas": row.cantidad_facturas or 0,
        }
        for row in rows
    ]


async def _execute_treatment_completion_rate(
    db: AsyncSession, **params: Any
) -> list[dict]:
    """Treatment plan completion rate in the given period."""
    date_from = _parse_date(params.get("date_from"), _default_date_from())
    date_to = _parse_date(params.get("date_to"), _default_date_to())

    filters = [
        TreatmentPlan.is_active.is_(True),
        TreatmentPlan.status.in_(["active", "completed"]),
        cast(TreatmentPlan.created_at, Date) >= date_from,
        cast(TreatmentPlan.created_at, Date) <= date_to,
    ]

    total_stmt = select(func.count(TreatmentPlan.id)).where(*filters)
    completed_stmt = select(func.count(TreatmentPlan.id)).where(
        *filters,
        TreatmentPlan.status == "completed",
    )

    total_result = await db.execute(total_stmt)
    completed_result = await db.execute(completed_stmt)

    total = total_result.scalar() or 0
    completed = completed_result.scalar() or 0
    rate = round((completed / total * 100), 1) if total > 0 else 0.0

    return [
        {
            "total_planes": total,
            "completados": completed,
            "tasa_completamiento_porcentaje": rate,
        }
    ]


async def _execute_unpaid_invoices_aging(
    db: AsyncSession, **params: Any
) -> list[dict]:
    """Aging report of unpaid invoices grouped into 0-30, 31-60, 61-90, 90+ days."""
    today = date.today()

    # Calculate days outstanding using created_at date
    days_outstanding = func.extract("epoch", func.now() - Invoice.created_at) / 86400

    aging_bucket = case(
        (days_outstanding <= 30, "0-30 dias"),
        (days_outstanding <= 60, "31-60 dias"),
        (days_outstanding <= 90, "61-90 dias"),
        else_="90+ dias",
    )

    stmt = (
        select(
            aging_bucket.label("rango"),
            func.count(Invoice.id).label("cantidad"),
            func.sum(Invoice.balance).label("saldo_cents"),
        )
        .where(
            Invoice.is_active.is_(True),
            Invoice.status.in_(["sent", "partial", "overdue"]),
            Invoice.balance > 0,
        )
        .group_by(aging_bucket)
        .order_by(aging_bucket)
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Ensure all buckets appear even if empty
    bucket_map: dict[str, dict] = {
        "0-30 dias": {"rango": "0-30 dias", "cantidad": 0, "saldo_pendiente": 0},
        "31-60 dias": {"rango": "31-60 dias", "cantidad": 0, "saldo_pendiente": 0},
        "61-90 dias": {"rango": "61-90 dias", "cantidad": 0, "saldo_pendiente": 0},
        "90+ dias": {"rango": "90+ dias", "cantidad": 0, "saldo_pendiente": 0},
    }

    for row in rows:
        key = row.rango
        if key in bucket_map:
            bucket_map[key]["cantidad"] = row.cantidad or 0
            bucket_map[key]["saldo_pendiente"] = (
                round(row.saldo_cents / 100, 2) if row.saldo_cents else 0
            )

    return list(bucket_map.values())


async def _execute_daily_appointment_count(
    db: AsyncSession, **params: Any
) -> list[dict]:
    """Appointments per day in the given date range."""
    date_from = _parse_date(params.get("date_from"), _default_date_from())
    date_to = _parse_date(params.get("date_to"), _default_date_to())

    day_expr = cast(Appointment.start_time, Date)

    stmt = (
        select(
            day_expr.label("fecha"),
            func.count(Appointment.id).label("total_citas"),
            func.sum(
                case((Appointment.status == "completed", 1), else_=0)
            ).label("completadas"),
            func.sum(
                case((Appointment.status == "no_show", 1), else_=0)
            ).label("inasistencias"),
            func.sum(
                case((Appointment.status == "cancelled", 1), else_=0)
            ).label("canceladas"),
        )
        .where(
            Appointment.is_active.is_(True),
            day_expr >= date_from,
            day_expr <= date_to,
        )
        .group_by(day_expr)
        .order_by(day_expr)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "fecha": row.fecha.isoformat() if row.fecha else "",
            "total_citas": row.total_citas or 0,
            "completadas": row.completadas or 0,
            "inasistencias": row.inasistencias or 0,
            "canceladas": row.canceladas or 0,
        }
        for row in rows
    ]


async def _execute_insurance_distribution(
    db: AsyncSession, **params: Any
) -> list[dict]:
    """Patient distribution by insurance provider."""
    provider_expr = func.coalesce(Patient.insurance_provider, "Sin aseguradora")

    stmt = (
        select(
            provider_expr.label("aseguradora"),
            func.count(Patient.id).label("cantidad"),
        )
        .where(Patient.is_active.is_(True))
        .group_by(provider_expr)
        .order_by(func.count(Patient.id).desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    total = sum(row.cantidad for row in rows) or 1

    return [
        {
            "aseguradora": row.aseguradora,
            "cantidad": row.cantidad or 0,
            "porcentaje": round((row.cantidad or 0) / total * 100, 1),
        }
        for row in rows
    ]


async def _execute_patients_by_age_group(
    db: AsyncSession, **params: Any
) -> list[dict]:
    """Patient demographics by age range (0-17, 18-30, 31-45, 46-60, 61+)."""
    today = date.today()

    # Calculate age in years from birthdate
    age_expr = func.extract("year", func.age(func.current_date(), Patient.birthdate))

    age_bucket = case(
        (age_expr < 18, "0-17"),
        (age_expr <= 30, "18-30"),
        (age_expr <= 45, "31-45"),
        (age_expr <= 60, "46-60"),
        else_="61+",
    )

    stmt = (
        select(
            age_bucket.label("grupo_edad"),
            func.count(Patient.id).label("cantidad"),
        )
        .where(
            Patient.is_active.is_(True),
            Patient.birthdate.is_not(None),
        )
        .group_by(age_bucket)
        .order_by(age_bucket)
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Ensure all buckets appear
    bucket_order = ["0-17", "18-30", "31-45", "46-60", "61+"]
    bucket_map: dict[str, int] = {b: 0 for b in bucket_order}

    for row in rows:
        if row.grupo_edad in bucket_map:
            bucket_map[row.grupo_edad] = row.cantidad or 0

    total = sum(bucket_map.values()) or 1

    return [
        {
            "grupo_edad": grupo,
            "cantidad": cantidad,
            "porcentaje": round(cantidad / total * 100, 1),
        }
        for grupo, cantidad in bucket_map.items()
    ]


# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------

QUERY_TEMPLATES: dict[str, QueryTemplate] = {}


def _register(template: QueryTemplate) -> None:
    """Register a query template in the global registry."""
    QUERY_TEMPLATES[template.key] = template


_register(QueryTemplate(
    key="revenue_by_period",
    description=(
        "Ingresos (facturacion) desglosados por mes o semana. "
        "Responde preguntas como: cuanto se facturo este mes, ingresos por semana, "
        "tendencia de facturacion, ventas del trimestre."
    ),
    params_schema={
        "date_from": "ISO date string (YYYY-MM-DD). Default: first day of current month.",
        "date_to": "ISO date string (YYYY-MM-DD). Default: today.",
        "group_by": "'month' or 'week'. Default: 'month'.",
    },
    executor=_execute_revenue_by_period,
    default_chart="bar",
))

_register(QueryTemplate(
    key="top_procedures",
    description=(
        "Procedimientos mas realizados con cantidad. "
        "Responde: cuales son los procedimientos mas comunes, "
        "que tratamientos se hacen mas, top 10 procedimientos."
    ),
    params_schema={
        "date_from": "ISO date string. Default: first day of current month.",
        "date_to": "ISO date string. Default: today.",
        "limit": "Integer 1-50. Default: 10.",
    },
    executor=_execute_top_procedures,
    default_chart="bar",
))

_register(QueryTemplate(
    key="appointment_no_show_rate",
    description=(
        "Tasa de inasistencia (no-show) de citas. Puede filtrar por doctor. "
        "Responde: cuantos pacientes no vinieron, tasa de ausencias, "
        "porcentaje de no-show, inasistencias del mes."
    ),
    params_schema={
        "date_from": "ISO date string. Default: first day of current month.",
        "date_to": "ISO date string. Default: today.",
        "doctor_id": "UUID string. Optional: filter by specific doctor.",
    },
    executor=_execute_appointment_no_show_rate,
    default_chart="number",
))

_register(QueryTemplate(
    key="patient_retention_rate",
    description=(
        "Tasa de retencion de pacientes — porcentaje que regresaron mas de una vez. "
        "Responde: cuantos pacientes vuelven, retencion de pacientes, "
        "fidelidad de pacientes, tasa de retorno."
    ),
    params_schema={
        "date_from": "ISO date string. Default: first day of current month.",
        "date_to": "ISO date string. Default: today.",
    },
    executor=_execute_patient_retention_rate,
    default_chart="number",
))

_register(QueryTemplate(
    key="revenue_by_doctor",
    description=(
        "Ingresos por doctor. "
        "Responde: cuanto factura cada doctor, quien genera mas ingresos, "
        "productividad por doctor, ranking de doctores por facturacion."
    ),
    params_schema={
        "date_from": "ISO date string. Default: first day of current month.",
        "date_to": "ISO date string. Default: today.",
    },
    executor=_execute_revenue_by_doctor,
    default_chart="pie",
))

_register(QueryTemplate(
    key="treatment_completion_rate",
    description=(
        "Tasa de completamiento de planes de tratamiento. "
        "Responde: cuantos planes se completaron, porcentaje de tratamientos finalizados, "
        "eficiencia de tratamientos."
    ),
    params_schema={
        "date_from": "ISO date string. Default: first day of current month.",
        "date_to": "ISO date string. Default: today.",
    },
    executor=_execute_treatment_completion_rate,
    default_chart="number",
))

_register(QueryTemplate(
    key="unpaid_invoices_aging",
    description=(
        "Reporte de antiguedad de facturas pendientes (cuentas por cobrar). "
        "Agrupa por rangos: 0-30, 31-60, 61-90, 90+ dias. "
        "Responde: cuanto nos deben, facturas pendientes, cartera, cuentas por cobrar, "
        "morosidad, deudas de pacientes."
    ),
    params_schema={},
    executor=_execute_unpaid_invoices_aging,
    default_chart="bar",
))

_register(QueryTemplate(
    key="daily_appointment_count",
    description=(
        "Cantidad de citas por dia en un rango de fechas. "
        "Responde: cuantas citas hay por dia, agenda diaria, "
        "tendencia de citas, ocupacion de la agenda."
    ),
    params_schema={
        "date_from": "ISO date string. Default: first day of current month.",
        "date_to": "ISO date string. Default: today.",
    },
    executor=_execute_daily_appointment_count,
    default_chart="line",
))

_register(QueryTemplate(
    key="insurance_distribution",
    description=(
        "Distribucion de pacientes por aseguradora/EPS. "
        "Responde: de que EPS vienen los pacientes, distribucion de seguros, "
        "cuantos pacientes tiene cada aseguradora."
    ),
    params_schema={},
    executor=_execute_insurance_distribution,
    default_chart="pie",
))

_register(QueryTemplate(
    key="patients_by_age_group",
    description=(
        "Demografia de pacientes por grupo de edad (0-17, 18-30, 31-45, 46-60, 61+). "
        "Responde: edades de pacientes, demografia, distribucion por edad, "
        "cuantos ninos, cuantos adultos mayores."
    ),
    params_schema={},
    executor=_execute_patients_by_age_group,
    default_chart="pie",
))


# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------

def _build_system_prompt() -> str:
    """Build the Claude system prompt listing all available query templates.

    The prompt instructs Claude to pick one template key and extract
    parameters from the user's question. All output must be JSON.
    """
    today_str = date.today().isoformat()
    first_of_month = date.today().replace(day=1).isoformat()

    template_descriptions: list[str] = []
    for t in QUERY_TEMPLATES.values():
        params_desc = ""
        if t.params_schema:
            params_lines = [f"    - {k}: {v}" for k, v in t.params_schema.items()]
            params_desc = "\n  Parametros:\n" + "\n".join(params_lines)
        else:
            params_desc = "\n  Parametros: ninguno"

        template_descriptions.append(
            f"- key: \"{t.key}\"\n"
            f"  Descripcion: {t.description}\n"
            f"  Chart sugerido: {t.default_chart}"
            f"{params_desc}"
        )

    templates_block = "\n\n".join(template_descriptions)

    return f"""Eres un asistente de analitica para una clinica dental en Colombia.
Tu trabajo es interpretar preguntas en lenguaje natural sobre la clinica y
seleccionar la consulta predefinida mas apropiada.

Fecha de hoy: {today_str}
Primer dia del mes actual: {first_of_month}

CONSULTAS DISPONIBLES:

{templates_block}

INSTRUCCIONES:
1. Analiza la pregunta del usuario.
2. Selecciona la consulta (query_key) mas apropiada.
3. Extrae los parametros necesarios de la pregunta.
4. Si el usuario no especifica fechas, usa el mes actual ({first_of_month} a {today_str}).
5. Si la pregunta no corresponde a ninguna consulta, usa query_key "unknown".

RESPONDE SIEMPRE con un unico JSON valido con esta estructura exacta:
{{
  "query_key": "nombre_de_la_consulta",
  "parameters": {{}},
  "chart_type": "bar|line|pie|table|number",
  "explanation": "Explicacion breve en espanol de lo que se va a consultar."
}}

REGLAS:
- Solo responde con JSON, sin texto adicional.
- Solo usa query_keys del catalogo listado arriba.
- Los parametros deben ser del tipo correcto (strings de fecha ISO, enteros, UUIDs).
- chart_type puede ser: bar, line, pie, table, number.
- explanation debe ser en espanol y amigable para el usuario.
- Si no puedes responder la pregunta con las consultas disponibles, usa query_key "unknown"
  y en explanation lista los tipos de consulta disponibles."""


# ---------------------------------------------------------------------------
# Main service entry point
# ---------------------------------------------------------------------------

_VALID_CHART_TYPES = {"bar", "line", "pie", "table", "number"}

_AVAILABLE_QUERIES_MESSAGE = (
    "No encontre una consulta predefinida para esa pregunta. "
    "Puedo ayudarte con: ingresos por periodo, procedimientos mas realizados, "
    "tasa de inasistencia, retencion de pacientes, ingresos por doctor, "
    "completamiento de tratamientos, facturas pendientes (antiguedad), "
    "citas diarias, distribucion por aseguradora, y demografia por edad."
)


async def process_ai_query(
    db: AsyncSession,
    question: str,
) -> dict[str, Any]:
    """Process a natural language analytics question.

    Args:
        db: Tenant-scoped async database session.
        question: User's natural language question (3-500 chars).

    Returns:
        dict with keys: answer, data, chart_type, query_key
    """
    # 1. Build prompt and call Claude
    system_prompt = _build_system_prompt()

    try:
        llm_response = await call_claude(
            system_prompt=system_prompt,
            user_content=question,
            max_tokens=settings.ai_report_max_tokens,
            temperature=0.1,
        )
    except Exception as exc:
        logger.error("Claude API call failed for AI report: %s", str(exc))
        raise DentalOSError(
            error=AIReportErrors.GENERATION_FAILED,
            message="No se pudo procesar la pregunta. Intente nuevamente.",
            status_code=502,
        ) from exc

    # 2. Parse Claude's JSON response
    content = llm_response.get("content", "")
    parsed = extract_json_object(content)

    if not parsed:
        logger.warning("Failed to parse Claude response for AI report query")
        raise DentalOSError(
            error=AIReportErrors.GENERATION_FAILED,
            message="No se pudo interpretar la respuesta. Intente reformular la pregunta.",
            status_code=422,
        )

    query_key = parsed.get("query_key", "unknown")
    parameters = parsed.get("parameters", {})
    chart_type = parsed.get("chart_type", "table")
    explanation = parsed.get("explanation", "")

    # Validate chart_type
    if chart_type not in _VALID_CHART_TYPES:
        chart_type = "table"

    # 3. Handle unknown query type
    if query_key == "unknown" or query_key not in QUERY_TEMPLATES:
        logger.info("AI report: unknown query_key=%s for question (len=%d)", query_key, len(question))
        return {
            "answer": explanation or _AVAILABLE_QUERIES_MESSAGE,
            "data": [],
            "chart_type": "table",
            "query_key": "unknown",
        }

    # 4. Execute the pre-validated query
    template = QUERY_TEMPLATES[query_key]

    # Override chart_type with Claude's suggestion if valid, else use template default
    if chart_type not in _VALID_CHART_TYPES:
        chart_type = template.default_chart

    try:
        if not isinstance(parameters, dict):
            parameters = {}
        data = await template.executor(db, **parameters)
    except Exception as exc:
        logger.error(
            "Query execution failed: key=%s error=%s",
            query_key,
            str(exc),
        )
        raise DentalOSError(
            error=AIReportErrors.QUERY_FAILED,
            message="Error al ejecutar la consulta. Intente nuevamente.",
            status_code=500,
        ) from exc

    # 5. Build answer
    answer = explanation or f"Resultados de {query_key}."

    logger.info(
        "AI report executed: query_key=%s rows=%d input_tokens=%d output_tokens=%d",
        query_key,
        len(data),
        llm_response.get("input_tokens", 0),
        llm_response.get("output_tokens", 0),
    )

    return {
        "answer": answer,
        "data": data,
        "chart_type": chart_type,
        "query_key": query_key,
    }
