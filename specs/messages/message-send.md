# MS-03 Send Message in Thread Spec

---

## Overview

**Feature:** Send a message within an existing thread. Both clinic staff and the patient who owns the thread can send messages. Supports text content and an optional file attachment (image or PDF, max 5MB). Attachments are stored in S3. Triggers an in-app notification always, plus email/WhatsApp per recipient's notification preferences. Returns the created message.

**Domain:** messages

**Priority:** Medium

**Dependencies:** MS-01 (thread-create.md), MS-02 (thread-list.md), infra/authentication-rules.md, S3 file storage (CDN), notifications domain, RabbitMQ

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist, patient (own thread only)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Patient can only send messages in threads where they are a participant. Staff can send in any thread within the tenant.

---

## Endpoint

```
POST /api/v1/messages/threads/{thread_id}/messages
```

**Rate Limiting:**
- 60 requests per minute per user (prevent spam messaging)
- Redis sliding window: `dentalos:rl:message_send:{user_id}` (TTL 60s)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | multipart/form-data (if attachment) or application/json | multipart/form-data |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| thread_id | Yes | UUID | UUID v4, must exist in tenant | Thread to send message in | thr-aaaa-1111-bbbb-2222-cccc33334444 |

### Query Parameters

None.

### Request Body Schema

**When sending text only (application/json):**
```json
{
  "content": "string (required) — message text, max 2000 chars"
}
```

**When sending with attachment (multipart/form-data):**
- `content`: string field, max 2000 chars (required even with attachment)
- `attachment`: file field, max 5MB, accepted MIME types: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`

**Example Request (JSON):**
```json
{
  "content": "Hola Maria, adjunto el resumen de tu plan de tratamiento para que lo revises antes de la cita del viernes."
}
```

---

## Response

### Success Response

**Status:** 201 Created

**Schema:**
```json
{
  "id": "uuid",
  "thread_id": "uuid",
  "sender": {
    "id": "uuid",
    "first_name": "string",
    "last_name": "string",
    "role": "string"
  },
  "content": "string",
  "attachment": {
    "url": "string | null — signed S3 URL, 1h expiry",
    "filename": "string | null",
    "content_type": "string | null",
    "size_bytes": "integer | null"
  },
  "read_by": [],
  "created_at": "string ISO 8601"
}
```

**Example:**
```json
{
  "id": "msg-aaaa-1111-bbbb-2222-cccc33334444",
  "thread_id": "thr-dddd-5555-eeee-6666-ffff77778888",
  "sender": {
    "id": "usr-doctor-0001-000000000000",
    "first_name": "Carlos",
    "last_name": "Mendez",
    "role": "doctor"
  },
  "content": "Hola Maria, adjunto el resumen de tu plan de tratamiento para que lo revises antes de la cita del viernes.",
  "attachment": {
    "url": "https://cdn.dentalos.app/tenants/tn_abc123/messages/thr-dddd/plan_tratamiento.pdf?X-Amz-Expires=3600&...",
    "filename": "plan_tratamiento.pdf",
    "content_type": "application/pdf",
    "size_bytes": 245760
  },
  "read_by": [],
  "created_at": "2026-02-25T14:30:00-05:00"
}
```

### Error Responses

#### 400 Bad Request
**When:** Missing `content`, empty content string.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El contenido del mensaje es requerido.",
  "details": {
    "content": ["El mensaje no puede estar vacio."]
  }
}
```

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Patient tries to send in a thread they do not participate in, or thread belongs to a different tenant's patient.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tienes permiso para enviar mensajes en este hilo."
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

#### 409 Conflict
**When:** Thread is closed/archived and no longer accepts messages.

**Example:**
```json
{
  "error": "thread_closed",
  "message": "Este hilo de mensajes esta cerrado. Contacta al consultorio para abrir uno nuevo."
}
```

#### 413 Payload Too Large
**When:** Attachment file size exceeds 5MB.

**Example:**
```json
{
  "error": "file_too_large",
  "message": "El archivo adjunto no puede superar 5MB.",
  "details": {
    "max_size_bytes": 5242880,
    "received_size_bytes": 7340032
  }
}
```

#### 415 Unsupported Media Type
**When:** Attachment MIME type not in allowed list.

**Example:**
```json
{
  "error": "unsupported_file_type",
  "message": "Tipo de archivo no permitido. Se aceptan: imagen JPEG, PNG, WebP y PDF.",
  "details": {
    "received_content_type": "video/mp4",
    "allowed_types": ["image/jpeg", "image/png", "image/webp", "application/pdf"]
  }
}
```

#### 422 Unprocessable Entity
**When:** content exceeds 2000 chars.

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure or S3 upload failure.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT; extract `tenant_id`, `user_id`, `role`.
2. Validate `thread_id` as UUID v4.
3. Set `search_path` to tenant schema.
4. Load thread: `SELECT * FROM message_threads WHERE id = :thread_id AND tenant_id = :tenant_id`. If not found, return 404.
5. If `role = patient`: verify `user_id` is in `thread_participants` for this thread. If not, return 403.
6. Check thread status: if `status = 'closed'`, return 409.
7. Determine content type from request:
   - `application/json`: parse JSON body, extract `content`.
   - `multipart/form-data`: extract `content` field and `attachment` file field.
8. Validate `content`: non-empty, max 2000 chars.
9. If attachment present:
   a. Check MIME type from `content-type` header of the file part. Must be in allowed list. If not, return 415.
   b. Check file size: read bytes and check <= 5,242,880 bytes (5MB). If not, return 413.
   c. Validate file header magic bytes as an additional check (JPEG: FF D8 FF; PNG: 89 50 4E 47; PDF: 25 50 44 46; WebP: RIFF...WEBP).
   d. Generate S3 key: `tenants/{tenant_id}/messages/{thread_id}/{uuid4}.{ext}`.
   e. Upload to S3 with `ContentType` set to the validated MIME type and `ServerSideEncryption = AES256`.
   f. Store attachment metadata: filename (sanitized), content_type, size_bytes, s3_key.
10. Begin database transaction.
11. Insert message: `thread_id`, `sender_id = user_id`, `sender_role = role`, `content`, `attachment_s3_key`, `attachment_filename`, `attachment_content_type`, `attachment_size_bytes`, `created_at = now()`.
12. Update `message_threads`: `last_message_id = message.id`, `last_message_at = now()`.
13. Update `thread_participants` for sender: `last_read_at = now()` (sender has read their own message). Upsert.
14. Commit transaction.
15. Generate pre-signed S3 URL for attachment (1-hour expiry) if attachment present.
16. Write audit log: action `create`, resource `message`, PHI=yes.
17. Dispatch notification to RabbitMQ.
18. Return 201 with message including signed attachment URL.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| thread_id (URL) | Valid UUID v4, must exist in tenant | El hilo de mensajes no fue encontrado. |
| content | Non-empty string, max 2000 chars | El mensaje no puede estar vacio. / No puede superar 2000 caracteres. |
| attachment MIME type | Must be: image/jpeg, image/png, image/webp, application/pdf | Tipo de archivo no permitido. |
| attachment size | <= 5MB (5,242,880 bytes) | El archivo adjunto no puede superar 5MB. |
| thread.status | Must be open | Este hilo esta cerrado. |

**Business Rules:**

- `content` is required even when an attachment is included. A message cannot have an attachment with no accompanying text. This prevents context-less file drops in conversation history.
- The attachment pre-signed URL in the response has a 1-hour expiry. For subsequent access (e.g., reading old messages in MS-04), a fresh signed URL is generated at read time.
- Attachment filenames are sanitized server-side: spaces replaced with underscores, special characters stripped (keep alphanumeric, hyphens, underscores, dots). Original filename stored for display.
- If S3 upload succeeds but the database insert fails, the S3 object is marked for deletion via a cleanup job (S3 key without DB record). The response is a 500 — no partial success returned.
- Sending a message in a closed thread returns 409. Staff can reopen a thread via a separate endpoint (post-MVP).
- When a patient sends a message, the `last_message_sender.role = 'patient'` is set, and the staff's `unread_count` for that thread increments (handled by reading thread_participants in MS-02).
- The `sender_role` is denormalized into the messages table so that the sender's role at time of message is preserved even if the user's role changes later.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| S3 upload fails after DB insert | Transaction rolled back; S3 upload attempted first, then DB insert |
| Very long filename (500 chars) | Sanitized and truncated to 200 chars before storage |
| Patient sends first reply | Thread updated, staff unread_count increments |
| Content has HTML tags | bleach.clean strips HTML; stored as plain text |
| Attachment is a PDF with macros | Only MIME type and size validated; content scanning post-MVP |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `messages`: INSERT — new message
- `message_threads`: UPDATE — `last_message_id`, `last_message_at`
- `thread_participants`: UPSERT — sender's `last_read_at = now()`
- `audit_logs`: INSERT — message creation event

**Example query (SQLAlchemy):**
```python
async with session.begin():
    msg = Message(
        thread_id=thread_id,
        sender_id=user_id,
        sender_role=role,
        content=data.content,
        attachment_s3_key=s3_key,
        attachment_filename=sanitized_filename,
        attachment_content_type=file_content_type,
        attachment_size_bytes=file_size,
    )
    session.add(msg)
    await session.flush()

    await session.execute(
        update(MessageThread)
        .where(MessageThread.id == thread_id)
        .values(last_message_id=msg.id, last_message_at=msg.created_at)
    )

    await session.execute(
        insert(ThreadParticipant)
        .values(thread_id=thread_id, user_id=user_id, last_read_at=datetime.utcnow())
        .on_conflict_do_update(
            index_elements=["thread_id", "user_id"],
            set_={"last_read_at": datetime.utcnow()}
        )
    )
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:messages:threads:*`: INVALIDATE — thread list cache (last_message_preview changed)

**Cache TTL:** N/A — invalidation only

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | message.new_message | { tenant_id, thread_id, message_id, sender_id, sender_role, content_preview, patient_id, recipients: [user_ids to notify] } | After successful commit |

### Audit Log

**Audit entry:** Yes

- **Action:** create
- **Resource:** message
- **PHI involved:** Yes — message content and any attachment may contain clinical data

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in-app | new_message | Thread recipient(s) | Always |
| email | new_message_email | Thread recipient(s) | Per notification preferences |
| whatsapp | new_message_wa | Thread recipient(s) | Per notification preferences if enabled |

Recipients for staff-sent messages: the patient in the thread.
Recipients for patient-sent messages: all staff participants in the thread (based on `thread_participants`).

---

## Performance

### Expected Response Time
- **Target:** < 300ms (text-only)
- **Target:** < 1000ms (with attachment — includes S3 upload)
- **Maximum acceptable:** < 2000ms (large attachment)

### Caching Strategy
- **Strategy:** No response caching; thread list cache invalidated
- **Cache key:** `tenant:{tenant_id}:messages:threads:*` (DELETED)
- **TTL:** N/A

### Database Performance

**Queries executed:** 3-4 (thread load, message insert, thread update, participant upsert)

**Indexes required:**
- `messages.thread_id` — INDEX
- `messages.created_at` — INDEX (for chronological ordering in MS-04)
- `thread_participants.(thread_id, user_id)` — COMPOSITE UNIQUE INDEX

**N+1 prevention:** Thread load and message insert are separate queries; no per-message queries.

### Pagination

**Pagination:** No — single message creation endpoint.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| thread_id (URL) | Pydantic UUID | |
| content | Pydantic strip(), max_length=2000, bleach.clean | Strip HTML |
| attachment filename | Regex sanitize: `re.sub(r'[^\w\-.]', '_', filename)`, truncate to 200 | Prevent path traversal |
| attachment content-type | Whitelist check against allowed MIME types | |
| attachment bytes | Magic bytes validation (not just content-type header) | Defense against MIME type spoofing |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization. Message content sanitized with bleach before storage.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** content (clinical communication), any attached images/PDFs

**Audit requirement:** All write operations logged with PHI flag.

### S3 Security

- Attachments stored in private S3 bucket. No public read access.
- Pre-signed URLs with 1-hour expiry for secure time-limited access.
- Server-side encryption (AES-256) for all stored attachments.
- S3 key includes tenant_id in the path to enforce logical tenant isolation.

---

## Testing

### Test Cases

#### Happy Path
1. Staff sends text-only message
   - **Given:** Authenticated doctor, open thread with patient
   - **When:** POST /api/v1/messages/threads/{id}/messages with content
   - **Then:** 201 Created, message with content, read_by=[], attachment=null, thread.last_message_at updated

2. Staff sends message with PDF attachment
   - **Given:** Open thread, valid PDF file (< 5MB)
   - **When:** POST multipart/form-data with content + PDF
   - **Then:** 201 Created, attachment block with signed URL (1h expiry), filename stored

3. Patient replies in own thread
   - **Given:** Authenticated patient, thread where patient is participant
   - **When:** POST message
   - **Then:** 201 Created, staff unread_count increments

#### Edge Cases
1. JPEG attachment with wrong extension but correct magic bytes
   - **Given:** JPEG file uploaded with .txt extension but correct FF D8 FF magic bytes
   - **When:** POST with this file
   - **Then:** 201 Created (magic bytes validation passes; MIME type determined from magic bytes)

2. Content exactly 2000 chars
   - **Given:** content is exactly 2000 characters
   - **When:** POST
   - **Then:** 201 Created

#### Error Cases
1. Patient sends in thread they are not part of
   - **Given:** Patient A authenticated, thread belongs to Patient B
   - **When:** POST
   - **Then:** 403 Forbidden

2. Closed thread
   - **Given:** Thread with status=closed
   - **When:** POST message
   - **Then:** 409 Conflict with thread_closed error

3. Attachment exceeds 5MB
   - **Given:** Attachment file 6MB
   - **When:** POST multipart
   - **Then:** 413 Payload Too Large

4. Unsupported file type (video)
   - **Given:** MP4 file attached
   - **When:** POST multipart
   - **Then:** 415 Unsupported Media Type

5. Empty content
   - **Given:** content = ""
   - **When:** POST
   - **Then:** 400 Bad Request

### Test Data Requirements

**Users:** Doctor, receptionist, patient (linked to patient record), Patient B (different thread)

**Threads:** Open thread for Patient A; closed thread; thread where Patient B is participant

**S3:** Mock S3 client for upload and pre-signed URL generation

### Mocking Strategy

- S3: Mock `boto3.client('s3').put_object()` and `generate_presigned_url()`; assert key format and bucket name
- RabbitMQ: Mock publish; assert `message.new_message` dispatched with correct recipients
- Redis: `fakeredis` for rate limit and thread list cache invalidation

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST message returns 201 with message object
- [ ] content required even with attachment
- [ ] Attachment uploaded to S3 with AES-256 encryption
- [ ] Pre-signed S3 URL with 1-hour expiry in response
- [ ] thread.last_message_id and last_message_at updated
- [ ] Sender's thread_participants.last_read_at updated (UPSERT)
- [ ] Thread list cache invalidated
- [ ] Notification dispatched to RabbitMQ with correct recipients
- [ ] Patient can only send in own threads (403 for others)
- [ ] Closed thread returns 409
- [ ] Attachment > 5MB returns 413
- [ ] Non-allowed MIME type returns 415
- [ ] Magic bytes validation as secondary MIME check
- [ ] Audit log written with PHI flag
- [ ] All test cases pass
- [ ] Performance targets met (< 300ms text, < 1000ms with attachment)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Creating a thread (see MS-01)
- Listing messages in a thread (see MS-04)
- Marking a thread as read (see MS-05)
- Thread closing/archiving
- Message editing or deletion (immutable messages in clinical context)
- Real-time delivery via WebSocket (post-MVP)
- Virus scanning of attachments (post-MVP)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (content + optional attachment)
- [x] All outputs defined (message with attachment block)
- [x] API contract defined (supports both JSON and multipart)
- [x] Validation rules stated
- [x] Error cases enumerated (including 413, 415)
- [x] Auth requirements explicit
- [x] Side effects listed (S3, DB, cache, RabbitMQ)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (messages domain)
- [x] S3 for file storage (not DB blob)
- [x] Tenant isolation in S3 key path
- [x] Matches FastAPI conventions

### Hook 3: Security & Privacy
- [x] MIME type whitelist + magic bytes validation
- [x] S3 private bucket + pre-signed URL
- [x] Content sanitized with bleach
- [x] PHI audit log

### Hook 4: Performance & Scalability
- [x] Targets defined (text vs attachment)
- [x] S3 upload outside DB transaction (order: S3 first, then DB)
- [x] Indexes for message ordering

### Hook 5: Observability
- [x] Audit log (PHI)
- [x] RabbitMQ job monitoring
- [x] S3 upload errors logged separately

### Hook 6: Testability
- [x] Test cases enumerated
- [x] S3 mock strategy defined
- [x] RabbitMQ mock strategy defined
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
