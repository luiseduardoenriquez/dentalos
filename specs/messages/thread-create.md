# MS-01 Create Message Thread Spec

---

## Overview

**Feature:** Create a new message thread between clinic staff and a patient. Clinic staff initiates threads; patients cannot create threads (they respond within existing threads via the patient portal). The initial message is required and sent with the thread. Creates an in-app and channel notification for the patient. Returns the created thread with its first message.

**Domain:** messages

**Priority:** Medium

**Dependencies:** P-01 (patient-get.md), MS-03 (message-send.md), infra/authentication-rules.md, infra/multi-tenancy.md, notifications domain

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Only clinic staff can create threads. Patient role cannot initiate a thread. The patient referenced by `patient_id` must belong to the same tenant.

---

## Endpoint

```
POST /api/v1/messages/threads
```

**Rate Limiting:**
- 30 requests per minute per user (prevent spam messaging)
- Redis sliding window: `dentalos:rl:thread_create:{user_id}` (TTL 60s)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

None.

### Request Body Schema

```json
{
  "patient_id": "uuid (required) — patient to open thread with",
  "subject": "string (optional) — thread subject, max 200 chars",
  "initial_message": "string (required) — first message content, max 2000 chars"
}
```

**Example Request:**
```json
{
  "patient_id": "pt_550e8400-e29b-41d4-a716-446655440000",
  "subject": "Recordatorio de cita y cuidados post-operatorios",
  "initial_message": "Hola Maria, te escribimos para recordarte tu cita del proximo martes a las 10am. Tambien te enviamos las indicaciones de cuidado despues de la extraccion. Ante cualquier duda, respondenos aqui."
}
```

---

## Response

### Success Response

**Status:** 201 Created

**Schema:**
```json
{
  "thread": {
    "id": "uuid",
    "patient": {
      "id": "uuid",
      "first_name": "string",
      "last_name": "string",
      "avatar_url": "string | null"
    },
    "subject": "string | null",
    "status": "open",
    "created_by": "uuid",
    "created_at": "string ISO 8601",
    "last_message_at": "string ISO 8601",
    "unread_count_patient": "integer — always 1 on creation (patient has not read yet)",
    "unread_count_staff": "integer — 0 on creation (staff just wrote)"
  },
  "message": {
    "id": "uuid",
    "thread_id": "uuid",
    "sender": {
      "id": "uuid",
      "first_name": "string",
      "last_name": "string",
      "role": "string"
    },
    "content": "string",
    "attachment_url": "null — no attachment on thread creation",
    "read_by": [],
    "created_at": "string ISO 8601"
  }
}
```

**Example:**
```json
{
  "thread": {
    "id": "thr-aaaa-1111-bbbb-2222-cccc33334444",
    "patient": {
      "id": "pt_550e8400-e29b-41d4-a716-446655440000",
      "first_name": "Maria",
      "last_name": "Garcia Lopez",
      "avatar_url": null
    },
    "subject": "Recordatorio de cita y cuidados post-operatorios",
    "status": "open",
    "created_by": "usr-receptionist-0001-000000000000",
    "created_at": "2026-02-25T11:00:00-05:00",
    "last_message_at": "2026-02-25T11:00:00-05:00",
    "unread_count_patient": 1,
    "unread_count_staff": 0
  },
  "message": {
    "id": "msg-dddd-5555-eeee-6666-ffff77778888",
    "thread_id": "thr-aaaa-1111-bbbb-2222-cccc33334444",
    "sender": {
      "id": "usr-receptionist-0001-000000000000",
      "first_name": "Laura",
      "last_name": "Torres",
      "role": "receptionist"
    },
    "content": "Hola Maria, te escribimos para recordarte tu cita del proximo martes...",
    "attachment_url": null,
    "read_by": [],
    "created_at": "2026-02-25T11:00:00-05:00"
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Missing required fields or empty initial_message.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El mensaje inicial es requerido para crear un hilo.",
  "details": {
    "initial_message": ["El mensaje no puede estar vacio."]
  }
}
```

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Patient role attempts to create a thread.

**Example:**
```json
{
  "error": "forbidden",
  "message": "Los pacientes no pueden iniciar conversaciones. Responde a un mensaje del consultorio."
}
```

#### 404 Not Found
**When:** `patient_id` does not exist in the tenant.

**Example:**
```json
{
  "error": "not_found",
  "message": "El paciente no fue encontrado."
}
```

#### 422 Unprocessable Entity
**When:** Field validation fails — subject too long, initial_message too long.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Los datos del hilo contienen errores.",
  "details": {
    "subject": ["El asunto no puede superar 200 caracteres."],
    "initial_message": ["El mensaje no puede superar 2000 caracteres."]
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
2. Check role: if role = `patient`, return 403.
3. Validate request body against Pydantic schema.
4. Set `search_path` to tenant schema.
5. Verify `patient_id` exists in `patients` table for this tenant. If not, return 404.
6. Begin database transaction.
7. Insert into `message_threads`: `tenant_id`, `patient_id`, `subject`, `status = 'open'`, `created_by = user_id`, `created_at = now()`, `last_message_at = now()`.
8. Insert into `messages`: `thread_id`, `sender_id = user_id`, `sender_role = role`, `content = initial_message`, `created_at = now()`.
9. Insert into `thread_participants` for the staff sender: `thread_id`, `user_id`, `last_read_at = now()` (staff has read their own message).
10. Insert into `thread_participants` for the patient: `thread_id`, `user_id = patient_user_id` (resolved from patients.user_id FK), `last_read_at = null` (patient has not read yet).
11. Commit transaction.
12. Write audit log: action `create`, resource `message_thread`, PHI=yes (message may contain clinical references).
13. Dispatch notification job to RabbitMQ: in-app notification always sent to patient; email/WhatsApp per patient notification preferences.
14. Return 201 with thread and message objects.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | Valid UUID v4, must exist in tenant | El paciente no fue encontrado. |
| subject | Max 200 chars (optional) | El asunto no puede superar 200 caracteres. |
| initial_message | Required, non-empty, max 2000 chars | El mensaje no puede estar vacio. / No puede superar 2000 caracteres. |

**Business Rules:**

- Only one thread can be open between a specific staff member and patient at a time (configurable, but default allows multiple threads to support different topics per subject).
- There is no restriction on the number of open threads per patient with different staff members.
- The `patient.user_id` is required to be non-null for notifications to work. If the patient has no linked user account (e.g., patient created via import with no portal access), the thread is created but no notification is sent.
- `unread_count_staff` starts at 0 (the creator has effectively "read" by writing the message). `unread_count_patient` starts at 1 (patient has one unread message).
- The `sender.role` field in the message response allows the patient portal to display appropriate sender labels (e.g., "Receptionist", "Doctor").

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Patient has no linked user account | Thread created; notification skipped; unread_count_patient still set to 1 |
| subject = null (not provided) | Thread created with subject=null; displayed as "Sin asunto" in UI |
| initial_message at exact 2000 chars | Valid |
| initial_message = 2001 chars | 422 validation error |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `message_threads`: INSERT — new thread
- `messages`: INSERT — first message
- `thread_participants`: INSERT — 2 records (staff sender + patient)
- `audit_logs`: INSERT — thread creation event

**Example query (SQLAlchemy):**
```python
async with session.begin():
    thread = MessageThread(
        tenant_id=tenant_id,
        patient_id=data.patient_id,
        subject=data.subject,
        status="open",
        created_by=user_id,
        last_message_at=datetime.utcnow(),
    )
    session.add(thread)
    await session.flush()

    message = Message(
        thread_id=thread.id,
        sender_id=user_id,
        sender_role=role,
        content=data.initial_message,
    )
    session.add(message)

    # Staff participant (already read)
    session.add(ThreadParticipant(thread_id=thread.id, user_id=user_id, last_read_at=datetime.utcnow()))
    # Patient participant (unread)
    if patient.user_id:
        session.add(ThreadParticipant(thread_id=thread.id, user_id=patient.user_id, last_read_at=None))
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:messages:threads:*`: INVALIDATE — thread list caches for this tenant

**Cache TTL:** N/A — invalidation only

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| notifications | message.new_thread | { tenant_id, patient_id, thread_id, subject, sender_name, message_preview } | After successful commit |

### Audit Log

**Audit entry:** Yes

- **Action:** create
- **Resource:** message_thread
- **PHI involved:** Yes — message content may contain clinical references

### Notifications

**Notifications triggered:** Yes

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| in-app | new_message | patient | Always on thread creation |
| email | new_message_email | patient | Per patient notification preferences |
| whatsapp | new_message_wa | patient | Per patient notification preferences if WhatsApp enabled |

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 400ms

### Caching Strategy
- **Strategy:** No caching on create; invalidates thread list cache
- **Cache key:** `tenant:{tenant_id}:messages:threads:*` (INVALIDATED)
- **TTL:** N/A

### Database Performance

**Queries executed:** 3 (patient validation, thread insert, message insert + participants)

**Indexes required:**
- `message_threads.(tenant_id, patient_id)` — COMPOSITE INDEX
- `messages.thread_id` — INDEX
- `thread_participants.(thread_id, user_id)` — COMPOSITE UNIQUE INDEX

**N+1 prevention:** Patient and sender info loaded in single queries.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID | |
| subject | Pydantic strip(), max_length=200, bleach.clean | Rendered in notification |
| initial_message | Pydantic strip(), max_length=2000, bleach.clean | Message content |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization. Content sanitized with bleach before storage.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** initial_message content (may contain clinical context), patient_id

**Audit requirement:** Write operation logged with PHI flag.

---

## Testing

### Test Cases

#### Happy Path
1. Receptionist creates thread with subject and message
   - **Given:** Authenticated receptionist, valid patient in tenant
   - **When:** POST /api/v1/messages/threads with all fields
   - **Then:** 201 Created, thread with status=open, message with content, unread_count_patient=1, notification dispatched

2. Create thread without subject
   - **Given:** Authenticated doctor, valid patient
   - **When:** POST with no subject field
   - **Then:** 201 Created, thread.subject=null

#### Edge Cases
1. Patient has no user account (import patient)
   - **Given:** Patient record with user_id=null
   - **When:** POST create thread
   - **Then:** 201 Created, thread and message created, no notification dispatched (patient has no portal access), no error

#### Error Cases
1. Patient role attempts to create thread
   - **Given:** Authenticated patient
   - **When:** POST
   - **Then:** 403 Forbidden

2. patient_id not in tenant
   - **Given:** UUID not matching any patient in tenant
   - **When:** POST
   - **Then:** 404 Not Found

3. initial_message empty string
   - **Given:** `{ "patient_id": "...", "initial_message": "" }`
   - **When:** POST
   - **Then:** 422 validation error

4. subject exceeds 200 chars
   - **Given:** subject is 201-character string
   - **When:** POST
   - **Then:** 422 validation error

### Test Data Requirements

**Users:** Receptionist, doctor, patient (linked to patient record), clinic_owner

**Patients:** Active patient with linked user account; active patient without user account

### Mocking Strategy

- RabbitMQ: Mock publish; assert `message.new_thread` event dispatched
- Redis: `fakeredis` for thread list cache invalidation

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST /api/v1/messages/threads returns 201 with thread and first message
- [ ] Thread created with status=open
- [ ] Thread participant records created for sender and patient
- [ ] unread_count_patient=1, unread_count_staff=0 on creation
- [ ] Notification dispatched to RabbitMQ
- [ ] Patient with no user account: thread created, notification skipped (no error)
- [ ] Patient role returns 403
- [ ] Unknown patient_id returns 404
- [ ] Thread list cache invalidated
- [ ] Audit log written
- [ ] All test cases pass
- [ ] Performance targets met (< 200ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Patient initiating a thread (patients can only reply)
- Sending messages in existing threads (see MS-03 message-send.md)
- Listing threads (see MS-02 thread-list.md)
- Closing/archiving a thread
- Multi-staff thread (one thread can have multiple staff participants in future)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined
- [x] All outputs defined (thread + message)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (staff only)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (messages domain)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions

### Hook 3: Security & Privacy
- [x] Auth level stated (staff only, not patient)
- [x] Input sanitization (bleach on content)
- [x] PHI audit log

### Hook 4: Performance & Scalability
- [x] Response time target (< 200ms)
- [x] Thread list cache invalidated
- [x] Composite indexes defined

### Hook 5: Observability
- [x] Audit log (PHI flag)
- [x] RabbitMQ job dispatched
- [x] Structured logging

### Hook 6: Testability
- [x] Test cases enumerated
- [x] Test data specified
- [x] Mocking strategy defined
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
