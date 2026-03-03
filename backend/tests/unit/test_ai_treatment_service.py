"""Unit tests for the AITreatmentService class.

Tests cover:
  - generate_suggestions: add-on gate, no conditions, happy path with Claude mock,
    invalid CUPS code dropped from suggestions, token usage stored
  - review_suggestion: accept items, reject all, already reviewed raises 409
  - create_plan_from_suggestions: accepted items delegated to treatment_plan_service,
    non-reviewed status raises error
  - get_usage_stats: aggregated tokens returned
"""

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import AITreatmentErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.services.ai_treatment_service import AITreatmentService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_patient_row(**overrides) -> MagicMock:
    """Build a mock patient query result row."""
    row = MagicMock()
    row.id = overrides.get("id", uuid.uuid4())
    row.birthdate = overrides.get("birthdate", date(1990, 5, 15))
    row.blood_type = overrides.get("blood_type", "O+")
    row.allergies = overrides.get("allergies", None)
    row.chronic_conditions = overrides.get("chronic_conditions", None)
    return row


def _make_condition_row(**overrides) -> MagicMock:
    """Build a mock OdontogramCondition query result row."""
    row = MagicMock()
    row.tooth_number = overrides.get("tooth_number", "16")
    row.zone = overrides.get("zone", "occlusal")
    row.condition_code = overrides.get("condition_code", "caries")
    row.severity = overrides.get("severity", "moderate")
    row.notes = overrides.get("notes", None)
    return row


def _make_catalog_row(**overrides) -> MagicMock:
    """Build a mock ServiceCatalog query result row."""
    row = MagicMock()
    row.cups_code = overrides.get("cups_code", "890301")
    row.name = overrides.get("name", "Obturación simple")
    row.default_price = overrides.get("default_price", 8000000)
    row.category = overrides.get("category", "restaurativa")
    return row


def _make_suggestion(**overrides) -> MagicMock:
    """Build a mock AITreatmentSuggestion ORM row."""
    row = MagicMock()
    row.id = overrides.get("id", uuid.uuid4())
    row.patient_id = overrides.get("patient_id", uuid.uuid4())
    row.doctor_id = overrides.get("doctor_id", uuid.uuid4())
    row.suggestions = overrides.get(
        "suggestions",
        [
            {
                "cups_code": "890301",
                "cups_description": "Obturación simple",
                "tooth_number": "16",
                "rationale": "Caries detectada",
                "confidence": "high",
                "priority_order": 1,
                "estimated_cost": 8000000,
                "action": None,
            }
        ],
    )
    row.model_used = overrides.get("model_used", "claude-3-sonnet")
    row.status = overrides.get("status", "pending_review")
    row.input_tokens = overrides.get("input_tokens", 500)
    row.output_tokens = overrides.get("output_tokens", 150)
    row.reviewed_at = overrides.get("reviewed_at", None)
    row.treatment_plan_id = overrides.get("treatment_plan_id", None)
    row.created_at = overrides.get("created_at", datetime.now(UTC))
    return row


# ── TestGenerateSuggestions ───────────────────────────────────────────────────


@pytest.mark.unit
class TestGenerateSuggestions:
    """Tests for AITreatmentService.generate_suggestions."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        return session

    async def test_addon_not_active(self, db):
        """When ai_treatment_advisor feature is missing, ADDON_REQUIRED (402) is raised."""
        service = AITreatmentService()
        with pytest.raises(DentalOSError) as exc_info:
            await service.generate_suggestions(
                db=db,
                patient_id=str(uuid.uuid4()),
                doctor_id=str(uuid.uuid4()),
                tenant_features={},
            )

        assert exc_info.value.error == AITreatmentErrors.ADDON_REQUIRED
        assert exc_info.value.status_code == 402

    async def test_addon_false_raises(self, db):
        """Explicitly False add-on flag also raises ADDON_REQUIRED."""
        service = AITreatmentService()
        with pytest.raises(DentalOSError) as exc_info:
            await service.generate_suggestions(
                db=db,
                patient_id=str(uuid.uuid4()),
                doctor_id=str(uuid.uuid4()),
                tenant_features={"ai_treatment_advisor": False},
            )

        assert exc_info.value.error == AITreatmentErrors.ADDON_REQUIRED

    async def test_no_active_conditions(self, db):
        """When no odontogram conditions exist, NO_ACTIVE_CONDITIONS (422) is raised."""
        patient_id = uuid.uuid4()

        patient_row = _make_patient_row(id=patient_id)
        patient_result = MagicMock()
        patient_result.one_or_none.return_value = patient_row

        empty_conditions_result = MagicMock()
        empty_conditions_result.all.return_value = []

        db.execute = AsyncMock(
            side_effect=[patient_result, empty_conditions_result]
        )

        service = AITreatmentService()
        with pytest.raises(DentalOSError) as exc_info:
            await service.generate_suggestions(
                db=db,
                patient_id=str(patient_id),
                doctor_id=str(uuid.uuid4()),
                tenant_features={"ai_treatment_advisor": True},
            )

        assert exc_info.value.error == AITreatmentErrors.NO_ACTIVE_CONDITIONS
        assert exc_info.value.status_code == 422

    async def test_generate_success(self, db):
        """Happy path: patient + conditions + catalog + Claude mock yields suggestions."""
        patient_id = uuid.uuid4()
        doctor_id = uuid.uuid4()

        patient_row = _make_patient_row(id=patient_id)
        patient_result = MagicMock()
        patient_result.one_or_none.return_value = patient_row

        condition_row = _make_condition_row(cups_code="890301")
        conditions_result = MagicMock()
        conditions_result.all.return_value = [condition_row]

        catalog_row = _make_catalog_row(cups_code="890301")
        catalog_result = MagicMock()
        catalog_result.all.return_value = [catalog_row]

        suggestion_orm = _make_suggestion(
            patient_id=patient_id, doctor_id=doctor_id
        )

        db.execute = AsyncMock(
            side_effect=[patient_result, conditions_result, catalog_result]
        )

        claude_response = {
            "content": '[{"cups_code": "890301", "cups_description": "Obturacion", "tooth_number": "16", "rationale": "Caries", "confidence": "high", "priority_order": 1, "estimated_cost": 8000000}]',
            "input_tokens": 500,
            "output_tokens": 150,
        }

        with patch(
            "app.services.ai_treatment_service.call_claude",
            new_callable=AsyncMock,
            return_value=claude_response,
        ):
            with patch(
                "app.services.ai_treatment_service.extract_json_array",
                return_value=[
                    {
                        "cups_code": "890301",
                        "cups_description": "Obturacion",
                        "tooth_number": "16",
                        "rationale": "Caries",
                        "confidence": "high",
                        "priority_order": 1,
                        "estimated_cost": 8000000,
                    }
                ],
            ):
                with patch(
                    "app.services.ai_treatment_service.AITreatmentSuggestion",
                    return_value=suggestion_orm,
                ):
                    service = AITreatmentService()
                    result = await service.generate_suggestions(
                        db=db,
                        patient_id=str(patient_id),
                        doctor_id=str(doctor_id),
                        tenant_features={"ai_treatment_advisor": True},
                    )

        assert "suggestions" in result
        db.add.assert_called_once()
        db.flush.assert_called()

    async def test_catalog_validation_drops_invalid_cups(self, db):
        """Claude suggestions with unknown CUPS codes must be silently dropped."""
        patient_id = uuid.uuid4()
        doctor_id = uuid.uuid4()

        patient_row = _make_patient_row(id=patient_id)
        patient_result = MagicMock()
        patient_result.one_or_none.return_value = patient_row

        condition_row = _make_condition_row()
        conditions_result = MagicMock()
        conditions_result.all.return_value = [condition_row]

        # Catalog only has 890301
        catalog_row = _make_catalog_row(cups_code="890301")
        catalog_result = MagicMock()
        catalog_result.all.return_value = [catalog_row]

        db.execute = AsyncMock(
            side_effect=[patient_result, conditions_result, catalog_result]
        )

        # Claude returns one valid and one invalid CUPS code
        raw_suggestions = [
            {
                "cups_code": "890301",
                "cups_description": "Obturacion",
                "tooth_number": None,
                "rationale": "Valido",
                "confidence": "high",
                "priority_order": 1,
                "estimated_cost": 8000000,
            },
            {
                "cups_code": "INVALID_CODE",
                "cups_description": "Inexistente",
                "tooth_number": None,
                "rationale": "Invalido",
                "confidence": "low",
                "priority_order": 2,
                "estimated_cost": 1000,
            },
        ]

        suggestion_orm = _make_suggestion(patient_id=patient_id, doctor_id=doctor_id)

        with patch(
            "app.services.ai_treatment_service.call_claude",
            new_callable=AsyncMock,
            return_value={"content": "[]", "input_tokens": 400, "output_tokens": 100},
        ):
            with patch(
                "app.services.ai_treatment_service.extract_json_array",
                return_value=raw_suggestions,
            ):
                with patch(
                    "app.services.ai_treatment_service.AITreatmentSuggestion",
                    return_value=suggestion_orm,
                ):
                    service = AITreatmentService()
                    result = await service.generate_suggestions(
                        db=db,
                        patient_id=str(patient_id),
                        doctor_id=str(doctor_id),
                        tenant_features={"ai_treatment_advisor": True},
                    )

        # The stored suggestions list must not contain the invalid CUPS code
        stored_suggestions = suggestion_orm.suggestions
        cups_codes_stored = [s["cups_code"] for s in stored_suggestions]
        assert "INVALID_CODE" not in cups_codes_stored

    async def test_stores_token_usage(self, db):
        """Input and output token counts from Claude must be persisted on the row."""
        patient_id = uuid.uuid4()
        doctor_id = uuid.uuid4()

        patient_row = _make_patient_row(id=patient_id)
        patient_result = MagicMock()
        patient_result.one_or_none.return_value = patient_row

        condition_row = _make_condition_row()
        conditions_result = MagicMock()
        conditions_result.all.return_value = [condition_row]

        catalog_row = _make_catalog_row(cups_code="890301")
        catalog_result = MagicMock()
        catalog_result.all.return_value = [catalog_row]

        db.execute = AsyncMock(
            side_effect=[patient_result, conditions_result, catalog_result]
        )

        expected_input = 712
        expected_output = 234

        suggestion_orm = _make_suggestion(
            patient_id=patient_id,
            doctor_id=doctor_id,
            input_tokens=expected_input,
            output_tokens=expected_output,
        )

        with patch(
            "app.services.ai_treatment_service.call_claude",
            new_callable=AsyncMock,
            return_value={
                "content": "[]",
                "input_tokens": expected_input,
                "output_tokens": expected_output,
            },
        ):
            with patch(
                "app.services.ai_treatment_service.extract_json_array",
                return_value=[
                    {
                        "cups_code": "890301",
                        "cups_description": "Obturacion",
                        "tooth_number": None,
                        "rationale": "Test",
                        "confidence": "high",
                        "priority_order": 1,
                        "estimated_cost": 8000000,
                    }
                ],
            ):
                with patch(
                    "app.services.ai_treatment_service.AITreatmentSuggestion",
                    return_value=suggestion_orm,
                ) as MockSuggestion:
                    service = AITreatmentService()
                    await service.generate_suggestions(
                        db=db,
                        patient_id=str(patient_id),
                        doctor_id=str(doctor_id),
                        tenant_features={"ai_treatment_advisor": True},
                    )
                    # Verify the constructor received token counts
                    call_kwargs = MockSuggestion.call_args.kwargs
                    assert call_kwargs["input_tokens"] == expected_input
                    assert call_kwargs["output_tokens"] == expected_output


# ── TestReviewSuggestion ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestReviewSuggestion:
    """Tests for AITreatmentService.review_suggestion."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        return session

    async def test_review_accept_items(self, db):
        """Accepted items must have action='accept' and status becomes 'reviewed'."""
        suggestion_id = uuid.uuid4()
        row = _make_suggestion(
            id=suggestion_id,
            status="pending_review",
            suggestions=[
                {
                    "cups_code": "890301",
                    "cups_description": "Obturacion",
                    "tooth_number": "16",
                    "rationale": "Caries",
                    "confidence": "high",
                    "priority_order": 1,
                    "estimated_cost": 8000000,
                    "action": None,
                }
            ],
        )

        result = MagicMock()
        result.scalar_one_or_none.return_value = row
        db.execute = AsyncMock(return_value=result)

        service = AITreatmentService()
        await service.review_suggestion(
            db=db,
            suggestion_id=str(suggestion_id),
            review_items=[{"cups_code": "890301", "action": "accept"}],
        )

        assert row.status == "reviewed"
        assert row.suggestions[0]["action"] == "accept"
        db.flush.assert_called()

    async def test_review_reject_all(self, db):
        """When all items are rejected the status must become 'rejected'."""
        suggestion_id = uuid.uuid4()
        row = _make_suggestion(
            id=suggestion_id,
            status="pending_review",
            suggestions=[
                {
                    "cups_code": "890301",
                    "action": None,
                    "cups_description": "X",
                    "tooth_number": None,
                    "rationale": "R",
                    "confidence": "low",
                    "priority_order": 1,
                    "estimated_cost": 1000,
                },
                {
                    "cups_code": "890401",
                    "action": None,
                    "cups_description": "Y",
                    "tooth_number": None,
                    "rationale": "R",
                    "confidence": "low",
                    "priority_order": 2,
                    "estimated_cost": 2000,
                },
            ],
        )

        result = MagicMock()
        result.scalar_one_or_none.return_value = row
        db.execute = AsyncMock(return_value=result)

        service = AITreatmentService()
        await service.review_suggestion(
            db=db,
            suggestion_id=str(suggestion_id),
            review_items=[
                {"cups_code": "890301", "action": "reject"},
                {"cups_code": "890401", "action": "reject"},
            ],
        )

        assert row.status == "rejected"

    async def test_already_reviewed(self, db):
        """A suggestion not in pending_review status must raise ALREADY_REVIEWED (409)."""
        suggestion_id = uuid.uuid4()
        row = _make_suggestion(id=suggestion_id, status="reviewed")

        result = MagicMock()
        result.scalar_one_or_none.return_value = row
        db.execute = AsyncMock(return_value=result)

        service = AITreatmentService()
        with pytest.raises(DentalOSError) as exc_info:
            await service.review_suggestion(
                db=db,
                suggestion_id=str(suggestion_id),
                review_items=[{"cups_code": "890301", "action": "accept"}],
            )

        assert exc_info.value.error == AITreatmentErrors.ALREADY_REVIEWED
        assert exc_info.value.status_code == 409


# ── TestCreatePlanFromSuggestions ─────────────────────────────────────────────


@pytest.mark.unit
class TestCreatePlanFromSuggestions:
    """Tests for AITreatmentService.create_plan_from_suggestions."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        return session

    async def test_creates_plan_from_accepted(self, db):
        """Accepted suggestion items are passed to treatment_plan_service.create_plan."""
        suggestion_id = uuid.uuid4()
        patient_id = uuid.uuid4()
        doctor_id = uuid.uuid4()
        plan_id = uuid.uuid4()

        row = _make_suggestion(
            id=suggestion_id,
            status="reviewed",
            suggestions=[
                {
                    "cups_code": "890301",
                    "cups_description": "Obturacion",
                    "tooth_number": "16",
                    "rationale": "Caries moderada",
                    "confidence": "high",
                    "priority_order": 1,
                    "estimated_cost": 8000000,
                    "action": "accept",
                },
                {
                    "cups_code": "890401",
                    "cups_description": "Extraccion",
                    "tooth_number": "18",
                    "rationale": "No recuperable",
                    "confidence": "high",
                    "priority_order": 2,
                    "estimated_cost": 12000000,
                    "action": "reject",
                },
            ],
        )

        result = MagicMock()
        result.scalar_one_or_none.return_value = row
        db.execute = AsyncMock(return_value=result)

        plan_result = {"id": str(plan_id), "name": "Plan IA", "status": "draft"}

        with patch(
            "app.services.ai_treatment_service.treatment_plan_service"
        ) as mock_tps:
            mock_tps.create_plan = AsyncMock(return_value=plan_result)

            service = AITreatmentService()
            result_dict = await service.create_plan_from_suggestions(
                db=db,
                suggestion_id=str(suggestion_id),
                patient_id=str(patient_id),
                doctor_id=str(doctor_id),
            )

        mock_tps.create_plan.assert_called_once()
        call_kwargs = mock_tps.create_plan.call_args.kwargs
        # Only the accepted item should be passed
        assert len(call_kwargs["items"]) == 1
        assert call_kwargs["items"][0]["cups_code"] == "890301"
        assert result_dict["items_created"] == 1
        assert result_dict["status"] == "applied"

    async def test_requires_reviewed_status(self, db):
        """Suggestion not in 'reviewed' status must raise ALREADY_REVIEWED (409)."""
        suggestion_id = uuid.uuid4()
        row = _make_suggestion(id=suggestion_id, status="pending_review")

        result = MagicMock()
        result.scalar_one_or_none.return_value = row
        db.execute = AsyncMock(return_value=result)

        service = AITreatmentService()
        with pytest.raises(DentalOSError) as exc_info:
            await service.create_plan_from_suggestions(
                db=db,
                suggestion_id=str(suggestion_id),
                patient_id=str(uuid.uuid4()),
                doctor_id=str(uuid.uuid4()),
            )

        assert exc_info.value.error == AITreatmentErrors.ALREADY_REVIEWED
        assert exc_info.value.status_code == 409


# ── TestGetUsageStats ─────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetUsageStats:
    """Tests for AITreatmentService.get_usage_stats."""

    @pytest.fixture
    def db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session

    async def test_aggregates_tokens(self, db):
        """Aggregated totals for calls, input tokens, and output tokens are returned."""
        doctor_id = uuid.uuid4()

        stats_row = MagicMock()
        stats_row.total_calls = 10
        stats_row.total_input_tokens = 7500
        stats_row.total_output_tokens = 2100

        stats_result = MagicMock()
        stats_result.one.return_value = stats_row
        db.execute = AsyncMock(return_value=stats_result)

        service = AITreatmentService()
        result = await service.get_usage_stats(
            db=db,
            doctor_id=str(doctor_id),
            date_from="2026-03-01T00:00:00",
            date_to="2026-03-03T23:59:59",
        )

        assert result["total_calls"] == 10
        assert result["total_input_tokens"] == 7500
        assert result["total_output_tokens"] == 2100
        assert "period_from" in result
        assert "period_to" in result
