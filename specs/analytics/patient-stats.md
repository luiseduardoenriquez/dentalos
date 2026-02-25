# AN-02 — Patient Analytics Spec

---

## Overview

**Feature:** Patient analytics endpoint. Returns patient-centric metrics including new patient acquisition over time (by day/week/month), patient retention rate, average visits per patient, demographic breakdowns by age group and biological sex, and referral source distribution. Supports date range filtering and granularity selection. clinic_owner sees clinic-wide data; doctor sees only their own patient cohort.

**Domain:** analytics

**Priority:** Medium

**Dependencies:** AN-01 (dashboard), patients/patient-list, patients/patient-create, infra/caching-strategy.md, infra/audit-logging.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor
- **Tenant context:** Required — resolved from JWT
- **Special rules:** doctor role is automatically scoped to patients they have treated (patients who have at least one appointment or clinical record with the doctor). clinic_owner sees all patients in the tenant schema.

---

## Endpoint

```
GET /api/v1/analytics/patients
```

**Rate Limiting:**
- 20 requests per minute per user
- Analytics heavy queries warrant conservative rate limits

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | No | string | Tenant identifier (auto-resolved from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| period | No | string | Enum: `today`, `this_week`, `this_month`, `this_quarter`, `this_year`, `custom`. Default: `this_month` | Date range preset | `this_quarter` |
| date_from | Conditional | string | ISO 8601 date. Required when period=custom | Custom range start | `2026-01-01` |
| date_to | Conditional | string | ISO 8601 date. Required when period=custom. Must be >= date_from. Max 366 days | Custom range end | `2026-03-31` |
| granularity | No | string | Enum: `day`, `week`, `month`. Default: `month` | Granularity for time-series data | `week` |

### Request Body Schema

None. GET request.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "period": {
    "preset": "string | null",
    "date_from": "string (YYYY-MM-DD)",
    "date_to": "string (YYYY-MM-DD)",
    "timezone": "string (IANA timezone)",
    "granularity": "string (day | week | month)"
  },
  "summary": {
    "total_active_patients": "integer",
    "new_patients_in_period": "integer",
    "returning_patients_in_period": "integer",
    "retention_rate": "number (percentage 0-100) — patients who returned vs churned",
    "average_visits_per_patient": "number",
    "growth_vs_previous": "number | null (percentage change in new patients)"
  },
  "new_patients_over_time": [
    {
      "period_label": "string (e.g., '2026-02', '2026-W08', '2026-02-15')",
      "date_from": "string (YYYY-MM-DD)",
      "date_to": "string (YYYY-MM-DD)",
      "new_patients": "integer",
      "cumulative_total": "integer"
    }
  ],
  "demographics": {
    "age_groups": [
      {
        "group": "string (e.g., '0-12', '13-17', '18-30', '31-45', '46-60', '60+')",
        "count": "integer",
        "percentage": "number"
      }
    ],
    "sex_distribution": [
      {
        "sex": "string (masculino | femenino | otro | no_especificado)",
        "count": "integer",
        "percentage": "number"
      }
    ]
  },
  "referral_sources": [
    {
      "source": "string (referral source label)",
      "count": "integer",
      "percentage": "number"
    }
  ],
  "generated_at": "string (ISO 8601 datetime)",
  "cache_hit": "boolean"
}
```

**Example:**
```json
{
  "period": {
    "preset": "this_quarter",
    "date_from": "2026-01-01",
    "date_to": "2026-03-31",
    "timezone": "America/Bogota",
    "granularity": "month"
  },
  "summary": {
    "total_active_patients": 342,
    "new_patients_in_period": 54,
    "returning_patients_in_period": 201,
    "retention_rate": 78.5,
    "average_visits_per_patient": 2.3,
    "growth_vs_previous": 15.2
  },
  "new_patients_over_time": [
    {"period_label": "2026-01", "date_from": "2026-01-01", "date_to": "2026-01-31", "new_patients": 18, "cumulative_total": 288},
    {"period_label": "2026-02", "date_from": "2026-02-01", "date_to": "2026-02-28", "new_patients": 22, "cumulative_total": 310},
    {"period_label": "2026-03", "date_from": "2026-03-01", "date_to": "2026-03-31", "new_patients": 14, "cumulative_total": 324}
  ],
  "demographics": {
    "age_groups": [
      {"group": "0-12", "count": 28, "percentage": 8.2},
      {"group": "13-17", "count": 15, "percentage": 4.4},
      {"group": "18-30", "count": 87, "percentage": 25.4},
      {"group": "31-45", "count": 112, "percentage": 32.7},
      {"group": "46-60", "count": 68, "percentage": 19.9},
      {"group": "60+", "count": 32, "percentage": 9.4}
    ],
    "sex_distribution": [
      {"sex": "femenino", "count": 198, "percentage": 57.9},
      {"sex": "masculino", "count": 138, "percentage": 40.4},
      {"sex": "otro", "count": 4, "percentage": 1.2},
      {"sex": "no_especificado", "count": 2, "percentage": 0.6}
    ]
  },
  "referral_sources": [
    {"source": "Referido por paciente", "count": 98, "percentage": 28.7},
    {"source": "Redes sociales", "count": 76, "percentage": 22.2},
    {"source": "Google / búsqueda web", "count": 54, "percentage": 15.8},
    {"source": "Recomendación médica", "count": 42, "percentage": 12.3},
    {"source": "Convenio / empresa", "count": 38, "percentage": 11.1},
    {"source": "Otro / no especificado", "count": 34, "percentage": 9.9}
  ],
  "generated_at": "2026-02-25T10:30:00Z",
  "cache_hit": false
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid period enum, custom period missing required dates, date_from > date_to, date range exceeds 366 days, invalid granularity enum.

**Example:**
```json
{
  "error": "parametro_invalido",
  "message": "La granularidad especificada no es válida.",
  "details": {
    "granularity": ["Valores permitidos: day, week, month."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. See `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Role not in `[clinic_owner, doctor]`.

**Example:**
```json
{
  "error": "acceso_denegado",
  "message": "No tiene permisos para acceder a los análisis de pacientes.",
  "details": {}
}
```

#### 422 Unprocessable Entity
**When:** Date strings cannot be parsed as valid ISO 8601 dates.

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Aggregation query failure or unexpected exception.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT — extract `user_id`, `tenant_id`, `role`. Authorize — reject non-analyst roles with 403.
2. Parse and validate query parameters. Compute `date_from`/`date_to` from preset using tenant timezone.
3. Determine scope filter: `doctor_filter = current_user.id` if role is doctor, else `None`.
4. Build Redis cache key: `tenant:{tenant_id}:analytics:patients:{doctor_filter}:{date_from}:{date_to}:{granularity}`. Check cache. If hit, return with `cache_hit: true`.
5. Execute concurrent async queries via `asyncio.gather`:

   **Summary queries:**
   - `total_active_patients`: `SELECT COUNT(*) FROM patients WHERE deleted_at IS NULL [AND doctor_filter join]`
   - `new_patients_in_period`: `COUNT(*) WHERE created_at BETWEEN date_from AND date_to`
   - `returning_patients_in_period`: patients with >= 2 appointments total and at least 1 appointment in period
   - `retention_rate`: `(returning_patients_in_period / (returning_patients_in_period + churned)) * 100`. Churned = had appointments before period but none in period.
   - `average_visits_per_patient`: `AVG(appointment_count)` per patient in period

   **Time-series query (new_patients_over_time):**
   - `DATE_TRUNC(granularity, created_at)` GROUP BY buckets, ordered ascending, with running SUM for cumulative_total

   **Demographics queries:**
   - Age groups: `EXTRACT(YEAR FROM AGE(date_of_birth))` — bucket into defined ranges using CASE WHEN
   - Sex distribution: `GROUP BY biological_sex`

   **Referral sources:**
   - `SELECT referral_source, COUNT(*) FROM patients WHERE [scope] GROUP BY referral_source ORDER BY COUNT(*) DESC`

6. Compute `growth_vs_previous`: query previous same-length period for new patient count, compute percentage delta.
7. Assemble response, compute percentages for demographics and referral sources.
8. Cache result in Redis with 300-second TTL.
9. Return 200.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| period | One of: today, this_week, this_month, this_quarter, this_year, custom | Período no válido. |
| granularity | One of: day, week, month | La granularidad especificada no es válida. |
| date_from | Valid ISO date, required for custom | La fecha de inicio es requerida. |
| date_to | Valid ISO date, >= date_from, custom period; max 366-day span | La fecha de fin no puede ser anterior a la fecha de inicio. |

**Business Rules:**

- Age is calculated as of the `date_to` parameter, not today's date, for historical accuracy.
- Retention rate definition: a patient is "retained" if they had at least one visit before the selected period AND at least one visit within the selected period.
- Patients with `deleted_at IS NOT NULL` (deactivated) are excluded from all counts.
- Patients without a `date_of_birth` are counted under `"no_especificado"` in age groups.
- Patients without a `referral_source` are counted under `"Otro / no especificado"`.
- Time-series granularity constraints: `day` granularity is only sensible for ranges up to 90 days; `week` for up to 366 days; `month` for any range. API accepts any combination but warns in structured log if combination is unusual.
- Demographics include ALL active patients in the tenant (not filtered by period) to represent the full patient population base.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| No patients in period | new_patients_in_period = 0, time-series has zero-count buckets for each period |
| All patients have no referral source | referral_sources has one item: "Otro / no especificado" with count = total |
| Single-day period with granularity=month | One bucket returned in new_patients_over_time |
| doctor role with no patients | All counts = 0, empty arrays |
| Clinic with patients but no age data | age_groups has all counts under "no_especificado" |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- All queries READ-ONLY.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:analytics:patients:{doctor_filter}:{date_from}:{date_to}:{granularity}`: SET with 300s TTL.

**Cache TTL:** 300 seconds.

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Yes.
- **Action:** read
- **Resource:** analytics_patients
- **PHI involved:** No (aggregated data, no individual patient records)

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 300ms (cached), < 2000ms (cache miss)
- **Maximum acceptable:** < 5000ms

### Caching Strategy
- **Strategy:** Redis cache, 5-minute TTL
- **Cache key:** `tenant:{tenant_id}:analytics:patients:{doctor_filter}:{date_from}:{date_to}:{granularity}`
- **TTL:** 300 seconds
- **Invalidation:** Time-based expiry only

### Database Performance

**Queries executed:** 6-8 concurrent async queries

**Indexes required:**
- `patients.(created_at, deleted_at)` — new patients in period
- `patients.(biological_sex, deleted_at)` — sex distribution
- `patients.(date_of_birth, deleted_at)` — age group analytics
- `patients.(referral_source, deleted_at)` — referral source distribution
- `appointments.(patient_id, scheduled_at)` — visits per patient, retention

**N+1 prevention:** All queries are aggregate GROUP BY queries. No per-patient iteration.

### Pagination

**Pagination:** No — returns complete analytical dataset.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| period | Pydantic enum validator | |
| granularity | Pydantic enum validator | |
| date_from / date_to | Pydantic date validator | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized aggregate queries.

### XSS Prevention

**Output encoding:** Pydantic serialization. No user-generated free text in response.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None. Aggregated data only. Individual patient names, IDs, or records are never returned. Age groups and sex distribution are de-identified aggregate statistics.

**Audit requirement:** Read access logged for accountability.

---

## Testing

### Test Cases

#### Happy Path
1. clinic_owner requests quarterly patient analytics
   - **Given:** Tenant with 342 patients, varied demographics, 5 referral sources
   - **When:** GET /api/v1/analytics/patients?period=this_quarter&granularity=month
   - **Then:** 200 with 3 time-series buckets, demographics populated, referral sources list populated

2. doctor role — scoped data
   - **Given:** Doctor has treated 45 of the 342 total patients
   - **When:** GET /api/v1/analytics/patients
   - **Then:** total_active_patients = 45 (not 342)

#### Edge Cases
1. Empty clinic
   - **Given:** New tenant with 0 patients
   - **When:** GET /api/v1/analytics/patients
   - **Then:** All counts = 0, empty arrays for time-series, demographics, referral_sources

2. Cache hit scenario
   - **When:** Second request within 5 minutes with same params
   - **Then:** `cache_hit: true`, served in < 300ms

#### Error Cases
1. Invalid granularity
   - **When:** GET /api/v1/analytics/patients?granularity=hour
   - **Then:** 400 with Spanish error

2. Forbidden role (assistant)
   - **When:** assistant user requests endpoint
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** clinic_owner, doctor, assistant (for 403).

**Patients/Entities:** 20+ patients with varied `date_of_birth`, `biological_sex`, `referral_source`, spread across multiple creation dates.

### Mocking Strategy

- Redis: fakeredis.
- Database: Full tenant schema with seeded patient demographics.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] New patients over time returned with correct granularity buckets (day/week/month)
- [ ] Retention rate computed correctly per business rule definition
- [ ] Average visits per patient correct
- [ ] Demographics (age groups + sex) based on all active patients (not period-filtered)
- [ ] Referral sources aggregated and sorted by count descending
- [ ] Doctor role scoped to their patient cohort
- [ ] 5-minute Redis cache applied; cache_hit flag accurate
- [ ] 403 for unauthorized roles
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Individual patient-level drill-down
- Patient satisfaction/NPS metrics
- Geographic distribution analytics
- Insurance/EPS coverage analytics
- Patient lifetime value (LTV) calculations
- Cohort analysis

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined
- [x] All outputs defined
- [x] API contract defined
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated
- [x] Input sanitization defined
- [x] SQL injection prevented
- [x] No PHI exposure
- [x] Audit trail defined

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated
- [x] DB queries optimized
- [x] Pagination defined

### Hook 5: Observability
- [x] Structured logging
- [x] Audit log entries defined
- [x] Error tracking
- [x] Queue job monitoring

### Hook 6: Testability
- [x] Test cases enumerated
- [x] Test data requirements specified
- [x] Mocking strategy defined
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
