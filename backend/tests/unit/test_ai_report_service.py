"""Unit tests for the AI Report service (process_ai_query) and supporting helpers.

Tests cover:
  - process_ai_query: valid question returns data, unknown query key returns
    friendly message, Claude API failure raises GENERATION_FAILED
  - QUERY_TEMPLATES registry: all 10 expected keys are present
  - _execute_revenue_by_period: executor called directly with mock db returns list
"""

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import AIReportErrors
from app.core.exceptions import DentalOSError
from app.services.ai_report_service import (
    QUERY_TEMPLATES,
    _execute_revenue_by_period,
    process_ai_query,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_revenue_row(**overrides) -> MagicMock:
    """Build a mock row for _execute_revenue_by_period results."""
    row = MagicMock()
    row.periodo = overrides.get("periodo", datetime(2026, 3, 1, tzinfo=UTC))
    row.total_cents = overrides.get("total_cents", 50000000)
    row.cantidad_facturas = overrides.get("cantidad_facturas", 10)
    return row


def _make_claude_response(query_key: str, **params) -> dict:
    """Build a fake Claude response dict selecting the given query_key."""
    import json

    content = json.dumps(
        {
            "query_key": query_key,
            "parameters": params,
            "chart_type": "bar",
            "explanation": f"Consultando {query_key}.",
        }
    )
    return {
        "content": content,
        "input_tokens": 300,
        "output_tokens": 80,
    }


# ── TestProcessAIQuery ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestProcessAIQuery:
    """Tests for the process_ai_query() module-level function."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session

    async def test_valid_question_returns_data(self, db):
        """A recognized query_key must execute the template and return data rows."""
        revenue_row = _make_revenue_row()

        execute_result = MagicMock()
        execute_result.all.return_value = [revenue_row]
        db.execute = AsyncMock(return_value=execute_result)

        claude_response = _make_claude_response(
            "revenue_by_period",
            date_from="2026-03-01",
            date_to="2026-03-31",
        )

        with patch(
            "app.services.ai_report_service.call_claude",
            new_callable=AsyncMock,
            return_value=claude_response,
        ):
            with patch(
                "app.services.ai_report_service.extract_json_object",
                return_value={
                    "query_key": "revenue_by_period",
                    "parameters": {"date_from": "2026-03-01", "date_to": "2026-03-31"},
                    "chart_type": "bar",
                    "explanation": "Ingresos del mes de marzo.",
                },
            ):
                result = await process_ai_query(
                    db=db,
                    question="¿Cuánto se facturó en marzo de 2026?",
                )

        assert result["query_key"] == "revenue_by_period"
        assert isinstance(result["data"], list)
        assert result["chart_type"] in {"bar", "line", "pie", "table", "number"}
        assert "answer" in result

    async def test_unknown_query_key(self, db):
        """When Claude returns an unrecognized key, a friendly message listing queries is returned."""
        with patch(
            "app.services.ai_report_service.call_claude",
            new_callable=AsyncMock,
            return_value={
                "content": '{"query_key": "unknown", "parameters": {}, "chart_type": "table", "explanation": "No encontre una consulta."}',
                "input_tokens": 200,
                "output_tokens": 50,
            },
        ):
            with patch(
                "app.services.ai_report_service.extract_json_object",
                return_value={
                    "query_key": "unknown",
                    "parameters": {},
                    "chart_type": "table",
                    "explanation": "No encontre una consulta.",
                },
            ):
                result = await process_ai_query(
                    db=db,
                    question="¿Cómo está el clima hoy?",
                )

        assert result["query_key"] == "unknown"
        assert result["data"] == []
        # The answer must mention at least some available queries
        assert "ingresos" in result["answer"].lower() or "No encontre" in result["answer"]

    async def test_unregistered_key_returns_fallback(self, db):
        """A query_key not in QUERY_TEMPLATES registry returns the fallback message."""
        with patch(
            "app.services.ai_report_service.call_claude",
            new_callable=AsyncMock,
            return_value={
                "content": '{}',
                "input_tokens": 100,
                "output_tokens": 20,
            },
        ):
            with patch(
                "app.services.ai_report_service.extract_json_object",
                return_value={
                    "query_key": "nonexistent_template_xyz",
                    "parameters": {},
                    "chart_type": "table",
                    "explanation": "No hay consulta disponible.",
                },
            ):
                result = await process_ai_query(
                    db=db,
                    question="Dame el reporte de ventas por galaxia",
                )

        assert result["query_key"] == "unknown"
        assert result["data"] == []

    async def test_claude_call_failure(self, db):
        """When the Claude API raises an exception, GENERATION_FAILED (502) is raised."""
        with patch(
            "app.services.ai_report_service.call_claude",
            new_callable=AsyncMock,
            side_effect=Exception("API timeout"),
        ):
            with pytest.raises(DentalOSError) as exc_info:
                await process_ai_query(
                    db=db,
                    question="¿Cuántos pacientes atendimos?",
                )

        assert exc_info.value.error == AIReportErrors.GENERATION_FAILED
        assert exc_info.value.status_code == 502

    async def test_claude_invalid_json_raises(self, db):
        """When Claude response cannot be parsed as JSON, GENERATION_FAILED (422) is raised."""
        with patch(
            "app.services.ai_report_service.call_claude",
            new_callable=AsyncMock,
            return_value={
                "content": "Este no es JSON válido...",
                "input_tokens": 100,
                "output_tokens": 10,
            },
        ):
            with patch(
                "app.services.ai_report_service.extract_json_object",
                return_value=None,
            ):
                with pytest.raises(DentalOSError) as exc_info:
                    await process_ai_query(
                        db=db,
                        question="¿Ingresos del mes?",
                    )

        assert exc_info.value.error == AIReportErrors.GENERATION_FAILED
        assert exc_info.value.status_code == 422


# ── TestAllTemplatesRegistered ────────────────────────────────────────────────


@pytest.mark.unit
class TestAllTemplatesRegistered:
    """Verify the QUERY_TEMPLATES registry contains all expected keys."""

    def test_all_templates_registered(self):
        """All 10 query template keys must be present in the registry."""
        expected_keys = {
            "revenue_by_period",
            "top_procedures",
            "appointment_no_show_rate",
            "patient_retention_rate",
            "revenue_by_doctor",
            "treatment_completion_rate",
            "unpaid_invoices_aging",
            "daily_appointment_count",
            "insurance_distribution",
            "patients_by_age_group",
        }

        registered_keys = set(QUERY_TEMPLATES.keys())
        missing = expected_keys - registered_keys
        assert missing == set(), f"Missing query template keys: {missing}"

    def test_each_template_has_executor(self):
        """Every registered template must have a callable executor."""
        for key, template in QUERY_TEMPLATES.items():
            assert callable(template.executor), (
                f"Template '{key}' executor is not callable"
            )

    def test_each_template_has_valid_chart_type(self):
        """Every registered template must declare a valid default_chart."""
        valid_charts = {"bar", "line", "pie", "table", "number"}
        for key, template in QUERY_TEMPLATES.items():
            assert template.default_chart in valid_charts, (
                f"Template '{key}' has invalid default_chart: {template.default_chart}"
            )

    def test_registry_size_is_ten(self):
        """Registry must contain exactly 10 templates."""
        assert len(QUERY_TEMPLATES) == 10


# ── TestRevenueByPeriodExecutor ───────────────────────────────────────────────


@pytest.mark.unit
class TestRevenueByPeriodExecutor:
    """Direct tests for the _execute_revenue_by_period executor function."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session

    async def test_revenue_by_period_returns_list(self, db):
        """Executor must return a list of dicts with expected keys."""
        row = _make_revenue_row(
            periodo=datetime(2026, 3, 1, tzinfo=UTC),
            total_cents=10000000,
            cantidad_facturas=5,
        )

        result = MagicMock()
        result.all.return_value = [row]
        db.execute = AsyncMock(return_value=result)

        data = await _execute_revenue_by_period(
            db,
            date_from="2026-03-01",
            date_to="2026-03-31",
            group_by="month",
        )

        assert isinstance(data, list)
        assert len(data) == 1
        assert "periodo" in data[0]
        assert "ingresos" in data[0]
        assert "cantidad_facturas" in data[0]

    async def test_revenue_converts_cents_to_display(self, db):
        """Cent values must be divided by 100 for display."""
        row = _make_revenue_row(total_cents=5000000, cantidad_facturas=3)

        result = MagicMock()
        result.all.return_value = [row]
        db.execute = AsyncMock(return_value=result)

        data = await _execute_revenue_by_period(
            db,
            date_from="2026-03-01",
            date_to="2026-03-31",
        )

        # 5_000_000 cents / 100 = 50_000.0 display value
        assert data[0]["ingresos"] == round(5000000 / 100, 2)

    async def test_revenue_empty_result(self, db):
        """Empty DB result returns an empty list without crashing."""
        result = MagicMock()
        result.all.return_value = []
        db.execute = AsyncMock(return_value=result)

        data = await _execute_revenue_by_period(
            db,
            date_from="2026-03-01",
            date_to="2026-03-31",
        )

        assert data == []

    async def test_revenue_invalid_group_by_defaults_to_month(self, db):
        """An invalid group_by value must fall back to 'month' without raising."""
        row = _make_revenue_row()
        result = MagicMock()
        result.all.return_value = [row]
        db.execute = AsyncMock(return_value=result)

        # Should not raise even with an invalid group_by
        data = await _execute_revenue_by_period(
            db,
            date_from="2026-03-01",
            date_to="2026-03-31",
            group_by="invalid_value",
        )

        assert isinstance(data, list)

    async def test_revenue_week_grouping_accepted(self, db):
        """group_by='week' is a valid value and must be accepted."""
        row = _make_revenue_row()
        result = MagicMock()
        result.all.return_value = [row]
        db.execute = AsyncMock(return_value=result)

        data = await _execute_revenue_by_period(
            db,
            date_from="2026-03-01",
            date_to="2026-03-31",
            group_by="week",
        )

        assert isinstance(data, list)
