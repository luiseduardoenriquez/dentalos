# Update Doctor Schedule Spec

---

## Overview

**Feature:** Set or replace a doctor's full weekly working schedule, including working days, time windows, break periods, and default appointment durations by procedure type. Invalidates the appointment availability cache for the affected doctor.

**Domain:** users

**Priority:** Medium

**Dependencies:** U-07 (doctor-schedule-get.md), AP-09 (appointment availability slots)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** doctor (own schedule only), clinic_owner (any doctor in tenant)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Receptionists and assistants cannot update doctor schedules. A doctor may only update their own schedule.

---

## Endpoint

```
PUT /api/v1/users/{user_id}/schedule
```

**Rate Limiting:**
- 30 requests per minute per user (schedule updates are infrequent; stricter limit to prevent abuse)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_a1b2c3d4e5f6 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| user_id | Yes | uuid | Must be valid UUID; user must have role = doctor | The doctor's user ID to update | f47ac10b-58cc-4372-a567-0e02b2c3d479 |

### Query Parameters

None.

### Request Body Schema

```json
{
  "days": [
    {
      "day_of_week": "integer (required, 0-6, Monday=0)",
      "is_working": "boolean (required)",
      "start_time": "string | null (optional, HH:MM 24h — required if is_working=true)",
      "end_time": "string | null (optional, HH:MM 24h — required if is_working=true)",
      "breaks": [
        {
          "break_start": "string (required, HH:MM 24h)",
          "break_end": "string (required, HH:MM 24h)"
        }
      ]
    }
  ],
  "appointment_duration_defaults": {
    "procedure_type_key": "integer (minutes, required — positive integer)"
  }
}
```

**Example Request:**
```json
{
  "days": [
    {
      "day_of_week": 0,
      "is_working": true,
      "start_time": "08:00",
      "end_time": "17:00",
      "breaks": [
        { "break_start": "13:00", "break_end": "14:00" }
      ]
    },
    {
      "day_of_week": 1,
      "is_working": true,
      "start_time": "08:00",
      "end_time": "17:00",
      "breaks": []
    },
    {
      "day_of_week": 2,
      "is_working": true,
      "start_time": "08:00",
      "end_time": "17:00",
      "breaks": [
        { "break_start": "12:30", "break_end": "13:30" }
      ]
    },
    {
      "day_of_week": 3,
      "is_working": true,
      "start_time": "08:00",
      "end_time": "17:00",
      "breaks": []
    },
    {
      "day_of_week": 4,
      "is_working": true,
      "start_time": "08:00",
      "end_time": "13:00",
      "breaks": []
    },
    {
      "day_of_week": 5,
      "is_working": false,
      "start_time": null,
      "end_time": null,
      "breaks": []
    },
    {
      "day_of_week": 6,
      "is_working": false,
      "start_time": null,
      "end_time": null,
      "breaks": []
    }
  ],
  "appointment_duration_defaults": {
    "evaluacion": 20,
    "endodoncia": 80,
    "limpieza": 30,
    "urgencia": 15,
    "corona": 60
  }
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "user_id": "uuid",
  "days": [
    {
      "day_of_week": "integer (0-6)",
      "is_working": "boolean",
      "start_time": "string | null",
      "end_time": "string | null",
      "breaks": [
        { "break_start": "string", "break_end": "string" }
      ]
    }
  ],
  "appointment_duration_defaults": {
    "procedure_type_key": "integer"
  },
  "updated_at": "datetime"
}
```

**Example:**
```json
{
  "user_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "days": [
    {
      "day_of_week": 0,
      "is_working": true,
      "start_time": "08:00",
      "end_time": "17:00",
      "breaks": [{ "break_start": "13:00", "break_end": "14:00" }]
    }
  ],
  "appointment_duration_defaults": {
    "evaluacion": 20,
    "endodoncia": 80,
    "limpieza": 30,
    "urgencia": 15,
    "corona": 60
  },
  "updated_at": "2026-02-24T15:30:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Malformed JSON or missing required fields.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El cuerpo de la solicitud no es JSON valido.",
  "details": {}
}
```

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Caller is not clinic_owner and is not the target doctor. Receptionist, assistant, or a doctor trying to update another doctor's schedule.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permiso para modificar el horario de este doctor."
}
```

#### 404 Not Found
**When:** `user_id` does not exist in the tenant, or the user has a role other than `doctor`.

**Example:**
```json
{
  "error": "not_found",
  "message": "Doctor no encontrado."
}
```

#### 422 Unprocessable Entity
**When:** Validation failures — time ranges invalid, breaks outside working hours, duplicate day entries, etc.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "El horario contiene errores de validacion.",
  "details": {
    "days[0].end_time": ["La hora de fin debe ser posterior a la hora de inicio."],
    "days[0].breaks[0]": ["El descanso debe estar dentro del horario de trabajo."],
    "appointment_duration_defaults.evaluacion": ["La duracion debe ser un entero positivo mayor a 0."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or cache error during upsert.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT and extract `caller_user_id`, `caller_role`, and `tenant_id` from claims.
2. Resolve tenant schema from `tenant_id`.
3. Check RBAC: caller must be clinic_owner, or a doctor with `caller_user_id == user_id`. Reject all others with 403.
4. Query `users` table to confirm `user_id` exists and has `role = 'doctor'`. If not, return 404.
5. Parse and validate request body via Pydantic `DoctorScheduleUpdateRequest`.
6. Apply business validation rules (see Validation Rules below).
7. If validation fails, return 422 with field-level error details.
8. Upsert `doctor_schedules` table: INSERT or UPDATE the single schedule row for this doctor (UPSERT pattern — replace entire schedule atomically).
9. Invalidate Redis cache keys:
   - `tenant:{tenant_id}:user:{user_id}:schedule`
   - `tenant:{tenant_id}:availability:doctor:{user_id}:*` (wildcard delete — all availability slots for this doctor)
10. Write audit log entry: action=`update`, resource=`doctor_schedule`, actor=`caller_user_id`.
11. Serialize updated schedule via Pydantic `DoctorScheduleResponse`.
12. Return 200 with the updated schedule.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| days | Must contain exactly 7 entries, one per day (0-6) | "El horario debe incluir los 7 dias de la semana (0-6)." |
| days[].day_of_week | Must be unique within the request (no duplicate days) | "El dia {n} aparece mas de una vez en el horario." |
| days[].start_time | Required when is_working=true | "La hora de inicio es obligatoria para los dias laborales." |
| days[].end_time | Required when is_working=true | "La hora de fin es obligatoria para los dias laborales." |
| days[].end_time | Must be strictly after start_time | "La hora de fin debe ser posterior a la hora de inicio." |
| days[].end_time - start_time | Minimum working window: 30 minutes | "El horario laboral debe tener al menos 30 minutos de duracion." |
| days[].breaks[].break_start | Must be >= working start_time | "El descanso debe comenzar dentro del horario de trabajo." |
| days[].breaks[].break_end | Must be <= working end_time | "El descanso debe terminar dentro del horario de trabajo." |
| days[].breaks[].break_end | Must be strictly after break_start | "La hora de fin del descanso debe ser posterior a la hora de inicio." |
| days[].breaks | No two breaks may overlap | "Los periodos de descanso no pueden superponerse." |
| appointment_duration_defaults | Must include the 4 standard keys: evaluacion, endodoncia, limpieza, urgencia | "Los tipos de cita estandar son obligatorios: evaluacion, endodoncia, limpieza, urgencia." |
| appointment_duration_defaults[value] | Must be a positive integer > 0 and <= 480 (8 hours) | "La duracion debe ser un numero entero entre 1 y 480 minutos." |
| days[].start_time / end_time format | Must match HH:MM with valid hours 00-23, minutes 00-59 | "Formato de hora invalido. Use HH:MM en formato de 24 horas." |

**Business Rules:**

- The PUT replaces the entire schedule atomically. Partial updates are not supported.
- The 4 standard procedure types (`evaluacion`, `endodoncia`, `limpieza`, `urgencia`) are always required in `appointment_duration_defaults`. Additional custom types are allowed.
- Non-working days (`is_working=false`) must have `start_time=null`, `end_time=null`, and `breaks=[]`.
- Schedule changes take effect immediately for future appointment slot calculations.
- Existing confirmed appointments are NOT automatically cancelled or modified when the schedule changes; that is handled by the appointment domain.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Doctor sets all 7 days as non-working | Valid — 200 OK with all days is_working=false |
| Doctor sends exactly minimum working window (30 min) | Valid — accepted |
| Break covers entire working window | 422 — remaining net working time would be 0 |
| Request omits one day (e.g., day 3) | 422 — all 7 days required |
| Custom procedure type key with spaces or special chars | 422 — procedure type keys must match pattern `^[a-z_]{1,50}$` |
| Upsert when no previous schedule existed | Creates new row — 200 OK |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `doctor_schedules`: UPSERT — full replace of the doctor's schedule row.

**Example query (SQLAlchemy):**
```python
stmt = insert(DoctorSchedule).values(
    user_id=user_id,
    schedule_data=schedule_json,
    appointment_duration_defaults=duration_defaults,
    updated_at=datetime.utcnow()
).on_conflict_do_update(
    index_elements=["user_id"],
    set_={
        "schedule_data": schedule_json,
        "appointment_duration_defaults": duration_defaults,
        "updated_at": datetime.utcnow()
    }
)
await session.execute(stmt)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:user:{user_id}:schedule`: DELETE — invalidated on schedule update.
- `tenant:{tenant_id}:availability:doctor:{user_id}:*`: DELETE (wildcard) — all appointment availability slots for this doctor are invalidated.

**Cache TTL:** N/A (deletion).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| appointments | `recalculate_doctor_availability` | `{ tenant_id, user_id, effective_date: today }` | After successful schedule upsert |

### Audit Log

**Audit entry:** Yes — see `infra/audit-logging.md`.

**If Yes:**
- **Action:** update
- **Resource:** doctor_schedule
- **PHI involved:** No

### Notifications

**Notifications triggered:** No. (Notification to clinic owner when a doctor self-updates their schedule is out of scope for v1.)

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** No caching on write. Invalidates existing cache entries.
- **Cache key:** N/A (write operation)
- **TTL:** N/A
- **Invalidation:** Deletes `schedule` and `availability:*` keys for this doctor.

### Database Performance

**Queries executed:** 2 (user role check + schedule upsert)

**Indexes required:**
- `users.id` — PRIMARY KEY (exists)
- `doctor_schedules.user_id` — UNIQUE INDEX (enforces one schedule per doctor, enables fast upsert)

**N+1 prevention:** Not applicable — single doctor operation.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| user_id (URL param) | Pydantic UUID validator | Rejects non-UUID strings |
| days[].start_time / end_time | Pydantic pattern validator `^\d{2}:\d{2}$` | Strict HH:MM format |
| breaks[].break_start / break_end | Pydantic pattern validator `^\d{2}:\d{2}$` | Strict HH:MM format |
| appointment_duration_defaults keys | Pydantic pattern validator `^[a-z_]{1,50}$` | Lowercase letters and underscores only |
| appointment_duration_defaults values | Pydantic int validator, range 1-480 | Prevents absurdly large durations |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None. Doctor working schedules are operational data, not PHI.

**Audit requirement:** Write-only logged (schedule update audited for accountability).

---

## Testing

### Test Cases

#### Happy Path
1. Clinic owner updates a doctor's full weekly schedule
   - **Given:** Valid clinic_owner JWT, doctor exists in tenant
   - **When:** PUT /api/v1/users/{user_id}/schedule with valid 7-day payload
   - **Then:** 200 with updated schedule, cache invalidated, availability recalculation job queued

2. Doctor updates own schedule
   - **Given:** Valid doctor JWT, `user_id` matches caller
   - **When:** PUT /api/v1/users/{user_id}/schedule with valid payload
   - **Then:** 200 with updated schedule

3. First-time schedule set (no prior schedule row)
   - **Given:** Doctor has never configured a schedule
   - **When:** PUT /api/v1/users/{user_id}/schedule with valid payload
   - **Then:** 200, new row created in `doctor_schedules`

4. Schedule with custom procedure type
   - **Given:** Payload includes `corona: 60` in addition to standard types
   - **When:** PUT /api/v1/users/{user_id}/schedule
   - **Then:** 200, custom type persisted and returned in response

#### Edge Cases
1. All 7 days set to non-working
   - **Given:** All days have `is_working: false`
   - **When:** PUT /api/v1/users/{user_id}/schedule
   - **Then:** 200 — valid configuration accepted

2. Doctor updates own schedule, replaces previous breaks
   - **Given:** Doctor previously had a break on Monday, now sends no breaks
   - **When:** PUT /api/v1/users/{user_id}/schedule with `breaks: []` for Monday
   - **Then:** 200, previous breaks removed

#### Error Cases
1. Doctor tries to update another doctor's schedule
   - **Given:** Valid doctor JWT, `user_id` belongs to a different doctor
   - **When:** PUT /api/v1/users/{other_doctor_id}/schedule
   - **Then:** 403 Forbidden

2. end_time before start_time
   - **Given:** day_of_week=0 has start_time=17:00, end_time=08:00
   - **When:** PUT /api/v1/users/{user_id}/schedule
   - **Then:** 422 with field error on days[0].end_time

3. Break outside working hours
   - **Given:** Working 08:00-17:00, break 17:00-18:00
   - **When:** PUT /api/v1/users/{user_id}/schedule
   - **Then:** 422 with field error on days[0].breaks[0]

4. Missing standard procedure type
   - **Given:** `appointment_duration_defaults` omits `urgencia`
   - **When:** PUT /api/v1/users/{user_id}/schedule
   - **Then:** 422 with error on `appointment_duration_defaults`

5. Only 6 days provided (missing day 6)
   - **Given:** `days` array has 6 entries
   - **When:** PUT /api/v1/users/{user_id}/schedule
   - **Then:** 422 "El horario debe incluir los 7 dias de la semana."

6. Receptionist attempts to update a doctor's schedule
   - **Given:** Valid receptionist JWT
   - **When:** PUT /api/v1/users/{user_id}/schedule
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** One clinic_owner, two doctors (one with existing schedule, one without), one receptionist.

**Patients/Entities:** None.

### Mocking Strategy

- Redis: Use `fakeredis` for cache invalidation tests.
- RabbitMQ: Mock `recalculate_doctor_availability` job dispatch; verify payload.
- Database: Use test tenant schema with seeded `doctor_schedules`.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] PUT /api/v1/users/{user_id}/schedule returns 200 with updated schedule
- [ ] Full 7-day schedule is required; partial updates rejected with 422
- [ ] All validation rules enforced: end > start, breaks within hours, no overlap, standard types present
- [ ] Schedule cache key invalidated on success
- [ ] Appointment availability cache keys invalidated on success
- [ ] Availability recalculation job dispatched to RabbitMQ
- [ ] clinic_owner can update any doctor's schedule; doctor can only update own
- [ ] Receptionist and assistant receive 403
- [ ] Non-doctor user_id returns 404
- [ ] Audit log entry written for schedule updates
- [ ] All test cases pass
- [ ] Performance target met (< 200ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Reading the schedule (see U-07: doctor-schedule-get.md)
- Partial schedule updates (entire schedule replaced on each PUT)
- Exception dates (e.g., doctor off on a specific calendar date)
- Automatic cancellation or rescheduling of existing appointments affected by schedule changes (appointment domain)
- Timezone storage — times stored as-is in HH:MM; tenant timezone context handled at the application layer

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (role + tenant)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (domain separation)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (role + tenant context)
- [x] Input sanitization defined (Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (tenant-namespaced)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy for external services
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
