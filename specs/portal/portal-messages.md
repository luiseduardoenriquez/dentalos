# PP-10 Portal Messages Spec

---

## Overview

**Feature:** List in-app message threads between the patient and the clinic from the portal. Shows thread previews, unread count, last message timestamp, and last message preview. Polling-based (every 30s) for MVP — no WebSocket. Read-only list; sending messages is PP-11.

**Domain:** portal

**Priority:** Medium

**Dependencies:** PP-01 (portal-login.md), PP-11 (portal-message-send.md), MS-01 (thread-create.md), MS-02 (thread-list.md), infra/multi-tenancy.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** patient (portal scope only)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Portal-scoped JWT required (scope=portal). Patient sees only threads where they are a participant — threads are per patient-clinic pair, always filtered by patient_id from JWT sub.

---

## Endpoint

```
GET /api/v1/portal/messages
```

**Rate Limiting:**
- 60 requests per minute per patient (supports 30s polling)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer portal JWT token (scope=portal) | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| cursor | No | string | Opaque cursor from previous response | Pagination cursor | eyJpZCI6... |
| limit | No | integer | 1-100; default: 20 | Results per page | 20 |
| since | No | string | ISO 8601 datetime | Return only threads with activity after this timestamp (for polling) | 2026-02-25T16:00:00Z |

### Request Body Schema

None. GET request.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "unread_count": "integer — total unread threads across all pages",
  "items": [
    {
      "id": "uuid",
      "subject": "string | null — thread subject if set by clinic",
      "status": "string — enum: open, closed",
      "created_at": "string (ISO 8601 datetime)",
      "last_message_at": "string (ISO 8601 datetime)",
      "last_message_preview": "string — first 100 chars of last message text",
      "last_message_sender": "string — 'Tu' (patient) or 'Clinica'",
      "unread_count": "integer — unread messages in this thread for this patient",
      "has_attachment": "boolean — whether last message has an attachment"
    }
  ],
  "pagination": {
    "cursor": "string | null",
    "has_more": "boolean",
    "total_count": "integer"
  }
}
```

**Example:**
```json
{
  "unread_count": 2,
  "items": [
    {
      "id": "h0i1j2k3-l4m5-6789-nopq-rs1234567890",
      "subject": "Consulta sobre mi plan de tratamiento",
      "status": "open",
      "created_at": "2026-02-20T14:00:00-05:00",
      "last_message_at": "2026-02-25T10:30:00-05:00",
      "last_message_preview": "Hola Maria, el Dr. Martinez estara disponible el jueves a las 10am para resolver sus dudas.",
      "last_message_sender": "Clinica",
      "unread_count": 2,
      "has_attachment": false
    },
    {
      "id": "i1j2k3l4-m5n6-7890-opqr-st1234567890",
      "subject": null,
      "status": "closed",
      "created_at": "2026-01-10T09:00:00-05:00",
      "last_message_at": "2026-01-15T11:00:00-05:00",
      "last_message_preview": "Gracias por su respuesta. Quedamos confirmados.",
      "last_message_sender": "Tu",
      "unread_count": 0,
      "has_attachment": false
    }
  ],
  "pagination": {
    "cursor": null,
    "has_more": false,
    "total_count": 2
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid query parameter values (invalid cursor, limit out of range, invalid since datetime).

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Parametros de consulta no validos.",
  "details": {
    "since": ["Formato de fecha no valido. Use ISO 8601."],
    "limit": ["El limite debe estar entre 1 y 100."]
  }
}
```

#### 401 Unauthorized
**When:** Missing, expired, or invalid portal JWT.

#### 403 Forbidden
**When:** JWT scope is not "portal" or role is not "patient".

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure.

---

## Business Logic

**Step-by-step process:**

1. Validate portal JWT (scope=portal, role=patient). Extract patient_id, tenant_id.
2. Validate query parameters: limit range, cursor format, since datetime format.
3. Resolve tenant schema; set `search_path`.
4. Base query: `SELECT ... FROM message_threads WHERE patient_id = :patient_id`.
5. If `since` parameter provided: `WHERE last_message_at > :since` (for polling — returns only threads with new activity, efficient for 30s polling).
6. If no `since`: return all threads sorted by last_message_at DESC.
7. Apply cursor-based pagination on `(last_message_at DESC, id DESC)`.
8. For each thread, compute:
   - `last_message_preview`: first 100 chars of `last_message.content` (strip any markdown/HTML).
   - `last_message_sender`: if `last_message.sender_type = 'patient'` → "Tu"; else → "Clinica".
   - `unread_count`: messages WHERE thread_id = :thread_id AND read_by_patient = false AND sent_at > :patient_last_read_at.
9. Compute global `unread_count`: total unread threads (where thread.patient_unread_count > 0). Always computed regardless of `since` filter.
10. Build pagination cursor.
11. Cache result with very short TTL (15s — supports 30s polling without hammering DB on every poll).
12. Return 200.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| limit | Integer 1-100 | El limite debe estar entre 1 y 100. |
| cursor | Valid base64 cursor | Cursor de paginacion no valido. |
| since | ISO 8601 datetime | Formato de fecha no valido. Use ISO 8601. |

**Business Rules:**

- Threads are per patient-clinic pair — a patient in a tenant has a single thread history with that clinic. Not per-doctor.
- `unread_count` in the top-level response is the total across all threads (for badge display). Not paginated.
- `since` parameter is the polling optimization: clients send `since={last_response_timestamp}` every 30s; server returns only changed threads.
- Closed threads shown in list but cannot receive new messages (see PP-11 for send logic).
- `last_message_sender`: patient's own messages shown as "Tu" (informal "you" in Spanish) to avoid exposing patient name redundantly.
- Message content is NOT clinical records — PHI handling is simplified vs. clinical notes.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient has no threads | items=[], unread_count=0 |
| since parameter with no new activity | items=[], unread_count still computed from full history |
| Thread with only deleted messages | last_message_preview = "[Mensaje eliminado]" |
| Thread subject not set by clinic | subject=null |
| All threads read (no unread) | unread_count=0 top-level and per-thread |

---

## Side Effects

### Database Changes

None. Read-only endpoint.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:portal:patient:{patient_id}:threads:list:{cursor}:{limit}`: SET — TTL 15 seconds

**Cache TTL:** 15 seconds (short enough for polling; reduces DB load from 2 queries/min per patient to ~1 query/8 polls when cached)

**Cache invalidation triggers:**
- New message in any of patient's threads
- Thread status change (open/closed)

### Queue Jobs (RabbitMQ)

None.

### Audit Log

**Audit entry:** No — thread list views not individually audited (high frequency, low clinical sensitivity for inbox listing). Message content audit is in MS-03/MS-04.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 80ms (with cache hit — critical for 30s polling UX)
- **Maximum acceptable:** < 150ms (cache miss)

### Caching Strategy
- **Strategy:** Redis cache, patient-namespaced, very short TTL for polling
- **Cache key:** `tenant:{tenant_id}:portal:patient:{patient_id}:threads:list:{cursor_hash}:{limit}`
- **TTL:** 15 seconds
- **Invalidation:** On new message or thread status change for this patient

### Database Performance

**Queries executed:** 2 (thread list with last message JOIN; global unread count)

**Indexes required:**
- `message_threads.(patient_id, last_message_at)` — COMPOSITE INDEX (primary sort)
- `message_threads.(patient_id, status)` — COMPOSITE INDEX (if status filter added)
- `messages.(thread_id, read_by_patient, sent_at)` — COMPOSITE INDEX (unread count per thread)
- `message_threads.(patient_id, last_message_at)` with since filter — supports polling query efficiently

**N+1 prevention:** Last message data fetched via LATERAL JOIN or subquery in main query.

### Pagination

**Pagination:** Yes
- **Style:** Cursor-based (keyset on last_message_at + id)
- **Default page size:** 20
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| cursor | Base64 decode + datetime/UUID validation | Malformed returns 400 |
| limit | Pydantic int ge=1, le=100 | Bounded |
| since | ISO 8601 datetime parse | Malformed returns 400 |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** last_message_preview is a plain text excerpt — stripped of HTML/markdown before storage in DB or on read.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** last_message_preview (may contain health information in message text)

**Audit requirement:** Not individually audited per request (thread list is non-clinical). PHI in message content audited in MS-03/MS-04.

---

## Testing

### Test Cases

#### Happy Path
1. Patient with 2 open threads, 1 closed
   - **Given:** 2 open threads (1 unread), 1 closed thread
   - **When:** GET /api/v1/portal/messages
   - **Then:** 200 OK, 3 items sorted by last_message_at DESC, unread_count=1

2. Polling with since parameter
   - **Given:** Patient last polled at T; one new message arrived at T+15s
   - **When:** GET /api/v1/portal/messages?since=T
   - **Then:** 1 thread returned (with new activity); global unread_count updated

3. Polling with no new activity
   - **Given:** since=T, no messages after T
   - **When:** GET /api/v1/portal/messages?since=T
   - **Then:** items=[], unread_count reflects total from all threads

4. Second poll hits cache
   - **Given:** Patient polls twice within 15 seconds
   - **When:** Second GET
   - **Then:** Response from Redis cache; DB not queried

#### Edge Cases
1. Patient has no threads
   - **Given:** Patient never sent or received a message
   - **When:** GET /api/v1/portal/messages
   - **Then:** items=[], unread_count=0

2. Thread with deleted last message
   - **Given:** Last message in thread was soft-deleted
   - **When:** GET /api/v1/portal/messages
   - **Then:** last_message_preview = "[Mensaje eliminado]"

3. Long message preview truncation
   - **Given:** Last message content = 500 chars
   - **When:** GET /api/v1/portal/messages
   - **Then:** last_message_preview = first 100 chars + "..."

#### Error Cases
1. Invalid since parameter
   - **Given:** Patient authenticated
   - **When:** GET /api/v1/portal/messages?since=not-a-date
   - **Then:** 400 Bad Request

2. Staff token
   - **Given:** Doctor JWT (scope=staff)
   - **When:** GET /api/v1/portal/messages
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** Patient with portal_access=true; 3 threads with varying read/unread states and statuses.

**Patients/Entities:** Message threads with messages; tenant schema with messaging enabled.

### Mocking Strategy

- Redis: fakeredis (with TTL verification for 15s cache)
- Time: pytest-freezegun for since-parameter polling tests

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Patient sees only their own message threads
- [ ] Threads sorted by last_message_at DESC
- [ ] Global unread_count always computed regardless of since/pagination
- [ ] since parameter returns only threads with activity after that timestamp
- [ ] last_message_preview truncated to 100 chars
- [ ] last_message_sender shows "Tu" or "Clinica" (not staff name or patient name)
- [ ] 15-second Redis cache supports polling without DB overload
- [ ] Cursor-based pagination works
- [ ] Staff JWT returns 403
- [ ] All test cases pass
- [ ] Performance targets met (< 80ms cache hit, < 150ms miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Sending messages from portal (see PP-11 portal-message-send.md)
- Viewing messages within a thread (see MS-04 message-list.md — used by both staff and portal)
- Real-time WebSocket notifications (future enhancement; polling is MVP approach)
- Thread creation by patient (patient initiates via PP-11 which auto-creates thread if none exists)
- Message search from portal

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined
- [x] All outputs defined
- [x] API contract defined (OpenAPI compatible)
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
- [x] No PHI exposure in logs or errors
- [x] Message preview PHI risk noted

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 80ms for polling UX)
- [x] Caching strategy stated (15s TTL for polling)
- [x] DB queries optimized (LATERAL JOIN for last message)
- [x] Pagination applied (cursor-based)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined (N/A for list)
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (N/A)

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
| 1.0 | 2026-02-25 | Initial spec |
