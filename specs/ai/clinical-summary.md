# AI Clinical Summary Spec

---

## Overview

**Feature:** AI-02 — Before a patient appointment, an AI-generated comprehensive clinical briefing is available for the treating doctor. The summary aggregates data from odontogram, diagnoses, treatment plans, billing, appointments, evolution notes, lab orders, and medications into a structured JSON response with sections, risk alerts, and action suggestions. The summary is appointment-context aware: it tailors emphasis based on today's scheduled procedure type.

**Domain:** ai

**Priority:** Critical (Tier 1 — competitive parity with Dentalink)

**Dependencies:** patients, odontogram, clinical-records, treatment-plans, billing, appointments, evolution-notes, lab-orders, medications, ai_claude_client, feature-flags, caching

**Feature Flag:** `ai_clinical_summary`

**Plan Gating:** Pro+ plan (included, not an add-on)

**Model:** Claude Haiku (optimized for speed, ~3K input + ~500 output tokens)

**Target Latency:** < 3 seconds (cache hit < 50ms)

---

## Data Flow

```
┌────────────────────────────────────────────────────────────────────┐
│  Doctor opens patient chart or appointment view                    │
│                                                                    │
│  GET /api/v1/patients/{patient_id}/clinical-summary                │
│       ?appointment_id=...  (optional context)                      │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 1. Auth + RBAC check (doctor, assistant, clinic_owner)       │  │
│  │ 2. Feature flag check (ai_clinical_summary enabled)          │  │
│  │ 3. Plan check (Pro+ required)                                │  │
│  │ 4. Redis cache lookup                                        │  │
│  │    Key: dentalos:{tid}:ai:clinical_summary:{patient_id}      │  │
│  │    ├─ HIT  → return cached summary (< 50ms)                 │  │
│  │    └─ MISS → continue to step 5                              │  │
│  │ 5. Aggregate patient data from 8 sources (parallel queries)  │  │
│  │ 6. Build prompt from template + injected data                │  │
│  │ 7. Call Claude Haiku via ai_claude_client                     │  │
│  │ 8. Parse + validate structured JSON response                 │  │
│  │ 9. Cache result in Redis (TTL 5 min)                         │  │
│  │ 10. Log usage to ai_usage_logs (no PHI)                      │  │
│  │ 11. Return structured summary                                │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

### Cache Invalidation

The cached summary is invalidated (Redis DEL) when any of the following events occur for the patient:

| Event | Trigger Location |
|-------|-----------------|
| New evolution note created | `evolution_note_service.create()` |
| Diagnosis created/updated | `diagnosis_service.create()`, `diagnosis_service.update()` |
| Treatment plan status change | `treatment_plan_service.update_status()` |
| Payment recorded | `invoice_service.record_payment()` |
| Appointment created/updated/cancelled | `appointment_service.*()` |
| Odontogram finding added | `odontogram_service.add_finding()` |
| Medication prescribed/updated | `medication_service.*()` |
| Lab order created/updated | `lab_order_service.*()` |
| Allergy added/removed | `patient_service.update_medical_history()` |

Implementation: Each service calls `cache.delete(f"dentalos:{tid}:ai:clinical_summary:{patient_id}")` after successful mutation.

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** `clinic_owner`, `doctor`, `assistant`
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Receptionist is excluded (no clinical data access). Access is audit-logged.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/clinical-summary
```

**Rate Limiting:**
- 30 requests per minute per user (AI endpoint throttle)
- Inherits global rate limit (100/min per user)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| patient_id | Yes | uuid | Valid UUID v4 | The patient to summarize | f47ac10b-58cc-4372-a567-0e02b2c3d479 |

### Query Parameters

| Parameter | Required | Type | Default | Description | Example |
|-----------|----------|------|---------|-------------|---------|
| appointment_id | No | uuid | null | Upcoming appointment to contextualize the summary around | a1b2c3d4-... |
| force_refresh | No | boolean | false | Bypass cache and regenerate. Clinic_owner only. | true |

### Request Body Schema

None (GET request).

---

## Response

### Success — 200 OK

```json
{
  "patient_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "appointment_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "generated_at": "2026-03-13T14:30:00Z",
  "cached": true,
  "cached_until": "2026-03-13T14:35:00Z",
  "model_used": "claude-haiku",
  "sections": {
    "patient_snapshot": {
      "title": "Resumen del Paciente",
      "content": "Paciente masculino, 45 anos. Ultima visita: 2026-02-15. Visitas totales: 12.",
      "data": {
        "age": 45,
        "gender": "male",
        "total_visits": 12,
        "last_visit_date": "2026-02-15",
        "patient_since": "2024-06-10"
      }
    },
    "today_context": {
      "title": "Contexto de la Cita de Hoy",
      "content": "Cita programada para endodoncia en diente 46. Considerar historia de tratamiento previo en ese diente.",
      "data": {
        "appointment_type": "endodontics",
        "scheduled_time": "2026-03-13T15:00:00Z",
        "doctor_name": "Dr. Martinez",
        "estimated_duration_minutes": 60,
        "related_teeth": ["46"]
      }
    },
    "active_conditions": {
      "title": "Condiciones Activas",
      "content": "3 diagnosticos activos. Caries en diente 46 (principal motivo de consulta hoy), gingivitis generalizada leve, bruxismo nocturno.",
      "items": [
        {
          "diagnosis": "Caries dentinaria profunda",
          "cie10_code": "K02.1",
          "tooth": "46",
          "severity": "high",
          "diagnosed_date": "2026-02-15",
          "relevant_to_today": true
        },
        {
          "diagnosis": "Gingivitis cronica generalizada",
          "cie10_code": "K05.1",
          "tooth": null,
          "severity": "low",
          "diagnosed_date": "2025-11-20",
          "relevant_to_today": false
        }
      ]
    },
    "risk_alerts": {
      "title": "Alertas de Riesgo",
      "content": "2 alertas requieren atencion antes de proceder.",
      "alerts": [
        {
          "type": "allergy",
          "severity": "critical",
          "message": "Alergia documentada a penicilina. Evitar amoxicilina como antibiotico post-operatorio.",
          "recommendation": "Usar clindamicina como alternativa."
        },
        {
          "type": "medication_interaction",
          "severity": "warning",
          "message": "Paciente toma warfarina (anticoagulante). Riesgo de sangrado aumentado.",
          "recommendation": "Verificar INR reciente antes del procedimiento. Considerar coordinacion con medico tratante."
        }
      ]
    },
    "pending_treatments": {
      "title": "Tratamientos Pendientes",
      "content": "3 items de tratamiento pendientes por un valor total de $450,000 COP.",
      "items": [
        {
          "procedure": "Endodoncia molar",
          "cups_code": "997330",
          "tooth": "46",
          "status": "pending",
          "estimated_cost_cents": 25000000,
          "planned_for_today": true
        },
        {
          "procedure": "Corona ceramica",
          "cups_code": "997520",
          "tooth": "46",
          "status": "pending",
          "estimated_cost_cents": 35000000,
          "planned_for_today": false
        }
      ],
      "total_pending_cost_cents": 60000000
    },
    "last_visit_summary": {
      "title": "Resumen Ultima Visita",
      "content": "El 15 de febrero se realizo examen clinico y radiografia periapical del diente 46. Se diagnostico caries profunda con compromiso pulpar. Se programo endodoncia.",
      "data": {
        "date": "2026-02-15",
        "procedures_performed": ["Examen clinico", "Radiografia periapical"],
        "notes_excerpt": "Caries profunda diente 46 con sintomatologia pulpar. Paciente refiere dolor espontaneo nocturno.",
        "doctor_name": "Dr. Martinez"
      }
    },
    "financial_status": {
      "title": "Estado Financiero",
      "content": "Saldo pendiente de $85,000 COP. Ultimo pago: 2026-02-15 por $120,000 COP.",
      "data": {
        "outstanding_balance_cents": 8500000,
        "last_payment_date": "2026-02-15",
        "last_payment_amount_cents": 12000000,
        "payment_history": "regular",
        "has_active_financing": false
      }
    },
    "action_suggestions": {
      "title": "Sugerencias de Accion",
      "content": "3 acciones sugeridas para esta cita.",
      "suggestions": [
        {
          "priority": "high",
          "action": "Verificar INR del paciente antes de iniciar la endodoncia por uso de warfarina.",
          "category": "safety"
        },
        {
          "priority": "medium",
          "action": "Discutir plan de corona post-endodoncia y costos con el paciente.",
          "category": "treatment_planning"
        },
        {
          "priority": "low",
          "action": "Paciente tiene saldo pendiente de $85,000. Considerar mencionarlo antes del procedimiento.",
          "category": "financial"
        }
      ]
    }
  }
}
```

### Pydantic Response Schema

```python
class RiskAlert(BaseModel):
    type: str  # allergy, medication_interaction, medical_condition, compliance
    severity: str  # critical, warning, info
    message: str
    recommendation: str

class ActiveConditionItem(BaseModel):
    diagnosis: str
    cie10_code: str | None
    tooth: str | None  # FDI notation
    severity: str  # critical, high, medium, low
    diagnosed_date: date
    relevant_to_today: bool

class PendingTreatmentItem(BaseModel):
    procedure: str
    cups_code: str | None
    tooth: str | None
    status: str
    estimated_cost_cents: int
    planned_for_today: bool

class ActionSuggestion(BaseModel):
    priority: str  # high, medium, low
    action: str
    category: str  # safety, treatment_planning, financial, follow_up, compliance

class PatientSnapshotData(BaseModel):
    age: int
    gender: str
    total_visits: int
    last_visit_date: date | None
    patient_since: date

class TodayContextData(BaseModel):
    appointment_type: str | None
    scheduled_time: datetime | None
    doctor_name: str | None
    estimated_duration_minutes: int | None
    related_teeth: list[str]

class LastVisitData(BaseModel):
    date: date
    procedures_performed: list[str]
    notes_excerpt: str
    doctor_name: str

class FinancialData(BaseModel):
    outstanding_balance_cents: int
    last_payment_date: date | None
    last_payment_amount_cents: int | None
    payment_history: str  # regular, irregular, delinquent, new
    has_active_financing: bool

class SummarySection(BaseModel):
    title: str
    content: str

class PatientSnapshotSection(SummarySection):
    data: PatientSnapshotData

class TodayContextSection(SummarySection):
    data: TodayContextData

class ActiveConditionsSection(SummarySection):
    items: list[ActiveConditionItem]

class RiskAlertsSection(SummarySection):
    alerts: list[RiskAlert]

class PendingTreatmentsSection(SummarySection):
    items: list[PendingTreatmentItem]
    total_pending_cost_cents: int

class LastVisitSection(SummarySection):
    data: LastVisitData

class FinancialSection(SummarySection):
    data: FinancialData

class ActionSuggestionsSection(SummarySection):
    suggestions: list[ActionSuggestion]

class ClinicalSummarySections(BaseModel):
    patient_snapshot: PatientSnapshotSection
    today_context: TodayContextSection | None  # null if no appointment_id
    active_conditions: ActiveConditionsSection
    risk_alerts: RiskAlertsSection
    pending_treatments: PendingTreatmentsSection
    last_visit_summary: LastVisitSection | None  # null if first visit
    financial_status: FinancialSection
    action_suggestions: ActionSuggestionsSection

class ClinicalSummaryResponse(BaseModel):
    patient_id: UUID
    appointment_id: UUID | None
    generated_at: datetime
    cached: bool
    cached_until: datetime | None
    model_used: str
    sections: ClinicalSummarySections
```

---

## Data Sources and Aggregation

The service runs up to 8 parallel async queries to build the data context for the prompt. All queries are tenant-scoped via `get_tenant_db`.

| # | Source | Table(s) | Data Extracted | Max Records |
|---|--------|----------|----------------|-------------|
| 1 | **Patient profile** | `patients` | Demographics, age, registration date, allergies, medical history | 1 |
| 2 | **Odontogram** | `odontogram_findings` | Active findings per tooth, last modified | All active |
| 3 | **Diagnoses** | `diagnoses` | Active diagnoses with CIE-10, severity, tooth | Last 20 active |
| 4 | **Treatment plans** | `treatment_plans`, `treatment_plan_items` | Pending/in-progress items, CUPS codes, costs | Last 3 active plans |
| 5 | **Evolution notes** | `evolution_notes` | Last 5 notes (date, summary, doctor, procedures) | Last 5 |
| 6 | **Appointments** | `appointments` | Today's appointment details, next upcoming, last 3 past | 5 total |
| 7 | **Billing** | `invoices`, `payments` | Outstanding balance, last payment, payment pattern | Aggregated |
| 8 | **Medications** | `prescriptions`, `medications` | Active medications, allergies | All active |
| 9 | **Lab orders** | `lab_orders` | Pending/recent lab results | Last 5 |

### Aggregation Service

```python
# backend/app/services/clinical_summary_service.py

async def aggregate_patient_data(
    db: AsyncSession,
    patient_id: UUID,
    appointment_id: UUID | None = None,
) -> ClinicalSummaryContext:
    """
    Runs all data source queries in parallel using asyncio.gather().
    Returns a structured context object ready for prompt injection.
    No PHI is logged during aggregation.
    """
    (
        patient,
        odontogram,
        diagnoses,
        treatment_plans,
        evolution_notes,
        appointments,
        billing,
        medications_and_allergies,
        lab_orders,
    ) = await asyncio.gather(
        _get_patient_profile(db, patient_id),
        _get_odontogram_findings(db, patient_id),
        _get_active_diagnoses(db, patient_id),
        _get_treatment_plans(db, patient_id),
        _get_recent_evolution_notes(db, patient_id),
        _get_appointments(db, patient_id, appointment_id),
        _get_billing_summary(db, patient_id),
        _get_medications_and_allergies(db, patient_id),
        _get_lab_orders(db, patient_id),
    )
    # ... build ClinicalSummaryContext
```

---

## Prompt Engineering

### Template Structure

The prompt uses a structured template with injected patient data. The AI generates the `content` (natural language) fields and `suggestions`/`alerts` based on the structured data provided.

```
SYSTEM:
You are a clinical decision support assistant for a dental clinic.
Your role is to generate a structured pre-appointment briefing for a dentist.

Rules:
- Respond ONLY in Spanish (es-419, Latin American Spanish).
- Use formal medical terminology appropriate for a dentist.
- Be concise — each section's "content" field should be 1-3 sentences.
- Flag any safety concerns (allergies, drug interactions, medical conditions) as risk_alerts.
- Suggest actionable items based on the patient data.
- Never invent data — only reference what is provided.
- If a section has no relevant data, still include it with an appropriate "no data" message.
- Output valid JSON matching the required schema exactly.

USER:
Generate a clinical summary for the following patient data.

## Patient Profile
- Age: {age}
- Gender: {gender}
- Patient since: {patient_since}
- Total visits: {total_visits}
- Last visit: {last_visit_date}
- Allergies: {allergies_list}
- Medical conditions: {medical_conditions_list}
- Current medications: {medications_list}

## Today's Appointment (if applicable)
- Type: {appointment_type}
- Scheduled: {scheduled_time}
- Doctor: {doctor_name}
- Duration: {estimated_duration} min
- Related teeth: {related_teeth}

## Active Diagnoses
{diagnoses_json}

## Odontogram Findings
{odontogram_json}

## Treatment Plans (pending items)
{treatment_plans_json}

## Recent Evolution Notes (last 5)
{evolution_notes_json}

## Financial Summary
- Outstanding balance: {outstanding_balance} COP
- Last payment: {last_payment_date} — {last_payment_amount} COP
- Payment pattern: {payment_pattern}

## Lab Orders
{lab_orders_json}

Respond with a JSON object matching this schema:
{output_schema_json}
```

### Data Anonymization for Prompt

Before injecting into the prompt:

- Patient name is **never** included — only age, gender, and visit history
- Document number (cedula) is **never** included
- Phone number and email are **never** included
- Financial amounts are converted from cents to display format for readability
- Doctor names are included (not PHI, they are staff)
- Tooth numbers use FDI notation
- Diagnosis/procedure descriptions are included (clinical, not identifying)

### Response Parsing

```python
raw_json = await ai_claude_client.call_claude(
    model="claude-haiku",
    system_prompt=SYSTEM_PROMPT,
    user_prompt=rendered_user_prompt,
    max_tokens=1500,
    temperature=0.2,  # low temperature for consistency
)
parsed = ai_claude_client.extract_json_object(raw_json)
validated = ClinicalSummarySections.model_validate(parsed)
```

If parsing fails, a fallback summary is generated from the raw data without AI:

```python
async def generate_fallback_summary(
    context: ClinicalSummaryContext,
) -> ClinicalSummarySections:
    """
    Deterministic fallback when AI call fails.
    Populates sections from raw data without natural language generation.
    The 'content' fields use simple template strings instead of AI prose.
    """
```

---

## Caching Strategy

### Redis Cache

| Aspect | Value |
|--------|-------|
| Key pattern | `dentalos:{tid}:ai:clinical_summary:{patient_id}` |
| TTL | 300 seconds (5 minutes) |
| Value format | JSON-serialized `ClinicalSummaryResponse` |
| Compression | None (typically < 5KB) |

### Cache Behavior

1. **Cache hit:** Return cached response with `cached: true` and `cached_until` set.
2. **Cache miss:** Generate summary, store in Redis, return with `cached: false`.
3. **`force_refresh=true`:** Skip cache read, regenerate, overwrite cache. Restricted to `clinic_owner`.
4. **Redis down:** Generate summary synchronously, return with `cached: false`, `cached_until: null`. Log warning (no PHI).

### Cache Key Design

The cache key does NOT include `appointment_id` intentionally. The summary is patient-centric and re-generated when patient data changes. If a different appointment is queried for the same patient within the TTL window, the cache is bypassed and a new context-aware summary is generated.

When `appointment_id` is provided and differs from the cached version's `appointment_id`, the cache is treated as a miss to ensure appointment-context accuracy.

---

## Database Table

### `clinical_summaries` (tenant schema)

Stores generated summaries for audit trail. Not used for serving (Redis is the fast path).

```sql
CREATE TABLE clinical_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id),
    appointment_id UUID REFERENCES appointments(id),
    summary JSONB NOT NULL,
    model_used VARCHAR(50) NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    generation_time_ms INTEGER NOT NULL,
    was_fallback BOOLEAN NOT NULL DEFAULT false,
    requested_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_clinical_summaries_patient_id ON clinical_summaries(patient_id);
CREATE INDEX idx_clinical_summaries_created_at ON clinical_summaries(created_at);
```

### `ai_usage_logs` (shared table, already defined in AI Strategy)

Each generation logs:

```sql
INSERT INTO ai_usage_logs (tenant_id, feature, model, input_tokens, output_tokens, cost_cents, created_at)
VALUES (:tid, 'clinical_summary', 'claude-haiku', :in_tok, :out_tok, :cost, now());
```

No PHI in this table — only feature name, model, token counts, cost.

---

## Error Codes

All errors follow the standard format: `{"error": "...", "message": "...", "details": {}}`.

| Error Code | HTTP | Condition |
|------------|------|-----------|
| `AI_CLINICAL_SUMMARY_patient_not_found` | 404 | Patient ID does not exist or is soft-deleted |
| `AI_CLINICAL_SUMMARY_appointment_not_found` | 404 | Appointment ID does not exist or does not belong to this patient |
| `AI_CLINICAL_SUMMARY_feature_disabled` | 403 | Feature flag `ai_clinical_summary` is not enabled for this tenant |
| `AI_CLINICAL_SUMMARY_plan_insufficient` | 403 | Tenant plan is below Pro (Free or Starter) |
| `AI_CLINICAL_SUMMARY_generation_failed` | 502 | Claude API call failed and fallback also failed |
| `AI_CLINICAL_SUMMARY_rate_limited` | 429 | User exceeded 30 requests/minute for this endpoint |
| `AI_CLINICAL_SUMMARY_insufficient_data` | 422 | Patient has no clinical data to summarize (brand new patient with zero records) |

### Error Response Examples

```json
{
  "error": "AI_CLINICAL_SUMMARY_feature_disabled",
  "message": "La funcion de resumen clinico con IA no esta habilitada para su clinica.",
  "details": {
    "feature_flag": "ai_clinical_summary",
    "upgrade_url": "/settings/plan"
  }
}
```

```json
{
  "error": "AI_CLINICAL_SUMMARY_plan_insufficient",
  "message": "El resumen clinico con IA requiere un plan Pro o superior.",
  "details": {
    "current_plan": "starter",
    "required_plan": "pro",
    "upgrade_url": "/settings/plan"
  }
}
```

---

## Security

### PHI Protection

| Rule | Implementation |
|------|---------------|
| No PHI in logs | Logger never logs patient name, cedula, phone, email, clinical content. Only logs: patient_id (UUID), model, tokens, latency. |
| No PHI in cache keys | Key uses only `{tid}` and `{patient_id}` (UUIDs), not names or document numbers. |
| No PHI in AI usage logs | `ai_usage_logs` stores only: tenant_id, feature, model, token counts, cost. |
| Prompt anonymization | Patient name, document number, phone, and email are stripped before prompt injection. Only age, gender, clinical data, and visit metadata are sent to Claude. |
| Cache value encryption | Summary cached as-is in Redis (tenant-isolated Redis namespace). Redis is in private network, not internet-exposed. |
| Audit logging | Every summary request logged to `audit_logs` with user_id, patient_id, action=`ai_clinical_summary_viewed`. |

### Access Control

```python
@router.get(
    "/patients/{patient_id}/clinical-summary",
    response_model=ClinicalSummaryResponse,
    tags=["ai", "patients"],
)
async def get_clinical_summary(
    patient_id: UUID,
    appointment_id: UUID | None = Query(None),
    force_refresh: bool = Query(False),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(resolve_tenant),
    db: AsyncSession = Depends(get_tenant_db),
) -> ClinicalSummaryResponse:
    """Generate or retrieve AI clinical summary for a patient."""
    require_role(current_user, ["clinic_owner", "doctor", "assistant"])
    require_feature(tenant, "ai_clinical_summary")
    require_plan(tenant, min_plan="pro")

    if force_refresh and current_user.role != "clinic_owner":
        raise ForbiddenError("AI_CLINICAL_SUMMARY_force_refresh_denied")

    return await clinical_summary_service.get_or_generate(
        db=db,
        tenant=tenant,
        patient_id=patient_id,
        appointment_id=appointment_id,
        force_refresh=force_refresh,
        requested_by=current_user.id,
    )
```

---

## Feature Flag Gating

### Check Order

1. **Feature flag:** `ai_clinical_summary` must be `true` in tenant's feature flags.
2. **Plan check:** Tenant must be on Pro, Clinica, or Enterprise plan. Free and Starter return 403.
3. **Role check:** User must be `clinic_owner`, `doctor`, or `assistant`.

### Feature Flag Definition

```json
{
  "ai_clinical_summary": {
    "category": "ai",
    "default": false,
    "description": "AI-generated pre-appointment clinical briefing",
    "min_plan": "pro",
    "add_on": null
  }
}
```

The flag is auto-enabled for Pro+ tenants. No separate add-on purchase required.

---

## Frontend Component Requirements

### Summary Panel Component

**Location:** `frontend/components/ai/clinical-summary-panel.tsx`

**Where it appears:**
1. **Patient detail page** — collapsible card in the right sidebar
2. **Appointment detail view** — expandable section above clinical notes
3. **Doctor's daily agenda** — quick-view popover per appointment row

### Component Behavior

| Aspect | Behavior |
|--------|----------|
| Loading state | Skeleton loader with 6 section placeholders |
| Error state | Inline error banner with retry button. If plan insufficient, show upgrade CTA. |
| Empty state | Message: "No hay datos clinicos suficientes para generar un resumen." |
| Refresh | Manual refresh button (circular arrow icon). Calls with `force_refresh=true` if user is clinic_owner, otherwise normal re-fetch. |
| Sections | Collapsible accordion — `risk_alerts` and `today_context` expanded by default, others collapsed |
| Risk alerts | Color-coded badges: critical=red, warning=amber, info=blue |
| Action suggestions | Rendered as a checklist with priority indicators (high=red dot, medium=amber, low=gray) |
| Financial | Only visible to `clinic_owner` and `doctor` (assistant should not see financial details) |
| Timestamp | "Generado hace X minutos" relative time display |
| AI disclaimer | Footer: "Generado por IA. El juicio clinico del profesional prevalece." |

### React Query Hook

```typescript
// frontend/lib/hooks/use-clinical-summary.ts

export function useClinicalSummary(
  patientId: string,
  appointmentId?: string,
) {
  return useQuery({
    queryKey: ["clinical-summary", patientId, appointmentId],
    queryFn: () => apiClient.get(
      `/patients/${patientId}/clinical-summary`,
      { params: { appointment_id: appointmentId } },
    ),
    staleTime: 5 * 60 * 1000, // 5 min — matches backend cache TTL
    enabled: !!patientId,
    retry: 1,
  });
}
```

### Zod Validation Schema

```typescript
// frontend/lib/validations/clinical-summary.ts

import { z } from "zod";

export const riskAlertSchema = z.object({
  type: z.string(),
  severity: z.enum(["critical", "warning", "info"]),
  message: z.string(),
  recommendation: z.string(),
});

export const clinicalSummaryResponseSchema = z.object({
  patient_id: z.string().uuid(),
  appointment_id: z.string().uuid().nullable(),
  generated_at: z.string().datetime(),
  cached: z.boolean(),
  cached_until: z.string().datetime().nullable(),
  model_used: z.string(),
  sections: z.object({
    patient_snapshot: z.object({
      title: z.string(),
      content: z.string(),
      data: z.object({
        age: z.number(),
        gender: z.string(),
        total_visits: z.number(),
        last_visit_date: z.string().nullable(),
        patient_since: z.string(),
      }),
    }),
    today_context: z.object({
      title: z.string(),
      content: z.string(),
      data: z.object({
        appointment_type: z.string().nullable(),
        scheduled_time: z.string().datetime().nullable(),
        doctor_name: z.string().nullable(),
        estimated_duration_minutes: z.number().nullable(),
        related_teeth: z.array(z.string()),
      }),
    }).nullable(),
    active_conditions: z.object({
      title: z.string(),
      content: z.string(),
      items: z.array(z.object({
        diagnosis: z.string(),
        cie10_code: z.string().nullable(),
        tooth: z.string().nullable(),
        severity: z.enum(["critical", "high", "medium", "low"]),
        diagnosed_date: z.string(),
        relevant_to_today: z.boolean(),
      })),
    }),
    risk_alerts: z.object({
      title: z.string(),
      content: z.string(),
      alerts: z.array(riskAlertSchema),
    }),
    pending_treatments: z.object({
      title: z.string(),
      content: z.string(),
      items: z.array(z.object({
        procedure: z.string(),
        cups_code: z.string().nullable(),
        tooth: z.string().nullable(),
        status: z.string(),
        estimated_cost_cents: z.number(),
        planned_for_today: z.boolean(),
      })),
      total_pending_cost_cents: z.number(),
    }),
    last_visit_summary: z.object({
      title: z.string(),
      content: z.string(),
      data: z.object({
        date: z.string(),
        procedures_performed: z.array(z.string()),
        notes_excerpt: z.string(),
        doctor_name: z.string(),
      }),
    }).nullable(),
    financial_status: z.object({
      title: z.string(),
      content: z.string(),
      data: z.object({
        outstanding_balance_cents: z.number(),
        last_payment_date: z.string().nullable(),
        last_payment_amount_cents: z.number().nullable(),
        payment_history: z.enum(["regular", "irregular", "delinquent", "new"]),
        has_active_financing: z.boolean(),
      }),
    }),
    action_suggestions: z.object({
      title: z.string(),
      content: z.string(),
      suggestions: z.array(z.object({
        priority: z.enum(["high", "medium", "low"]),
        action: z.string(),
        category: z.enum(["safety", "treatment_planning", "financial", "follow_up", "compliance"]),
      })),
    }),
  }),
});
```

---

## Test Plan

### Backend Unit Tests

| # | Test Case | Expected |
|---|-----------|----------|
| 1 | Valid request with `appointment_id` | 200, summary with `today_context` populated |
| 2 | Valid request without `appointment_id` | 200, `today_context` is null, `appointment_id` is null |
| 3 | Cache hit | 200, `cached: true`, no Claude API call made |
| 4 | Cache miss | 200, `cached: false`, Claude API called, result stored in Redis |
| 5 | `force_refresh=true` by clinic_owner | 200, cache bypassed, new summary generated |
| 6 | `force_refresh=true` by doctor | 403, only clinic_owner can force refresh |
| 7 | Patient not found | 404, `AI_CLINICAL_SUMMARY_patient_not_found` |
| 8 | Appointment not found | 404, `AI_CLINICAL_SUMMARY_appointment_not_found` |
| 9 | Appointment belongs to different patient | 404, `AI_CLINICAL_SUMMARY_appointment_not_found` |
| 10 | Feature flag disabled | 403, `AI_CLINICAL_SUMMARY_feature_disabled` |
| 11 | Plan is Starter | 403, `AI_CLINICAL_SUMMARY_plan_insufficient` |
| 12 | Plan is Free | 403, `AI_CLINICAL_SUMMARY_plan_insufficient` |
| 13 | Plan is Pro | 200, summary generated |
| 14 | Receptionist role | 403, insufficient role |
| 15 | Patient role | 403, insufficient role |
| 16 | Claude API fails → fallback | 200, `was_fallback: true` in DB, summary has template content |
| 17 | Claude returns invalid JSON → fallback | 200, fallback summary generated |
| 18 | Brand new patient (no records) | 422, `AI_CLINICAL_SUMMARY_insufficient_data` |
| 19 | Patient with allergies | 200, `risk_alerts` includes allergy alerts |
| 20 | Patient on anticoagulants with surgery scheduled | 200, `risk_alerts` includes medication interaction warning |
| 21 | Rate limit exceeded | 429, `AI_CLINICAL_SUMMARY_rate_limited` |
| 22 | Redis down — graceful degradation | 200, summary generated without cache, no error |
| 23 | Cache invalidation on new diagnosis | Cache key deleted after diagnosis creation |
| 24 | Cache invalidation on payment | Cache key deleted after payment recorded |
| 25 | Soft-deleted patient | 404, `AI_CLINICAL_SUMMARY_patient_not_found` |

### Backend Integration Tests

| # | Test Case | Expected |
|---|-----------|----------|
| 1 | Full flow: create patient + data + request summary | 200, all sections populated |
| 2 | Multi-tenant isolation | Summary only includes data from requesting tenant |
| 3 | Concurrent requests for same patient | Only one Claude call, second request gets cached result |
| 4 | AI usage log created | `ai_usage_logs` row exists with correct feature and token counts |
| 5 | Audit log created | `audit_logs` row exists with `ai_clinical_summary_viewed` action |

### Frontend Tests

| # | Test Case | Expected |
|---|-----------|----------|
| 1 | Panel renders with loading skeleton | Skeleton visible while fetching |
| 2 | Panel renders all sections | All 8 sections visible with correct titles |
| 3 | Risk alerts color coding | Critical=red badge, warning=amber, info=blue |
| 4 | Accordion expand/collapse | Click toggles section visibility |
| 5 | Error state with retry | Error banner shown, retry button re-fetches |
| 6 | Plan upgrade CTA | Shown when 403 plan_insufficient error received |
| 7 | Financial section hidden for assistant | `financial_status` section not rendered for assistant role |
| 8 | AI disclaimer visible | Footer disclaimer always visible |
| 9 | Relative timestamp | "Generado hace X minutos" updates correctly |
| 10 | Empty state | Appropriate message when 422 insufficient_data returned |

---

## Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `backend/app/services/clinical_summary_service.py` | Business logic: aggregation, prompt building, caching, fallback |
| `backend/app/api/v1/ai/clinical_summary.py` | Route handler |
| `backend/app/schemas/ai/clinical_summary.py` | Pydantic request/response schemas |
| `backend/tests/unit/test_clinical_summary_service.py` | Unit tests |
| `backend/tests/integration/test_clinical_summary_api.py` | Integration tests |
| `frontend/components/ai/clinical-summary-panel.tsx` | Summary panel component |
| `frontend/lib/hooks/use-clinical-summary.ts` | React Query hook |
| `frontend/lib/validations/clinical-summary.ts` | Zod schema |
| `alembic_tenant/versions/016_add_clinical_summaries.py` | Migration for `clinical_summaries` table |

### Modified Files

| File | Change |
|------|--------|
| `backend/app/api/v1/__init__.py` | Register AI clinical summary router |
| `backend/app/services/diagnosis_service.py` | Add cache invalidation call |
| `backend/app/services/evolution_note_service.py` | Add cache invalidation call |
| `backend/app/services/treatment_plan_service.py` | Add cache invalidation call |
| `backend/app/services/invoice_service.py` | Add cache invalidation call |
| `backend/app/services/appointment_service.py` | Add cache invalidation call |
| `backend/app/services/odontogram_service.py` | Add cache invalidation call |
| `backend/app/services/medication_service.py` | Add cache invalidation call |
| `backend/app/services/lab_order_service.py` | Add cache invalidation call |
| `frontend/app/(dashboard)/patients/[id]/page.tsx` | Add summary panel to sidebar |
| `frontend/app/(dashboard)/appointments/[id]/page.tsx` | Add summary section |

---

## Performance Considerations

| Metric | Target | Notes |
|--------|--------|-------|
| Cache hit latency | < 50ms | Redis GET + JSON deserialize |
| Cache miss latency | < 3s | DB queries (~200ms) + Claude Haiku (~2s) + cache write (~10ms) |
| Data aggregation | < 300ms | 8 parallel async queries |
| Claude Haiku call | < 2s | ~3K input, ~500 output tokens |
| Payload size | < 5KB | Typical summary JSON |
| Cache hit rate | > 70% | Expected during appointment hours |

### Optimization Notes

- Use `asyncio.gather()` for parallel data source queries — do not query sequentially.
- Claude Haiku selected over Sonnet for speed (sub-2s). Quality is sufficient for structured summaries.
- Temperature set to 0.2 for consistent, reproducible outputs.
- Max tokens capped at 1500 to prevent runaway generation.
- If the patient has extensive history (>20 diagnoses, >50 evolution notes), truncate to most recent/relevant to stay within token budget.
