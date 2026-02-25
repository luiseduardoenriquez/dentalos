# PP-11 Portal Message Send Spec

---

## Overview

**Feature:** Patient sends a message to the clinic from the portal. Supports text content plus optional image or file attachment (max 5MB). Auto-creates a new thread if the patient has no open thread with this clinic. Triggers in-app and email/WhatsApp notification to clinic staff. Rate-limited to prevent spam.

**Domain:** portal

**Priority:** Medium

**Dependencies:** PP-01 (portal-login.md), PP-10 (portal-messages.md), MS-01 (thread-create.md), MS-03 (message-send.md), infra/multi-tenancy.md, infra/rate-limiting.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** patient (portal scope only)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Portal-scoped JWT required (scope=portal). Patient can only send messages within their own threads — sender_id always set from JWT sub.

---

## Endpoint

```
POST /api/v1/portal/messages
```

**Rate Limiting:**
- 20 messages per hour per patient
- 100 messages per day per patient
- File attachments: max 10 per hour per patient

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer portal JWT token (scope=portal) | Bearer eyJhbGc... |
| Content-Type | Yes | string | multipart/form-data for attachments; application/json for text-only | multipart/form-data |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

None.

### Request Body Schema

**Text-only (application/json):**
```json
{
  "content": "string (required) — message text, 1-2000 chars",
  "thread_id": "string (optional) — UUID; if provided, add message to existing thread; if omitted, auto-create new thread",
  "subject": "string (optional) — thread subject if creating new thread, max 200 chars"
}
```

**With attachment (multipart/form-data):**
```
content: string (required) — message text, 1-2000 chars
thread_id: string (optional) — UUID
subject: string (optional) — max 200 chars
attachment: file (optional) — image (JPEG, PNG, WebP) or document (PDF), max 5MB
```

**Example Request (JSON):**
```json
{
  "content": "Hola, tengo una pregunta sobre mi plan de tratamiento. Cuando podria hablar con el Dr. Martinez?",
  "subject": "Consulta sobre plan de tratamiento"
}
```

---

## Response

### Success Response

**Status:** 201 Created

**Schema:**
```json
{
  "message_id": "uuid",
  "thread_id": "uuid — thread this message belongs to (new or existing)",
  "thread_created": "boolean — true if a new thread was auto-created",
  "content": "string",
  "sent_at": "string (ISO 8601 datetime)",
  "attachment": {
    "id": "uuid | null",
    "filename": "string | null",
    "mime_type": "string | null",
    "file_size_bytes": "integer | null",
    "url": "string | null — pre-signed S3 URL, valid 60 minutes"
  }
}
```

**Example:**
```json
{
  "message_id": "j2k3l4m5-n6o7-8901-pqrs-tu1234567890",
  "thread_id": "h0i1j2k3-l4m5-6789-nopq-rs1234567890",
  "thread_created": true,
  "content": "Hola, tengo una pregunta sobre mi plan de tratamiento. Cuando podria hablar con el Dr. Martinez?",
  "sent_at": "2026-02-25T17:00:00-05:00",
  "attachment": {
    "id": null,
    "filename": null,
    "mime_type": null,
    "file_size_bytes": null,
    "url": null
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Missing content, empty message, content too long.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El cuerpo de la solicitud no es valido.",
  "details": {
    "content": ["El mensaje no puede estar vacio.", "El mensaje no puede superar los 2000 caracteres."]
  }
}
```

#### 401 Unauthorized
**When:** Missing, expired, or invalid portal JWT.

#### 403 Forbidden
**When:** JWT scope is not "portal", role is not "patient", or thread does not belong to this patient.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tiene permiso para enviar mensajes en este hilo."
}
```

#### 404 Not Found
**When:** Provided thread_id does not exist or does not belong to this patient.

**Example:**
```json
{
  "error": "thread_not_found",
  "message": "Hilo de mensajes no encontrado."
}
```

#### 409 Conflict
**When:** Thread is closed — no new messages allowed.

**Example:**
```json
{
  "error": "thread_closed",
  "message": "Este hilo de mensajes esta cerrado. Por favor inicie un nuevo mensaje para contactar a la clinica."
}
```

#### 413 Payload Too Large
**When:** Attachment file exceeds 5MB.

**Example:**
```json
{
  "error": "attachment_too_large",
  "message": "El archivo adjunto no puede superar los 5MB."
}
```

#### 415 Unsupported Media Type
**When:** Attachment MIME type not allowed.

**Example:**
```json
{
  "error": "unsupported_file_type",
  "message": "Tipo de archivo no permitido. Se aceptan: JPEG, PNG, WebP, PDF."
}
```

#### 422 Unprocessable Entity
**When:** Field validation failures.

#### 429 Too Many Requests
**When:** Rate limit exceeded (20/hour or 100/day). See `infra/rate-limiting.md`.

**Example:**
```json
{
  "error": "message_rate_limit",
  "message": "Ha enviado demasiados mensajes. Intente nuevamente en 30 minutos.",
  "retry_after_seconds": 1800
}
```

#### 500 Internal Server Error
**When:** S3 upload failure or database error.

---

## Business Logic

**Step-by-step process:**

1. Validate portal JWT (scope=portal, role=patient). Extract patient_id, tenant_id.
2. Check rate limits: 20/hour and 100/day per patient_id.
3. Parse Content-Type:
   - `application/json`: read content, thread_id, subject from JSON body.
   - `multipart/form-data`: read content, thread_id, subject from form fields; read attachment file.
4. Validate content: required, 1-2000 chars, strip leading/trailing whitespace.
5. Validate subject if provided: max 200 chars.
6. If attachment provided:
   a. Check MIME type: allowed = image/jpeg, image/png, image/webp, application/pdf.
   b. Check file size <= 5MB.
   c. Check attachment rate limit: 10/hour per patient.
7. Resolve tenant schema; set `search_path`.
8. Resolve thread:
   - If `thread_id` provided: fetch thread WHERE id = :thread_id AND patient_id = :patient_id. If not found → 404. If status='closed' → 409.
   - If no `thread_id`: look for patient's most recent open thread. If none exists, auto-create a new thread (INSERT message_threads with patient_id, status='open', subject from request or null).
9. If attachment: upload to S3 at `s3://dentaios-docs/{tenant_id}/messages/{thread_id}/{message_id}_{filename}`. On failure, abort and return 500 (do not create message without successful upload).
10. INSERT message:
    - thread_id, content, sender_id=patient_id, sender_type='patient', sent_at=NOW()
    - attachment_id if file uploaded, else null
11. UPDATE message_threads: last_message_at=NOW(), last_message_by='patient', staff_unread_count += 1.
12. Write audit log.
13. Invalidate thread list cache for this patient.
14. Dispatch RabbitMQ job: notify clinic staff of new portal message.
15. Generate pre-signed S3 URL for attachment if applicable.
16. Return 201.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| content | Required; 1-2000 chars after trim; strip_tags | El mensaje es obligatorio y no puede superar los 2000 caracteres. |
| thread_id | Valid UUID v4 if provided | Hilo de mensajes no encontrado. |
| subject | Optional; max 200 chars; strip_tags | El asunto no puede superar los 200 caracteres. |
| attachment | MIME: image/jpeg, image/png, image/webp, application/pdf; size <= 5MB | Tipo de archivo no permitido o archivo demasiado grande. |

**Business Rules:**

- Content is REQUIRED even when an attachment is included — message must have text.
- If no thread_id provided and patient has an open thread: message is added to the most recently active thread, not always the oldest.
- Thread auto-creation: one new thread per send is the max; if patient already has 10+ open threads (unusual), still auto-create (no limit on threads).
- `staff_unread_count` is a denormalized counter on thread for fast staff inbox queries (MS-02).
- Messages are never auto-deleted; soft-delete only (staff can delete from clinic side).
- Attachment filenames are sanitized (remove path traversal characters, preserve extension).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient sends message with no existing threads | New thread auto-created with or without subject |
| Patient has open thread; sends without thread_id | Message added to most recently active open thread |
| Patient sends to closed thread | 409 thread_closed — instruct to create new message |
| Attachment upload fails mid-insert | DB transaction rolled back; S3 object deleted (cleanup job); 500 returned |
| Content is only whitespace | After trim: empty string fails 1-char minimum → 400 |
| Very large valid text (2000 chars exactly) | Accept |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `message_threads`: INSERT (if new thread) — patient_id, subject, status='open', created_at
- `message_threads`: UPDATE — last_message_at, last_message_by, staff_unread_count += 1
- `messages`: INSERT — thread_id, content, sender_id, sender_type, sent_at, attachment_id
- `message_attachments`: INSERT (if attachment) — filename, mime_type, size, s3_url

**Example query (SQLAlchemy):**
```python
message = Message(
    thread_id=thread.id,
    content=data.content,
    sender_id=patient_id,
    sender_type="patient",
    sent_at=func.now(),
    attachment_id=attachment.id if attachment else None,
)
session.add(message)
await session.flush()

await session.execute(
    update(MessageThread)
    .where(MessageThread.id == thread.id)
    .values(
        last_message_at=func.now(),
        last_message_by="patient",
        staff_unread_count=MessageThread.staff_unread_count + 1,
    )
)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:portal:patient:{patient_id}:threads:list:*`: INVALIDATE — patient's thread list
- `tenant:{tenant_id}:messages:threads:list:*`: INVALIDATE — staff thread list (MS-02)
- `tenant:{tenant_id}:messages:thread:{thread_id}:messages:*`: INVALIDATE — message list in thread

**Cache TTL:** N/A (invalidation only)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | message.new_from_portal | { tenant_id, thread_id, message_id, patient_id } | After successful insert |

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** create
- **Resource:** message
- **PHI involved:** Yes (message content may contain health information; attachment may be clinical image)

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in-app | new_portal_message | all clinic staff (receptionist) | On message send |
| email | new_portal_message_staff | receptionist | On message send |

---

## Performance

### Expected Response Time
- **Target:** < 300ms (text-only message)
- **Maximum acceptable:** < 1500ms (with 5MB file upload to S3)

### Caching Strategy
- **Strategy:** No caching on write; cache invalidation
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** Patient thread list, staff thread list, thread message list all invalidated

### Database Performance

**Queries executed:** 3-4 (thread resolve/create, message insert, thread update, optional attachment insert)

**Indexes required:**
- `message_threads.(patient_id, status, last_message_at)` — COMPOSITE INDEX (thread resolution)
- `messages.(thread_id, sent_at)` — COMPOSITE INDEX
- `messages.sender_id` — INDEX

**N+1 prevention:** Not applicable (single insert flow).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| content | Pydantic strip + bleach.clean (allow minimal formatting: bold, italic); max 2000 chars | User-generated text; PHI potential |
| subject | Pydantic strip + strip_tags; max 200 chars | Thread subject |
| attachment filename | Sanitize: remove path separators, null bytes; preserve extension; UUID prefix added | Prevent path traversal |
| attachment content | MIME sniffing on server side (python-magic); do not trust Content-Type header alone | Prevent polyglot files |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries.

### XSS Prevention

**Output encoding:** Message content stored sanitized; output escaped by Pydantic. Attachment served from S3 with Content-Disposition: attachment (not inline for non-images).

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** content (patient health information), attachment (may be clinical image or document)

**Audit requirement:** All message sends logged (PHI: content stored and audited per Resolución 1888).

### File Security

- Server-side MIME type detection using python-magic (not trusting Content-Type header).
- Filename sanitized and prefixed with UUID to prevent collisions and path traversal.
- S3 bucket policy: attachments not publicly accessible; only accessible via pre-signed URLs.
- Antivirus scanning: RabbitMQ job dispatched to scan attachment after upload (async; message accessible before scan completes — acceptable for MVP).

---

## Testing

### Test Cases

#### Happy Path
1. Send first message (auto-creates thread)
   - **Given:** Patient authenticated; no existing message threads
   - **When:** POST /api/v1/portal/messages with content + subject
   - **Then:** 201 Created, thread_created=true, message stored, staff notification dispatched

2. Send message to existing thread
   - **Given:** Patient has open thread h0i1...
   - **When:** POST with thread_id=h0i1...
   - **Then:** 201 Created, thread_created=false, message appended to thread

3. Send message with PDF attachment
   - **Given:** Patient authenticated; valid PDF <= 5MB
   - **When:** POST multipart/form-data with content + attachment
   - **Then:** 201 Created, attachment stored to S3, pre-signed URL in response

4. Send message without thread_id (has existing open thread)
   - **Given:** Patient has 1 open thread
   - **When:** POST without thread_id
   - **Then:** 201 Created, message added to most recently active open thread

#### Edge Cases
1. Content at max length (2000 chars)
   - **Given:** Valid patient, existing thread
   - **When:** POST with exactly 2000 char content
   - **Then:** 201 Created — accepted

2. Attachment at size boundary (exactly 5MB)
   - **Given:** PDF file exactly 5,242,880 bytes
   - **When:** POST multipart with attachment
   - **Then:** 201 Created — accepted

3. S3 upload fails
   - **Given:** S3 endpoint unavailable (mock error)
   - **When:** POST with attachment
   - **Then:** 500 Internal Server Error; no message inserted in DB

#### Error Cases
1. Empty content
   - **Given:** Patient authenticated
   - **When:** POST with content="" (or whitespace only)
   - **Then:** 400 Bad Request

2. Attachment exceeds 5MB
   - **Given:** File is 6MB
   - **When:** POST multipart
   - **Then:** 413 Payload Too Large

3. Unsupported file type (DOCX)
   - **Given:** Patient uploads a .docx file
   - **When:** POST multipart
   - **Then:** 415 Unsupported Media Type

4. Thread is closed
   - **Given:** Thread with status='closed'
   - **When:** POST with thread_id pointing to closed thread
   - **Then:** 409 thread_closed

5. Hourly rate limit exceeded
   - **Given:** Patient sent 20 messages this hour
   - **When:** 21st POST
   - **Then:** 429 with retry_after_seconds

### Test Data Requirements

**Users:** Patient with portal_access=true; existing open and closed threads; tenant with messaging enabled.

**Patients/Entities:** S3 mock; RabbitMQ mock; message threads in various states.

### Mocking Strategy

- S3: moto library for upload and pre-signed URL testing; simulate upload failure
- RabbitMQ: Mock publish; assert notification job payload
- python-magic: mock for MIME detection in unit tests; real in integration tests
- Redis: fakeredis for rate limit testing

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Patient can send text message to clinic
- [ ] New thread auto-created if no thread_id provided and no open thread exists
- [ ] Message added to existing thread if thread_id provided and valid
- [ ] Optional file attachment (JPEG, PNG, WebP, PDF) stored to S3
- [ ] Attachment size check (5MB max) returns 413
- [ ] Unsupported MIME type returns 415
- [ ] Closed thread returns 409
- [ ] staff_unread_count incremented on message_threads
- [ ] Staff notification dispatched via RabbitMQ
- [ ] All relevant caches invalidated (patient list, staff list, thread messages)
- [ ] Rate limit 20/hour, 100/day enforced
- [ ] S3 failure rolls back DB insert atomically
- [ ] Audit log entry written with PHI flag
- [ ] All test cases pass
- [ ] Performance targets met (< 300ms text-only, < 1500ms with 5MB upload)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Staff sending messages to patients (see MS-03 message-send.md)
- Reading/listing messages within a thread (see MS-04 message-list.md)
- Deleting messages from portal (not allowed from patient side)
- Real-time delivery (WebSocket — future enhancement; polling is MVP)
- Antivirus scan results notification (async background job; out of scope for this spec)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (JSON and multipart/form-data schemas)
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
- [x] Auth level stated (patient portal scope)
- [x] Input sanitization defined (MIME sniff, filename sanitize, bleach)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] File security measures documented (MIME detection, S3 access control)

### Hook 4: Performance & Scalability
- [x] Response time target defined (text vs. attachment)
- [x] Caching strategy stated (invalidation)
- [x] DB queries optimized
- [x] Pagination N/A

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry for S3 failures)
- [x] Queue job monitoring

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy (moto, fakeredis, RabbitMQ mock)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
