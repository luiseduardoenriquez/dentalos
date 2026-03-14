# AI Treatment Acceptance Predictor — Spec (AI-08)

> **Spec ID:** AI-08
> **Status:** Draft
> **Last Updated:** 2026-03-14
> **Feature Flag:** `ai_acceptance`
> **Plan:** Clinica+ ($69/location/mo and above)
> **Sprint:** S37-38 (Tier 3 — Leapfrog)
> **Priority:** Medium-High

---

## 1. Overview

**Feature:** When a doctor or receptionist opens a treatment plan quotation, the system displays a predicted probability (0–100%) that the patient will accept and start the treatment. This helps the clinic prioritize follow-ups, tailor payment plan offers, and identify patients who need extra counseling.

**This is NOT Claude-based.** It uses a per-clinic logistic regression model trained on the clinic's own historical quotation and acceptance data. No PHI leaves the server. No external API calls.

**Key properties:**
- Score updates on every new quotation (incremental retraining on a nightly job)
- Cold start: model falls back to global defaults when a clinic has fewer than 50 accepted/rejected quotations
- Displayed as a badge on the quotation detail screen and the quotation list
- Confidence level (`low` / `medium` / `high`) shown alongside the score to prevent over-reliance

**Regulatory disclaimer:**
> "Esta predicción es orientativa. No reemplaza el criterio clínico."

### Dependencies

- `specs/billing/quotations.md` — Quotation model
- `specs/patients/patients-api.md` — Patient payment history
- `backend/app/models/tenant/quotation.py`
- `backend/app/models/tenant/treatment_plan.py`

---

## 2. Model Design

### Algorithm

**Logistic regression** (scikit-learn `LogisticRegression`). Chosen for:
- Interpretability (clinics can understand feature weights)
- Low compute cost (retrains in < 5 seconds per clinic)
- Works well with sparse data (50–5000 samples)
- Probability output natively calibrated

### Feature Vector

| Feature | Type | Source | Notes |
|---------|------|---------|-------|
| `total_cost_cop` | float (normalized) | Quotation total | Normalized to [0,1] per clinic's cost range |
| `procedure_count` | int | Quotation line items | Number of distinct procedures |
| `has_insurance` | bool | Patient `insurance_status` | EPS/ARS coverage active |
| `payment_history_score` | float 0–1 | Historical invoices | % invoices paid on time |
| `past_acceptance_rate` | float 0–1 | Patient's own history | Quotations accepted / total |
| `procedure_category` | one-hot | CUPS code prefix | `preventive`, `restorative`, `surgical`, `ortho`, `perio`, `other` |
| `days_since_last_visit` | int | `appointments` table | Recency of engagement |
| `is_existing_patient` | bool | Patient created_at | True if > 30 days |
| `quotation_month` | one-hot | Created_at month | Captures seasonal patterns |
| `doctor_acceptance_rate` | float 0–1 | Doctor-level aggregate | Historical rate for this doctor |

### Output

```python
{
    "score": 73,          # int 0-100 (probability * 100, rounded)
    "confidence": "medium",  # "low" | "medium" | "high"
    "top_factors": [         # Top 3 contributing features (positive/negative)
        {"factor": "has_insurance", "impact": "positive"},
        {"factor": "total_cost_cop", "impact": "negative"},
        {"factor": "past_acceptance_rate", "impact": "positive"}
    ]
}
```

**Confidence mapping:**

| Clinic training samples | Confidence |
|------------------------|------------|
| < 50 | `low` (uses global fallback model) |
| 50–200 | `medium` |
| > 200 | `high` |

---

## 3. Training Data

### Label Definition

- **Positive (accepted = 1):** Quotation with `status = 'approved'` AND at least one linked invoice created within 30 days.
- **Negative (rejected = 0):** Quotation with `status = 'rejected'` OR no invoice created within 90 days.
- **Excluded:** Quotations still in `draft` or `pending` status (unlabeled).

### Training Schedule

- **Full retrain:** Nightly at 02:00 clinic local time via `maintenance` queue job.
- **Incremental:** Triggered on any new label (acceptance or rejection) with a debounce of 4 hours.
- **Cold start fallback:** Global model trained on anonymized aggregate data from all clinics with > 200 quotations (opt-in setting per tenant).

### Model Persistence

Serialized with `joblib` and stored in S3:

```
/{tenant_id}/ml-models/acceptance_predictor_v{version}_{date}.pkl
```

Active model version tracked in `tenant_ml_models` table.

---

## 4. Database Schema

### Table: `tenant_ml_models` (public schema)

```sql
CREATE TABLE tenant_ml_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    tenant_id   UUID NOT NULL REFERENCES tenants(id),
    model_type  VARCHAR(50) NOT NULL,   -- 'acceptance_predictor', 'risk_score', etc.
    version     INTEGER NOT NULL DEFAULT 1,
    s3_path     VARCHAR(500) NOT NULL,
    sample_count INTEGER NOT NULL DEFAULT 0,
    accuracy    FLOAT DEFAULT NULL,     -- Held-out accuracy (last eval)
    is_active   BOOLEAN NOT NULL DEFAULT true,
    trained_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (tenant_id, model_type, version)
);

CREATE INDEX idx_tenant_ml_models_tenant_type ON tenant_ml_models(tenant_id, model_type);
```

### Table: `acceptance_predictions` (tenant schema `tn_*`)

```sql
CREATE TABLE acceptance_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    quotation_id UUID NOT NULL REFERENCES quotations(id),
    patient_id   UUID NOT NULL REFERENCES patients(id),

    -- Prediction output
    score        INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    confidence   VARCHAR(10) NOT NULL CHECK (confidence IN ('low', 'medium', 'high')),
    top_factors  JSONB NOT NULL DEFAULT '[]'::jsonb,
    feature_vector JSONB NOT NULL DEFAULT '{}'::jsonb,  -- For audit/retraining

    -- Model metadata
    model_version INTEGER NOT NULL DEFAULT 1,
    model_type    VARCHAR(50) NOT NULL DEFAULT 'logistic_regression',

    -- Outcome tracking (filled in later for retraining)
    actual_outcome BOOLEAN DEFAULT NULL,  -- true=accepted, false=rejected, null=pending
    outcome_at     TIMESTAMPTZ DEFAULT NULL,

    -- Soft delete
    is_active   BOOLEAN NOT NULL DEFAULT true,
    deleted_at  TIMESTAMPTZ DEFAULT NULL
);

CREATE INDEX idx_acceptance_predictions_quotation ON acceptance_predictions(quotation_id);
CREATE INDEX idx_acceptance_predictions_patient   ON acceptance_predictions(patient_id);
```

---

## 5. API Endpoints

### GET `/api/v1/quotations/{id}/acceptance-prediction`

Returns the current acceptance prediction for a quotation. Computes on the fly if not cached; uses cached prediction if quotation has not changed since last computation.

**Auth:** `doctor`, `receptionist`, `clinic_owner`
**Feature gate:** `ai_acceptance`

**Response `200`:**

```json
{
  "quotation_id": "uuid",
  "score": 73,
  "confidence": "medium",
  "top_factors": [
    {"factor": "has_insurance", "impact": "positive", "label": "Tiene seguro activo"},
    {"factor": "total_cost_cop", "impact": "negative", "label": "Costo alto vs. historial"},
    {"factor": "past_acceptance_rate", "impact": "positive", "label": "Acepta tratamientos frecuentemente"}
  ],
  "model_version": 3,
  "computed_at": "2026-03-14T10:30:00Z",
  "disclaimer": "Esta predicción es orientativa. No reemplaza el criterio clínico."
}
```

**Response `404`:** Quotation not found.
**Response `503`:** Model not yet trained (fewer than 50 samples) — returns cold-start score with `confidence: "low"`.

---

### POST `/api/v1/ml/acceptance-predictor/retrain` (internal)

Triggered by the `maintenance` worker. Not exposed to clinic staff.

**Auth:** Internal service token only.

**Body:** `{"tenant_id": "uuid"}`

**Response `202`:** Job enqueued.

---

## 6. Frontend

**Component:** `AcceptancePredictionBadge`

**Location:** `frontend/components/billing/acceptance-prediction-badge.tsx`

### Quotation Detail Page

Displayed below the total cost section:

```
┌──────────────────────────────────────────┐
│  Predicción de aceptación                │
│                                          │
│  ████████████░░░  73%    [confianza media]│
│                                          │
│  + Tiene seguro activo                   │
│  + Acepta tratamientos frecuentemente    │
│  − Costo alto vs. historial              │
│                                          │
│  ⚠ Esta predicción es orientativa.       │
└──────────────────────────────────────────┘
```

**Color coding:**
- 0–30%: Red badge
- 31–60%: Amber badge
- 61–80%: Teal badge
- 81–100%: Green badge

### Quotation List

Shows compact badge per row (score only, no factors).

### Hook

```typescript
// frontend/lib/hooks/use-acceptance-prediction.ts
function useAcceptancePrediction(quotationId: string): {
  prediction: AcceptancePrediction | null;
  isLoading: boolean;
  error: Error | null;
}
```

---

## 7. Privacy

- Feature vector stored in `acceptance_predictions.feature_vector` uses only aggregated/numeric values — no names, document numbers, or clinical notes.
- Global fallback model training uses only aggregated, de-identified statistics (counts, rates) — never individual patient rows.
- Tenants can opt out of global model contribution via `features.ai_global_model_opt_out = true`.
- Predictions are never shown to patients (portal has no access to this endpoint).

---

## 8. Test Plan

| # | Scenario | Expected |
|---|----------|----------|
| T1 | Quotation for existing patient with insurance | Score computed, `confidence` based on sample count |
| T2 | Tenant with < 50 samples | Returns cold-start score, `confidence: "low"` |
| T3 | Quotation updated after prediction | New prediction computed, old one retained for audit |
| T4 | Retrain job runs | `tenant_ml_models` version incremented, new pkl in S3 |
| T5 | Outcome filled (quotation accepted) | `actual_outcome = true`, available for next retrain |
| T6 | Feature flag disabled | Endpoint returns 403 |
| T7 | `top_factors` always has ≤ 3 items | Passes schema validation |
| T8 | Score always 0–100 integer | Cannot be null or float in response |
| T9 | Portal user calls endpoint | Returns 403 |
| T10 | Opt-out of global model | Tenant excluded from aggregate training dataset |
