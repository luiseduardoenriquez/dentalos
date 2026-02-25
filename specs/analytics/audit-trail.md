# AN-07 — Audit Trail Spec

---

## Overview

**Feature:** View immutable audit trail records for clinic activities. Returns paginated, filterable audit log entries from the audit schema. Allows clinic_owner to investigate who accessed what data and when. Filters by user, action type (create/read/update/delete), resource type, date range, and patient_id. Audit records are read-only — they cannot be deleted or modified. Required for Colombian regulatory compliance (Resolución 1888 clinical record audit requirements).

**Domain:** analytics

**Priority:** Medium

**Dependencies:** A-01 (login), A-02 (me), infra/audit-logging.md, patients/patient-get, infra/authentication-rules.md, infra/caching-strategy.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner only
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only clinic_owner can access the audit trail. Doctors, assistants, receptionists, and patients cannot view audit logs. superadmin accesses a platform-wide audit trail through a separate admin endpoint. Audit trail access itself is logged to the audit system (meta-audit).

---

## Endpoint

```
GET /api/v1/analytics/audit-trail
```

**Rate Limiting:**
- 30 requests per minute per user (audit access is less frequent but should not be throttled too aggressively)

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
| user_id | No | string (UUID) | Must be a valid user in the tenant | Filter by the user who performed the action | `a1b2c3d4-0001-0001-0001-a1b2c3d4e5f6` |
| action | No | string | Enum: `create`, `read`, `update`, `delete` | Filter by action type | `read` |
| resource_type | No | string | Enum: `patient`, `clinical_record`, `odontogram`, `invoice`, `treatment_plan`, `consent`, `appointment`, `user`, `prescription`, `sterilization_record`, `analytics_dashboard`, `analytics_revenue`, `analytics_export` | Filter by resource type | `clinical_record` |
| patient_id | No | string (UUID) | Must be a valid patient in the tenant | Filter all audit entries related to a specific patient | `b2c3d4e5-0002-0002-0002-b2c3d4e5f6a7` |
| date_from | No | string | ISO 8601 date (YYYY-MM-DD). Default: 30 days ago | Filter entries from this date | `2026-02-01` |
| date_to | No | string | ISO 8601 date (YYYY-MM-DD). Default: today. Must be >= date_from. Max range: 366 days | Filter entries to this date | `2026-02-25` |
| cursor | No | string | Opaque cursor for pagination (base64-encoded) | Next page cursor | `eyJpZCI6IjEyMyJ9` |
| limit | No | integer | Min: 1, Max: 100, Default: 50 | Number of results per page | `50` |

### Request Body Schema

None. GET request.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "data": [
    {
      "id": "uuid — audit entry ID",
      "tenant_id": "uuid",
      "user_id": "uuid",
      "user_name": "string (full name of user who performed action)",
      "user_role": "string (role at time of action)",
      "action": "string (create | read | update | delete)",
      "resource_type": "string",
      "resource_id": "string | null (UUID of affected resource)",
      "resource_label": "string | null (human-readable identifier, e.g., patient name for privacy-aware display)",
      "patient_id": "string | null (UUID of associated patient, if applicable)",
      "ip_address": "string | null (anonymized — last octet zeroed: 192.168.1.0)",
      "user_agent": "string | null",
      "changes_summary": "object | null (before/after values for updates, with PHI masked)",
      "metadata": "object | null (additional context, e.g., export format, date range queried)",
      "created_at": "string (ISO 8601 datetime — when the action occurred)"
    }
  ],
  "pagination": {
    "next_cursor": "string | null",
    "has_more": "boolean",
    "total_count": "integer | null (total matching records — computed only on first page)"
  },
  "filters_applied": {
    "user_id": "string | null",
    "action": "string | null",
    "resource_type": "string | null",
    "patient_id": "string | null",
    "date_from": "string (YYYY-MM-DD)",
    "date_to": "string (YYYY-MM-DD)"
  }
}
```

**Example:**
```json
{
  "data": [
    {
      "id": "f1e2d3c4-0001-0001-0001-f1e2d3c4b5a6",
      "tenant_id": "e1d2c3b4-0000-0000-0000-e1d2c3b4a596",
      "user_id": "a1b2c3d4-0001-0001-0001-a1b2c3d4e5f6",
      "user_name": "Dr. Carlos García",
      "user_role": "doctor",
      "action": "read",
      "resource_type": "clinical_record",
      "resource_id": "c4d5e6f7-0004-0004-0004-c4d5e6f7a8b9",
      "resource_label": "Historia clínica #2024-0042",
      "patient_id": "b2c3d4e5-0002-0002-0002-b2c3d4e5f6a7",
      "ip_address": "192.168.1.0",
      "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) DentalOS/1.0",
      "changes_summary": null,
      "metadata": null,
      "created_at": "2026-02-25T09:45:12Z"
    },
    {
      "id": "g2f3e4d5-0002-0002-0002-g2f3e4d5c6b7",
      "tenant_id": "e1d2c3b4-0000-0000-0000-e1d2c3b4a596",
      "user_id": "a1b2c3d4-0001-0001-0001-a1b2c3d4e5f6",
      "user_name": "Dr. Carlos García",
      "user_role": "doctor",
      "action": "update",
      "resource_type": "odontogram",
      "resource_id": "d5e6f7a8-0005-0005-0005-d5e6f7a8b9c0",
      "resource_label": "Odontograma — Vista general",
      "patient_id": "b2c3d4e5-0002-0002-0002-b2c3d4e5f6a7",
      "ip_address": "192.168.1.0",
      "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) DentalOS/1.0",
      "changes_summary": {
        "tooth_18": {
          "before": {"condition": "healthy"},
          "after": {"condition": "caries_initial", "surface": ["occlusal"]}
        }
      },
      "metadata": null,
      "created_at": "2026-02-25T09:48:33Z"
    },
    {
      "id": "h3g4f5e6-0003-0003-0003-h3g4f5e6d7c8",
      "tenant_id": "e1d2c3b4-0000-0000-0000-e1d2c3b4a596",
      "user_id": "b3c4d5e6-0002-0002-0002-b3c4d5e6f7a8",
      "user_name": "Dra. Ana López",
      "user_role": "doctor",
      "action": "read",
      "resource_type": "analytics_revenue",
      "resource_id": null,
      "resource_label": "Análisis de ingresos — Febrero 2026",
      "patient_id": null,
      "ip_address": "10.0.0.0",
      "user_agent": "Mozilla/5.0 DentalOS/1.0",
      "changes_summary": null,
      "metadata": {
        "date_from": "2026-02-01",
        "date_to": "2026-02-25",
        "report_scope": "self"
      },
      "created_at": "2026-02-25T10:02:45Z"
    }
  ],
  "pagination": {
    "next_cursor": "eyJpZCI6ImgzZzRmNWU2LTAwMDMifQ==",
    "has_more": true,
    "total_count": 1247
  },
  "filters_applied": {
    "user_id": null,
    "action": null,
    "resource_type": null,
    "patient_id": null,
    "date_from": "2026-02-25",
    "date_to": "2026-02-25"
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid enum value for `action` or `resource_type`, `date_from` > `date_to`, date range > 366 days, malformed cursor.

**Example:**
```json
{
  "error": "parametro_invalido",
  "message": "El tipo de acción especificado no es válido.",
  "details": {
    "action": ["Valores permitidos: create, read, update, delete."]
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token.

#### 403 Forbidden
**When:** Role is not clinic_owner.

**Example:**
```json
{
  "error": "acceso_denegado",
  "message": "Solo el propietario de la clínica puede acceder al registro de auditoría.",
  "details": {}
}
```

#### 404 Not Found
**When:** `user_id` filter specifies a user that does not exist in the tenant. `patient_id` filter specifies a patient that does not exist.

#### 422 Unprocessable Entity
**When:** UUID parameters cannot be parsed, cursor malformed.

#### 429 Too Many Requests
**When:** Rate limit exceeded.

#### 500 Internal Server Error
**When:** Audit schema query failure.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT — extract `user_id`, `tenant_id`, `role`. Authorize: if role != `clinic_owner`, return 403.
2. Parse and validate all query parameters with Pydantic `AuditTrailQueryParams`.
3. Apply default date range: `date_to = today`, `date_from = today - 30 days` if not provided.
4. Validate `user_id` filter if provided — check existence in tenant users table. Return 404 if not found.
5. Validate `patient_id` filter if provided — check existence in tenant patients table. Return 404 if not found.
6. Query the audit schema. The audit table is in a separate schema (not the tenant schema) to ensure immutability even if the tenant schema is compromised or migrated. The audit table is `audit.events` and is partitioned by `tenant_id`.

   ```sql
   SELECT ae.*, u.full_name AS user_name, u.role AS user_role
   FROM audit.events ae
   JOIN {tenant_schema}.users u ON ae.user_id = u.id
   WHERE ae.tenant_id = :tenant_id
     AND ae.created_at::date BETWEEN :date_from AND :date_to
     [AND ae.user_id = :user_id IF filter provided]
     [AND ae.action = :action IF filter provided]
     [AND ae.resource_type = :resource_type IF filter provided]
     [AND ae.patient_id = :patient_id IF filter provided]
     [AND (ae.created_at, ae.id) < (:cursor_created_at, :cursor_id) IF cursor]
   ORDER BY ae.created_at DESC, ae.id DESC
   LIMIT :limit + 1
   ```

7. Compute `total_count` only on the first page (no cursor provided) using a `COUNT(*)` query with the same filters. Cache count separately with 60-second TTL.
8. Determine `has_more` and encode `next_cursor`.
9. Anonymize IP addresses: zero out the last octet of IPv4, zero out the last 80 bits of IPv6.
10. Mask sensitive fields in `changes_summary`: patient date_of_birth (show only year), document numbers masked to `***{last4}`, raw clinical note text replaced with `"[contenido omitido]"`.
11. Log the audit trail access itself to the audit system: `{"action": "read", "resource_type": "audit_trail", "user_id": current_user.id, "tenant_id": tenant_id, "filters": {...}}`.
12. Return 200 with paginated results.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| action | One of: create, read, update, delete | El tipo de acción especificado no es válido. |
| resource_type | One of the 13 valid resource types | El tipo de recurso especificado no es válido. |
| user_id | Valid UUID, must exist in tenant | El usuario especificado no existe en esta clínica. |
| patient_id | Valid UUID, must exist in tenant | El paciente especificado no existe en esta clínica. |
| date_from | Valid ISO 8601 date | Formato de fecha inválido. |
| date_to | Valid ISO 8601 date; >= date_from; max 366 days from date_from | El rango de fechas no puede superar 366 días. |
| limit | Integer 1-100 | El límite debe estar entre 1 y 100. |
| cursor | Valid base64-encoded JSON {id, created_at} | El cursor de paginación tiene un formato inválido. |

**Business Rules:**

- Audit records are **immutable** — no UPDATE or DELETE is ever performed on `audit.events`. This is enforced at the database level with a PostgreSQL trigger that raises an exception on any UPDATE/DELETE.
- Audit trail access is itself audited. The meta-audit entry records who viewed the audit trail and with what filters.
- IP addresses are partially anonymized in the API response (last octet zeroed) while the full IP is retained in the audit database for regulatory purposes (Colombian Resolución 1888 requires IP logging for clinical record access).
- `resource_label` is a human-readable identifier computed at query time for display — it is NOT stored in the audit record. Computed by joining with the referenced resource table. If the resource has been deleted, `resource_label` is `"[recurso eliminado]"`.
- `changes_summary` is stored as JSONB in the audit record at the time of the action. It contains before/after state for update operations. PHI in changes_summary is masked in the API response but stored unmasked in the audit table (for regulatory access by authorized inspectors via a separate privileged process).
- Default date range is 30 days to prevent accidental full-history loads on large tenants.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| No audit entries in date range | Returns empty `data: []`, `total_count: 0`, `has_more: false` |
| user_id filter for deleted user | Returns 404 — deleted users are not queryable |
| patient_id of deleted/deactivated patient | Returns 404 — deactivated patients not in query scope |
| Very large audit trail (100k+ entries) | Keyset pagination handles correctly; total_count cached; response within performance target |
| changes_summary contains patient date_of_birth | Year shown, month/day masked: "1985-**-**" |
| resource no longer exists in DB | resource_label = "[recurso eliminado]"; audit entry still returned |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- No writes to tenant schema (read-only).

**Audit schema tables affected:**
- `audit.events`: INSERT — meta-audit entry logging this audit trail access.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:analytics:audit_trail:count:{filter_hash}`: SET — cached total_count for first page, 60s TTL.

**Cache TTL:** 60 seconds for count cache only. List results are not cached (audit data must always be fresh).

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Yes — meta-audit of viewing the audit trail.
- **Action:** read
- **Resource:** audit_trail
- **PHI involved:** Yes — audit entries may reference patient records.

### Notifications

**Notifications triggered:** No.

---

## Performance

### Expected Response Time
- **Target:** < 200ms (default 30-day range, no filters)
- **Target (heavy filter, large range):** < 1000ms
- **Maximum acceptable:** < 2000ms

### Caching Strategy
- **Strategy:** Count cache only (60s TTL). List results always read fresh from DB.
- **Cache key:** `tenant:{tenant_id}:analytics:audit_trail:count:{hash_of_filters}`
- **TTL:** 60 seconds (count only)
- **Invalidation:** Time-based

### Database Performance

**Queries executed:** 2 (list query + count query on first page)

**Indexes required on `audit.events`:**
- `audit.events.(tenant_id, created_at DESC, id DESC)` — main pagination index
- `audit.events.(tenant_id, user_id, created_at)` — user filter
- `audit.events.(tenant_id, action, created_at)` — action filter
- `audit.events.(tenant_id, resource_type, created_at)` — resource_type filter
- `audit.events.(tenant_id, patient_id, created_at)` — patient filter
- Table is partitioned by `tenant_id` for efficient isolation

**N+1 prevention:** Single JOIN query for user name. resource_label computed in application layer only (no per-row DB lookup — use a batch JOIN or accept the resource_label from stored `resource_snapshot` JSONB in audit table).

### Pagination

**Pagination:** Yes
- **Style:** Cursor-based (keyset on `created_at DESC, id DESC`)
- **Default page size:** 50
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| user_id | Pydantic UUID + DB existence check | |
| action | Pydantic enum | |
| resource_type | Pydantic enum | |
| patient_id | Pydantic UUID + DB existence check | |
| date_from / date_to | Pydantic date | |
| limit | Pydantic int ge=1, le=100 | |
| cursor | Base64 decode + JSON parse | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable.

### Data Privacy (PHI)

**PHI fields in this endpoint:** `changes_summary` may contain PHI (patient fields changed). Masking rules:
- `date_of_birth`: show year only (`"1985-**-**"`)
- `document_number`: show only last 4 digits (`"***4567"`)
- Clinical note content: replaced with `"[contenido omitido]"`
- Patient name: shown in full (clinic_owner has authorized access)
- IP addresses: last octet zeroed in API response

**Audit requirement:** All audit trail access is itself logged (meta-audit). Required for regulatory chain of custody.

---

## Testing

### Test Cases

#### Happy Path
1. clinic_owner views default audit trail (last 30 days)
   - **Given:** 1247 audit entries in last 30 days
   - **When:** GET /api/v1/analytics/audit-trail (no filters)
   - **Then:** 200 with first 50 entries ordered by created_at DESC; total_count = 1247; next_cursor set

2. Filter by action=update
   - **Given:** 1247 entries, 312 are updates
   - **When:** GET ?action=update
   - **Then:** Returns update entries only; each has action="update"

3. Filter by patient_id
   - **Given:** Patient with 23 audit entries
   - **When:** GET ?patient_id={patient_uuid}
   - **Then:** Returns entries referencing that patient

4. Filter by resource_type=clinical_record
   - **When:** GET ?resource_type=clinical_record
   - **Then:** Only clinical_record entries returned

5. Cursor-based pagination
   - **Given:** 1247 entries, first page fetched
   - **When:** GET ?cursor={next_cursor}
   - **Then:** Next 50 entries returned; no duplicates; ordering maintained

#### Edge Cases
1. PHI masking in changes_summary
   - **Given:** Audit entry for patient update containing `date_of_birth` change
   - **When:** GET audit-trail including this entry
   - **Then:** `date_of_birth.before = "1985-**-**"`, `date_of_birth.after = "1985-**-**"` — year visible only

2. Deleted resource (resource no longer in DB)
   - **Given:** Audit entry references a clinical record that was deleted
   - **When:** GET audit-trail including this entry
   - **Then:** Entry returned with `resource_label = "[recurso eliminado]"`, no error

3. Empty result set
   - **Given:** No audit entries in selected date range
   - **When:** GET ?date_from=2026-01-01&date_to=2026-01-01
   - **Then:** `data: []`, `total_count: 0`, `has_more: false`

#### Error Cases
1. doctor role attempts access
   - **Given:** Authenticated doctor
   - **When:** GET /api/v1/analytics/audit-trail
   - **Then:** 403 with Spanish error

2. Invalid user_id filter
   - **When:** GET ?user_id=non-existent-uuid
   - **Then:** 404 — user not found in tenant

3. date_from > date_to
   - **When:** GET ?date_from=2026-02-25&date_to=2026-02-01
   - **Then:** 400 with Spanish error

4. Date range > 366 days
   - **When:** GET ?date_from=2024-01-01&date_to=2026-02-25
   - **Then:** 400 with Spanish error

5. Meta-audit verification
   - **Given:** clinic_owner views audit trail
   - **When:** Check audit.events for meta-entry
   - **Then:** Entry exists with action=read, resource_type=audit_trail, user_id=clinic_owner

### Test Data Requirements

**Users:** clinic_owner, doctor (for 403), assistant (for 403). Active users in test tenant.

**Patients/Entities:** `audit.events` table seeded with 100+ entries across varied action types, resource types, and user IDs. Some entries with patient_id, some without. Some with `changes_summary` containing PHI fields.

### Mocking Strategy

- Redis: fakeredis for count cache tests.
- Database: Test tenant with `audit.events` seeded; PHI masking tested against known entries.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Only clinic_owner can access — 403 for all other roles
- [ ] Default date range (30 days) applied when no date filters provided
- [ ] Cursor-based pagination works correctly for large audit trails
- [ ] `total_count` returned on first page (no cursor); null on subsequent pages
- [ ] Filters by user_id, action, resource_type, patient_id work correctly and in combination
- [ ] IP addresses anonymized (last octet zeroed) in API response
- [ ] PHI masking in changes_summary: date_of_birth year-only, document number last-4, clinical notes omitted
- [ ] resource_label shows "[recurso eliminado]" for references to deleted resources
- [ ] Audit trail access itself logged to audit.events (meta-audit)
- [ ] user_id and patient_id filters return 404 when not found in tenant
- [ ] Rate limit 30 req/min enforced
- [ ] Response time < 200ms for default range
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Admin-level platform audit trail across all tenants (superadmin feature)
- Audit trail deletion or archival
- Export of audit trail to CSV/PDF (may be added for compliance reporting)
- Real-time audit stream (WebSocket)
- Audit trail notifications (e.g., alert when specific action occurs)
- Automated anomaly detection on audit trail
- Audit trail for system-level events (server start/stop, deploys) — ops monitoring scope

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined
- [x] All outputs defined
- [x] API contract defined
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (clinic_owner only)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries
- [x] Reads from audit schema (separate from tenant schema — immutability)
- [x] Matches FastAPI conventions
- [x] Database models match infra/audit-logging.md

### Hook 3: Security & Privacy
- [x] Auth level stated (clinic_owner only — privileged)
- [x] Input sanitization defined
- [x] SQL injection prevented
- [x] PHI masking rules defined
- [x] Audit trail access itself audited (meta-audit)

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Count cache applied (60s TTL)
- [x] DB indexes listed (including partitioned table)
- [x] Cursor pagination for large datasets

### Hook 5: Observability
- [x] Structured logging
- [x] Meta-audit entry on every access
- [x] Error tracking
- [x] Queue job monitoring

### Hook 6: Testability
- [x] Test cases enumerated
- [x] PHI masking test cases
- [x] Meta-audit test case
- [x] Test data requirements specified

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
