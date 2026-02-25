# MS-05 Mark Thread as Read Spec

---

## Overview

**Feature:** Mark all messages in a thread as read for the authenticated user. Updates the user's `last_read_at` timestamp on the thread participant record. Decrements the unread counter cache for the authenticated user. Returns an updated thread summary. Used by both staff and patient to dismiss unread indicators after viewing a conversation.

**Domain:** messages

**Priority:** Medium

**Dependencies:** MS-02 (thread-list.md), MS-04 (message-list.md), infra/authentication-rules.md, infra/caching.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist, patient (own thread only)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Patients can only mark threads where they are a participant. Each user's read status is independent — marking as read for one user does not affect others.

---

## Endpoint

```
POST /api/v1/messages/threads/{thread_id}/read
```

**Rate Limiting:**
- 120 requests per minute per user (mark-as-read is called frequently as users view messages)

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
| thread_id | Yes | UUID | UUID v4, must exist in tenant | Thread to mark as read | thr-aaaa-1111-bbbb-2222-cccc33334444 |

### Query Parameters

None.

### Request Body Schema

None — empty POST body.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "thread_id": "uuid",
  "user_id": "uuid — the authenticated user whose read status was updated",
  "last_read_at": "string ISO 8601 — the new last_read_at timestamp",
  "unread_count": "integer — 0 after successful mark-read (messages since last_read_at for this user)"
}
```

**Example:**
```json
{
  "thread_id": "thr-aaaa-1111-bbbb-2222-cccc33334444",
  "user_id": "usr-receptionist-0001-000000000000",
  "last_read_at": "2026-02-25T15:00:00-05:00",
  "unread_count": 0
}
```

### Error Responses

#### 401 Unauthorized
**When:** JWT missing, expired, or invalid. Standard auth failure — see `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Patient tries to mark a thread they do not participate in.

**Example:**
```json
{
  "error": "forbidden",
  "message": "No tienes permiso para marcar este hilo como leido."
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

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database or cache failure.

---

## Business Logic

**Step-by-step process:**

1. Validate JWT; extract `tenant_id`, `user_id`, `role`.
2. Validate `thread_id` as UUID v4.
3. Set `search_path` to tenant schema.
4. Load thread: `SELECT id FROM message_threads WHERE id = :thread_id AND tenant_id = :tenant_id`. If not found, return 404.
5. If `role = patient`: verify `user_id` in `thread_participants WHERE thread_id = :thread_id AND user_id = :user_id`. If not participant, return 403.
6. Set `now_ts = datetime.utcnow()`.
7. UPSERT into `thread_participants`: if record exists for `(thread_id, user_id)`, update `last_read_at = now_ts`. If record does not exist, insert with `thread_id, user_id, last_read_at = now_ts`. This handles the case where a staff member reads a thread without having been explicitly added as participant.
8. Update `message_reads` table: insert records for all messages in this thread sent after previous `last_read_at` (if previous value is known) where `sender_id != user_id` and no existing record for `(message_id, user_id)`. Bulk insert using `INSERT ... ON CONFLICT DO NOTHING`. This populates the `read_by` arrays seen in MS-04.
9. Invalidate unread count cache for this user: `tenant:{tenant_id}:unread_count:{user_id}`.
10. Compute `unread_count = 0` (all messages are now read for this user, since `last_read_at = now`).
11. Return 200 with updated read status.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| thread_id (URL) | Valid UUID v4, must exist in tenant | El hilo de mensajes no fue encontrado. |

**Business Rules:**

- Mark-as-read is per-user and per-thread. Calling this endpoint does not affect other users' read status for the same thread.
- The operation is idempotent — calling mark-as-read on an already-fully-read thread is safe and returns `unread_count = 0` without errors.
- `last_read_at` is set to `now()` (server time, UTC). Any messages sent after this timestamp will be "unread" for this user until they call this endpoint again.
- For staff users who are not yet in `thread_participants` (they are reading a thread for the first time), the participant record is created on first mark-as-read call.
- The `message_reads` bulk insert enables the `read_by` feature shown in MS-04. It records which users have read which messages and at what time. Using `ON CONFLICT DO NOTHING` ensures idempotency.
- `unread_count` in the response is always 0 immediately after a successful call. The actual real-time unread count is managed by comparing `last_read_at` with message `created_at` timestamps in MS-02 (thread-list).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Thread already fully read | 200 OK, unread_count=0, last_read_at updated to now (idempotent) |
| Staff calls mark-read for a thread they were not yet a participant in | Participant record created; 200 OK |
| Thread with 0 messages | 200 OK, unread_count=0 (nothing to mark) |
| Very high frequency calls (polling) | Rate limited to 120/min; above that returns 429 |
| Patient calls mark-read on a thread they participate in | 200 OK, patient's read status updated independently of staff |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `thread_participants`: UPSERT — `last_read_at = now()` for (thread_id, user_id)
- `message_reads`: BULK INSERT — one record per unread message for this user (ON CONFLICT DO NOTHING)

**Example query (SQLAlchemy):**
```python
now_ts = datetime.utcnow()

# UPSERT thread_participants
await session.execute(
    insert(ThreadParticipant)
    .values(thread_id=thread_id, user_id=user_id, last_read_at=now_ts)
    .on_conflict_do_update(
        index_elements=["thread_id", "user_id"],
        set_={"last_read_at": now_ts}
    )
)

# Bulk insert message_reads for messages after previous last_read_at
# (only for messages sent by others, not by self)
unread_messages = await session.execute(
    select(Message.id)
    .where(
        Message.thread_id == thread_id,
        Message.sender_id != user_id,
        Message.created_at > (prev_last_read_at or datetime.min),
    )
)
message_ids = [row[0] for row in unread_messages]

if message_ids:
    await session.execute(
        insert(MessageRead)
        .values([{"message_id": mid, "user_id": user_id, "read_at": now_ts} for mid in message_ids])
        .on_conflict_do_nothing()
    )

await session.commit()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:unread_count:{user_id}`: DELETE — force recomputation on next thread list load

**Cache TTL:** N/A — deletion only

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None.

### Audit Log

**Audit entry:** No — marking messages as read is a routine interaction action, not a clinical event.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 50ms
- **Maximum acceptable:** < 150ms

### Caching Strategy
- **Strategy:** No response caching; unread count cache invalidated for the caller
- **Cache key:** `tenant:{tenant_id}:unread_count:{user_id}` (DELETED)
- **TTL:** N/A — deletion

### Database Performance

**Queries executed:** 3-4 (thread load, participant UPSERT, unread messages query, bulk message_reads insert)

**Indexes required:**
- `thread_participants.(thread_id, user_id)` — COMPOSITE UNIQUE INDEX (for UPSERT)
- `message_reads.(message_id, user_id)` — COMPOSITE UNIQUE INDEX (for ON CONFLICT DO NOTHING)
- `messages.(thread_id, sender_id, created_at)` — COMPOSITE INDEX for unread message lookup

**N+1 prevention:** Unread message IDs loaded in a single query; bulk insert uses a single multi-row INSERT statement.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| thread_id (URL) | Pydantic UUID | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None in request or response — only thread_id and timestamps.

**Audit requirement:** Not required — routine UI interaction.

---

## Testing

### Test Cases

#### Happy Path
1. Staff marks thread with 3 unread messages as read
   - **Given:** Authenticated receptionist, thread with 3 messages all from patient, receptionist's last_read_at is before all messages
   - **When:** POST /api/v1/messages/threads/{id}/read
   - **Then:** 200 OK, last_read_at = now, unread_count=0, thread_participants updated, 3 message_reads rows created, unread cache key deleted

2. Patient marks own thread as read
   - **Given:** Authenticated patient, 2 unread staff messages in thread
   - **When:** POST mark-read
   - **Then:** 200 OK, unread_count=0, patient's read status updated independently of staff

3. Mark already-read thread (idempotent)
   - **Given:** Thread with no unread messages for this user
   - **When:** POST mark-read
   - **Then:** 200 OK, unread_count=0, last_read_at updated to now (no error)

4. First-time staff reads a thread they were not yet a participant in
   - **Given:** Thread exists; staff user has no thread_participants record
   - **When:** POST mark-read
   - **Then:** 200 OK, participant record created, unread_count=0

#### Edge Cases
1. Thread with 0 messages
   - **Given:** Empty thread
   - **When:** POST mark-read
   - **Then:** 200 OK, unread_count=0, last_read_at set to now

2. Thread with messages only from self (no incoming messages)
   - **Given:** Staff opened thread, no patient reply yet
   - **When:** POST mark-read
   - **Then:** 200 OK, message_reads not inserted (no incoming messages), unread_count=0

#### Error Cases
1. Patient marks read on thread they don't participate in
   - **Given:** Patient A, thread_id belonging to Patient B's thread
   - **When:** POST
   - **Then:** 403 Forbidden

2. Unknown thread_id
   - **Given:** Non-existent UUID
   - **When:** POST
   - **Then:** 404 Not Found

3. Rate limit exceeded
   - **Given:** User made 120 mark-read calls in last minute
   - **When:** 121st call
   - **Then:** 429 Too Many Requests

### Test Data Requirements

**Users:** Receptionist, doctor, patient (linked to patient record), Patient B

**Threads:** Thread with 3 unread messages for receptionist; thread already marked read; empty thread; Patient B's thread

**Thread Participants:** Seeded with known last_read_at timestamps for deterministic unread calculations

### Mocking Strategy

- Redis: `fakeredis` to verify unread count cache key deletion
- Database: SQLite in-memory; seed messages with timestamps before and after known last_read_at values
- Fixed `now()` in tests for deterministic last_read_at verification

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST /api/v1/messages/threads/{id}/read returns 200 with last_read_at and unread_count=0
- [ ] thread_participants.last_read_at updated to server time
- [ ] message_reads rows created for all previously unread messages (not sent by self)
- [ ] ON CONFLICT DO NOTHING — idempotent multiple calls
- [ ] Staff not yet participant: participant record created on first call
- [ ] Unread count cache key deleted on success
- [ ] Patient can only mark own threads (403 for others)
- [ ] Unknown thread_id returns 404
- [ ] All test cases pass
- [ ] Performance targets met (< 50ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Marking individual messages as read (thread-level granularity only)
- Real-time read receipts via WebSocket (post-MVP)
- Marking all threads as read in bulk
- Unread count badge management (computed from thread_participants in MS-02)
- Thread archiving or deletion

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (thread_id URL param only)
- [x] All outputs defined (thread_id, user_id, last_read_at, unread_count)
- [x] API contract defined
- [x] Validation rules stated (minimal — thread existence only)
- [x] Error cases enumerated
- [x] Auth requirements explicit
- [x] Side effects listed (2 DB writes + cache delete)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows messages domain boundaries
- [x] Per-user read status (independent per user)
- [x] UPSERT + bulk INSERT pattern

### Hook 3: Security & Privacy
- [x] Patient access scoped to own threads
- [x] No PHI in response
- [x] SQL injection prevented

### Hook 4: Performance & Scalability
- [x] Target < 50ms
- [x] UPSERT (single query for participant)
- [x] Bulk INSERT for message_reads (no N+1)
- [x] Cache key deleted (not a blocking operation)

### Hook 5: Observability
- [x] Structured logging (tenant_id, user_id, thread_id, messages_marked)
- [x] Cache invalidation logged

### Hook 6: Testability
- [x] Test cases enumerated
- [x] Fixed timestamps for deterministic tests
- [x] fakeredis for cache verification
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
