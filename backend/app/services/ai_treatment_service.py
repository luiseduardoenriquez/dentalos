"""AI treatment advisor service (VP-13).

Generates treatment suggestions using Claude based on a patient's
odontogram conditions, medical history, and the clinic's service catalog.

Security invariants:
  - PHI is NEVER logged (patient names, phones, emails, diagnoses).
  - The patient context sent to Claude is minimised to clinical data only:
    age, blood type, allergy flags, chronic condition flags, odontogram
    conditions, and catalog entries.  No identifying information.
  - The add-on gate (tenant_features["ai_treatment_advisor"]) is enforced
    before any Claude API call.
  - All monetary values are in COP cents.
"""

import logging
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.error_codes import AITreatmentErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.models.tenant.ai_treatment import AITreatmentSuggestion
from app.models.tenant.ai_usage_log import AIUsageLog
from app.models.tenant.chatbot import ChatbotMessage
from app.models.tenant.odontogram import OdontogramCondition
from app.models.tenant.voice_session import VoiceParse, VoiceSession
from app.models.tenant.patient import Patient
from app.models.tenant.service_catalog import ServiceCatalog
from app.services.ai_claude_client import call_claude, extract_json_array
from app.services.treatment_plan_service import treatment_plan_service

logger = logging.getLogger("dentalos.ai_treatment")


def _compute_age(birthdate: date | None) -> int | None:
    """Compute age in years from a birthdate, or None if unknown."""
    if birthdate is None:
        return None
    today = date.today()
    return today.year - birthdate.year - (
        (today.month, today.day) < (birthdate.month, birthdate.day)
    )


def _suggestion_to_dict(row: AITreatmentSuggestion) -> dict[str, Any]:
    """Serialize an AITreatmentSuggestion ORM instance to a plain dict."""
    return {
        "id": str(row.id),
        "patient_id": str(row.patient_id),
        "doctor_id": str(row.doctor_id),
        "suggestions": row.suggestions if isinstance(row.suggestions, list) else [],
        "model_used": row.model_used,
        "status": row.status,
        "input_tokens": row.input_tokens,
        "output_tokens": row.output_tokens,
        "reviewed_at": row.reviewed_at,
        "treatment_plan_id": (
            str(row.treatment_plan_id) if row.treatment_plan_id else None
        ),
        "created_at": row.created_at,
    }


# ── Prompt templates ─────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are an expert dental treatment advisor for a dental clinic in Colombia.
Given a patient's current odontogram conditions, medical history, and the
clinic's available service catalog, suggest appropriate treatment procedures.

Rules:
1. Only suggest procedures whose CUPS codes exist in the provided catalog.
2. Prioritise urgent conditions (caries, fractures) over preventive care.
3. Consider medical contraindications (allergies, chronic conditions).
4. For each suggestion, explain the clinical rationale briefly.
5. Set confidence to "high", "medium", or "low" based on clinical certainty.
6. Set estimated_cost from the catalog's default_price for each CUPS code.
7. Order suggestions by clinical priority (most urgent first).

Return ONLY a JSON array. Each element must have exactly these keys:
  cups_code, cups_description, tooth_number (string or null),
  rationale, confidence, priority_order, estimated_cost
"""


def _build_user_prompt(
    *,
    age: int | None,
    blood_type: str | None,
    allergies: list[str] | None,
    chronic_conditions: list[str] | None,
    conditions: list[dict[str, Any]],
    catalog_entries: list[dict[str, Any]],
) -> str:
    """Build the user message content for the Claude call."""
    parts: list[str] = []

    # Patient context (no PII)
    parts.append("## Patient Context")
    if age is not None:
        parts.append(f"- Age: {age} years")
    if blood_type:
        parts.append(f"- Blood type: {blood_type}")
    if allergies:
        parts.append(f"- Allergies: {', '.join(allergies)}")
    if chronic_conditions:
        parts.append(f"- Chronic conditions: {', '.join(chronic_conditions)}")
    if not any([age, blood_type, allergies, chronic_conditions]):
        parts.append("- No additional medical history available")

    # Odontogram conditions
    parts.append("\n## Current Odontogram Conditions")
    for cond in conditions:
        line = (
            f"- Tooth {cond['tooth_number']} ({cond['zone']}): "
            f"{cond['condition_code']}"
        )
        if cond.get("severity"):
            line += f" (severity: {cond['severity']})"
        if cond.get("notes"):
            line += f" -- {cond['notes']}"
        parts.append(line)

    # Service catalog
    parts.append("\n## Available Service Catalog (CUPS codes with prices in COP cents)")
    for entry in catalog_entries:
        parts.append(
            f"- {entry['cups_code']}: {entry['name']} "
            f"(category: {entry['category']}, price: {entry['default_price']} cents)"
        )

    return "\n".join(parts)


class AITreatmentService:
    """Stateless service for AI treatment recommendation features."""

    # ── Generate suggestions ─────────────────────────────────────

    async def generate_suggestions(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        doctor_id: str,
        tenant_features: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate AI treatment suggestions for a patient.

        Steps:
        1. Verify the ai_treatment_advisor add-on is active.
        2. Fetch patient demographics (age, medical flags) -- no PII is logged.
        3. Fetch active odontogram conditions.
        4. Fetch the clinic's service catalog.
        5. Call Claude with a structured prompt.
        6. Parse, validate, and store the suggestions.

        Raises:
            DentalOSError (402) -- add-on not active.
            DentalOSError (404) -- patient not found.
            DentalOSError (422) -- no active odontogram conditions.
            DentalOSError (502) -- Claude API or parsing failure.
        """
        # 1. Check add-on gate
        if not tenant_features.get("ai_treatment_advisor"):
            raise DentalOSError(
                error=AITreatmentErrors.ADDON_REQUIRED,
                message=(
                    "El complemento AI Treatment Advisor no está activo. "
                    "Contacte al administrador para habilitarlo."
                ),
                status_code=402,
            )

        pid = uuid.UUID(patient_id)

        # 2. Fetch patient (no PII logged)
        result = await db.execute(
            select(
                Patient.id,
                Patient.birthdate,
                Patient.blood_type,
                Patient.allergies,
                Patient.chronic_conditions,
            ).where(Patient.id == pid, Patient.is_active.is_(True))
        )
        patient_row = result.one_or_none()
        if patient_row is None:
            raise ResourceNotFoundError(
                error="PATIENT_not_found",
                resource_name="Patient",
            )

        age = _compute_age(patient_row.birthdate)

        # 3. Fetch active odontogram conditions
        cond_result = await db.execute(
            select(
                OdontogramCondition.tooth_number,
                OdontogramCondition.zone,
                OdontogramCondition.condition_code,
                OdontogramCondition.severity,
                OdontogramCondition.notes,
            ).where(
                OdontogramCondition.patient_id == pid,
                OdontogramCondition.is_active.is_(True),
            )
        )
        conditions = [
            {
                "tooth_number": row.tooth_number,
                "zone": row.zone,
                "condition_code": row.condition_code,
                "severity": row.severity,
                "notes": row.notes,
            }
            for row in cond_result.all()
        ]

        if not conditions:
            raise DentalOSError(
                error=AITreatmentErrors.NO_ACTIVE_CONDITIONS,
                message=(
                    "No hay condiciones activas en el odontograma del paciente. "
                    "Registre al menos una condición antes de solicitar sugerencias."
                ),
                status_code=422,
            )

        # 4. Fetch service catalog (active entries, limit 200)
        catalog_result = await db.execute(
            select(
                ServiceCatalog.cups_code,
                ServiceCatalog.name,
                ServiceCatalog.default_price,
                ServiceCatalog.category,
            )
            .where(ServiceCatalog.is_active.is_(True))
            .limit(200)
        )
        catalog_entries = [
            {
                "cups_code": row.cups_code,
                "name": row.name,
                "default_price": row.default_price,
                "category": row.category,
            }
            for row in catalog_result.all()
        ]

        # Build a lookup set for validation
        valid_cups: dict[str, dict[str, Any]] = {
            e["cups_code"]: e for e in catalog_entries
        }

        # 5. Build prompt and call Claude
        user_content = _build_user_prompt(
            age=age,
            blood_type=patient_row.blood_type,
            allergies=patient_row.allergies,
            chronic_conditions=patient_row.chronic_conditions,
            conditions=conditions,
            catalog_entries=catalog_entries,
        )

        model = settings.anthropic_model_treatment

        try:
            claude_response = await call_claude(
                system_prompt=_SYSTEM_PROMPT,
                user_content=user_content,
                max_tokens=settings.ai_treatment_max_tokens,
                temperature=0.2,
                model_override=model,
            )
        except Exception:
            logger.exception("Claude API call failed for AI treatment suggestion")
            raise DentalOSError(
                error=AITreatmentErrors.GENERATION_FAILED,
                message=(
                    "No se pudieron generar las sugerencias de tratamiento. "
                    "Intente nuevamente en unos minutos."
                ),
                status_code=502,
            ) from None

        # 6. Parse response
        raw_suggestions = extract_json_array(claude_response["content"])
        if not raw_suggestions:
            logger.warning("Claude returned empty suggestions array")
            raise DentalOSError(
                error=AITreatmentErrors.GENERATION_FAILED,
                message=(
                    "El modelo de IA no generó sugerencias válidas. "
                    "Intente nuevamente."
                ),
                status_code=502,
            )

        # 7. Validate and clean suggestions
        validated_suggestions: list[dict[str, Any]] = []
        for idx, raw in enumerate(raw_suggestions):
            cups_code = str(raw.get("cups_code", "")).strip()
            if not cups_code:
                continue

            # Check if cups_code exists in catalog
            catalog_match = valid_cups.get(cups_code)
            if catalog_match is None:
                # Drop suggestions with invalid CUPS codes
                logger.info(
                    "Dropping suggestion with unknown CUPS code: %s", cups_code
                )
                continue

            # Validate confidence level
            confidence = str(raw.get("confidence", "low")).lower()
            if confidence not in {"high", "medium", "low"}:
                confidence = "low"

            # Use catalog price if AI did not provide or provided incorrect price
            estimated_cost = raw.get("estimated_cost")
            catalog_price = catalog_match["default_price"]
            if not isinstance(estimated_cost, int) or estimated_cost <= 0:
                estimated_cost = catalog_price
            elif catalog_price > 0 and estimated_cost < catalog_price // 2:
                # AI likely returned pesos instead of cents — multiply by 100
                estimated_cost = estimated_cost * 100

            # Normalize tooth_number to string or None
            tooth_number = raw.get("tooth_number")
            if tooth_number is not None:
                tooth_number = str(tooth_number).strip() or None

            validated_suggestions.append({
                "cups_code": cups_code,
                "cups_description": str(
                    raw.get("cups_description", catalog_match["name"])
                ),
                "tooth_number": tooth_number,
                "rationale": str(raw.get("rationale", "")),
                "confidence": confidence,
                "priority_order": raw.get("priority_order", idx + 1),
                "estimated_cost": estimated_cost,
                "action": None,
            })

        if not validated_suggestions:
            raise DentalOSError(
                error=AITreatmentErrors.GENERATION_FAILED,
                message=(
                    "Ninguna de las sugerencias generadas coincide con el "
                    "catálogo de servicios de la clínica."
                ),
                status_code=502,
            )

        # 8. Store in database
        suggestion = AITreatmentSuggestion(
            patient_id=pid,
            doctor_id=uuid.UUID(doctor_id),
            odontogram_snapshot=conditions,
            patient_context={
                "age": age,
                "blood_type": patient_row.blood_type,
                "has_allergies": bool(patient_row.allergies),
                "has_chronic_conditions": bool(patient_row.chronic_conditions),
            },
            suggestions=validated_suggestions,
            model_used=model,
            input_tokens=claude_response["input_tokens"],
            output_tokens=claude_response["output_tokens"],
            status="pending_review",
        )
        db.add(suggestion)
        await db.flush()
        await db.refresh(suggestion)

        logger.info(
            "AI treatment suggestions generated: patient=%s count=%d tokens=%d+%d",
            patient_id[:8],
            len(validated_suggestions),
            claude_response["input_tokens"],
            claude_response["output_tokens"],
        )

        return _suggestion_to_dict(suggestion)

    # ── Get suggestion ───────────────────────────────────────────

    async def get_suggestion(
        self,
        *,
        db: AsyncSession,
        suggestion_id: str,
    ) -> dict[str, Any]:
        """Fetch a single AI treatment suggestion by ID.

        Raises:
            ResourceNotFoundError (404) -- suggestion not found.
        """
        result = await db.execute(
            select(AITreatmentSuggestion).where(
                AITreatmentSuggestion.id == uuid.UUID(suggestion_id)
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise ResourceNotFoundError(
                error=AITreatmentErrors.SUGGESTION_NOT_FOUND,
                resource_name="AITreatmentSuggestion",
            )
        return _suggestion_to_dict(row)

    # ── Review suggestion ────────────────────────────────────────

    async def review_suggestion(
        self,
        *,
        db: AsyncSession,
        suggestion_id: str,
        review_items: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Apply review decisions to suggestion items.

        Each review_item has {cups_code, action} where action is one of
        "accept", "modify", or "reject".

        Raises:
            ResourceNotFoundError (404) -- suggestion not found.
            DentalOSError (409) -- suggestion already reviewed.
        """
        result = await db.execute(
            select(AITreatmentSuggestion).where(
                AITreatmentSuggestion.id == uuid.UUID(suggestion_id)
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise ResourceNotFoundError(
                error=AITreatmentErrors.SUGGESTION_NOT_FOUND,
                resource_name="AITreatmentSuggestion",
            )

        if row.status != "pending_review":
            raise DentalOSError(
                error=AITreatmentErrors.ALREADY_REVIEWED,
                message="Las sugerencias ya han sido revisadas.",
                status_code=409,
            )

        # Build lookup from review items
        review_lookup: dict[str, str] = {
            item["cups_code"]: item["action"] for item in review_items
        }

        # Update each suggestion item's action field
        updated_suggestions = []
        current_suggestions = (
            row.suggestions if isinstance(row.suggestions, list) else []
        )
        for item in current_suggestions:
            cups_code = item.get("cups_code", "")
            action = review_lookup.get(cups_code)
            if action is not None:
                item["action"] = action
            updated_suggestions.append(item)

        # Determine if all items were rejected -> status = rejected
        all_rejected = all(
            s.get("action") == "reject" for s in updated_suggestions
        )

        row.suggestions = updated_suggestions
        row.status = "rejected" if all_rejected else "reviewed"
        row.reviewed_at = datetime.now(UTC)

        await db.flush()
        await db.refresh(row)

        logger.info(
            "AI suggestions reviewed: id=%s status=%s",
            suggestion_id[:8],
            row.status,
        )

        return _suggestion_to_dict(row)

    # ── Create plan from accepted suggestions ────────────────────

    async def create_plan_from_suggestions(
        self,
        *,
        db: AsyncSession,
        suggestion_id: str,
        patient_id: str,
        doctor_id: str,
    ) -> dict[str, Any]:
        """Convert accepted suggestion items into a treatment plan.

        Only items with action="accept" (or "modify") are included.

        Raises:
            ResourceNotFoundError (404) -- suggestion not found.
            DentalOSError (409) -- suggestion not in 'reviewed' status.
            DentalOSError (502) -- plan creation failed.
        """
        result = await db.execute(
            select(AITreatmentSuggestion).where(
                AITreatmentSuggestion.id == uuid.UUID(suggestion_id)
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise ResourceNotFoundError(
                error=AITreatmentErrors.SUGGESTION_NOT_FOUND,
                resource_name="AITreatmentSuggestion",
            )

        if row.status != "reviewed":
            raise DentalOSError(
                error=AITreatmentErrors.ALREADY_REVIEWED,
                message=(
                    "Las sugerencias deben estar en estado 'reviewed' "
                    "para crear un plan de tratamiento."
                ),
                status_code=409,
            )

        # Extract accepted items (accept or modify)
        current_suggestions = (
            row.suggestions if isinstance(row.suggestions, list) else []
        )
        accepted_items = [
            s for s in current_suggestions
            if s.get("action") in ("accept", "modify")
        ]

        if not accepted_items:
            raise DentalOSError(
                error=AITreatmentErrors.PLAN_CREATION_FAILED,
                message=(
                    "No hay sugerencias aceptadas para crear un plan de tratamiento."
                ),
                status_code=422,
            )

        # Build plan items in the format expected by treatment_plan_service
        plan_items: list[dict[str, Any]] = []
        for item in accepted_items:
            tooth_number = item.get("tooth_number")
            if tooth_number is not None:
                try:
                    tooth_number = int(tooth_number)
                except (ValueError, TypeError):
                    tooth_number = None

            plan_items.append({
                "cups_code": item["cups_code"],
                "cups_description": item["cups_description"],
                "tooth_number": tooth_number,
                "estimated_cost": item.get("estimated_cost"),
                "priority_order": item.get("priority_order", 0),
                "notes": f"AI suggestion: {item.get('rationale', '')}",
            })

        # Create treatment plan via existing service
        try:
            plan_result = await treatment_plan_service.create_plan(
                db=db,
                patient_id=patient_id,
                doctor_id=doctor_id,
                name="Plan de tratamiento (sugerido por IA)",
                description=(
                    "Plan generado a partir de sugerencias de IA. "
                    "Revise y ajuste según criterio clínico."
                ),
                items=plan_items,
            )
        except Exception:
            logger.exception("Failed to create treatment plan from AI suggestions")
            raise DentalOSError(
                error=AITreatmentErrors.PLAN_CREATION_FAILED,
                message=(
                    "Error al crear el plan de tratamiento. "
                    "Intente nuevamente."
                ),
                status_code=502,
            ) from None

        # Link the plan back to the suggestion
        row.treatment_plan_id = uuid.UUID(plan_result["id"])
        row.status = "applied"
        await db.flush()

        logger.info(
            "Treatment plan created from AI suggestions: suggestion=%s plan=%s items=%d",
            suggestion_id[:8],
            plan_result["id"][:8],
            len(accepted_items),
        )

        return {
            "suggestion_id": str(row.id),
            "treatment_plan_id": plan_result["id"],
            "items_created": len(accepted_items),
            "status": "applied",
        }

    # ── Usage statistics ─────────────────────────────────────────

    async def get_usage_stats(
        self,
        *,
        db: AsyncSession,
        doctor_id: str,
        date_from: str,
        date_to: str,
    ) -> dict[str, Any]:
        """Aggregate AI usage across ALL features for a doctor within a date range.

        Sources:
          - ai_treatment_suggestions: Treatment Advisor (Claude) — has token counts
          - voice_parses: Voice-to-Odontogram NLP (Claude/Ollama) — count as calls
          - chatbot_messages: AI Chatbot (Claude Haiku) — count assistant messages
        """
        did = uuid.UUID(doctor_id)
        dt_from = datetime.fromisoformat(date_from)
        dt_to = datetime.fromisoformat(date_to)

        # 1. Treatment suggestions (has full token tracking)
        treatment_result = await db.execute(
            select(
                func.count(AITreatmentSuggestion.id).label("calls"),
                func.coalesce(func.sum(AITreatmentSuggestion.input_tokens), 0).label("inp"),
                func.coalesce(func.sum(AITreatmentSuggestion.output_tokens), 0).label("out"),
            ).where(
                AITreatmentSuggestion.doctor_id == did,
                AITreatmentSuggestion.created_at >= dt_from,
                AITreatmentSuggestion.created_at <= dt_to,
            )
        )
        t_row = treatment_result.one()

        # 2. Voice parses (each parse = 1 Claude/Ollama API call)
        voice_result = await db.execute(
            select(
                func.count(VoiceParse.id).label("calls"),
                func.coalesce(func.sum(VoiceParse.input_tokens), 0).label("inp"),
                func.coalesce(func.sum(VoiceParse.output_tokens), 0).label("out"),
            ).join(
                VoiceSession, VoiceParse.session_id == VoiceSession.id,
            ).where(
                VoiceSession.doctor_id == did,
                VoiceParse.created_at >= dt_from,
                VoiceParse.created_at <= dt_to,
                VoiceParse.status.in_(["success", "partial"]),
            )
        )
        v_row = voice_result.one()

        # 3. Chatbot messages (each assistant message = 1 Claude Haiku call)
        chatbot_result = await db.execute(
            select(
                func.count(ChatbotMessage.id).label("calls"),
            ).where(
                ChatbotMessage.role == "assistant",
                ChatbotMessage.created_at >= dt_from,
                ChatbotMessage.created_at <= dt_to,
            )
        )
        c_row = chatbot_result.one()

        # 4. AI usage logs (AI Reports and any future features)
        logs_result = await db.execute(
            select(
                func.count(AIUsageLog.id).label("calls"),
                func.coalesce(func.sum(AIUsageLog.input_tokens), 0).label("inp"),
                func.coalesce(func.sum(AIUsageLog.output_tokens), 0).label("out"),
            ).where(
                AIUsageLog.doctor_id == did,
                AIUsageLog.created_at >= dt_from,
                AIUsageLog.created_at <= dt_to,
            )
        )
        l_row = logs_result.one()

        total_calls = t_row.calls + v_row.calls + c_row.calls + l_row.calls
        total_input = t_row.inp + v_row.inp + l_row.inp
        total_output = t_row.out + v_row.out + l_row.out

        return {
            "total_calls": total_calls,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "period_from": date_from,
            "period_to": date_to,
        }


# Module-level singleton
ai_treatment_service = AITreatmentService()
