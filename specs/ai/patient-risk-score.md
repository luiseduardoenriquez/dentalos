# AI Patient Risk Score — Spec (AI-09)

> **Spec ID:** AI-09
> **Status:** Draft
> **Last Updated:** 2026-03-14
> **Feature Flag:** `ai_risk_score`
> **Plan:** Pro+ ($39/doctor/mo and above)
> **Sprint:** S37-38 (Tier 3 — Leapfrog)
> **Priority:** Medium

---

## 1. Overview

**Feature:** Every patient gets a composite risk score automatically maintained by the system. The score has four dimensions: **caries risk**, **periodontal risk**, **no-show risk**, and **payment risk**. Each dimension is a color-coded badge visible on the patient card, patient list, and appointment scheduler.

Clinicians use these badges to:
- Prioritize recall scheduling (high-risk patients flagged first)
- Plan preventive interventions before conditions worsen
- Identify patients likely to miss appointments (scheduling optimization)
- Flag accounts that may need payment plan discussions

**This is NOT Claude-based.** The scoring uses rule-based heuristics combined with weighted scoring, updated after each relevant event (visit, payment, appointment outcome).

**Displayed to:** `doctor`, `assistant`, `receptionist`, `clinic_owner`. Never shown in patient portal.

---

## 2. Scoring Algorithm

### 2.1 Caries Risk

| Factor | Weight | Low | Medium | High |
|--------|--------|-----|--------|------|
| Active caries count (current) | 30% | 0 | 1–2 | ≥ 3 |
| Restorations in last 12 months | 20% | 0 | 1–2 | ≥ 3 |
| Last professional cleaning | 20% | < 6 mo | 6–18 mo | > 18 mo |
| Radiographic caries (AI-01 findings) | 15% | 0 | 1 | ≥ 2 |
| Patient age bracket | 15% | 18–45 | < 18 or 45–65 | > 65 |

### 2.2 Periodontal Risk

| Factor | Weight | Low | Medium | High |
|--------|--------|-----|--------|------|
| Avg probing depth (latest perio record) | 35% | ≤ 3 mm | 3–5 mm | > 5 mm |
| Bleeding on probing % | 25% | < 10% | 10–30% | > 30% |
| Bone loss (radiographic) | 20% | None | Mild | Moderate/Severe |
| Systemic risk factors (diabetes, smoker) | 20% | None | 1 factor | ≥ 2 factors |

Systemic factors sourced from `patient_conditions` and `patient_intake_forms.medical_history` JSONB fields.

### 2.3 No-Show Risk

| Factor | Weight | Low | Medium | High |
|--------|--------|-----|--------|------|
| No-show rate (last 12 months) | 40% | < 10% | 10–30% | > 30% |
| Last-minute cancellations | 20% | 0 | 1–2 | ≥ 3 |
| Days since last kept appointment | 25% | < 90 | 90–270 | > 270 |
| Appointment confirmation response | 15% | Always | Sometimes | Never |

### 2.4 Payment Risk

| Factor | Weight | Low | Medium | High |
|--------|--------|-----|--------|------|
| Outstanding balance | 35% | $0 | < $200k COP | ≥ $200k COP |
| Late payment rate (last 12 months) | 30% | < 10% | 10–30% | > 30% |
| Payment plan defaults | 20% | 0 | 1 | ≥ 2 |
| Has active insurance/EPS | 15% | Yes | — | No |

### 2.5 Composite Score

Each dimension outputs: `low` (1) | `medium` (2) | `high` (3).

Composite overall risk = max of all four dimensions. Stored separately so each dimension badge is independent.

---

## 3. Risk Categories

| Level | Color | Badge text | Action |
|-------|-------|------------|--------|
| `low` | Green | Bajo riesgo | Routine recall |
| `medium` | Amber | Riesgo moderado | Priority recall within 30 days |
| `high` | Red | Alto riesgo | Immediate follow-up recommended |

---

## 4. Database Schema

### Table: `patient_risk_scores` (tenant schema `tn_*`)

```sql
CREATE TABLE patient_risk_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    patient_id UUID NOT NULL REFERENCES patients(id),

    -- Per-dimension risk levels
    caries_risk      VARCHAR(10) NOT NULL DEFAULT 'low'
                     CHECK (caries_risk IN ('low', 'medium', 'high')),
    periodontal_risk VARCHAR(10) NOT NULL DEFAULT 'low'
                     CHECK (periodontal_risk IN ('low', 'medium', 'high')),
    noshow_risk      VARCHAR(10) NOT NULL DEFAULT 'low'
                     CHECK (noshow_risk IN ('low', 'medium', 'high')),
    payment_risk     VARCHAR(10) NOT NULL DEFAULT 'low'
                     CHECK (payment_risk IN ('low', 'medium', 'high')),

    -- Composite
    overall_risk     VARCHAR(10) NOT NULL DEFAULT 'low'
                     CHECK (overall_risk IN ('low', 'medium', 'high')),

    -- Factor snapshot (for UI tooltips and audit)
    caries_factors      JSONB NOT NULL DEFAULT '{}'::jsonb,
    periodontal_factors JSONB NOT NULL DEFAULT '{}'::jsonb,
    noshow_factors      JSONB NOT NULL DEFAULT '{}'::jsonb,
    payment_factors     JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- When was this score computed
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- What event triggered recomputation
    trigger_event   VARCHAR(50) DEFAULT NULL,
    -- 'appointment_completed', 'invoice_paid', 'invoice_overdue',
    -- 'perio_record_created', 'radiograph_reviewed', 'manual_refresh'

    -- Soft delete
    is_active  BOOLEAN NOT NULL DEFAULT true,
    deleted_at TIMESTAMPTZ DEFAULT NULL,

    -- Only one active score per patient
    CONSTRAINT uq_patient_risk_score_patient UNIQUE (patient_id, is_active)
);

CREATE INDEX idx_patient_risk_scores_patient     ON patient_risk_scores(patient_id);
CREATE INDEX idx_patient_risk_scores_overall     ON patient_risk_scores(overall_risk);
CREATE INDEX idx_patient_risk_scores_noshow      ON patient_risk_scores(noshow_risk);
CREATE INDEX idx_patient_risk_scores_payment     ON patient_risk_scores(payment_risk);
```

**`caries_factors` JSONB structure (example):**

```json
{
  "active_caries_count": 2,
  "restorations_12mo": 1,
  "last_cleaning_days": 210,
  "radiograph_caries": 1,
  "age_bracket": "adult"
}
```

---

## 5. Score Computation Service

**File:** `backend/app/services/patient_risk_score_service.py`

```python
async def compute_patient_risk(
    patient_id: UUID,
    db: AsyncSession,
    trigger_event: str = "manual_refresh"
) -> PatientRiskScore:
    """Compute all four risk dimensions and upsert patient_risk_scores."""
```

### Trigger Events (automatic recomputation)

| Event | Risk dimensions recomputed |
|-------|---------------------------|
| Appointment marked `completed` | no_show_risk, caries_risk |
| Appointment marked `no_show` | no_show_risk |
| Invoice paid | payment_risk |
| Invoice overdue (> 30 days) | payment_risk |
| Periodontal record created | periodontal_risk |
| AI-01 radiograph review completed | caries_risk, periodontal_risk |
| Patient intake form updated | periodontal_risk, caries_risk |

Triggers implemented as post-commit hooks in the relevant service files (not database triggers — stays in application layer for tenant isolation).

### Caching

Redis key: `dentalos:{tid}:clinical:risk_score:{patient_id}` — TTL: **10 minutes**.

Invalidated on any trigger event for that patient.

---

## 6. API Endpoints

### GET `/api/v1/patients/{id}/risk-score`

Returns current risk score for a patient.

**Auth:** `doctor`, `assistant`, `receptionist`, `clinic_owner`
**Feature gate:** `ai_risk_score`

**Response `200`:**

```json
{
  "patient_id": "uuid",
  "overall_risk": "medium",
  "dimensions": {
    "caries":      {"level": "high",   "factors": {"active_caries_count": 2, "last_cleaning_days": 210}},
    "periodontal": {"level": "low",    "factors": {"avg_probing_depth_mm": 2.8, "bleeding_pct": 8}},
    "no_show":     {"level": "medium", "factors": {"noshow_rate_12mo": 0.22, "last_kept_appt_days": 180}},
    "payment":     {"level": "low",    "factors": {"outstanding_balance_cop": 0, "late_rate_12mo": 0.05}}
  },
  "computed_at": "2026-03-14T08:00:00Z",
  "trigger_event": "appointment_completed"
}
```

**Response `404`:** Patient not found.
**Response `403`:** Feature flag not active or insufficient role.

---

### POST `/api/v1/patients/{id}/risk-score/refresh`

Forces immediate recomputation (bypasses cache).

**Auth:** `doctor`, `clinic_owner`
**Rate limit:** 10 requests per patient per hour.

**Response `200`:** Returns fresh score (same schema as GET).

---

### GET `/api/v1/patients/risk-score/summary`

Returns aggregate counts by risk level — for dashboard widget.

**Auth:** `clinic_owner`, `doctor`

**Query params:** `?risk_type=overall|caries|periodontal|noshow|payment`

**Response `200`:**

```json
{
  "risk_type": "overall",
  "low": 142,
  "medium": 38,
  "high": 12,
  "total": 192,
  "computed_at": "2026-03-14T08:00:00Z"
}
```

---

## 7. Frontend

**Component:** `PatientRiskBadges`

**Location:** `frontend/components/patients/patient-risk-badges.tsx`

### Badge Display

```
┌──────────────────────────────────────────────┐
│  [🟢 Caries: Bajo] [🟡 Perio: Mod] [🔴 Inasistencia: Alto] [🟢 Pago: Bajo]  │
└──────────────────────────────────────────────┘
```

Hover/click on any badge opens a tooltip with the contributing factors:

```
Riesgo de inasistencia: ALTO
• Tasa de inasistencia (12 meses): 22%
• Último turno cumplido: hace 180 días
• Cancelaciones de último momento: 2
```

### Locations Shown

1. **Patient card** (top of patient profile): all 4 dimension badges
2. **Patient list table**: compact overall risk badge only
3. **Appointment scheduler** (patient selector): overall + no-show badge
4. **Recalls list** (`/appointments/recalls`): all 4 badges with sort by overall risk

### Hook

```typescript
// frontend/lib/hooks/use-patient-risk-score.ts
function usePatientRiskScore(patientId: string): {
  riskScore: PatientRiskScore | null;
  isLoading: boolean;
  refresh: () => Promise<void>;
}
```

---

## 8. Test Plan

| # | Scenario | Expected |
|---|----------|----------|
| T1 | Patient with 3 active caries, no recent cleaning | `caries_risk: "high"` |
| T2 | Patient with 25% no-show rate in 12 months | `noshow_risk: "medium"` |
| T3 | Patient with $250k COP outstanding balance | `payment_risk: "high"` |
| T4 | Patient with avg probing depth 6mm | `periodontal_risk: "high"` |
| T5 | All dimensions low | `overall_risk: "low"` |
| T6 | One dimension high, rest low | `overall_risk: "high"` |
| T7 | Appointment marked no-show → trigger event | Score recomputed, cache invalidated |
| T8 | Invoice paid → trigger event | `payment_risk` recomputed |
| T9 | Feature flag disabled | GET returns 403 |
| T10 | Redis cache hit | Score served from cache, no DB query |
| T11 | Force refresh clears cache | Fresh DB computation returned |
| T12 | Portal user calls endpoint | Returns 403 |
