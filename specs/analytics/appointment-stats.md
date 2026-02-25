# AN-03 — Appointment Analytics Spec

---

## Overview

**Feature:** Appointment analytics endpoint. Returns appointment efficiency and utilization metrics: utilization rate per doctor, average duration vs scheduled duration, cancellation rate, no-show rate, peak hours heatmap data (hour × day-of-week grid), and appointment type distribution. Supports date range filtering. clinic_owner sees clinic-wide; doctor sees own appointments.

**Domain:** analytics

**Priority:** Medium

**Dependencies:** AN-01 (dashboard), appointments (sprint 5-6), users/list-team, infra/caching-strategy.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor
- **Tenant context:** Required — resolved from JWT
- **Special rules:** doctor role is automatically scoped to their own appointments. clinic_owner sees all doctors. assistant/receptionist cannot access analytics.

---

## Endpoint

```
GET /api/v1/analytics/appointments
```

**Rate Limiting:**
- 20 requests per minute per user

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
| period | No | string | Enum: `today`, `this_week`, `this_month`, `this_quarter`, `this_year`, `custom`. Default: `this_month` | Date range preset | `this_month` |
| date_from | Conditional | string | ISO 8601 date. Required when period=custom | Custom range start | `2026-02-01` |
| date_to | Conditional | string | ISO 8601 date. Required when period=custom; >= date_from; max 366 days | Custom range end | `2026-02-28` |
| doctor_id | No | string (UUID) | Only valid for clinic_owner role | Filter to single doctor | `b2c3d4e5-0002-0002-0002-b2c3d4e5f6a7` |

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
    "timezone": "string (IANA)"
  },
  "summary": {
    "total_scheduled": "integer",
    "completed": "integer",
    "no_shows": "integer",
    "cancelled": "integer",
    "rescheduled": "integer",
    "no_show_rate": "number (percentage)",
    "cancellation_rate": "number (percentage)",
    "completion_rate": "number (percentage)"
  },
  "duration_analysis": {
    "average_scheduled_minutes": "number",
    "average_actual_minutes": "number",
    "duration_accuracy_rate": "number (percentage — how often actual matches scheduled within 10%)",
    "overrun_rate": "number (percentage of appointments that ran > 10% over scheduled)"
  },
  "utilization_by_doctor": [
    {
      "doctor_id": "uuid",
      "doctor_name": "string",
      "total_available_slots": "integer",
      "used_slots": "integer",
      "utilization_rate": "number (percentage)",
      "average_daily_appointments": "number",
      "no_show_rate": "number (percentage)"
    }
  ],
  "peak_hours_heatmap": [
    {
      "day_of_week": "integer (0=Monday, 6=Sunday)",
      "day_name": "string (Lunes, Martes, ...)",
      "hours": [
        {
          "hour": "integer (0-23)",
          "appointment_count": "integer",
          "intensity": "number (0.0-1.0 normalized — 0=no appointments, 1=busiest slot)"
        }
      ]
    }
  ],
  "appointment_type_distribution": [
    {
      "appointment_type": "string",
      "count": "integer",
      "percentage": "number",
      "average_duration_minutes": "number"
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
    "preset": "this_month",
    "date_from": "2026-02-01",
    "date_to": "2026-02-25",
    "timezone": "America/Bogota"
  },
  "summary": {
    "total_scheduled": 187,
    "completed": 162,
    "no_shows": 12,
    "cancelled": 13,
    "rescheduled": 8,
    "no_show_rate": 6.4,
    "cancellation_rate": 6.95,
    "completion_rate": 86.6
  },
  "duration_analysis": {
    "average_scheduled_minutes": 45.2,
    "average_actual_minutes": 48.7,
    "duration_accuracy_rate": 72.3,
    "overrun_rate": 21.4
  },
  "utilization_by_doctor": [
    {
      "doctor_id": "a1b2c3d4-0001-0001-0001-a1b2c3d4e5f6",
      "doctor_name": "Dr. García",
      "total_available_slots": 160,
      "used_slots": 142,
      "utilization_rate": 88.75,
      "average_daily_appointments": 7.1,
      "no_show_rate": 5.6
    }
  ],
  "peak_hours_heatmap": [
    {
      "day_of_week": 0,
      "day_name": "Lunes",
      "hours": [
        {"hour": 8, "appointment_count": 12, "intensity": 0.8},
        {"hour": 9, "appointment_count": 15, "intensity": 1.0},
        {"hour": 10, "appointment_count": 13, "intensity": 0.87},
        {"hour": 14, "appointment_count": 10, "intensity": 0.67},
        {"hour": 15, "appointment_count": 8, "intensity": 0.53}
      ]
    }
  ],
  "appointment_type_distribution": [
    {"appointment_type": "Consulta general", "count": 68, "percentage": 36.4, "average_duration_minutes": 30.0},
    {"appointment_type": "Limpieza dental", "count": 45, "percentage": 24.1, "average_duration_minutes": 60.0},
    {"appointment_type": "Endodoncia", "count": 28, "percentage": 15.0, "average_duration_minutes": 90.0},
    {"appointment_type": "Ortodoncia seguimiento", "count": 24, "percentage": 12.8, "average_duration_minutes": 20.0},
    {"appointment_type": "Extracción", "count": 22, "percentage": 11.8, "average_duration_minutes": 45.0}
  ],
  "generated_at": "2026-02-25T10:30:00Z",
  "cache_hit": false
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid `period`, `date_from` > `date_to`, missing custom range dates, date range > 366 days, `doctor_id` used by doctor role.

**Example:**
```json
{
  "error": "parametro_invalido",
  "message": "El rango de fechas no puede superar 366 días.",
  "details": {
    "date_to": ["El rango máximo permitido es de 366 días."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. See `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Role not in `[clinic_owner, doctor]`.

#### 422 Unprocessable Entity
**When:** Date strings cannot be parsed as valid ISO 8601 dates.

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Aggregation query failure or heatmap computation error.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT — extract `user_id`, `tenant_id`, `role`. Authorize.
2. Parse and validate query parameters. Compute date range from preset using tenant timezone.
3. Determine doctor scope filter.
4. Build cache key and check Redis.
5. On cache miss, execute concurrent analytics queries:

   **Summary counts:** Single aggregate query grouping by `status` (scheduled/completed/no_show/cancelled/rescheduled) with `COUNT(*)` per group.

   **Duration analysis:** For completed appointments only, compute AVG(`actual_end_time - actual_start_time`) and AVG(`scheduled_duration_minutes`). Compute `duration_accuracy_rate` as percentage of appointments where `|actual_minutes - scheduled_minutes| / scheduled_minutes <= 0.10`. Compute `overrun_rate` as percentage where actual > scheduled * 1.10.

   **Utilization by doctor:** For each doctor in scope, compute:
   - `total_available_slots` from the doctor's schedule grid (working hours blocks in period)
   - `used_slots` = COUNT of non-cancelled appointments
   - `utilization_rate` = `used_slots / total_available_slots * 100`

   **Peak hours heatmap:** `SELECT EXTRACT(DOW FROM scheduled_at), EXTRACT(HOUR FROM scheduled_at), COUNT(*) FROM appointments WHERE [scope] AND [period] AND status != 'cancelled' GROUP BY DOW, HOUR`. Results restructured into 7×24 grid. Normalize counts: `intensity = count / max_count_in_grid`.

   **Appointment type distribution:** `GROUP BY appointment_type ORDER BY COUNT(*) DESC`.

6. Assemble response, compute percentages and rates.
7. Cache response with 300-second TTL.
8. Return 200.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| period | Enum: today, this_week, this_month, this_quarter, this_year, custom | Período no válido. |
| date_from | Valid ISO date, required for custom | La fecha de inicio es requerida. |
| date_to | Valid ISO date, >= date_from, max 366-day span | La fecha de fin no puede ser anterior a la fecha de inicio. |
| doctor_id | UUID format; existence verified; only for clinic_owner | No puede filtrar por médico con su rol actual. |

**Business Rules:**

- `no_show_rate` = `no_shows / (completed + no_shows) * 100` — denominator excludes cancellations to avoid penalizing clinics with high cancellation policies.
- `cancellation_rate` = `cancelled / total_scheduled * 100`.
- `completion_rate` = `completed / total_scheduled * 100`.
- Peak hours heatmap uses the tenant's timezone for extracting hour and day-of-week from UTC timestamps.
- Duration analysis only covers completed appointments — appointments without `actual_end_time` are excluded.
- Heatmap hours with 0 appointments are included in the response with `appointment_count: 0` and `intensity: 0` only if adjacent hours have non-zero counts (sparse representation for efficiency — hours with 0 adjacent to non-zero hours are included, otherwise omitted).
- Total available slots is computed from doctor schedule templates. If no schedule template exists for a doctor, `total_available_slots = 0` and `utilization_rate = null` (not computable).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| All appointments cancelled | completion_rate = 0, no_show_rate = 0 (denominator is 0), duration_analysis nulls |
| No completed appointments | duration_analysis fields are null (cannot compute) |
| Doctor has no schedule template | utilization fields for that doctor are null |
| period=today, empty heatmap | peak_hours_heatmap returns empty arrays |
| Appointment type is null/unset | Grouped under "Sin tipo" |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- All queries READ-ONLY.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:analytics:appointments:{doctor_filter}:{date_from}:{date_to}`: SET, 300s TTL.

**Cache TTL:** 300 seconds.

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Yes.
- **Action:** read
- **Resource:** analytics_appointments
- **PHI involved:** No (aggregated data)

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 300ms (cached), < 2000ms (cache miss)
- **Maximum acceptable:** < 5000ms

### Caching Strategy
- **Strategy:** Redis cache, 5-minute TTL
- **Cache key:** `tenant:{tenant_id}:analytics:appointments:{doctor_filter_hash}:{date_from}:{date_to}`
- **TTL:** 300 seconds
- **Invalidation:** Time-based expiry

### Database Performance

**Queries executed:** 4-6 concurrent async queries

**Indexes required:**
- `appointments.(doctor_id, scheduled_at, status)` — per-doctor utilization
- `appointments.(scheduled_at, status)` — clinic-wide queries
- `appointments.(status, actual_start_time, actual_end_time)` — duration analysis
- `appointments.(appointment_type, scheduled_at)` — type distribution

**N+1 prevention:** All GROUP BY aggregate queries. No per-appointment iteration. Heatmap computed in single SQL query.

### Pagination

**Pagination:** No.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| period | Pydantic enum | |
| date_from / date_to | Pydantic date | |
| doctor_id | Pydantic UUID | Existence verified in DB |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** All strings escaped via Pydantic. Appointment type strings from DB are stored at creation time, not user-provided at query time.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None. Aggregated counts and rates only. No patient names, IDs, or clinical content.

**Audit requirement:** Read access logged for accountability.

---

## Testing

### Test Cases

#### Happy Path
1. clinic_owner requests this_month with full data
   - **Given:** 187 appointments across 2 doctors with varied statuses, types, actual durations
   - **When:** GET /api/v1/analytics/appointments?period=this_month
   - **Then:** All widgets populated correctly; rates sum consistently; heatmap has data for working hours

2. Peak hours heatmap structure
   - **When:** GET with 1 month of appointment data
   - **Then:** Heatmap has 7 day-of-week entries; each has only hours with appointment activity or adjacent-to-activity hours; intensity values normalized 0.0-1.0

#### Edge Cases
1. No appointments in period
   - **Given:** Empty appointments table for period
   - **When:** GET /api/v1/analytics/appointments
   - **Then:** All counts = 0, rates = 0, heatmap = [], type_distribution = []

2. Doctor with no schedule template
   - **Given:** Doctor exists but has no schedule template configured
   - **When:** GET /api/v1/analytics/appointments?doctor_id={doctor_id}
   - **Then:** utilization_by_doctor entry has `total_available_slots: 0, utilization_rate: null`

#### Error Cases
1. Forbidden role
   - **When:** receptionist requests endpoint
   - **Then:** 403

2. doctor_id used by doctor role
   - **When:** doctor requests with doctor_id query param
   - **Then:** 400 with Spanish error

### Test Data Requirements

**Users:** clinic_owner, 2 doctor users, receptionist (for 403).

**Patients/Entities:** 30+ appointments with varied statuses, types, and times across multiple days and hours; doctor schedule templates for utilization calculation.

### Mocking Strategy

- Redis: fakeredis.
- Database: Seeded tenant schema with appointments spread across weekdays and hours.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Summary rates (no_show, cancellation, completion) computed correctly per business rules
- [ ] Duration analysis covers only completed appointments; null when none exist
- [ ] Utilization per doctor based on schedule template availability
- [ ] Heatmap returns 7×N grid with normalized intensity values
- [ ] Appointment type distribution sorted by count descending
- [ ] doctor role scoped to own appointments
- [ ] 5-minute Redis cache; cache_hit flag accurate
- [ ] 403 for unauthorized roles
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Real-time appointment board
- Patient-level appointment history
- Appointment slot suggestion / availability forecasting
- Wait time analytics
- Inter-appointment gap analysis

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
