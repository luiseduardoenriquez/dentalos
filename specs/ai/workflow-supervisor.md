# AI Workflow Supervisor (Enhanced) Spec

---

## 1. Overview

**Feature:** AI-06 — Proactive monitoring of all clinic workflows with alerts, auto-remediation, compliance scoring, and per-doctor documentation quality metrics. Extends the existing Workflow Compliance Monitor (GAP-15) from a read-only snapshot into a persistent, actionable supervision engine.

**Domain:** ai / workflow_supervisor

**Priority:** High (Tier 2 — differentiation vs Dentalink)

**Dependencies:** workflow_compliance_service (GAP-15), staff_tasks, notifications, patients, clinical-records, treatment-plans, consents, appointments, inventory, odontogram, evolution-notes, lab-orders, billing, anamnesis, feature-flags, caching, RabbitMQ

**Feature Flag:** `ai_workflow_supervisor`

**Plan Gating:** Clinica+ plan (included, not an add-on)

**Sprint:** 37-38

---

## 2. Architecture

```
                  ┌──────────────────────────────────────────────┐
                  │          AI Workflow Supervisor                │
                  │                                                │
                  │  ┌────────────────┐   ┌────────────────────┐  │
                  │  │  Rule Engine    │   │  Scoring Engine     │  │
                  │  │                 │   │                     │  │
                  │  │ Built-in rules  │   │ Weighted average    │  │
                  │  │ Custom rules    │   │ Per-clinic score    │  │
                  │  │ Condition eval  │   │ Per-doctor score    │  │
                  │  │ Action dispatch │   │ Trend tracking      │  │
                  │  └───────┬─────────┘   └──────────┬─────────┘  │
                  │          │                         │            │
                  │  ┌───────┴─────────────────────────┴─────────┐  │
                  │  │        Alert Manager                        │  │
                  │  │                                             │  │
                  │  │  Create/resolve alerts                     │  │
                  │  │  Deduplicate (no spam)                     │  │
                  │  │  Escalation chain                          │  │
                  │  │  Auto-remediation dispatch                 │  │
                  │  └─────────────────────────────────────────────┘  │
                  └──────────────────────────────────────────────┘

  Triggers:
  ┌─────────────────────┐     ┌─────────────────────────────┐
  │  Scheduled Scan      │     │  Event-Driven (on mutation) │
  │  Every 15 min        │     │  Appointment completed      │
  │  RabbitMQ:           │     │  Consent created            │
  │  maintenance queue   │     │  Inventory updated          │
  │  workflow_supervisor │     │  Treatment plan changed     │
  │  .scan               │     │  Record created             │
  └─────────────────────┘     └─────────────────────────────┘
```

### Relationship to GAP-15

The existing `WorkflowComplianceService` (GAP-15) runs 7 SQL checks and returns a read-only snapshot. The enhanced Workflow Supervisor:

1. **Wraps** GAP-15 checks as built-in rules within a configurable rule engine.
2. **Adds** 15+ new rules covering regulatory, inventory, scheduling, and billing compliance.
3. **Persists** alerts in a new `workflow_alerts` table (GAP-15 violations are ephemeral).
4. **Scores** clinic and doctor compliance via a weighted algorithm.
5. **Remediates** by creating staff tasks, sending notifications, and optionally blocking non-compliant procedures.
6. **Schedules** recurring scans via a RabbitMQ worker (GAP-15 runs only on-demand).

---

## 3. Rule Engine Design

### 3.1 Rule Structure

Each rule is a declarative configuration describing what to check, how severe it is, and what to do when it fires.

```python
class WorkflowRule:
    """A single compliance rule in the supervisor engine."""

    id: UUID
    code: str                      # Unique rule identifier, e.g. "WF_CONSENT_UNSIGNED"
    name: str                      # Human-readable name (Spanish)
    description: str               # Explanation shown in UI (Spanish)
    category: str                  # "clinical", "regulatory", "administrative", "inventory"
    severity: str                  # "critical", "high", "medium", "low"
    is_built_in: bool              # True = system rule (cannot be deleted)
    is_enabled: bool               # Can be toggled by clinic_owner
    condition_type: str            # "sql_check", "event_check"
    condition_config: dict         # JSONB — SQL template params or event matcher
    action_type: str               # "alert", "task", "notification", "block", "multi"
    action_config: dict            # JSONB — action parameters
    weight: int                    # 1-100, used in compliance score calculation
    cooldown_hours: int            # Min hours between re-alerting for same entity
    lookback_days: int             # How far back to check (for scheduled scans)
    applies_to_roles: list[str]    # Which roles see the resulting alerts
    # Timestamps and soft delete
    created_at: datetime
    updated_at: datetime
    is_active: bool
```

### 3.2 Built-in vs Custom Rules

| Aspect | Built-in Rules | Custom Rules |
|--------|---------------|--------------|
| Source | System-defined, shipped with code | Created by clinic_owner via API |
| Delete | Cannot be deleted (can be disabled) | Can be soft-deleted |
| Edit | Only `is_enabled`, `weight`, `cooldown_hours` | Full edit of condition + action |
| Updates | Auto-updated on system upgrade | Unaffected by upgrades |
| Validation | Pre-tested | Validated on save (dry-run) |

### 3.3 Condition Types

**`sql_check`** — Used by scheduled scans. The rule engine runs a parameterized SQL query and checks if any rows are returned. Query templates are predefined (same security approach as AI Reports — the engine never generates raw SQL).

**`event_check`** — Used by event-driven triggers. Matches against an event payload (entity_type, action, field conditions).

### 3.4 Action Types

| Type | Description | Config Example |
|------|-------------|----------------|
| `alert` | Create a `workflow_alert` record | `{"auto_resolve_on": "consent_signed"}` |
| `task` | Create a `StaffTask` | `{"task_type": "manual", "priority": "high", "assign_to": "doctor"}` |
| `notification` | Send via notification engine | `{"channels": ["in_app", "email"], "template": "consent_reminder"}` |
| `block` | Flag a procedure as blocked until resolved | `{"block_type": "procedure_start", "message": "..."}` |
| `multi` | Combine multiple actions | `{"actions": [{"type": "alert", ...}, {"type": "task", ...}]}` |

---

## 4. Built-in Compliance Rules

### 4.1 Clinical Rules

| # | Code | Name | Severity | Description | Action |
|---|------|------|----------|-------------|--------|
| 1 | `WF_CONSENT_UNSIGNED` | Consentimiento sin firmar | critical | Active treatment plan with no signed consent | alert + task + notification |
| 2 | `WF_RECORD_NO_DIAGNOSIS` | Registro sin diagnostico | high | Clinical record created but no diagnosis linked | alert + task |
| 3 | `WF_RECORD_NO_PROCEDURE` | Registro sin procedimiento | medium | Clinical record with no linked procedure | alert |
| 4 | `WF_APPOINTMENT_NO_RECORD` | Cita sin registro clinico | high | Completed appointment with no clinical record within 48h | alert + task |
| 5 | `WF_NO_ANAMNESIS` | Paciente sin anamnesis | medium | Patient with completed appointments but no anamnesis | alert + notification |
| 6 | `WF_PLAN_ITEM_OVERDUE` | Item de plan vencido | medium | Pending treatment plan item older than 90 days | alert |
| 7 | `WF_EVOLUTION_INCOMPLETE` | Nota de evolucion incompleta | medium | Evolution note missing required SOAP sections | alert + task |
| 8 | `WF_ODONTOGRAM_STALE` | Odontograma desactualizado | low | Patient with active treatment but odontogram not updated in 180 days | alert |

### 4.2 Regulatory Rules (Colombia Resolution 1888)

| # | Code | Name | Severity | Description | Action |
|---|------|------|----------|-------------|--------|
| 9 | `WF_R1888_HISTORY_INCOMPLETE` | Historia clinica incompleta (Res. 1888) | critical | Patient record missing fields required by Resolution 1888 (identification, reason for visit, physical exam, diagnosis, treatment plan) | alert + block |
| 10 | `WF_R1888_CONSENT_BEFORE_PROCEDURE` | Consentimiento previo a procedimiento | critical | Procedure recorded without prior signed consent for that treatment type | alert + block |
| 11 | `WF_R1888_PROFESSIONAL_SIGNATURE` | Firma profesional faltante | critical | Clinical record not signed by treating professional within 24h | alert + task |
| 12 | `WF_R1888_RETENTION_RISK` | Riesgo de retencion documental | high | Patient records approaching 15-year minimum retention period without archival | alert |
| 13 | `WF_R1888_RIPS_NOT_GENERATED` | RIPS no generado | high | Invoice exists for procedures but RIPS file not generated within required window | alert + task |

### 4.3 Administrative Rules

| # | Code | Name | Severity | Description | Action |
|---|------|------|----------|-------------|--------|
| 14 | `WF_APPOINTMENT_UNCONFIRMED` | Cita sin confirmar | medium | Appointment within 24h that has not been confirmed by patient | alert + notification (WhatsApp/SMS) |
| 15 | `WF_FOLLOWUP_OVERDUE` | Seguimiento vencido | high | Patient's scheduled follow-up date has passed with no new appointment | alert + task |
| 16 | `WF_INVOICE_OVERDUE` | Factura vencida | medium | Invoice past due date by more than configurable threshold (default 30 days) | alert + task |
| 17 | `WF_LAB_ORDER_OVERDUE` | Orden de laboratorio vencida | medium | Lab order past due date and not delivered/cancelled | alert |
| 18 | `WF_QUOTATION_STALE` | Cotizacion sin respuesta | low | Quotation sent but not accepted/rejected within 14 days | alert + task |

### 4.4 Inventory Rules

| # | Code | Name | Severity | Description | Action |
|---|------|------|----------|-------------|--------|
| 19 | `WF_INVENTORY_EXPIRED` | Inventario vencido | critical | Inventory item past expiration date and not marked as disposed | alert + notification |
| 20 | `WF_INVENTORY_EXPIRING_SOON` | Inventario proximo a vencer | high | Inventory item expiring within 30 days | alert |
| 21 | `WF_INVENTORY_LOW_STOCK` | Stock bajo | medium | Inventory item below minimum stock threshold | alert + notification |
| 22 | `WF_STERILIZATION_OVERDUE` | Esterilizacion vencida | critical | Sterilization cycle overdue for equipment per configured schedule | alert + block |

### 4.5 Billing & Compliance Rules

| # | Code | Name | Severity | Description | Action |
|---|------|------|----------|-------------|--------|
| 23 | `WF_PROCEDURE_NO_INVOICE` | Procedimiento sin factura | medium | Completed procedure with no associated invoice within 7 days | alert + task |
| 24 | `WF_PAYMENT_UNRECONCILED` | Pago sin conciliar | low | Payment received but not reconciled with an invoice | alert |
| 25 | `WF_RETHUS_EXPIRING` | Registro RETHUS por vencer | high | Doctor's RETHUS professional registry certificate expiring within 60 days | alert + notification |

---

## 5. Compliance Scoring Algorithm

### 5.1 Clinic Compliance Score

The clinic compliance score is a weighted average of all enabled rules' pass rates, expressed as a percentage (0-100).

```
clinic_score = SUM(rule_weight * rule_pass_rate) / SUM(rule_weight) * 100

Where:
  rule_pass_rate = 1 - (active_alerts_for_rule / total_entities_checked_for_rule)
  rule_weight    = rule.weight (1-100, configured per rule)
```

**Weight defaults by severity:**

| Severity | Default Weight |
|----------|---------------|
| critical | 100 |
| high | 75 |
| medium | 50 |
| low | 25 |

**Score interpretation:**

| Score Range | Label | Color | Dashboard Icon |
|-------------|-------|-------|----------------|
| 90-100 | Excelente | Green | Shield check |
| 75-89 | Bueno | Blue | Shield |
| 50-74 | Necesita mejora | Yellow | Warning triangle |
| 0-49 | Critico | Red | Alert circle |

### 5.2 Per-Doctor Score

Same formula but filtered to alerts where `doctor_id` matches. Only clinical and regulatory rules apply (inventory/admin rules are clinic-wide).

```
doctor_score = SUM(rule_weight * doctor_rule_pass_rate) / SUM(rule_weight) * 100

Where:
  doctor_rule_pass_rate = 1 - (doctor_active_alerts / doctor_total_entities)
```

### 5.3 Score Persistence

Scores are computed on each scheduled scan and stored in the `compliance_scores` table. Historical scores enable trend tracking.

**Redis cache:**
- Key: `dentalos:{tid}:ai:compliance_score:clinic`
- Key: `dentalos:{tid}:ai:compliance_score:doctor:{doctor_id}`
- TTL: 15 minutes (invalidated on scan completion)

---

## 6. Auto-Remediation Actions

When a rule fires, the supervisor can automatically take corrective actions beyond just alerting.

### 6.1 Action Catalog

| Action | Description | Implementation |
|--------|-------------|----------------|
| **Create staff task** | Assign follow-up task to responsible staff member | `staff_task_service.create()` with `task_type="workflow_supervisor"` |
| **Send notification** | Push in-app, email, WhatsApp, or SMS to relevant user | `notification_service.send()` with appropriate template |
| **Send patient reminder** | Remind patient of unconfirmed appointment or pending action | `notification_service.send()` via patient portal/WhatsApp |
| **Block procedure** | Set a flag preventing procedure start until condition is resolved | `workflow_alert.blocks_procedure = True`, checked by procedure start endpoint |
| **Create follow-up appointment** | Auto-suggest a follow-up appointment slot | Creates a draft appointment suggestion (not confirmed) |
| **Escalate to clinic owner** | If alert unresolved after escalation period, notify clinic owner | `notification_service.send()` to clinic_owner role |

### 6.2 Escalation Chain

```
1. Alert created → assigned to responsible user (doctor/receptionist)
   └─ If unresolved after 24h:
2. Reminder notification sent
   └─ If unresolved after 72h:
3. Escalate to clinic_owner
   └─ If unresolved after 7 days:
4. Mark as "escalated" in dashboard (red badge)
```

Escalation timings are configurable per rule via `action_config.escalation_hours`.

### 6.3 Auto-Resolution

Alerts are automatically resolved when the underlying condition is no longer true:

| Alert Code | Auto-resolve Trigger |
|-----------|---------------------|
| `WF_CONSENT_UNSIGNED` | Consent signed for the treatment plan |
| `WF_APPOINTMENT_NO_RECORD` | Clinical record created for that appointment |
| `WF_APPOINTMENT_UNCONFIRMED` | Appointment confirmed by patient |
| `WF_LAB_ORDER_OVERDUE` | Lab order marked as delivered |
| `WF_INVENTORY_EXPIRED` | Item marked as disposed |
| `WF_INVOICE_OVERDUE` | Invoice paid or written off |
| `WF_FOLLOWUP_OVERDUE` | New appointment scheduled for patient |

When auto-resolved, the alert status changes to `resolved` with `resolved_by = "system"` and `resolved_at` timestamp.

---

## 7. API Endpoints

**Base path:** `/api/v1/workflow-supervisor`

### 7.1 Compliance Score

#### GET `/api/v1/workflow-supervisor/score`

Returns the current clinic compliance score and breakdown.

**Auth:** `workflow_supervisor:read` — `clinic_owner`, `doctor` (own score only), `receptionist` (clinic score only)

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `doctor_id` | UUID | null | Filter to a specific doctor (clinic_owner only) |
| `include_breakdown` | bool | true | Include per-rule pass rates |

**Response (200):**

```json
{
  "clinic_score": 82.5,
  "clinic_label": "bueno",
  "doctor_scores": [
    {
      "doctor_id": "uuid",
      "doctor_name": "Dr. Garcia",
      "score": 91.0,
      "label": "excelente",
      "total_alerts": 3,
      "critical_alerts": 0
    }
  ],
  "breakdown": [
    {
      "rule_code": "WF_CONSENT_UNSIGNED",
      "rule_name": "Consentimiento sin firmar",
      "category": "regulatory",
      "severity": "critical",
      "weight": 100,
      "total_checked": 45,
      "violations": 2,
      "pass_rate": 0.956
    }
  ],
  "trend": {
    "current": 82.5,
    "previous_week": 78.0,
    "previous_month": 75.2,
    "direction": "improving"
  },
  "generated_at": "2026-03-13T10:00:00Z",
  "next_scan_at": "2026-03-13T10:15:00Z"
}
```

#### GET `/api/v1/workflow-supervisor/score/history`

Returns historical compliance scores for trend charts.

**Auth:** `workflow_supervisor:read` — `clinic_owner`

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `doctor_id` | UUID | null | Filter to specific doctor |
| `period` | string | "30d" | "7d", "30d", "90d", "365d" |
| `granularity` | string | "daily" | "hourly", "daily", "weekly" |

**Response (200):**

```json
{
  "doctor_id": null,
  "period": "30d",
  "data_points": [
    {"date": "2026-02-12", "score": 72.0},
    {"date": "2026-02-13", "score": 74.5}
  ]
}
```

### 7.2 Alerts

#### GET `/api/v1/workflow-supervisor/alerts`

List active and recent alerts with pagination.

**Auth:** `workflow_supervisor:read` — `clinic_owner` (all), `doctor` (own), `receptionist` (administrative only)

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `status` | string | "active" | "active", "resolved", "dismissed", "escalated" |
| `severity` | string | null | Filter by severity |
| `category` | string | null | "clinical", "regulatory", "administrative", "inventory" |
| `doctor_id` | UUID | null | Filter by responsible doctor |
| `rule_code` | string | null | Filter by specific rule |
| `page` | int | 1 | Page number |
| `page_size` | int | 20 | Items per page (max 100) |

**Response (200):**

```json
{
  "items": [
    {
      "id": "uuid",
      "rule_code": "WF_CONSENT_UNSIGNED",
      "rule_name": "Consentimiento sin firmar",
      "category": "regulatory",
      "severity": "critical",
      "status": "active",
      "patient_id": "uuid",
      "doctor_id": "uuid",
      "reference_id": "uuid",
      "reference_type": "treatment_plan",
      "message": "Plan de tratamiento activo sin consentimiento firmado.",
      "suggested_action": "Solicitar firma de consentimiento informado al paciente.",
      "auto_remediation": {
        "task_created": true,
        "task_id": "uuid",
        "notification_sent": true
      },
      "blocks_procedure": true,
      "escalation_level": 0,
      "detected_at": "2026-03-13T09:30:00Z",
      "due_at": "2026-03-14T09:30:00Z",
      "resolved_at": null,
      "days_open": 0
    }
  ],
  "total": 12,
  "page": 1,
  "page_size": 20,
  "summary": {
    "critical": 2,
    "high": 4,
    "medium": 5,
    "low": 1
  }
}
```

#### GET `/api/v1/workflow-supervisor/alerts/{alert_id}`

Get a single alert with full detail.

**Auth:** `workflow_supervisor:read`

**Response (200):** Single alert object (same shape as list item, plus `audit_trail` array).

#### PUT `/api/v1/workflow-supervisor/alerts/{alert_id}`

Update alert status (dismiss, acknowledge, resolve manually).

**Auth:** `workflow_supervisor:write` — `clinic_owner`, `doctor` (own alerts)

**Request body:**

```json
{
  "status": "dismissed",
  "resolution_note": "Patient declined treatment, plan was cancelled."
}
```

**Allowed transitions:**
- `active` -> `resolved`, `dismissed`
- `escalated` -> `resolved`, `dismissed`

**Response (200):** Updated alert object.

#### POST `/api/v1/workflow-supervisor/alerts/{alert_id}/snooze`

Snooze an alert for a specified duration.

**Auth:** `workflow_supervisor:write` — `clinic_owner`, `doctor`

**Request body:**

```json
{
  "snooze_hours": 24
}
```

**Response (200):**

```json
{
  "id": "uuid",
  "status": "snoozed",
  "snoozed_until": "2026-03-14T10:00:00Z"
}
```

### 7.3 Rules Configuration

#### GET `/api/v1/workflow-supervisor/rules`

List all rules (built-in + custom) with their current configuration.

**Auth:** `workflow_supervisor:read` — `clinic_owner`

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `category` | string | null | Filter by category |
| `is_enabled` | bool | null | Filter by enabled status |
| `is_built_in` | bool | null | Filter built-in vs custom |

**Response (200):**

```json
{
  "items": [
    {
      "id": "uuid",
      "code": "WF_CONSENT_UNSIGNED",
      "name": "Consentimiento sin firmar",
      "description": "Detecta planes de tratamiento activos sin consentimiento firmado.",
      "category": "regulatory",
      "severity": "critical",
      "is_built_in": true,
      "is_enabled": true,
      "weight": 100,
      "cooldown_hours": 24,
      "lookback_days": 30,
      "action_type": "multi",
      "action_config": {
        "actions": [
          {"type": "alert"},
          {"type": "task", "priority": "high", "assign_to": "doctor"},
          {"type": "notification", "channels": ["in_app"]}
        ]
      },
      "applies_to_roles": ["clinic_owner", "doctor"]
    }
  ],
  "total": 25
}
```

#### GET `/api/v1/workflow-supervisor/rules/{rule_id}`

Get a single rule with full configuration.

**Auth:** `workflow_supervisor:read` — `clinic_owner`

#### PUT `/api/v1/workflow-supervisor/rules/{rule_id}`

Update a rule's configuration.

**Auth:** `workflow_supervisor:write` — `clinic_owner` only

**Request body (built-in rule — limited fields):**

```json
{
  "is_enabled": true,
  "weight": 80,
  "cooldown_hours": 48,
  "action_config": {
    "actions": [
      {"type": "alert"},
      {"type": "notification", "channels": ["in_app", "email"]}
    ]
  }
}
```

**Request body (custom rule — full edit):**

```json
{
  "name": "Cita de control no agendada",
  "description": "Paciente con procedimiento completado hace 30+ dias sin cita de control.",
  "category": "clinical",
  "severity": "medium",
  "is_enabled": true,
  "condition_type": "sql_check",
  "condition_config": {
    "template": "patients_without_followup",
    "params": {"days_threshold": 30}
  },
  "action_type": "alert",
  "action_config": {},
  "weight": 50,
  "cooldown_hours": 72,
  "lookback_days": 60,
  "applies_to_roles": ["clinic_owner", "doctor"]
}
```

**Response (200):** Updated rule object.

#### POST `/api/v1/workflow-supervisor/rules`

Create a new custom rule.

**Auth:** `workflow_supervisor:write` — `clinic_owner` only

**Request body:** Same shape as custom rule PUT body.

**Validation:**
- `code` must be unique, prefixed with `WF_CUSTOM_`
- `condition_config.template` must reference a valid predefined query template
- `weight` must be 1-100
- `cooldown_hours` must be >= 1
- Max 50 custom rules per tenant

**Response (201):** Created rule object.

#### DELETE `/api/v1/workflow-supervisor/rules/{rule_id}`

Soft-delete a custom rule. Built-in rules return 403.

**Auth:** `workflow_supervisor:write` — `clinic_owner` only

**Response (200):**

```json
{
  "id": "uuid",
  "deleted": true
}
```

#### POST `/api/v1/workflow-supervisor/rules/{rule_id}/dry-run`

Test a rule against current data without creating alerts.

**Auth:** `workflow_supervisor:write` — `clinic_owner` only

**Response (200):**

```json
{
  "rule_code": "WF_CUSTOM_FOLLOWUP",
  "would_fire": true,
  "violations_count": 7,
  "sample_violations": [
    {
      "patient_id": "uuid",
      "reference_id": "uuid",
      "reference_type": "procedure",
      "days_overdue": 45
    }
  ]
}
```

### 7.4 Doctor Metrics

#### GET `/api/v1/workflow-supervisor/doctor-metrics`

Per-doctor documentation quality and compliance metrics.

**Auth:** `workflow_supervisor:read` — `clinic_owner` (all doctors), `doctor` (own only)

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `doctor_id` | UUID | null | Specific doctor (clinic_owner only) |
| `period` | string | "30d" | "7d", "30d", "90d" |

**Response (200):**

```json
{
  "doctors": [
    {
      "doctor_id": "uuid",
      "doctor_name": "Dr. Garcia",
      "compliance_score": 91.0,
      "metrics": {
        "appointments_with_records_pct": 98.5,
        "records_with_diagnosis_pct": 95.0,
        "records_with_procedure_pct": 92.3,
        "consents_signed_before_procedure_pct": 100.0,
        "evolution_notes_complete_pct": 88.0,
        "avg_record_completion_hours": 2.4,
        "records_signed_within_24h_pct": 96.0,
        "total_appointments": 65,
        "total_records": 64,
        "total_alerts": 5,
        "critical_alerts": 0
      },
      "trend": {
        "score_change": 3.5,
        "direction": "improving"
      }
    }
  ],
  "period": "30d",
  "generated_at": "2026-03-13T10:00:00Z"
}
```

### 7.5 Manual Scan Trigger

#### POST `/api/v1/workflow-supervisor/scan`

Trigger an immediate compliance scan (does not wait for next scheduled run).

**Auth:** `workflow_supervisor:write` — `clinic_owner` only

**Rate limit:** 1 per 5 minutes per tenant.

**Response (202):**

```json
{
  "scan_id": "uuid",
  "status": "queued",
  "message": "Escaneo de cumplimiento en cola. Los resultados estaran disponibles en ~30 segundos."
}
```

The scan runs async via the RabbitMQ maintenance queue.

### 7.6 Dashboard Widget Data

#### GET `/api/v1/workflow-supervisor/dashboard`

Lightweight endpoint returning only the data needed for the dashboard widget.

**Auth:** `workflow_supervisor:read`

**Response (200):**

```json
{
  "clinic_score": 82.5,
  "clinic_label": "bueno",
  "active_alerts": {
    "critical": 2,
    "high": 4,
    "medium": 5,
    "low": 1,
    "total": 12
  },
  "trend_direction": "improving",
  "top_issues": [
    {
      "rule_code": "WF_CONSENT_UNSIGNED",
      "rule_name": "Consentimiento sin firmar",
      "count": 2,
      "severity": "critical"
    },
    {
      "rule_code": "WF_APPOINTMENT_NO_RECORD",
      "rule_name": "Cita sin registro clinico",
      "count": 4,
      "severity": "high"
    }
  ],
  "last_scan_at": "2026-03-13T09:45:00Z"
}
```

---

## 8. Database Schema

All tables in the tenant schema (`tn_{id}`).

### 8.1 `workflow_rules`

Stores both built-in and custom rules with their configuration.

```sql
CREATE TABLE workflow_rules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code            VARCHAR(60) NOT NULL UNIQUE,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    category        VARCHAR(20) NOT NULL,
    severity        VARCHAR(20) NOT NULL,
    is_built_in     BOOLEAN NOT NULL DEFAULT false,
    is_enabled      BOOLEAN NOT NULL DEFAULT true,
    condition_type  VARCHAR(20) NOT NULL,
    condition_config JSONB NOT NULL DEFAULT '{}',
    action_type     VARCHAR(20) NOT NULL,
    action_config   JSONB NOT NULL DEFAULT '{}',
    weight          INTEGER NOT NULL DEFAULT 50,
    cooldown_hours  INTEGER NOT NULL DEFAULT 24,
    lookback_days   INTEGER NOT NULL DEFAULT 30,
    applies_to_roles JSONB NOT NULL DEFAULT '["clinic_owner"]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_active       BOOLEAN NOT NULL DEFAULT true,
    deleted_at      TIMESTAMPTZ,

    CONSTRAINT chk_workflow_rules_category CHECK (
        category IN ('clinical', 'regulatory', 'administrative', 'inventory', 'billing')
    ),
    CONSTRAINT chk_workflow_rules_severity CHECK (
        severity IN ('critical', 'high', 'medium', 'low')
    ),
    CONSTRAINT chk_workflow_rules_condition_type CHECK (
        condition_type IN ('sql_check', 'event_check')
    ),
    CONSTRAINT chk_workflow_rules_action_type CHECK (
        action_type IN ('alert', 'task', 'notification', 'block', 'multi')
    ),
    CONSTRAINT chk_workflow_rules_weight CHECK (weight BETWEEN 1 AND 100),
    CONSTRAINT chk_workflow_rules_cooldown CHECK (cooldown_hours >= 1)
);

CREATE INDEX idx_workflow_rules_category ON workflow_rules(category);
CREATE INDEX idx_workflow_rules_is_enabled ON workflow_rules(is_enabled) WHERE is_active = true;
```

### 8.2 `workflow_alerts`

Persistent alerts generated by the rule engine.

```sql
CREATE TABLE workflow_alerts (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id           UUID NOT NULL REFERENCES workflow_rules(id),
    rule_code         VARCHAR(60) NOT NULL,
    category          VARCHAR(20) NOT NULL,
    severity          VARCHAR(20) NOT NULL,
    status            VARCHAR(20) NOT NULL DEFAULT 'active',
    patient_id        UUID REFERENCES patients(id),
    doctor_id         UUID REFERENCES users(id),
    reference_id      UUID,
    reference_type    VARCHAR(30),
    message           TEXT NOT NULL,
    suggested_action  TEXT,
    blocks_procedure  BOOLEAN NOT NULL DEFAULT false,
    escalation_level  INTEGER NOT NULL DEFAULT 0,
    snoozed_until     TIMESTAMPTZ,
    resolution_note   TEXT,
    resolved_by       VARCHAR(60),            -- user_id or "system"
    resolved_at       TIMESTAMPTZ,
    detected_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    due_at            TIMESTAMPTZ,
    task_id           UUID REFERENCES staff_tasks(id),
    alert_metadata    JSONB DEFAULT '{}',     -- extra context (days_overdue, etc.)
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_active         BOOLEAN NOT NULL DEFAULT true,
    deleted_at        TIMESTAMPTZ,

    CONSTRAINT chk_workflow_alerts_status CHECK (
        status IN ('active', 'snoozed', 'resolved', 'dismissed', 'escalated')
    ),
    CONSTRAINT chk_workflow_alerts_severity CHECK (
        severity IN ('critical', 'high', 'medium', 'low')
    ),
    CONSTRAINT chk_workflow_alerts_category CHECK (
        category IN ('clinical', 'regulatory', 'administrative', 'inventory', 'billing')
    )
);

CREATE INDEX idx_workflow_alerts_status ON workflow_alerts(status) WHERE is_active = true;
CREATE INDEX idx_workflow_alerts_rule_code ON workflow_alerts(rule_code);
CREATE INDEX idx_workflow_alerts_severity ON workflow_alerts(severity) WHERE status = 'active';
CREATE INDEX idx_workflow_alerts_doctor ON workflow_alerts(doctor_id) WHERE status = 'active';
CREATE INDEX idx_workflow_alerts_patient ON workflow_alerts(patient_id);
CREATE INDEX idx_workflow_alerts_reference ON workflow_alerts(reference_id, reference_type);
-- Deduplication index: prevent duplicate active alerts for the same rule + reference
CREATE UNIQUE INDEX idx_workflow_alerts_dedup
    ON workflow_alerts(rule_code, reference_id, reference_type)
    WHERE status IN ('active', 'snoozed', 'escalated') AND is_active = true;
```

### 8.3 `compliance_scores`

Historical compliance scores for trend tracking.

```sql
CREATE TABLE compliance_scores (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope           VARCHAR(20) NOT NULL,      -- "clinic" or "doctor"
    doctor_id       UUID REFERENCES users(id), -- NULL for clinic-wide scores
    score           NUMERIC(5,2) NOT NULL,
    label           VARCHAR(20) NOT NULL,
    rules_checked   INTEGER NOT NULL,
    total_violations INTEGER NOT NULL,
    breakdown       JSONB NOT NULL DEFAULT '{}', -- per-rule pass rates
    scan_id         UUID,                       -- links to the scan that produced this
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_compliance_scores_scope CHECK (scope IN ('clinic', 'doctor')),
    CONSTRAINT chk_compliance_scores_label CHECK (
        label IN ('excelente', 'bueno', 'necesita_mejora', 'critico')
    ),
    CONSTRAINT chk_compliance_scores_range CHECK (score BETWEEN 0 AND 100)
);

CREATE INDEX idx_compliance_scores_scope ON compliance_scores(scope, doctor_id);
CREATE INDEX idx_compliance_scores_created ON compliance_scores(created_at DESC);
-- Partition-friendly: keep only 365 days of history (maintenance worker cleans older)
```

### 8.4 StaffTask Extension

The existing `staff_tasks` table gains a new `task_type` value:

```sql
-- Update CHECK constraint to include 'workflow_supervisor'
ALTER TABLE staff_tasks DROP CONSTRAINT chk_staff_tasks_type;
ALTER TABLE staff_tasks ADD CONSTRAINT chk_staff_tasks_type
    CHECK (task_type IN ('delinquency', 'acceptance', 'manual', 'workflow_supervisor'));
```

Tasks created by the supervisor include `metadata.alert_id` linking back to the originating alert.

---

## 9. Scheduled Scan Worker

### 9.1 Worker Configuration

- **Queue:** `maintenance` (existing)
- **Job type:** `workflow_supervisor.scan`
- **Schedule:** Every 15 minutes via cron-like scheduler
- **Concurrency:** 1 worker per tenant (serialized to avoid duplicate alerts)

### 9.2 Scan Flow

```
1. Receive job from maintenance queue
   └─ Payload: { tenant_id, scan_type: "scheduled" | "manual" }

2. Load tenant DB session (SET search_path TO tn_{id}, public)

3. Load all enabled rules from workflow_rules table

4. For each rule with condition_type = "sql_check":
   a. Execute the predefined query template with rule params
   b. For each violation found:
      - Check deduplication (active alert for same rule + reference?)
      - Check cooldown (last alert for same entity within cooldown_hours?)
      - If new: create workflow_alert + execute action chain
      - If existing: update detection count in alert_metadata

5. Auto-resolve: query alerts where the underlying condition no longer holds
   - For each auto-resolvable alert, check if condition still true
   - If condition resolved: set status = "resolved", resolved_by = "system"

6. Escalation: check alerts past escalation thresholds
   - If alert.detected_at + escalation_hours < now AND escalation_level < max:
     - Increment escalation_level
     - Send escalation notification
     - If escalation_level reaches max: set status = "escalated"

7. Compute compliance scores
   a. Clinic-wide score from all rule pass rates
   b. Per-doctor scores for each doctor with activity in the lookback period
   c. Insert into compliance_scores table
   d. Update Redis cache

8. Publish scan completion event for SSE subscribers

9. Log scan summary (no PHI): rules_checked, alerts_created, alerts_resolved, score
```

### 9.3 Scan Performance

Target: complete a full scan in < 10 seconds for a clinic with 1000 patients.

Optimization strategies:
- Each rule query uses proper indexes
- Queries run concurrently via `asyncio.gather` (same pattern as GAP-15)
- Deduplication uses the unique index (upsert pattern)
- Score computation is a single aggregation query over workflow_alerts

### 9.4 Query Templates

All SQL queries used by rules are predefined templates stored in code (never user-provided SQL). This follows the same security model as AI Reports.

Templates are registered in `workflow_supervisor_query_templates.py`:

```python
QUERY_TEMPLATES = {
    "consent_unsigned": {
        "description": "Active treatment plans without signed consent",
        "params": [],
        "query_fn": "_check_consent_unsigned",
    },
    "appointment_no_record": {
        "description": "Completed appointments without clinical record",
        "params": ["hours_threshold"],
        "query_fn": "_check_appointment_no_record",
    },
    "patients_without_followup": {
        "description": "Patients with completed procedures but no follow-up",
        "params": ["days_threshold"],
        "query_fn": "_check_patients_without_followup",
    },
    # ... 20+ templates
}
```

---

## 10. Event-Driven Triggers

In addition to scheduled scans, certain data mutations trigger immediate rule evaluation for responsiveness.

### 10.1 Event Sources

| Event | Source Service | Rules Triggered |
|-------|--------------|-----------------|
| Appointment completed | `appointment_service.complete()` | `WF_APPOINTMENT_NO_RECORD` (delayed 2h) |
| Treatment plan activated | `treatment_plan_service.activate()` | `WF_CONSENT_UNSIGNED` |
| Consent signed | `consent_service.sign()` | Auto-resolve `WF_CONSENT_UNSIGNED` |
| Clinical record created | `clinical_record_service.create()` | Auto-resolve `WF_APPOINTMENT_NO_RECORD` |
| Procedure recorded | `procedure_service.create()` | `WF_R1888_CONSENT_BEFORE_PROCEDURE`, `WF_PROCEDURE_NO_INVOICE` (delayed 7d) |
| Inventory item updated | `inventory_service.update()` | `WF_INVENTORY_EXPIRED`, `WF_INVENTORY_LOW_STOCK` |
| Invoice created | `invoice_service.create()` | Auto-resolve `WF_PROCEDURE_NO_INVOICE` |
| Invoice overdue | `invoice_service.check_overdue()` | `WF_INVOICE_OVERDUE` |
| Lab order status change | `lab_order_service.update_status()` | Auto-resolve `WF_LAB_ORDER_OVERDUE` |
| Appointment confirmed | `appointment_service.confirm()` | Auto-resolve `WF_APPOINTMENT_UNCONFIRMED` |

### 10.2 Implementation

Each source service calls the supervisor after the primary operation:

```python
# In appointment_service.py, after completing an appointment:
async def complete(self, db, appointment_id, ...):
    # ... existing logic ...

    # Trigger workflow supervisor event check
    await workflow_supervisor_service.on_event(
        db=db,
        tenant_id=tenant_id,
        event_type="appointment_completed",
        entity_type="appointment",
        entity_id=appointment_id,
        context={"patient_id": appointment.patient_id, "doctor_id": appointment.doctor_id},
    )
```

The `on_event` method:
1. Loads rules with `condition_type = "event_check"` matching the event type.
2. Evaluates conditions.
3. Creates/resolves alerts as appropriate.
4. Runs lightweight (no full scan), target < 100ms.

---

## 11. Error Codes

**Domain:** `WORKFLOW_SUPERVISOR`

| Code | HTTP | Description |
|------|------|-------------|
| `WORKFLOW_SUPERVISOR_plan_required` | 403 | Tenant plan does not include workflow supervisor |
| `WORKFLOW_SUPERVISOR_feature_disabled` | 403 | Feature flag `ai_workflow_supervisor` is disabled |
| `WORKFLOW_SUPERVISOR_rule_not_found` | 404 | Rule ID does not exist |
| `WORKFLOW_SUPERVISOR_alert_not_found` | 404 | Alert ID does not exist |
| `WORKFLOW_SUPERVISOR_rule_builtin_delete` | 403 | Cannot delete a built-in rule |
| `WORKFLOW_SUPERVISOR_rule_builtin_restricted` | 403 | Cannot modify restricted fields on built-in rule |
| `WORKFLOW_SUPERVISOR_rule_code_exists` | 409 | Custom rule code already exists |
| `WORKFLOW_SUPERVISOR_rule_limit_exceeded` | 422 | Max 50 custom rules per tenant |
| `WORKFLOW_SUPERVISOR_invalid_template` | 422 | Condition references a non-existent query template |
| `WORKFLOW_SUPERVISOR_invalid_transition` | 422 | Invalid alert status transition |
| `WORKFLOW_SUPERVISOR_scan_rate_limited` | 429 | Manual scan rate limit exceeded (1 per 5 min) |
| `WORKFLOW_SUPERVISOR_snooze_too_long` | 422 | Snooze duration exceeds maximum (168h / 7 days) |

---

## 12. Security & Audit

### 12.1 Access Control

| Action | clinic_owner | doctor | assistant | receptionist |
|--------|:----------:|:------:|:---------:|:------------:|
| View clinic score | Yes | Yes | No | Yes |
| View doctor scores (all) | Yes | No | No | No |
| View own doctor score | Yes | Yes | No | No |
| View alerts (all) | Yes | No | No | Administrative only |
| View alerts (own) | Yes | Yes | No | No |
| Dismiss/resolve alerts | Yes | Own only | No | No |
| Snooze alerts | Yes | Own only | No | No |
| Configure rules | Yes | No | No | No |
| Create custom rules | Yes | No | No | No |
| Trigger manual scan | Yes | No | No | No |
| View doctor metrics (all) | Yes | No | No | No |
| View own doctor metrics | Yes | Yes | No | No |

### 12.2 Audit Logging

All supervisor actions are logged to the existing `audit_logs` table:

| Action | Logged Data |
|--------|------------|
| Rule created | rule_id, code, category, created_by |
| Rule updated | rule_id, changed_fields, updated_by |
| Rule deleted | rule_id, code, deleted_by |
| Alert dismissed | alert_id, rule_code, dismissed_by, resolution_note |
| Alert resolved (manual) | alert_id, rule_code, resolved_by, resolution_note |
| Alert resolved (auto) | alert_id, rule_code, resolved_by="system", trigger_event |
| Alert snoozed | alert_id, rule_code, snoozed_by, snooze_hours |
| Manual scan triggered | scan_id, triggered_by |
| Procedure blocked | alert_id, rule_code, patient_id (anonymized), blocked_procedure_type |

**PHI rules:** Alert audit logs never include patient names or document numbers. Only `patient_id` (UUID) and clinical reference IDs are stored.

### 12.3 Procedure Blocking

When a rule has `action_type = "block"` and fires, the resulting alert has `blocks_procedure = true`. The procedure start endpoint checks for blocking alerts:

```python
# In procedure_service.py, before starting a procedure:
blocking_alerts = await workflow_supervisor_service.get_blocking_alerts(
    db=db, patient_id=patient_id, reference_type="treatment_plan"
)
if blocking_alerts:
    raise HTTPException(
        status_code=422,
        detail={
            "error": "WORKFLOW_SUPERVISOR_procedure_blocked",
            "message": "Procedimiento bloqueado por alerta de cumplimiento.",
            "details": {
                "blocking_alerts": [
                    {"alert_id": str(a.id), "rule_code": a.rule_code, "message": a.message}
                    for a in blocking_alerts
                ]
            },
        },
    )
```

Only `clinic_owner` can override a block by dismissing the alert with a resolution note.

---

## 13. Feature Flag Gating

### 13.1 Plan Check

```python
_CLINICA_PLANS = {"clinica", "enterprise"}

# In every endpoint:
if current_user.tenant.plan_name not in _CLINICA_PLANS:
    raise HTTPException(403, detail={
        "error": WorkflowSupervisorErrors.PLAN_REQUIRED,
        "message": "El supervisor de flujos requiere plan Clinica o superior.",
    })
```

### 13.2 Feature Flag Check

```python
if not current_user.tenant.features.get("ai_workflow_supervisor"):
    raise HTTPException(403, detail={
        "error": WorkflowSupervisorErrors.FEATURE_DISABLED,
        "message": "La funcionalidad de supervisor de flujos no esta habilitada.",
    })
```

### 13.3 Graceful Degradation

If the feature flag is disabled:
- Scheduled scans skip the tenant
- Event-driven triggers are no-ops (check flag before processing)
- Dashboard widget shows "Disponible en plan Clinica" placeholder
- Existing alerts remain in DB but are not evaluated or escalated

---

## 14. Frontend

### 14.1 Dashboard Widget

**Location:** Main dashboard, alongside existing KPI cards.

**Component:** `components/workflow-supervisor/compliance-widget.tsx`

**Content:**
- Circular progress indicator showing clinic score (color-coded)
- Label: "Excelente" / "Bueno" / "Necesita mejora" / "Critico"
- Trend arrow (up/down/neutral) vs previous week
- Badge with count of active critical/high alerts
- "Ver detalles" link to full alerts page

**Data source:** `GET /api/v1/workflow-supervisor/dashboard`

**Cache:** React Query, stale time 5 minutes.

### 14.2 Alerts Page

**Route:** `/dashboard/workflow-supervisor/alerts`

**Component:** `app/(dashboard)/workflow-supervisor/alerts/page.tsx`

**Layout:**
- Summary bar: 4 severity buckets with counts (critical / high / medium / low)
- Filter controls: status, severity, category, doctor, rule
- Alert list (table or card view, user toggle):
  - Severity badge (color-coded)
  - Rule name
  - Affected patient (link to patient chart)
  - Responsible doctor
  - Time since detected
  - Status badge
  - Actions: Resolve, Dismiss, Snooze
- Alert detail slide-over panel:
  - Full alert information
  - Suggested action text
  - Auto-remediation status (task created? notification sent?)
  - Audit trail
  - Resolution note input (for dismiss/resolve)

### 14.3 Rules Configuration Page

**Route:** `/dashboard/workflow-supervisor/rules`

**Component:** `app/(dashboard)/workflow-supervisor/rules/page.tsx`

**Access:** clinic_owner only.

**Layout:**
- Tabs: "Reglas del sistema" (built-in) | "Reglas personalizadas" (custom)
- Each rule card shows:
  - Name, description, category, severity
  - Enable/disable toggle
  - Weight slider (1-100)
  - Cooldown hours input
  - Action configuration (expandable)
  - "Probar" (dry-run) button
- "Crear regla" button (custom tab only)
- Rule creation/edit form:
  - Name, description, category, severity
  - Query template selector (dropdown of available templates)
  - Template parameters (dynamic form based on selected template)
  - Action type and configuration
  - Weight, cooldown, lookback days
  - Role visibility checkboxes

### 14.4 Doctor Metrics Page

**Route:** `/dashboard/workflow-supervisor/doctor-metrics`

**Component:** `app/(dashboard)/workflow-supervisor/doctor-metrics/page.tsx`

**Access:** clinic_owner sees all doctors. doctor sees own only.

**Layout:**
- Period selector: 7d / 30d / 90d
- Doctor comparison table:
  - Doctor name
  - Compliance score (bar chart)
  - Key metrics (% records with diagnosis, % consents signed, avg completion time)
  - Alert count
  - Trend indicator
- Click on doctor row expands to full metric detail
- Score trend chart (line graph, using historical compliance_scores data)

### 14.5 Procedure Block Modal

When a doctor tries to start a procedure that is blocked by a supervisor alert, a modal appears:

**Component:** `components/workflow-supervisor/procedure-block-modal.tsx`

**Content:**
- Warning icon + "Procedimiento bloqueado"
- List of blocking alerts with rule name and message
- Link to resolve each alert
- "Contactar administrador" button (if doctor cannot resolve)
- clinic_owner override button (if applicable)

---

## 15. Test Plan

### 15.1 Unit Tests

| Test File | Coverage |
|-----------|----------|
| `test_workflow_supervisor_service.py` | Rule engine evaluation, score computation, deduplication, cooldown logic, auto-resolution |
| `test_workflow_supervisor_queries.py` | Each query template returns correct violations for given test data |
| `test_compliance_scoring.py` | Weighted average calculation, edge cases (no rules enabled, all pass, all fail), label assignment |
| `test_auto_remediation.py` | Task creation, notification dispatch, procedure blocking flag |
| `test_escalation.py` | Escalation level progression, escalation notifications, max escalation reached |

### 15.2 Integration Tests

| Test File | Coverage |
|-----------|----------|
| `test_workflow_supervisor_api.py` | All endpoint response shapes, auth/RBAC for each role, plan gating, feature flag gating |
| `test_workflow_supervisor_rules_crud.py` | Create/read/update/delete custom rules, built-in rule restrictions, validation errors |
| `test_workflow_supervisor_alerts_lifecycle.py` | Alert creation via scan, status transitions, snooze, auto-resolve, manual resolve |
| `test_workflow_supervisor_event_triggers.py` | Event-driven alert creation and auto-resolution from service mutations |
| `test_workflow_supervisor_scan_worker.py` | Full scan flow: rules loaded, queries executed, alerts created/resolved, scores computed |

### 15.3 Key Test Scenarios

1. **Deduplication:** Run two scans — second scan should not create duplicate alerts for same rule + reference.
2. **Cooldown:** Create and resolve an alert. Run scan within cooldown period — alert should not be re-created.
3. **Auto-resolution:** Create a `WF_CONSENT_UNSIGNED` alert. Sign the consent. Run scan — alert should auto-resolve.
4. **Escalation:** Create alert. Fast-forward time past escalation thresholds. Verify escalation_level increments and notifications are sent.
5. **Procedure blocking:** Create a blocking alert. Attempt to start procedure — verify 422 response with alert details.
6. **Custom rule limit:** Create 50 custom rules. Attempt 51st — verify 422 error.
7. **Built-in rule protection:** Attempt to delete a built-in rule — verify 403 error.
8. **Score calculation:** Set up known violation counts and weights. Verify score matches expected weighted average.
9. **Doctor scope isolation:** Doctor calls alerts endpoint — verify only their own alerts are returned.
10. **Feature flag off:** Disable feature flag. Verify all endpoints return 403 and scheduled scans skip tenant.
11. **Plan gating:** Tenant on Pro plan calls endpoint — verify 403 with upgrade message.
12. **Snooze:** Snooze an alert for 24h. Verify it does not appear in active alerts. After 24h, verify it becomes active again.
13. **Dry-run:** Create a custom rule and dry-run it. Verify violations are detected but no alerts are created.
14. **Event-driven auto-resolve:** Complete an appointment (trigger event), then create a clinical record (trigger auto-resolve). Verify alert lifecycle.

### 15.4 Performance Tests

- Full scan for a tenant with 1000 patients, 5 doctors, 25 rules: target < 10 seconds.
- Event-driven trigger processing: target < 100ms per event.
- Dashboard endpoint response time: target < 200ms (cache hit < 50ms).

---

## 16. Migration

**Alembic tenant migration:** `alembic_tenant/versions/XXX_add_workflow_supervisor_tables.py`

Creates:
1. `workflow_rules` table with all indexes
2. `workflow_alerts` table with all indexes (including dedup unique index)
3. `compliance_scores` table with indexes
4. Updates `staff_tasks` CHECK constraint to include `workflow_supervisor` task type
5. Seeds built-in rules (25 rules from Section 4)

**Rollback:** Drop tables in reverse order, restore original `staff_tasks` constraint.

---

## 17. Files to Create/Modify

### New Files

| File | Description |
|------|-------------|
| `backend/app/models/tenant/workflow_rule.py` | WorkflowRule SQLAlchemy model |
| `backend/app/models/tenant/workflow_alert.py` | WorkflowAlert SQLAlchemy model |
| `backend/app/models/tenant/compliance_score.py` | ComplianceScore SQLAlchemy model |
| `backend/app/schemas/workflow_supervisor.py` | Pydantic schemas (request/response) |
| `backend/app/services/workflow_supervisor_service.py` | Core service (rule engine, scoring, remediation) |
| `backend/app/services/workflow_supervisor_query_templates.py` | Predefined SQL query templates |
| `backend/app/api/v1/workflow_supervisor/router.py` | API route handlers |
| `frontend/app/(dashboard)/workflow-supervisor/alerts/page.tsx` | Alerts page |
| `frontend/app/(dashboard)/workflow-supervisor/rules/page.tsx` | Rules config page |
| `frontend/app/(dashboard)/workflow-supervisor/doctor-metrics/page.tsx` | Doctor metrics page |
| `frontend/components/workflow-supervisor/compliance-widget.tsx` | Dashboard widget |
| `frontend/components/workflow-supervisor/procedure-block-modal.tsx` | Block modal |
| `frontend/lib/hooks/use-workflow-supervisor.ts` | React Query hooks |

### Modified Files

| File | Change |
|------|--------|
| `backend/app/core/error_codes.py` | Add `WorkflowSupervisorErrors` class |
| `backend/app/models/tenant/__init__.py` | Register new models |
| `backend/app/models/tenant/staff_task.py` | Update CHECK constraint for new task_type |
| `backend/app/api/v1/router.py` | Register workflow_supervisor router |
| `backend/app/workers/maintenance_worker.py` | Add `workflow_supervisor.scan` handler |
| `backend/app/services/appointment_service.py` | Add event trigger on complete/confirm |
| `backend/app/services/consent_service.py` | Add event trigger on sign |
| `backend/app/services/clinical_record_service.py` | Add event trigger on create |
| `backend/app/services/procedure_service.py` | Add blocking alert check before start |
| `backend/app/services/inventory_service.py` | Add event trigger on update |
| `backend/app/services/invoice_service.py` | Add event trigger on create |
| `backend/app/services/lab_order_service.py` | Add event trigger on status change |
| `frontend/app/(dashboard)/layout.tsx` | Add nav link for workflow supervisor |

---

## 18. Dentalink Comparison

| Capability | Dentalink (Contralor IA) | DentalOS (AI Workflow Supervisor) |
|-----------|--------------------------|-----------------------------------|
| Basic workflow monitoring | Yes | Yes |
| Task creation | Yes | Yes + auto-assigned + linked to alert |
| Regulatory awareness | No | Yes (Resolution 1888 rules) |
| Auto-remediation | No | Yes (notifications, tasks, blocks) |
| Compliance scoring | No | Yes (clinic + per-doctor) |
| Per-doctor metrics | No | Yes (documentation quality tracking) |
| Customizable rules | No | Yes (up to 50 custom rules) |
| Procedure blocking | No | Yes (configurable per rule) |
| Escalation chain | No | Yes (3-level with configurable timing) |
| Event-driven checks | Unknown | Yes (immediate on data change) |
| Score history/trends | No | Yes (daily/weekly/monthly) |
| Dry-run for rules | No | Yes |
| Inventory compliance | No | Yes (expiration, stock, sterilization) |
