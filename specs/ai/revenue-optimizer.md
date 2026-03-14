# AI Revenue Optimizer — Spec (AI-11)

> **Spec ID:** AI-11
> **Status:** Draft
> **Last Updated:** 2026-03-14
> **Feature Flag:** `ai_revenue`
> **Plan:** Enterprise (custom pricing)
> **Sprint:** S39-40 (Tier 3 — Leapfrog)
> **Priority:** Medium

---

## 1. Overview

**Feature:** The Revenue Optimizer continuously analyzes clinic operational and financial data to surface actionable revenue opportunities. It does NOT predict or hallucinate — it queries real data and uses Claude only to generate natural-language summaries of findings that already exist in the database.

**Two delivery channels:**
1. **Real-time dashboard widget** — top 5 opportunities, refreshed every 4 hours.
2. **Weekly digest report** — comprehensive PDF/email sent every Monday at 08:00 clinic time.

**Six analysis types (see Section 2):**
1. Unfinished treatment plans
2. Overdue recalls
3. Underutilized time slots
4. Upsell opportunities
5. Pricing outliers
6. Payment recovery (overdue invoices)

**Claude's role:** Receives pre-computed structured findings from the database and generates a natural-language insight paragraph in Spanish. It never sees raw patient names or PHI — only aggregate stats and anonymized counts.

### Dependencies

- `specs/billing/quotations.md` — Quotation and treatment plan data
- `specs/appointments/appointments-api.md` — Slot utilization
- `specs/ai/patient-risk-score.md` (AI-09) — Payment risk scores
- `backend/app/services/ai_claude_client.py`
- `backend/app/models/tenant/invoice.py`
- `backend/app/models/tenant/treatment_plan.py`

---

## 2. Analysis Types

### 2.1 Unfinished Treatment Plans

**Query:** Treatment plans with `status = 'active'` where at least one item has `status = 'pending'` and no appointment scheduled in the next 30 days.

**Output:** Count of patients, estimated revenue at risk (sum of pending item costs), average days since plan was created.

**Example insight:**
> "Tiene 14 planes de tratamiento activos sin cita programada, con un valor estimado de $2.8M COP. El plan más antiguo lleva 87 días sin actividad."

---

### 2.2 Overdue Recalls

**Query:** Patients whose last appointment was more than N days ago (N configurable per clinic, default 180 days for general recall, 90 days for perio patients).

**Output:** Count of overdue patients by risk category, estimated recall revenue if reactivated (avg revenue per recall visit × overdue count).

---

### 2.3 Underutilized Time Slots

**Query:** Rolling 4-week average slot utilization per doctor. Flags doctors with < 70% utilization.

**Output:** Underutilized hours per doctor, estimated revenue per empty hour (avg revenue per appointment for that doctor).

---

### 2.4 Upsell Opportunities

**Query:** Patients who have had a cleaning in the last 6 months but have no active quotation for restorative work, AND whose last radiograph (AI-01) detected caries or bone loss findings that were accepted by the doctor.

**Output:** Count of patients with accepted AI-01 findings but no treatment plan started within 60 days.

---

### 2.5 Pricing Outliers

**Query:** Compare invoiced amounts per CUPS code to the clinic's own price catalog. Flag procedures consistently invoiced below catalog price (discounts applied too liberally) or procedures where the clinic's rate is significantly below regional average (if regional benchmark data available).

**Output:** Top 5 procedure codes where average invoiced price deviates most from catalog. Estimated revenue delta if catalog price was charged.

---

### 2.6 Payment Recovery

**Query:** Invoices with `status = 'overdue'` (due_date > 30 days ago and unpaid), grouped by patient payment risk score.

**Output:** Total overdue balance by risk level, count of patients, recommended actions (payment plan offer vs. direct follow-up).

---

## 3. Database Schema

### Table: `revenue_opportunity_snapshots` (tenant schema `tn_*`)

```sql
CREATE TABLE revenue_opportunity_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Which analysis type
    analysis_type VARCHAR(40) NOT NULL
        CHECK (analysis_type IN (
            'unfinished_plans', 'overdue_recalls', 'underutilized_slots',
            'upsell_opportunities', 'pricing_outliers', 'payment_recovery'
        )),

    -- Computed metrics (structured)
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Claude-generated insight text (Spanish)
    insight_text TEXT DEFAULT NULL,

    -- Estimated revenue impact in COP cents
    estimated_revenue_cop INTEGER NOT NULL DEFAULT 0,

    -- Model tracking (for Claude calls)
    model_used    VARCHAR(50) DEFAULT NULL,
    input_tokens  INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,

    -- Delivery
    included_in_digest BOOLEAN DEFAULT false,
    digest_sent_at     TIMESTAMPTZ DEFAULT NULL,

    -- Soft delete
    is_active  BOOLEAN NOT NULL DEFAULT true,
    deleted_at TIMESTAMPTZ DEFAULT NULL
);

CREATE INDEX idx_revenue_snapshots_type       ON revenue_opportunity_snapshots(analysis_type);
CREATE INDEX idx_revenue_snapshots_created    ON revenue_opportunity_snapshots(created_at DESC);
```

### Table: `revenue_digest_reports` (tenant schema `tn_*`)

```sql
CREATE TABLE revenue_digest_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Report period
    period_start TIMESTAMPTZ NOT NULL,
    period_end   TIMESTAMPTZ NOT NULL,

    -- Linked snapshots
    snapshot_ids UUID[] NOT NULL DEFAULT '{}',

    -- Delivery
    pdf_s3_path     VARCHAR(500) DEFAULT NULL,
    email_sent_at   TIMESTAMPTZ DEFAULT NULL,
    recipient_count INTEGER DEFAULT 0,

    -- Totals
    total_opportunity_cop INTEGER NOT NULL DEFAULT 0,

    status  VARCHAR(20) NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'generating', 'sent', 'failed')),

    is_active  BOOLEAN NOT NULL DEFAULT true,
    deleted_at TIMESTAMPTZ DEFAULT NULL
);
```

---

## 4. API Endpoints

### GET `/api/v1/revenue/opportunities`

Returns the latest snapshot for each analysis type.

**Auth:** `clinic_owner`
**Feature gate:** `ai_revenue`

**Response `200`:**

```json
{
  "generated_at": "2026-03-14T10:00:00-05:00",
  "total_estimated_opportunity_cop": 8500000,
  "opportunities": [
    {
      "type": "unfinished_plans",
      "insight": "Tiene 14 planes de tratamiento activos sin cita programada...",
      "estimated_revenue_cop": 2800000,
      "metrics": {
        "patient_count": 14,
        "oldest_plan_days": 87
      },
      "cta": "Ver planes sin actividad",
      "cta_url": "/treatment-plans?filter=inactive"
    },
    {
      "type": "overdue_recalls",
      "insight": "28 pacientes no regresan desde hace más de 6 meses...",
      "estimated_revenue_cop": 1960000,
      "metrics": {
        "overdue_count": 28,
        "avg_days_since_visit": 214
      },
      "cta": "Iniciar campaña de recall",
      "cta_url": "/patients/recalls"
    }
  ]
}
```

---

### POST `/api/v1/revenue/opportunities/refresh`

Forces recomputation of all snapshots (bypasses the 4-hour cache).

**Auth:** `clinic_owner`
**Rate limit:** 4 times per day.

**Response `202`:** `{"job_id": "uuid", "estimated_seconds": 30}`

---

### GET `/api/v1/revenue/digest-reports`

Lists past weekly digest reports.

**Auth:** `clinic_owner`
**Pagination:** `?page=1&page_size=12`

**Response `200`:** Standard paginated list with `period_start`, `period_end`, `total_opportunity_cop`, `pdf_s3_path`, `status`.

---

### GET `/api/v1/revenue/digest-reports/{id}/download`

Returns a signed S3 URL for the digest PDF (15-minute expiry).

**Auth:** `clinic_owner`

---

## 5. Dashboard Widget

**Component:** `RevenueOptimizerWidget`

**Location:** `frontend/components/analytics/revenue-optimizer-widget.tsx`

### Layout

```
┌──────────────────────────────────────────────────────┐
│  💰 Oportunidades de ingresos          [Actualizar]  │
│  Potencial estimado: $8.5M COP esta semana           │
│  ─────────────────────────────────────────────────   │
│  1. Planes sin actividad         $2.8M   [→ Ver]     │
│  2. Pacientes por recall          $2.0M   [→ Ver]    │
│  3. Slots sin reservar            $1.6M   [→ Ver]    │
│  4. Oportunidades de upsell       $1.2M   [→ Ver]    │
│  5. Recuperación de cartera        $0.9M   [→ Ver]   │
│                                                      │
│  Próximo informe semanal: lunes 18 mar, 08:00        │
└──────────────────────────────────────────────────────┘
```

- Revenue figures in millions COP (M), truncated for readability.
- Each row links to the relevant module (treatment plans, recalls, appointments, etc.).
- Widget refreshes every 4 hours via TanStack Query `staleTime`.

---

## 6. Scheduled Reports

**Worker:** `maintenance` queue, job type `revenue.weekly_digest`

**Schedule:** Every Monday 02:00 UTC (renders to clinic local time 08:00).

**Generation steps:**

1. Pull latest snapshots for all 6 analysis types (or compute fresh if stale > 8 hours).
2. Call Claude to generate executive summary paragraph (≤ 150 words, Spanish) combining all 6 insights into one narrative.
3. Render PDF with `WeasyPrint` using the clinic's brand template.
4. Upload PDF to S3: `/{tenant_id}/reports/revenue/digest_{date}.pdf`.
5. Send email to `clinic_owner` users with PDF attachment.
6. Update `revenue_digest_reports` row to `status = 'sent'`.

**Claude prompt for executive summary:**

```
You are a dental clinic business advisor. Summarize these 6 revenue opportunities
in 3-4 sentences in Spanish (es-419), professional but direct tone.
Focus on the highest-impact items. No markdown. No bullet points.

Data (JSON): {findings_json}
```

`findings_json` contains only aggregate metrics (counts, amounts, percentages) — no patient names or identifiers.

---

## 7. Test Plan

| # | Scenario | Expected |
|---|----------|----------|
| T1 | 14 active plans with no upcoming appointment | `unfinished_plans` opportunity shows 14 patients |
| T2 | Doctor with 60% slot utilization | `underutilized_slots` opportunity populated |
| T3 | Feature flag disabled | GET `/revenue/opportunities` returns 403 |
| T4 | Force refresh more than 4 times in a day | 429 rate limit returned |
| T5 | Weekly digest job runs | PDF generated, email sent, digest row updated |
| T6 | Claude call fails during digest | Retry 3 times, report marked `failed` |
| T7 | No opportunities found (full utilization) | Returns empty `opportunities` array, not an error |
| T8 | PDF download URL | Returns signed URL expiring in 15 min |
| T9 | Non-owner role calls endpoint | Returns 403 |
| T10 | `insight_text` contains no PHI | Assertions verify no patient names/document numbers |
