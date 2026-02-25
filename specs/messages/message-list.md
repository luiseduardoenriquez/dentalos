# MS-04 List Messages in Thread Spec

---

## Overview

**Feature:** Retrieve the messages within a specific thread in chronological order (oldest first). Supports cursor-based pagination. Each message includes the sender's information, text content, a signed attachment URL (1-hour expiry) if applicable, and the list of users who have read the message. Default page size is 50 messages.

**Domain:** messages

**Priority:** Medium

**Dependencies:** MS-01 (thread-create.md), MS-03 (message-send.md), MS-05 (message-mark-read.md), infra/authentication-rules.md, S3 file storage

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist, patient (own thread only)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Patient can only read messages in threads where they are a participant. Accessing another patient's thread returns 403.

---

## Endpoint

```
GET /api/v1/messages/threads/{thread_id}/messages
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

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| thread_id | Yes | UUID | UUID v4, must exist in tenant | Thread to list messages from | thr-aaaa-1111-bbbb-2222-cccc33334444 |

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| cursor | No | string | Opaque base64 cursor | Pagination cursor (oldest-to-newest) | eyJpZCI6Ii4uLiJ9 |
| limit | No | integer | Min 1, max 100, default 50 | Page size | 50 |

### Request Body Schema

None — GET request.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "thread": {
    "id": "uuid",
    "subject": "string | null",
    "status": "string",
    "patient_id": "uuid"
  },
  "messages": [
    {
      "id": "uuid",
      "thread_id": "uuid",
      "sender": {
        "id": "uuid",
        "first_name": "string",
        "last_name": "string",
        "role": "string — enum: clinic_owner, doctor, assistant, receptionist, patient"
      },
      "content": "string",
      "attachment": {
        "url": "string | null — pre-signed S3 URL, 1-hour expiry",
        "filename": "string | null",
        "content_type": "string | null",
        "size_bytes": "integer | null"
      },
      "read_by": [
        {
          "user_id": "uuid",
          "read_at": "string ISO 8601"
        }
      ],
      "created_at": "string ISO 8601"
    }
  ],
  "pagination": {
    "next_cursor": "string | null — cursor for next page (newer messages), null if at newest end",
    "has_more": "boolean",
    "total_count": "integer — total messages in thread"
  }
}
```

**Example:**
```json
{
  "thread": {
    "id": "thr-aaaa-1111-bbbb-2222-cccc33334444",
    "subject": "Recordatorio de cita y cuidados post-operatorios",
    "status": "open",
    "patient_id": "pt_550e8400-e29b-41d4-a716-446655440000"
  },
  "messages": [
    {
      "id": "msg-aaaa-0001-bbbb-0001-cccc00010001",
      "thread_id": "thr-aaaa-1111-bbbb-2222-cccc33334444",
      "sender": {
        "id": "usr-receptionist-0001-000000000000",
        "first_name": "Laura",
        "last_name": "Torres",
        "role": "receptionist"
      },
      "content": "Hola Maria, te escribimos para recordarte tu cita del proximo martes a las 10am.",
      "attachment": {
        "url": null,
        "filename": null,
        "content_type": null,
        "size_bytes": null
      },
      "read_by": [
        {
          "user_id": "pt_550e8400-e29b-41d4-a716-446655440000",
          "read_at": "2026-02-25T11:30:00-05:00"
        }
      ],
      "created_at": "2026-02-25T11:00:00-05:00"
    },
    {
      "id": "msg-bbbb-0002-cccc-0002-dddd00020002",
      "thread_id": "thr-aaaa-1111-bbbb-2222-cccc33334444",
      "sender": {
        "id": "pt_550e8400-e29b-41d4-a716-446655440000",
        "first_name": "Maria",
        "last_name": "Garcia Lopez",
        "role": "patient"
      },
      "content": "Gracias, alli estare. Una pregunta: debo ir en ayunas?",
      "attachment": {
        "url": "https://cdn.dentalos.app/tenants/tn_abc123/messages/thr-aaaa/indicaciones.pdf?X-Amz-Expires=3600&...",
        "filename": "indicaciones_cuidados.pdf",
        "content_type": "application/pdf",
        "size_bytes": 102400
      },
      "read_by": [],
      "created_at": "2026-02-25T11:45:00-05:00"
    }
  ],
  "pagination": {
    "next_cursor": null,
    "has_more": false,
    "total_count": 2
  }
}
```

### Error Responses

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Patient accesses a thread they do not participate in.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tienes permiso para ver este hilo de mensajes."
}
```

#### 404 Not Found
**When:** `thread_id` does not exist in the tenant.

**Example:**
```json
{
  "error": "not_found",
  "message": "El hilo de mensajes no fue encontrado."
}
```

#### 422 Unprocessable Entity
**When:** Invalid query parameters (invalid limit range).

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or S3 pre-signed URL generation failure.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT; extract `tenant_id`, `user_id`, `role`.
2. Validate `thread_id` as UUID v4.
3. Set `search_path` to tenant schema.
4. Load thread: `SELECT id, subject, status, patient_id FROM message_threads WHERE id = :thread_id AND tenant_id = :tenant_id`. If not found, return 404.
5. If `role = patient`: verify `user_id` in `thread_participants WHERE thread_id = :thread_id AND user_id = :user_id`. If not participant, return 403.
6. Decode cursor if provided: `{ "created_at": "ISO datetime", "id": "uuid" }` for keyset pagination.
7. Query messages:
   ```sql
   SELECT m.*, u.first_name, u.last_name, u.role AS sender_role
   FROM messages m
   JOIN users u ON u.id = m.sender_id
   WHERE m.thread_id = :thread_id
     AND (:cursor_created_at IS NULL OR (m.created_at, m.id) > (:cursor_created_at, :cursor_id))
   ORDER BY m.created_at ASC, m.id ASC
   LIMIT :limit + 1
   ```
8. Query `total_count`: `SELECT COUNT(*) FROM messages WHERE thread_id = :thread_id`.
9. For each message that has an attachment (`attachment_s3_key IS NOT NULL`): generate a pre-signed S3 URL with 1-hour expiry using `boto3.generate_presigned_url('get_object', ...)`.
10. Load `read_by` for each message: `SELECT mr.user_id, mr.read_at FROM message_reads mr WHERE mr.message_id = ANY(:message_ids)`. Group by message_id. Return only user_id and read_at (no name lookup for privacy — frontend can resolve names from participant list if needed).
11. If results length > limit: set `has_more = true`, trim last item, generate next_cursor from last item's `(created_at, id)`.
12. Build response.
13. Write audit log: action `read`, resource `message_thread`, PHI=yes (message content returned).
14. Return 200.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| thread_id (URL) | Valid UUID v4, must exist in tenant | El hilo de mensajes no fue encontrado. |
| limit | Integer 1-100 | El limite debe estar entre 1 y 100. |
| cursor | Valid base64-decodable JSON with created_at and id (if provided) | Cursor de paginacion invalido. |

**Business Rules:**

- Messages are returned in chronological order (oldest first, ASC by `created_at`). This matches the natural conversation reading flow.
- Cursor pagination moves forward in time (from oldest to newest). When `next_cursor` is null, the client has reached the most recent messages.
- The `read_by` array contains all users who have explicitly called MS-05 (mark-as-read) for this thread after this message was created. It is used by the sender to see delivery confirmation.
- Pre-signed S3 URLs expire after 1 hour. Clients that need to access attachments after expiry must re-fetch the message list or implement a refresh mechanism.
- A message with a null `attachment_s3_key` will have `attachment.url = null` and all other attachment fields null.
- Patient users see the `sender` fields for all messages including staff senders. The `role` field identifies who sent what (clinic_owner, doctor, receptionist, etc.).
- For messages sent by the patient themselves, `sender.role = 'patient'`.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Thread has 0 messages (empty thread) | messages: [], total_count: 0, has_more: false |
| Thread has exactly 50 messages, limit=50 | All 50 returned, next_cursor=null, has_more=false |
| Thread has 51 messages, limit=50 | 50 returned, next_cursor set, has_more=true |
| Attachment S3 key exists but pre-signed URL generation fails | Log error; return attachment.url=null for that message; do not 500 the entire response |
| read_by contains deleted user_id | Return user_id as-is; no user lookup in read_by |

---

## Side Effects

### Database Changes

**No write operations** — read-only endpoint. (Mark-as-read is a separate action, MS-05.)

### Cache Operations

**Cache keys affected:** None — message list is read from DB directly. Pre-signed URLs are generated at read time.

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** Yes

- **Action:** read
- **Resource:** message_thread
- **PHI involved:** Yes — message content returned

### Notifications

**Notifications triggered:** No — use MS-05 to mark as read (separate action).

---

## Performance

### Expected Response Time
- **Target:** < 100ms (no attachments)
- **Target:** < 300ms (with S3 pre-signed URL generation for multiple attachments)
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** No response caching (real-time message display expected)
- **Cache key:** N/A
- **TTL:** N/A

### Database Performance

**Queries executed:** 3 (thread load, messages with JOIN, read_by batch query)

**Indexes required:**
- `messages.(thread_id, created_at ASC, id ASC)` — COMPOSITE INDEX for keyset pagination
- `message_reads.message_id` — INDEX for read_by batch lookup
- `thread_participants.(thread_id, user_id)` — COMPOSITE UNIQUE INDEX for patient access check

**N+1 prevention:** `read_by` data loaded in a single batch query for all messages on the page using `WHERE message_id = ANY(:ids)`. S3 pre-signed URLs generated only for messages with attachments.

### Pagination

**Pagination:** Yes
- **Style:** Cursor-based (keyset on `(created_at ASC, id ASC)`)
- **Default page size:** 50
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| thread_id (URL) | Pydantic UUID | |
| limit | Pydantic int, ge=1, le=100 | |
| cursor | Base64 decode + JSON parse validation | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization. Message content was sanitized with bleach at write time (MS-03).

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** message content (clinical communication), attachment files (may contain clinical documents)

**Audit requirement:** All access logged with PHI flag.

### S3 Security

- Pre-signed URLs include HMAC signature tied to the requesting tenant's S3 path.
- URL expiry enforced by S3 (not just frontend).
- Private bucket — no public access possible.

---

## Testing

### Test Cases

#### Happy Path
1. List messages in a 2-message thread
   - **Given:** Authenticated receptionist, thread with 2 messages (one with PDF attachment)
   - **When:** GET /api/v1/messages/threads/{id}/messages
   - **Then:** 200 OK, 2 messages in chronological order, PDF has signed URL, read_by populated for read message

2. Patient reads own thread
   - **Given:** Authenticated patient, thread where they are participant with 3 messages
   - **When:** GET
   - **Then:** 200 OK, all 3 messages including staff sender names

3. Pagination across 55-message thread
   - **Given:** Thread with 55 messages
   - **When:** GET with default limit=50, then GET with cursor from first response
   - **Then:** Page 1: 50 messages; page 2: 5 messages, has_more=false

#### Edge Cases
1. Thread has no messages
   - **Given:** Thread created but no messages (edge case, should not happen in normal flow)
   - **When:** GET
   - **Then:** 200 OK, messages: [], total_count: 0

2. Message with no attachment
   - **Given:** Message with attachment_s3_key=null
   - **When:** GET
   - **Then:** attachment block: all null fields

3. S3 pre-signed URL generation fails for one message
   - **Given:** One message has attachment; S3 call fails for that message
   - **When:** GET
   - **Then:** 200 OK, that message's attachment.url=null, other messages unaffected

#### Error Cases
1. Patient accesses another patient's thread
   - **Given:** Patient A authenticated, thread_id belongs to Patient B
   - **When:** GET
   - **Then:** 403 Forbidden

2. Unknown thread_id
   - **Given:** UUID not in tenant
   - **When:** GET
   - **Then:** 404 Not Found

3. limit=0
   - **Given:** limit=0
   - **When:** GET
   - **Then:** 422 validation error

### Test Data Requirements

**Users:** Receptionist, doctor, 2 patients (each linked to patient record)

**Threads:** Thread with 2 messages (one with PDF), thread with 55 messages for pagination test, thread belonging to Patient B

**S3:** Mock S3 client for pre-signed URL generation; simulate failure for one attachment

### Mocking Strategy

- S3: Mock `generate_presigned_url`; return predictable URL format; simulate failure for one message
- Database: SQLite in-memory; seed messages with known created_at timestamps for deterministic pagination

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET returns messages in chronological order (oldest first)
- [ ] Default page size is 50; max 100
- [ ] Cursor-based pagination works correctly
- [ ] total_count accurate
- [ ] Attachments have pre-signed S3 URLs with 1-hour expiry
- [ ] read_by populated correctly from message_reads table
- [ ] Patient can only read own thread (403 for others)
- [ ] S3 URL failure for one message does not 500 the response
- [ ] Audit log written with PHI flag
- [ ] All test cases pass
- [ ] Performance targets met (< 100ms no attachment, < 300ms with attachments)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Sending messages (see MS-03)
- Marking thread as read (see MS-05)
- Real-time message delivery via WebSocket (post-MVP)
- Message search across threads (full-text search post-MVP)
- Message deletion or editing (immutable by design)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (thread_id, cursor, limit)
- [x] All outputs defined (messages with read_by, attachment signed URLs)
- [x] API contract defined
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit
- [x] Side effects listed (audit log, no writes)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows messages domain boundaries
- [x] S3 for attachment access (not DB blobs in response)
- [x] Keyset pagination (oldest-first)

### Hook 3: Security & Privacy
- [x] Patient access scoped to own threads
- [x] Pre-signed URLs (private bucket)
- [x] PHI audit log

### Hook 4: Performance & Scalability
- [x] Targets defined (no-attachment vs with-attachment)
- [x] Batch read_by query (no N+1)
- [x] S3 failure graceful degradation

### Hook 5: Observability
- [x] Audit log (PHI)
- [x] S3 errors logged separately

### Hook 6: Testability
- [x] Test cases enumerated
- [x] S3 mock strategy
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
