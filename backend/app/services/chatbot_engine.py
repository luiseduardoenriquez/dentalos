"""AI Virtual Receptionist engine -- VP-16.

The brain of the chatbot: intent classification with Claude,
multi-turn scheduling state machine, FAQ matching, and escalation
detection.

Security:
  - PHI (message content, patient names) is NEVER logged.
  - Intent classification uses Claude Haiku for fast, low-cost inference.
"""

import logging
from typing import Any

from app.core.config import settings
from app.services.ai_claude_client import call_claude, extract_json_object

logger = logging.getLogger("dentalos.chatbot")

# ─── Intent classification system prompt (Spanish for LATAM patients) ────────

INTENT_SYSTEM_PROMPT = (
    "Eres un asistente virtual de una clinica dental. Tu trabajo es "
    "clasificar la intencion del mensaje del paciente.\n\n"
    "Intenciones posibles:\n"
    "- schedule: quiere agendar una cita nueva\n"
    "- reschedule: quiere cambiar la fecha/hora de una cita existente\n"
    "- cancel: quiere cancelar una cita\n"
    "- faq: pregunta general sobre servicios, precios o procedimientos\n"
    "- payment: pregunta sobre pagos, facturas o costos\n"
    "- hours: pregunta sobre horarios de atencion\n"
    "- location: pregunta sobre direccion o como llegar\n"
    "- emergency: reporta dolor intenso, sangrado, trauma dental u otra urgencia\n"
    "- other: cualquier otra cosa que no encaje en las categorias anteriores\n\n"
    "Analiza el mensaje del paciente y el historial de conversacion (si existe).\n"
    "Responde SOLO con un objeto JSON valido, sin texto adicional:\n"
    '{"intent": "...", "confidence": 0.0, "entities": '
    '{"date": null, "time": null, "doctor": null, "procedure": null}}\n\n'
    "Reglas:\n"
    "- confidence es un numero entre 0.0 y 1.0\n"
    "- Extrae entidades cuando sea posible (fechas, horas, nombres de doctor, "
    "tipo de procedimiento)\n"
    "- Si el mensaje es ambiguo, usa confidence baja y intent='other'\n"
    "- Las fechas deben estar en formato YYYY-MM-DD si se pueden inferir\n"
    "- Las horas deben estar en formato HH:MM (24h) si se pueden inferir"
)

FAQ_MATCH_SYSTEM_PROMPT = (
    "Eres un asistente de clinica dental. Se te da una pregunta del paciente "
    "y una lista de preguntas frecuentes (FAQ) con sus respuestas.\n\n"
    "Selecciona la FAQ que mejor responda la pregunta del paciente.\n"
    "Si ninguna FAQ coincide bien, responde con una disculpa amable y "
    "sugiere contactar a la clinica directamente.\n\n"
    'Responde SOLO con un objeto JSON: {"matched_index": <int o null>, '
    '"response": "<texto de respuesta en espanol>"}\n'
    "- matched_index: indice (base 0) de la FAQ seleccionada, o null si "
    "ninguna coincide.\n"
    "- response: la respuesta final para el paciente, adaptada de la FAQ "
    "o una disculpa amable."
)

# Keywords that trigger immediate escalation to human staff
ESCALATION_KEYWORDS = [
    "hablar con alguien",
    "hablar con una persona",
    "quiero hablar con",
    "persona real",
    "agente humano",
    "operador",
    "recepcionista",
    "no entiendes",
    "no me entiendes",
    "atencion humana",
]


class ChatbotEngine:
    """Stateless engine for intent classification and response generation.

    Does not manage persistence -- that is the responsibility of
    ChatbotService.  All methods are async to support the Claude API
    calls via httpx.
    """

    # ─── Intent Classification ───────────────────────────────────────────

    async def classify_intent(
        self,
        message: str,
        conversation_history: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Classify the patient's intent using Claude Haiku.

        Args:
            message: The patient's latest message.
            conversation_history: Previous messages as [{"role": ..., "content": ...}].

        Returns:
            dict with keys: intent (str), confidence (float), entities (dict).
            On failure, returns intent="other" with confidence=0.0.
        """
        # Build context from conversation history (last 6 messages max)
        history_text = ""
        recent = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
        if recent:
            history_lines = []
            for msg in recent:
                role_label = "Paciente" if msg.get("role") == "user" else "Asistente"
                history_lines.append(f"{role_label}: {msg.get('content', '')}")
            history_text = (
                "Historial de conversacion:\n"
                + "\n".join(history_lines)
                + "\n\n"
            )

        user_content = f"{history_text}Mensaje actual del paciente: {message}"

        try:
            result = await call_claude(
                system_prompt=INTENT_SYSTEM_PROMPT,
                user_content=user_content,
                max_tokens=settings.chatbot_max_tokens,
                temperature=0.1,
                model_override=settings.chatbot_model,
            )

            parsed = extract_json_object(result["content"])

            intent = parsed.get("intent", "other")
            confidence = float(parsed.get("confidence", 0.0))
            entities = parsed.get("entities", {})

            # Clamp confidence to [0.0, 1.0]
            confidence = max(0.0, min(1.0, confidence))

            # Validate intent
            valid_intents = {
                "schedule", "reschedule", "cancel", "faq", "payment",
                "hours", "location", "emergency", "other",
            }
            if intent not in valid_intents:
                intent = "other"
                confidence = 0.0

            logger.info(
                "Intent classified: intent=%s confidence=%.2f",
                intent,
                confidence,
            )

            return {
                "intent": intent,
                "confidence": confidence,
                "entities": entities if isinstance(entities, dict) else {},
            }

        except Exception:
            logger.exception("Intent classification failed")
            return {
                "intent": "other",
                "confidence": 0.0,
                "entities": {},
            }

    # ─── Response Generation ─────────────────────────────────────────────

    async def generate_response(
        self,
        intent: str,
        entities: dict[str, Any],
        conversation: dict[str, Any],
        tenant_config: dict[str, Any],
    ) -> str:
        """Generate the bot's reply based on the classified intent.

        For simple intents (hours, location, faq), returns canned or
        config-driven responses.  For complex intents (schedule,
        reschedule, cancel), delegates to the multi-turn state machine.

        Args:
            intent: Classified intent string.
            entities: Extracted entities from classification.
            conversation: Current conversation dict (with intent_history).
            tenant_config: Chatbot config from clinic_settings.

        Returns:
            Spanish-language response text for the patient.
        """
        if intent == "hours":
            hours_text = tenant_config.get(
                "business_hours_text",
                "Nuestro horario de atencion es de lunes a viernes "
                "de 8:00 AM a 6:00 PM y sabados de 8:00 AM a 1:00 PM.",
            )
            return hours_text

        if intent == "location":
            return (
                "Puede encontrar nuestra ubicacion y como llegar en "
                "nuestra pagina web. Si necesita la direccion exacta, "
                "por favor contacte a la recepcion de la clinica."
            )

        if intent == "faq":
            faq_entries = tenant_config.get("faq_entries", [])
            # Retrieve the original message from the last user message in
            # conversation history for FAQ matching
            message = ""
            history = conversation.get("intent_history", [])
            if history:
                last_entry = history[-1] if history else {}
                message = last_entry.get("message", "")
            return await self._build_faq_response(message, faq_entries)

        if intent == "payment":
            return (
                "Para consultas sobre pagos, facturas pendientes o "
                "metodos de pago disponibles, por favor contacte a "
                "nuestra recepcion. Aceptamos efectivo, tarjeta de "
                "credito/debito, Nequi y Daviplata."
            )

        if intent == "emergency":
            return (
                "Si tiene una emergencia dental (dolor intenso, sangrado "
                "que no para, trauma dental), por favor llame directamente "
                "a la clinica o acuda a urgencias lo antes posible. "
                "Un miembro de nuestro equipo le atendera de inmediato."
            )

        if intent in ("schedule", "reschedule"):
            return self._build_scheduling_response(
                entities, conversation, tenant_config
            )

        if intent == "cancel":
            return (
                "Entiendo que desea cancelar su cita. Para proceder con "
                "la cancelacion, por favor proporcioneme su nombre completo "
                "y la fecha de la cita que desea cancelar. Un miembro de "
                "nuestro equipo confirmara la cancelacion."
            )

        # intent == "other" or unknown
        return (
            "Gracias por su mensaje. No estoy seguro de como ayudarle "
            "con eso. Si desea, puedo transferirle con un miembro de "
            "nuestro equipo. Escriba 'hablar con alguien' para ser "
            "atendido por una persona."
        )

    # ─── Scheduling State Machine ────────────────────────────────────────

    def _build_scheduling_response(
        self,
        entities: dict[str, Any],
        conversation: dict[str, Any],
        tenant_config: dict[str, Any],
    ) -> str:
        """Multi-turn scheduling flow.

        State transitions based on which entities have been collected:
          1. No date     -> ask for preferred date
          2. Date only   -> suggest available time slots
          3. Date + time -> confirm appointment details

        Returns:
            Spanish response text advancing the scheduling conversation.
        """
        extracted_date = entities.get("date")
        extracted_time = entities.get("time")
        extracted_doctor = entities.get("doctor")
        extracted_procedure = entities.get("procedure")

        # Check what the conversation has collected so far
        history = conversation.get("intent_history", [])
        collected_date = extracted_date
        collected_time = extracted_time
        collected_doctor = extracted_doctor

        # Scan previous intents for accumulated entities
        for entry in history:
            prev_entities = entry.get("entities", {})
            if not collected_date and prev_entities.get("date"):
                collected_date = prev_entities["date"]
            if not collected_time and prev_entities.get("time"):
                collected_time = prev_entities["time"]
            if not collected_doctor and prev_entities.get("doctor"):
                collected_doctor = prev_entities["doctor"]

        # State 1: No date collected yet
        if not collected_date:
            action = "agendar" if not any(
                e.get("intent") == "reschedule" for e in history
            ) else "reprogramar"

            response = (
                f"Con gusto le ayudo a {action} su cita. "
                "Por favor, indiqueme la fecha de su preferencia "
                "(por ejemplo: 'el proximo lunes', 'el 15 de abril', etc.)."
            )
            if extracted_procedure:
                response += (
                    f" Ya tengo registrado que necesita: {extracted_procedure}."
                )
            return response

        # State 2: Date collected but no time
        if not collected_time:
            response = (
                f"Perfecto, buscare disponibilidad para el {collected_date}. "
            )
            if collected_doctor:
                response += (
                    f"Con el Dr./Dra. {collected_doctor}. "
                )

            hours_text = tenant_config.get(
                "business_hours_text",
                "8:00 AM a 6:00 PM",
            )
            response += (
                f"Nuestro horario de atencion es {hours_text}. "
                "Por favor, indiqueme su hora preferida y verificare "
                "la disponibilidad."
            )
            return response

        # State 3: Date + time collected -> confirmation
        response = (
            f"Le confirmo los detalles de su cita:\n"
            f"- Fecha: {collected_date}\n"
            f"- Hora: {collected_time}\n"
        )
        if collected_doctor:
            response += f"- Doctor(a): {collected_doctor}\n"
        if extracted_procedure:
            response += f"- Procedimiento: {extracted_procedure}\n"

        response += (
            "\nPara confirmar la cita, un miembro de nuestro equipo se "
            "comunicara con usted en breve para verificar los datos. "
            "Si necesita hacer algun cambio, por favor indiquemelo."
        )
        return response

    # ─── FAQ Matching ────────────────────────────────────────────────────

    async def _build_faq_response(
        self,
        message: str,
        faq_entries: list[dict[str, Any]],
    ) -> str:
        """Match the patient's message against FAQ entries using Claude.

        When no FAQ entries are configured, returns a generic helpful
        response.  When entries exist, asks Claude to pick the best match.

        Args:
            message: The patient's question text.
            faq_entries: List of dicts with 'question' and 'answer' keys.

        Returns:
            Spanish response text with the best-matching FAQ answer.
        """
        if not faq_entries:
            return (
                "Gracias por su pregunta. En este momento no tenemos "
                "informacion especifica sobre eso en nuestras preguntas "
                "frecuentes. Le recomiendo contactar directamente a la "
                "clinica para obtener una respuesta mas detallada."
            )

        if not message:
            return (
                "Puedo ayudarle con preguntas frecuentes sobre nuestros "
                "servicios. Por favor, digame su consulta."
            )

        # Format FAQ list for Claude
        faq_text_lines = []
        for i, entry in enumerate(faq_entries):
            question = entry.get("question", "")
            answer = entry.get("answer", "")
            faq_text_lines.append(f"[{i}] P: {question}\n    R: {answer}")

        faq_text = "\n".join(faq_text_lines)

        user_content = (
            f"Pregunta del paciente: {message}\n\n"
            f"Preguntas frecuentes disponibles:\n{faq_text}"
        )

        try:
            result = await call_claude(
                system_prompt=FAQ_MATCH_SYSTEM_PROMPT,
                user_content=user_content,
                max_tokens=settings.chatbot_max_tokens,
                temperature=0.1,
                model_override=settings.chatbot_model,
            )

            parsed = extract_json_object(result["content"])
            response = parsed.get("response", "")

            if response:
                return response

        except Exception:
            logger.exception("FAQ matching failed")

        return (
            "Disculpe, no pude encontrar una respuesta adecuada en "
            "nuestras preguntas frecuentes. Le recomiendo contactar "
            "directamente a la clinica para mas informacion."
        )

    # ─── Escalation Detection ────────────────────────────────────────────

    def should_escalate(
        self,
        intent: str,
        confidence: float,
        message: str,
    ) -> bool:
        """Determine if the conversation should be escalated to a human.

        Escalation triggers:
          1. Classification confidence below 0.5
          2. Intent is "emergency" (always escalate emergencies)
          3. Message contains explicit escalation keywords

        Args:
            intent: The classified intent.
            confidence: Classification confidence score.
            message: The raw patient message.

        Returns:
            True if the conversation should be handed off to staff.
        """
        # Emergency always escalates
        if intent == "emergency":
            return True

        # Low confidence suggests the bot can't handle this
        if confidence < 0.5:
            return True

        # Check for explicit escalation keywords
        message_lower = message.lower().strip()
        for keyword in ESCALATION_KEYWORDS:
            if keyword in message_lower:
                return True

        return False


# Module-level singleton
chatbot_engine = ChatbotEngine()
