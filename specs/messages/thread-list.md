# MS-02 List Message Threads Spec

---

## Overview

**Feature:** List all message threads for the authenticated tenant. Supports filtering by patient, unread status, and full-text search on subject or message content. Returns thread summaries with last message preview, unread count, and patient info. Ordered by last_message_at descending (most recent activity first). Cursor-based pagination.

**Domain:** messages

**Priority:** Medium

**Dependencies:** MS-01 (thread-create.md), MS-03 (message-send.md), MS-05 (message-mark-read.md), infra/authentication-rules.md, infra/caching.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist, patient (own threads only)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Patients see only threads where they are a participant. Staff see all threads in the tenant. A doctor may optionally filter to threads for their own patients.

---

## Endpoint

```
GET /api/v1/messages/threads
```

**Rate Limiting:**
- Inherits global rate limit (100 requests per minute per user)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| patient_id | No | UUID | Valid UUID v4 | Filter to threads with a specific patient | pt_550e8400... |
| is_unread | No | boolean | true or false | Filter to threads with unread messages for the current user | true |
| search | No | string | Max 100 chars | Search in thread subject and most recent message content | recordatorio |
| cursor | No | string | Opaque base64 cursor | Pagination cursor from previous response | eyJpZCI6Ii4uLiJ9 |
| limit | No | integer | Min 1, max 100, default 20 | Page size | 20 |

### Request Body Schema

None — GET request.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "threads": [
    {
      "id": "uuid",
      "patient": {
        "id": "uuid",
        "first_name": "string",
        "last_name": "string",
        "avatar_url": "string | null"
      },
      "subject": "string | null",
      "status": "string — open or closed",
      "last_message_preview": "string — first 100 chars of the most recent message",
      "last_message_at": "string ISO 8601",
      "last_message_sender": {
        "id": "uuid",
        "first_name": "string",
        "last_name": "string",
        "role": "string"
      },
      "unread_count": "integer — unread count for the current authenticated user",
      "created_at": "string ISO 8601"
    }
  ],
  "pagination": {
    "next_cursor": "string | null",
    "has_more": "boolean"
  }
}
```

**Example:**
```json
{
  "threads": [
    {
      "id": "thr-aaaa-1111-bbbb-2222-cccc33334444",
      "patient": {
        "id": "pt_550e8400-e29b-41d4-a716-446655440000",
        "first_name": "Maria",
        "last_name": "Garcia Lopez",
        "avatar_url": null
      },
      "subject": "Recordatorio de cita y cuidados post-operatorios",
      "status": "open",
      "last_message_preview": "Hola Maria, te escribimos para recordarte tu cita del proximo martes a las 10am. Tambien te en",
      "last_message_at": "2026-02-25T14:30:00-05:00",
      "last_message_sender": {
        "id": "pt_550e8400-e29b-41d4-a716-446655440000",
        "first_name": "Maria",
        "last_name": "Garcia Lopez",
        "role": "patient"
      },
      "unread_count": 1,
      "created_at": "2026-02-25T11:00:00-05:00"
    },
    {
      "id": "thr-eeee-5555-ffff-6666-aaaa77778888",
      "patient": {
        "id": "pt_660f9511-f30c-52e5-b827-557766551111",
        "first_name": "Juan",
        "last_name": "Perez",
        "avatar_url": null
      },
      "subject": null,
      "status": "open",
      "last_message_preview": "Claro, tiene cita el viernes 28 de febrero a las 3pm. Recuerda traer sus examenes previos.",
      "last_message_at": "2026-02-24T16:00:00-05:00",
      "last_message_sender": {
        "id": "usr-receptionist-0001-000000000000",
        "first_name": "Laura",
        "last_name": "Torres",
        "role": "receptionist"
      },
      "unread_count": 0,
      "created_at": "2026-02-24T10:00:00-05:00"
    }
  ],
  "pagination": {
    "next_cursor": "eyJsYXN0X21lc3NhZ2VfYXQiOiIyMDI2LTAyLTI0VDE2OjAwOjAwWiIsImlkIjoidGhyLWVlZWUtNTU1NS1mZmZmLTY2NjYtYWFhYTc3Nzc4ODg4In0=",
    "has_more": true
  }
}
```

### Error Responses

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Patient tries to filter by a different patient's threads.

**Example:**
```json
{
  "error": "forbidden",
  "message": "Solo puedes ver tus propios mensajes."
}
```

#### 422 Unprocessable Entity
**When:** Invalid query parameter values.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Parametros de consulta invalidos.",
  "details": {
    "limit": ["El limite debe estar entre 1 y 100."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT; extract `tenant_id`, `user_id`, `role`.
2. If `role = patient`:
   - Automatically scope to threads where the patient is a participant (`thread_participants.user_id = user_id`).
   - If `patient_id` query param is provided and does not match the patient's own patient record, return 403.
3. For staff roles: if `patient_id` provided, filter to threads for that patient only.
4. Validate query parameters.
5. Decode `cursor` if provided: `{ "last_message_at": "ISO datetime", "id": "uuid" }`.
6. Build base query:
   ```sql
   SELECT
     t.id, t.subject, t.status, t.created_at, t.last_message_at,
     p.id AS patient_id, p.first_name, p.last_name, p.avatar_url,
     m.content AS last_message_content, m.sender_id,
     su.first_name AS sender_first_name, su.last_name AS sender_last_name, su.role AS sender_role,
     COALESCE(tp.last_read_at, '1970-01-01') AS caller_last_read_at
   FROM message_threads t
   JOIN patients p ON p.id = t.patient_id
   JOIN messages m ON m.id = t.last_message_id
   JOIN users su ON su.id = m.sender_id
   LEFT JOIN thread_participants tp ON tp.thread_id = t.id AND tp.user_id = :user_id
   WHERE t.tenant_id = :tenant_id
   ```
7. Apply filters:
   - `patient_id`: `AND t.patient_id = :patient_id`
   - `is_unread = true`: `AND (tp.last_read_at IS NULL OR m.created_at > tp.last_read_at)` — thread has messages newer than last_read_at for this user
   - `search`: `AND (t.subject ILIKE :pattern OR m.content ILIKE :pattern)`
   - Cursor: `AND (t.last_message_at, t.id) < (:last_message_at, :id)` (descending keyset pagination)
8. ORDER BY `t.last_message_at DESC, t.id DESC`
9. LIMIT `:limit + 1` to determine `has_more`.
10. Compute `unread_count` per thread: count messages in thread where `created_at > caller_last_read_at` and `sender_id != user_id`. Can be computed from a subquery or cached in `message_threads.unread_counts` JSONB field (updated on each message insert).
11. Truncate `last_message_preview` to 100 chars.
12. Build pagination cursor from last item's (`last_message_at`, `id`).
13. Return 200.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUID v4 (if provided) | Parametro patient_id invalido. |
| search | Max 100 chars (if provided) | La busqueda no puede superar 100 caracteres. |
| limit | Integer 1-100 | El limite debe estar entre 1 y 100. |
| cursor | Valid base64-decodable JSON with last_message_at and id | Cursor de paginacion invalido. |

**Business Rules:**

- `unread_count` is computed relative to the authenticated caller. Staff member A and Staff member B can have different unread counts for the same thread.
- `last_message_preview` is always the content of the most recently sent message (the message with the highest `created_at` in the thread), regardless of who sent it.
- Patient role sees only threads they participate in. They cannot see threads created for other patients even if they share the same doctor.
- The `last_message_id` field on `message_threads` is updated every time a new message is inserted in a thread (maintained by MS-03 message-send). This avoids a subquery to find the last message.
- `search` performs case-insensitive partial match on `subject` and on the `last_message_preview` (current last message content). It does not search through all historical messages for performance reasons.
- Threads where the authenticated staff member has never had a `thread_participants` record (they never read or wrote) still appear for staff roles. The `unread_count` for such threads equals the total message count.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| is_unread=true with no unread threads | threads: [], has_more: false |
| search matches subject but not recent message | Thread appears in results |
| Patient with no threads | threads: [], has_more: false |
| Thread with deleted patient | Should not occur due to FK constraints; if soft-deleted, patient fields show stored name |
| Staff member not a participant in any thread | Staff sees all threads; unread_count=total_messages per thread |

---

## Side Effects

### Database Changes

**No write operations** — read-only endpoint.

### Cache Operations

**Cache keys affected:** None — thread list is read from DB directly. The list changes frequently enough (new messages arriving in real-time) that caching individual user-scoped lists is not beneficial.

**Cache TTL:** N/A

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** No — routine messaging inbox access; no PHI data retrieved beyond thread subjects and previews.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 100ms
- **Maximum acceptable:** < 200ms

### Caching Strategy
- **Strategy:** No response caching (real-time inbox behavior expected)
- **Cache key:** N/A

### Database Performance

**Queries executed:** 1 main query with JOINs (+ optional subquery for unread_count if not using denormalized count column)

**Indexes required:**
- `message_threads.(tenant_id, last_message_at DESC, id DESC)` — COMPOSITE INDEX for keyset pagination
- `message_threads.(tenant_id, patient_id, last_message_at DESC)` — COMPOSITE INDEX for patient filter
- `thread_participants.(thread_id, user_id)` — COMPOSITE UNIQUE INDEX
- `messages.thread_id` — INDEX (for last_message JOIN)
- `message_threads.last_message_id` — INDEX (denormalized FK for fast last message lookup)

**N+1 prevention:** All thread data retrieved in a single JOIN query. Patient info and last message sender included in the same query via JOINs.

### Pagination

**Pagination:** Yes
- **Style:** Cursor-based (keyset on `(last_message_at DESC, id DESC)`)
- **Default page size:** 20
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID | |
| search | Pydantic strip(), max_length=100 | Used in ILIKE — parameterized |
| limit | Pydantic int, ge=1, le=100 | |
| cursor | Base64 decode + JSON parse validation | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Patient first_name, last_name, message preview (may contain clinical context)

**Audit requirement:** Not required for list read (routine inbox access).

---

## Testing

### Test Cases

#### Happy Path
1. Staff lists all threads (default)
   - **Given:** Authenticated receptionist, tenant has 5 threads for 3 patients
   - **When:** GET /api/v1/messages/threads (no filters)
   - **Then:** 200 OK, up to 20 threads ordered by last_message_at DESC, unread_count per thread for this user

2. Filter by patient_id
   - **Given:** Patient A has 2 threads, Patient B has 3 threads
   - **When:** GET with patient_id=Patient A
   - **Then:** Exactly 2 threads for Patient A

3. Filter is_unread=true
   - **Given:** 5 threads; 2 have messages after staff's last_read_at
   - **When:** GET with is_unread=true
   - **Then:** Exactly 2 threads returned

4. Patient views own threads
   - **Given:** Authenticated patient, 2 threads where they are participant
   - **When:** GET
   - **Then:** Both threads returned; threads for other patients not visible

5. Cursor-based pagination
   - **Given:** 25 threads total
   - **When:** GET with limit=20, then GET with cursor from first response
   - **Then:** First page: 20 threads, has_more=true; second page: 5 threads, has_more=false

#### Edge Cases
1. No threads exist
   - **Given:** Tenant with no message threads
   - **When:** GET
   - **Then:** 200 OK, threads: [], has_more: false

2. search with no matches
   - **Given:** search="xyznotfound"
   - **When:** GET
   - **Then:** 200 OK, threads: []

#### Error Cases
1. Patient filters by different patient_id
   - **Given:** Authenticated Patient A, patient_id=Patient B's ID
   - **When:** GET
   - **Then:** 403 Forbidden

2. Invalid limit=0
   - **Given:** limit=0
   - **When:** GET
   - **Then:** 422 validation error

### Test Data Requirements

**Users:** Receptionist, doctor, 2 patients (each linked to patient records)

**Threads:** 5 threads for Patient A, 3 threads for Patient B; some with staff replies; some with patient replies

**Thread Participants:** Seeded read timestamps for receptionist and patients

### Mocking Strategy

- Database: SQLite in-memory; seed message_threads, messages, thread_participants with known timestamps
- Fixed `now()` in tests for deterministic unread calculations

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET /api/v1/messages/threads returns paginated thread list ordered by last_message_at DESC
- [ ] patient_id filter scopes to that patient's threads
- [ ] is_unread=true filter returns only threads with messages after caller's last_read_at
- [ ] search matches on subject and last message content
- [ ] Patient role sees only own threads
- [ ] Patient filtering by different patient_id returns 403
- [ ] unread_count accurate per authenticated user
- [ ] last_message_preview truncated to 100 chars
- [ ] Cursor-based pagination works with no gaps or duplicates
- [ ] All test cases pass
- [ ] Performance targets met (< 100ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Creating threads (see MS-01)
- Reading messages within a thread (see MS-04)
- Marking threads as read (see MS-05)
- Thread archiving/closing
- Real-time thread updates via WebSocket (post-MVP)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (5 query params)
- [x] All outputs defined (thread summaries + pagination)
- [x] API contract defined
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (staff + patient own)
- [x] Side effects listed (none)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (messages domain)
- [x] Tenant schema isolation
- [x] Keyset pagination
- [x] Per-user unread count

### Hook 3: Security & Privacy
- [x] Patient access scoped to own threads
- [x] ILIKE parameterized (no injection)
- [x] PHI handled appropriately

### Hook 4: Performance & Scalability
- [x] Target < 100ms
- [x] Single JOIN query
- [x] Composite indexes for keyset pagination

### Hook 5: Observability
- [x] Structured logging (tenant_id, user_id, filters)
- [x] Error tracking compatible

### Hook 6: Testability
- [x] Test cases enumerated
- [x] Test data specified
- [x] Fixed timestamps for deterministic tests
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
