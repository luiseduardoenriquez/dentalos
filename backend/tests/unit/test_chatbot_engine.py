"""Unit tests for ChatbotEngine (VP-16 / Sprint 29-30).

Tests cover:
  - classify_intent: schedule, faq, emergency, malformed response, API failure
  - generate_response: hours, location, scheduling state machine (3 states)
  - _build_faq_response: match, no match
  - should_escalate: low confidence, emergency intent, keyword detection
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.chatbot_engine import ChatbotEngine


# ── TestClassifyIntent ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestClassifyIntent:
    """Tests for ChatbotEngine.classify_intent."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.engine = ChatbotEngine()

    async def test_classify_intent_schedule(self):
        """Message about booking an appointment → schedule intent with high confidence."""
        call_claude_response = {
            "content": '{"intent": "schedule", "confidence": 0.95, "entities": {"date": null, "time": null, "doctor": null, "procedure": null}}',
            "input_tokens": 200,
            "output_tokens": 50,
        }

        with patch(
            "app.services.chatbot_engine.call_claude",
            new_callable=AsyncMock,
            return_value=call_claude_response,
        ), patch(
            "app.services.chatbot_engine.extract_json_object",
            return_value={"intent": "schedule", "confidence": 0.95, "entities": {}},
        ):
            result = await self.engine.classify_intent(
                message="Quiero agendar una cita para el próximo lunes",
                conversation_history=[],
            )

        assert result["intent"] == "schedule"
        assert result["confidence"] == 0.95
        assert isinstance(result["entities"], dict)

    async def test_classify_intent_faq(self):
        """Question about services → faq intent."""
        call_claude_response = {
            "content": '{"intent": "faq", "confidence": 0.88, "entities": {}}',
            "input_tokens": 180,
            "output_tokens": 40,
        }

        with patch(
            "app.services.chatbot_engine.call_claude",
            new_callable=AsyncMock,
            return_value=call_claude_response,
        ), patch(
            "app.services.chatbot_engine.extract_json_object",
            return_value={"intent": "faq", "confidence": 0.88, "entities": {}},
        ):
            result = await self.engine.classify_intent(
                message="¿Cuánto cuesta una limpieza dental?",
                conversation_history=[],
            )

        assert result["intent"] == "faq"
        assert result["confidence"] == 0.88

    async def test_classify_intent_emergency(self):
        """Dental pain message → emergency intent."""
        call_claude_response = {
            "content": '{"intent": "emergency", "confidence": 0.99, "entities": {}}',
            "input_tokens": 150,
            "output_tokens": 30,
        }

        with patch(
            "app.services.chatbot_engine.call_claude",
            new_callable=AsyncMock,
            return_value=call_claude_response,
        ), patch(
            "app.services.chatbot_engine.extract_json_object",
            return_value={"intent": "emergency", "confidence": 0.99, "entities": {}},
        ):
            result = await self.engine.classify_intent(
                message="Tengo un dolor muy fuerte en la muela, no aguanto más",
                conversation_history=[],
            )

        assert result["intent"] == "emergency"
        assert result["confidence"] == 0.99

    async def test_classify_intent_malformed_response(self):
        """Claude returns malformed JSON → falls back to 'other' with 0 confidence."""
        with patch(
            "app.services.chatbot_engine.call_claude",
            new_callable=AsyncMock,
            return_value={"content": "not-json-at-all", "input_tokens": 100, "output_tokens": 10},
        ), patch(
            "app.services.chatbot_engine.extract_json_object",
            return_value={},  # empty dict from malformed parse
        ):
            result = await self.engine.classify_intent(
                message="asdfasdf",
                conversation_history=[],
            )

        assert result["intent"] == "other"
        assert result["confidence"] == 0.0

    async def test_classify_intent_api_failure(self):
        """Claude API raises exception → falls back to 'other' with 0 confidence."""
        with patch(
            "app.services.chatbot_engine.call_claude",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Claude API unreachable"),
        ):
            result = await self.engine.classify_intent(
                message="Hola quiero información",
                conversation_history=[],
            )

        assert result["intent"] == "other"
        assert result["confidence"] == 0.0
        assert result["entities"] == {}

    async def test_classify_intent_invalid_intent_fallback(self):
        """Claude returns an unknown intent string → coerced to 'other'."""
        with patch(
            "app.services.chatbot_engine.call_claude",
            new_callable=AsyncMock,
            return_value={"content": "{}", "input_tokens": 50, "output_tokens": 5},
        ), patch(
            "app.services.chatbot_engine.extract_json_object",
            return_value={"intent": "UNKNOWN_INTENT", "confidence": 0.9, "entities": {}},
        ):
            result = await self.engine.classify_intent(
                message="...",
                conversation_history=[],
            )

        assert result["intent"] == "other"
        assert result["confidence"] == 0.0

    async def test_classify_intent_confidence_clamped(self):
        """Confidence value > 1.0 is clamped to 1.0."""
        with patch(
            "app.services.chatbot_engine.call_claude",
            new_callable=AsyncMock,
            return_value={"content": "{}", "input_tokens": 50, "output_tokens": 5},
        ), patch(
            "app.services.chatbot_engine.extract_json_object",
            return_value={"intent": "schedule", "confidence": 1.5, "entities": {}},
        ):
            result = await self.engine.classify_intent(
                message="Quiero cita",
                conversation_history=[],
            )

        assert result["confidence"] == 1.0


# ── TestGenerateResponse ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestGenerateResponse:
    """Tests for ChatbotEngine.generate_response."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.engine = ChatbotEngine()
        self.tenant_config = {
            "business_hours_text": "Lunes a Viernes 8AM a 6PM, Sábados 8AM a 1PM",
            "faq_entries": [],
        }
        self.empty_conversation = {"intent_history": []}

    async def test_generate_response_hours(self):
        """Intent 'hours' returns business hours text from config."""
        result = await self.engine.generate_response(
            intent="hours",
            entities={},
            conversation=self.empty_conversation,
            tenant_config=self.tenant_config,
        )

        assert "Lunes a Viernes 8AM a 6PM" in result

    async def test_generate_response_location(self):
        """Intent 'location' returns clinic location guidance."""
        result = await self.engine.generate_response(
            intent="location",
            entities={},
            conversation=self.empty_conversation,
            tenant_config=self.tenant_config,
        )

        assert "ubicacion" in result.lower() or "clinica" in result.lower()

    async def test_generate_response_schedule_ask_date(self):
        """Schedule intent with no date in entities → asks for preferred date."""
        result = await self.engine.generate_response(
            intent="schedule",
            entities={"date": None, "time": None, "doctor": None, "procedure": None},
            conversation=self.empty_conversation,
            tenant_config=self.tenant_config,
        )

        # Should ask for date
        assert "fecha" in result.lower() or "cita" in result.lower()

    async def test_generate_response_schedule_ask_time(self):
        """Schedule intent with date but no time → asks for preferred time."""
        result = await self.engine.generate_response(
            intent="schedule",
            entities={"date": "2026-03-15", "time": None, "doctor": None, "procedure": None},
            conversation=self.empty_conversation,
            tenant_config=self.tenant_config,
        )

        # Should acknowledge date and ask for time
        assert "2026-03-15" in result
        assert "hora" in result.lower() or "horario" in result.lower()

    async def test_generate_response_schedule_confirm(self):
        """Schedule intent with date + time → shows confirmation summary."""
        result = await self.engine.generate_response(
            intent="schedule",
            entities={"date": "2026-03-15", "time": "10:00", "doctor": None, "procedure": None},
            conversation=self.empty_conversation,
            tenant_config=self.tenant_config,
        )

        assert "2026-03-15" in result
        assert "10:00" in result

    async def test_generate_response_emergency_message(self):
        """Intent 'emergency' returns emergency guidance."""
        result = await self.engine.generate_response(
            intent="emergency",
            entities={},
            conversation=self.empty_conversation,
            tenant_config=self.tenant_config,
        )

        assert "emergencia" in result.lower() or "urgencia" in result.lower()

    async def test_generate_response_payment_intent(self):
        """Intent 'payment' returns payment info."""
        result = await self.engine.generate_response(
            intent="payment",
            entities={},
            conversation=self.empty_conversation,
            tenant_config=self.tenant_config,
        )

        assert "pago" in result.lower() or "factura" in result.lower()

    async def test_generate_response_other_fallback(self):
        """Intent 'other' returns escalation suggestion."""
        result = await self.engine.generate_response(
            intent="other",
            entities={},
            conversation=self.empty_conversation,
            tenant_config=self.tenant_config,
        )

        assert result  # non-empty response


# ── TestBuildFaqResponse ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestBuildFaqResponse:
    """Tests for ChatbotEngine._build_faq_response."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.engine = ChatbotEngine()
        self.faq_entries = [
            {
                "question": "¿Cuánto cuesta una limpieza?",
                "answer": "La limpieza dental cuesta desde $80,000 COP.",
            },
            {
                "question": "¿Tienen rayos X?",
                "answer": "Sí, contamos con servicio de radiografías dentales.",
            },
        ]

    async def test_build_faq_response_match(self):
        """FAQ match: Claude selects the relevant FAQ and returns its answer."""
        with patch(
            "app.services.chatbot_engine.call_claude",
            new_callable=AsyncMock,
            return_value={"content": "{}", "input_tokens": 100, "output_tokens": 50},
        ), patch(
            "app.services.chatbot_engine.extract_json_object",
            return_value={
                "matched_index": 0,
                "response": "La limpieza dental cuesta desde $80,000 COP.",
            },
        ):
            result = await self.engine._build_faq_response(
                message="¿Cuánto vale la limpieza?",
                faq_entries=self.faq_entries,
            )

        assert "$80,000" in result or "limpieza" in result.lower()

    async def test_build_faq_response_no_match(self):
        """No FAQ matches → returns fallback apology message."""
        with patch(
            "app.services.chatbot_engine.call_claude",
            new_callable=AsyncMock,
            return_value={"content": "{}", "input_tokens": 100, "output_tokens": 30},
        ), patch(
            "app.services.chatbot_engine.extract_json_object",
            return_value={
                "matched_index": None,
                "response": "Lo siento, no tengo información sobre eso.",
            },
        ):
            result = await self.engine._build_faq_response(
                message="¿Hacen trasplantes capilares?",
                faq_entries=self.faq_entries,
            )

        assert result  # non-empty fallback

    async def test_build_faq_response_empty_faq_list(self):
        """Empty FAQ list → generic helpful response without calling Claude."""
        result = await self.engine._build_faq_response(
            message="¿Cuánto cuesta?",
            faq_entries=[],
        )

        assert "clinica" in result.lower() or "pregunta" in result.lower()


# ── TestShouldEscalate ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestShouldEscalate:
    """Tests for ChatbotEngine.should_escalate (synchronous method)."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.engine = ChatbotEngine()

    def test_should_escalate_low_confidence(self):
        """Confidence < 0.5 triggers escalation."""
        result = self.engine.should_escalate(
            intent="faq",
            confidence=0.3,
            message="Necesito información",
        )
        assert result is True

    def test_should_not_escalate_high_confidence(self):
        """Confidence >= 0.5 and no keywords → no escalation."""
        result = self.engine.should_escalate(
            intent="schedule",
            confidence=0.9,
            message="Quiero agendar una cita el lunes",
        )
        assert result is False

    def test_should_escalate_emergency(self):
        """Emergency intent always triggers escalation regardless of confidence."""
        result = self.engine.should_escalate(
            intent="emergency",
            confidence=0.99,
            message="Tengo dolor",
        )
        assert result is True

    def test_should_escalate_keywords_hablar_con_alguien(self):
        """Message containing 'hablar con alguien' → escalation."""
        result = self.engine.should_escalate(
            intent="other",
            confidence=0.8,
            message="Quiero hablar con alguien de la clínica",
        )
        assert result is True

    def test_should_escalate_keywords_recepcionista(self):
        """Message containing 'recepcionista' → escalation."""
        result = self.engine.should_escalate(
            intent="faq",
            confidence=0.7,
            message="¿Puedo hablar con la recepcionista por favor?",
        )
        assert result is True

    def test_should_escalate_keywords_operador(self):
        """Message containing 'operador' → escalation."""
        result = self.engine.should_escalate(
            intent="schedule",
            confidence=0.85,
            message="Necesito un operador humano ahora",
        )
        assert result is True

    def test_should_escalate_keywords_persona_real(self):
        """Message containing 'persona real' → escalation."""
        result = self.engine.should_escalate(
            intent="other",
            confidence=0.75,
            message="Quiero hablar con una persona real",
        )
        assert result is True

    def test_boundary_confidence_exactly_half(self):
        """Confidence exactly 0.5 does NOT trigger low-confidence escalation."""
        result = self.engine.should_escalate(
            intent="faq",
            confidence=0.5,
            message="Tengo una pregunta sobre servicios",
        )
        assert result is False
