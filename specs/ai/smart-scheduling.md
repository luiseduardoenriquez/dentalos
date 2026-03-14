# AI Smart Scheduling — Spec (AI-10)

> **Spec ID:** AI-10
> **Status:** Draft
> **Last Updated:** 2026-03-14
> **Feature Flag:** `ai_smart_schedule`
> **Plan:** Clinica+ ($69/location/mo and above)
> **Sprint:** S39-40 (Tier 3 — Leapfrog)
> **Priority:** Medium

---

## 1. Overview

**Feature:** A **Schedule Advisor** panel appears alongside the appointment creation form. It suggests optimal time slots based on procedure type, doctor preferences, patient no-show history, slot revenue value, and learned procedure duration patterns. The doctor/receptionist can accept a suggestion with one click or ignore it entirely — the advisor never blocks the manual scheduling flow.

**Core value:** Fills high-value slots first, reduces no-show-caused idle time, and matches appointment duration to procedure reality (not just the default 30-minute blocks).

**Not Claude-based.** Uses a scoring function over available slots with learned weights. No external API calls.

### Key Recommendations

1. **Best time for this procedure** — slots where this procedure type has historically been completed without running over.
2. **Group similar procedures** — if patient has multiple pending treatment plan items, suggest batching.
3. **High-risk no-show avoidance** — for patients with `noshow_risk: "high"` (AI-09), avoid prime morning slots on Mondays and avoid long-duration procedures.
4. **Buffer time** — automatically adds learned buffer after complex procedures (e.g., surgical extractions always need 15 min extra).

### Dependencies

- `specs/appointments/appointments-api.md` — Appointment model
- `specs/ai/patient-risk-score.md` (AI-09) — No-show risk score
- `backend/app/models/tenant/appointment.py`
- `backend/app/models/tenant/treatment_plan.py`

---

## 2. Algorithm Design

### 2.1 Candidate Slot Generation

1. Fetch all available slots for the requested doctor and date range (reuses existing `appointment_slots` logic).
2. Filter by minimum duration (based on procedure type default + learned buffer).
3. Score each candidate slot (see 2.2).
4. Return top 3 recommendations, sorted by score descending.

### 2.2 Slot Scoring Function

```
score(slot) = w1 * revenue_score
            + w2 * completion_score
            + w3 * noshow_penalty
            + w4 * grouping_bonus
            + w5 * preference_score
```

| Component | Description | Default weight |
|-----------|-------------|----------------|
| `revenue_score` | How revenue-optimal is this time? (Morning premium = higher) | 0.25 |
| `completion_score` | How often does this procedure type finish on time in this slot? | 0.30 |
| `noshow_penalty` | Penalty if patient has high no-show risk and slot is prime-time | 0.20 |
| `grouping_bonus` | Bonus if adjacent slot enables batching pending treatment items | 0.15 |
| `preference_score` | Doctor's stated preferences (from `doctor_scheduling_preferences`) | 0.10 |

Weights are configurable per clinic via `clinic_settings.ai_scheduling_weights` JSONB field.

### 2.3 Learned Duration

After each completed appointment, the system records actual duration:

```
actual_duration_min = appointment.ended_at - appointment.started_at
```

Stored in `appointment_duration_samples`. Used to compute:

```python
learned_duration[procedure_code] = percentile(actual_durations, 75)
# 75th percentile = enough buffer for most cases
```

Updated nightly. Falls back to procedure catalog default if < 5 samples.

### 2.4 No-Show Avoidance

If `patient.risk_score.noshow_risk == "high"`:
- Avoid Monday 08:00–10:00 (highest no-show window, historically)
- Prefer afternoon slots where no-show rates are lower for this risk profile
- Cap procedure duration at 60 min (long procedures with no-shows create large idle gaps)
- This heuristic is computed from the clinic's own appointment history.

---

## 3. Data Sources

| Data | Source Table | Freshness |
|------|-------------|-----------|
| Available slots | `appointments` (gaps) + `doctor_schedules` | Real-time |
| Procedure duration history | `appointment_duration_samples` | Nightly |
| No-show risk | `patient_risk_scores` | Event-driven (AI-09) |
| Pending treatment items | `treatment_plan_items` | Real-time |
| Doctor preferences | `doctor_scheduling_preferences` | On change |
| Revenue per slot | `invoices` joined to `appointments` | Nightly aggregate |

---

## 4. Database Schema

### Table: `appointment_duration_samples` (tenant schema `tn_*`)

```sql
CREATE TABLE appointment_duration_samples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    appointment_id  UUID NOT NULL REFERENCES appointments(id),
    doctor_id       UUID NOT NULL REFERENCES users(id),
    procedure_code  VARCHAR(10) NOT NULL,   -- CUPS code
    procedure_type  VARCHAR(30) NOT NULL,   -- 'preventive', 'restorative', etc.
    scheduled_min   INTEGER NOT NULL,        -- What was booked
    actual_min      INTEGER NOT NULL,        -- What actually happened
    day_of_week     SMALLINT NOT NULL,       -- 0=Monday … 6=Sunday
    hour_of_day     SMALLINT NOT NULL,       -- 0-23

    is_active  BOOLEAN NOT NULL DEFAULT true,
    deleted_at TIMESTAMPTZ DEFAULT NULL
);

CREATE INDEX idx_appt_duration_samples_procedure ON appointment_duration_samples(procedure_code);
CREATE INDEX idx_appt_duration_samples_doctor    ON appointment_duration_samples(doctor_id);
```

### Table: `doctor_scheduling_preferences` (tenant schema `tn_*`)

```sql
CREATE TABLE doctor_scheduling_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    doctor_id UUID NOT NULL REFERENCES users(id),

    -- Time preferences
    preferred_start_hour   SMALLINT DEFAULT 8,     -- Prefer not to book before this hour
    preferred_end_hour     SMALLINT DEFAULT 17,    -- Prefer not to book after this hour
    preferred_lunch_start  SMALLINT DEFAULT 12,
    preferred_lunch_end    SMALLINT DEFAULT 13,
    buffer_after_surgical  INTEGER DEFAULT 15,     -- Extra minutes after surgical procedures
    buffer_after_long      INTEGER DEFAULT 10,     -- Extra after procedures > 60 min

    -- Procedure grouping
    allow_grouping         BOOLEAN DEFAULT true,
    max_procedures_per_day INTEGER DEFAULT 12,

    -- Day preferences (JSONB): {"monday": 0.8, "tuesday": 1.0, ...}
    day_weights JSONB DEFAULT '{}'::jsonb,

    UNIQUE (doctor_id),

    is_active  BOOLEAN NOT NULL DEFAULT true,
    deleted_at TIMESTAMPTZ DEFAULT NULL
);
```

---

## 5. API Endpoints

### POST `/api/v1/appointments/schedule-suggestions`

Returns ranked slot recommendations for a new appointment.

**Auth:** `doctor`, `receptionist`, `clinic_owner`
**Feature gate:** `ai_smart_schedule`

**Request body:**

```json
{
  "patient_id": "uuid",
  "doctor_id": "uuid",
  "procedure_codes": ["890301", "890302"],
  "date_range_start": "2026-03-18",
  "date_range_end": "2026-03-25",
  "duration_override_min": null
}
```

**Response `200`:**

```json
{
  "suggestions": [
    {
      "rank": 1,
      "score": 0.87,
      "start_at": "2026-03-18T14:00:00-05:00",
      "end_at": "2026-03-18T15:00:00-05:00",
      "duration_min": 60,
      "reasons": [
        "Alta tasa de finalización para este procedimiento en la tarde",
        "Puede agrupar con limpieza pendiente del plan de tratamiento"
      ],
      "warnings": [],
      "grouping_suggestion": {
        "treatment_plan_item_id": "uuid",
        "procedure_name": "Detartraje supragingival",
        "additional_min": 20
      }
    },
    {
      "rank": 2,
      "score": 0.74,
      "start_at": "2026-03-20T09:00:00-05:00",
      "end_at": "2026-03-20T10:00:00-05:00",
      "duration_min": 60,
      "reasons": ["Slot de alta rentabilidad en la mañana"],
      "warnings": ["Paciente con historial de inasistencia en horario matutino"]
    }
  ],
  "learned_duration_min": 55,
  "noshow_risk_level": "medium",
  "total_slots_evaluated": 28
}
```

**Response `404`:** Doctor or patient not found.
**Response `422`:** Invalid date range (> 60 days).

---

### GET `/api/v1/appointments/scheduling-stats`

Aggregate stats for the Schedule Advisor dashboard widget.

**Auth:** `clinic_owner`, `doctor`

**Response `200`:**

```json
{
  "avg_slot_utilization_pct": 78,
  "noshow_rate_30d": 0.14,
  "avg_duration_accuracy_pct": 82,
  "prime_slot_waste_pct": 9
}
```

---

## 6. Frontend

**Component:** `ScheduleAdvisorPanel`

**Location:** `frontend/components/appointments/schedule-advisor-panel.tsx`

### Layout

The advisor panel appears as a collapsible sidebar next to the appointment creation form:

```
┌────────────────────────────────────────────┐
│  💡 Sugerencias del asistente              │
│  ─────────────────────────────             │
│  1. Mar 18, 14:00–15:00    ⭐ Mejor opción │
│     ✓ Alta tasa de finalización            │
│     ✓ Puede agrupar con detartraje         │
│     [Seleccionar este horario]             │
│                                            │
│  2. Mié 20, 09:00–10:00                    │
│     ✓ Slot de alta rentabilidad            │
│     ⚠ Historial de inasistencia matutina   │
│     [Seleccionar]                          │
│                                            │
│  3. Jue 21, 11:00–12:00                    │
│     ✓ Sin conflictos                       │
│     [Seleccionar]                          │
└────────────────────────────────────────────┘
```

- Clicking "Seleccionar" pre-fills the appointment date/time fields but does NOT submit.
- Receptionist/doctor still confirms manually.
- Panel is hidden if feature flag is off — no empty state shown.

### Hook

```typescript
// frontend/lib/hooks/use-schedule-suggestions.ts
function useScheduleSuggestions(params: ScheduleSuggestionParams): {
  suggestions: ScheduleSuggestion[];
  isLoading: boolean;
  error: Error | null;
}
```

---

## 7. Integration with Appointment Module

- On appointment `status → completed`: record duration sample to `appointment_duration_samples`.
- On appointment `status → no_show`: update patient no-show counters used by AI-09.
- Nightly `maintenance` worker job: `recalculate_duration_percentiles` — updates learned durations per procedure code.
- Suggestions are **advisory only** — the existing appointment booking flow is unchanged. Scheduling still enforces hard constraints (doctor availability, overlaps, working hours) independently of the advisor.

---

## 8. Test Plan

| # | Scenario | Expected |
|---|----------|----------|
| T1 | Request suggestions for known procedure | Returns ≤ 3 ranked suggestions |
| T2 | Patient with `noshow_risk: "high"` | Warning shown for prime morning slots |
| T3 | Patient has pending treatment plan items | `grouping_suggestion` populated in rank 1 |
| T4 | No available slots in date range | Empty `suggestions` array, informative message |
| T5 | Duration samples < 5 for procedure | Falls back to catalog default duration |
| T6 | Feature flag disabled | Returns 403 |
| T7 | Date range > 60 days | Returns 422 |
| T8 | Appointment completed → duration sample recorded | Row in `appointment_duration_samples` |
| T9 | Nightly recalculation runs | `learned_duration` updates for procedure |
| T10 | Doctor has stated preference hours | Suggestions respect preferred_start/end_hour |
