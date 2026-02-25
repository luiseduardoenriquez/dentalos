# Voice Transcription Spec

> **Spec ID:** V-02
> **Status:** Draft
> **Last Updated:** 2026-02-24

---

## Overview

**Feature:** Receives a raw audio chunk from the browser's MediaRecorder API (WebM/OGG format), stores it temporarily in S3-compatible object storage (tenant-isolated, auto-deleted after 24 hours), and dispatches an asynchronous transcription job to the `voice.transcription` RabbitMQ queue. The worker submits the audio to OpenAI Whisper Large v3 with Spanish language forcing and stores the resulting transcription text. A polling endpoint is provided so the frontend can check transcription status without holding an HTTP connection open.

**Domain:** voice

**Priority:** High

**Dependencies:** V-01 (voice-capture.md), V-03 (voice-parse.md), V-05 (voice-settings.md), I-06 (background-processing.md), I-01 (multi-tenancy.md), infra/audit-logging.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, assistant
- **Tenant context:** Required — resolved from JWT
- **Special rules:** The session identified by `session_id` must belong to the tenant resolved from the JWT. Only the user who created the session (or any doctor/assistant in the same tenant) can upload audio to it. Plan add-on check: Voice add-on must be active (re-checked on every upload).

---

## Endpoints

```
POST /api/v1/voice/sessions/{session_id}/audio
GET  /api/v1/voice/sessions/{session_id}/status
```

---

## POST /api/v1/voice/sessions/{session_id}/audio

**Rate Limiting:**
- 20 requests per hour per user (audio uploads are expensive; Whisper charges per audio minute)
- Rate limit key: `voice:audio_uploads:{user_id}`
- Each upload may trigger $0.005–$0.035 in Whisper API costs depending on duration

---

### Request

#### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Multipart form data | multipart/form-data |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

#### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| session_id | Yes | UUID v4 | Must exist, must be open, must belong to tenant | The voice capture session | 9f3a1d7c-2b4e-4f8a-bc1d-7e6f9a0b3c5e |

#### Query Parameters

None.

#### Request Body (multipart/form-data)

| Field | Required | Type | Constraints | Description |
|-------|----------|------|-------------|-------------|
| audio | Yes | file | WebM or OGG; max 150 MB; max 10 minutes duration | Audio chunk from browser MediaRecorder |
| duration_seconds | Yes | integer | 1–600 | Client-reported duration of the audio chunk |
| chunk_index | No | integer | >= 0, default 0 | Zero-based index if the recording is split into multiple chunks |

**Example curl:**
```bash
curl -X POST \
  "https://api.dentalos.app/api/v1/voice/sessions/9f3a1d7c-2b4e-4f8a-bc1d-7e6f9a0b3c5e/audio" \
  -H "Authorization: Bearer eyJhbGc..." \
  -F "audio=@recording.webm;type=audio/webm" \
  -F "duration_seconds=180" \
  -F "chunk_index=0"
```

---

### Response

#### Success Response

**Status:** 202 Accepted (async processing; transcription is not yet complete)

**Schema:**
```json
{
  "transcription_id": "uuid",
  "session_id": "uuid",
  "status": "string",
  "chunk_index": "integer",
  "duration_seconds": "integer",
  "s3_key": "string",
  "estimated_cost_usd": "number",
  "session_total_duration_seconds": "integer",
  "session_max_duration_seconds": "integer",
  "created_at": "string (ISO 8601 datetime)"
}
```

**Example:**
```json
{
  "transcription_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "session_id": "9f3a1d7c-2b4e-4f8a-bc1d-7e6f9a0b3c5e",
  "status": "processing",
  "chunk_index": 0,
  "duration_seconds": 180,
  "s3_key": "voice/tn_abc123/9f3a1d7c/chunk-0.webm",
  "estimated_cost_usd": 0.018,
  "session_total_duration_seconds": 180,
  "session_max_duration_seconds": 1800,
  "created_at": "2026-02-24T15:05:00Z"
}
```

#### Error Responses

##### 400 Bad Request
**When:** Missing required form fields or unsupported audio format.

**Example:**
```json
{
  "error": "invalid_audio",
  "message": "El archivo de audio no es valido. Se aceptan formatos WebM y OGG.",
  "details": {
    "received_mime_type": "audio/mp4",
    "accepted_mime_types": ["audio/webm", "audio/ogg"]
  }
}
```

##### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

##### 402 Payment Required
**When:** Voice add-on is not active.

**Example:**
```json
{
  "error": "addon_required",
  "message": "La funcion de voz requiere el complemento de Voz activo.",
  "details": {
    "addon": "voice",
    "upgrade_url": "/settings/billing/addons"
  }
}
```

##### 403 Forbidden
**When:** User role is not doctor or assistant.

##### 404 Not Found
**When:** session_id does not exist in the tenant.

**Example:**
```json
{
  "error": "session_not_found",
  "message": "La sesion de voz no fue encontrada.",
  "details": {
    "session_id": "9f3a1d7c-2b4e-4f8a-bc1d-7e6f9a0b3c5e"
  }
}
```

##### 409 Conflict
**When:** The session status is not "open" (already closed, applied, or expired).

**Example:**
```json
{
  "error": "session_not_open",
  "message": "La sesion de voz no esta activa. No se pueden agregar grabaciones.",
  "details": {
    "session_id": "9f3a1d7c-2b4e-4f8a-bc1d-7e6f9a0b3c5e",
    "current_status": "applied"
  }
}
```

##### 413 Payload Too Large
**When:** Audio file exceeds 150 MB.

**Example:**
```json
{
  "error": "audio_too_large",
  "message": "El archivo de audio supera el limite de 150 MB.",
  "details": {
    "max_size_mb": 150
  }
}
```

##### 422 Unprocessable Entity
**When:** Audio duration would exceed the 30-minute session limit.

**Example:**
```json
{
  "error": "session_duration_exceeded",
  "message": "Esta grabacion superaria el limite de 30 minutos por sesion.",
  "details": {
    "current_session_duration_seconds": 1750,
    "chunk_duration_seconds": 120,
    "max_session_duration_seconds": 1800
  }
}
```

##### 429 Too Many Requests
**When:** Rate limit of 20 audio uploads per hour exceeded. See `infra/rate-limiting.md`.

##### 500 Internal Server Error
**When:** S3 upload failure or RabbitMQ publish failure.

---

### Business Logic (POST audio)

**Step-by-step process:**

1. Validate multipart form: `audio` file is present, MIME type is `audio/webm` or `audio/ogg`, `duration_seconds` is between 1 and 600.
2. Validate file size: reject if > 150 MB (enforced at the web server layer via nginx `client_max_body_size` and re-validated in FastAPI).
3. Resolve tenant from JWT; set `search_path` to tenant schema.
4. Check user role (must be doctor or assistant).
5. Check Voice add-on status (same as V-01 step 4).
6. Fetch session: `SELECT id, status, total_duration_seconds, patient_id FROM voice_sessions WHERE id = :sid`. If not found, return 404. If status != 'open', return 409.
7. Check session total duration: `total_duration_seconds + duration_seconds > 1800` → return 422.
8. Check user rate limit via Redis key `voice:audio_uploads:{user_id}`. If >= 20, return 429.
9. Generate S3 key: `voice/{tenant_id}/{session_id}/chunk-{chunk_index}.webm` (tenant-isolated path).
10. Upload audio file to S3-compatible storage (async stream, not buffered in memory). Set object metadata: `x-amz-meta-tenant-id`, `x-amz-meta-session-id`, `x-amz-meta-expires-after: 24h`. Configure lifecycle rule to auto-delete after 24 hours.
11. Insert `voice_transcriptions` record with `status = 'processing'`, `s3_key`, `duration_seconds`, `chunk_index`, `whisper_cost_usd = NULL` (populated by worker after completion).
12. Update `voice_sessions`: `total_duration_seconds += duration_seconds`, `expires_at = NOW() + INTERVAL '30 minutes'` (reset inactivity timer).
13. Publish RabbitMQ message to queue `voice.transcription`:
    ```json
    {
      "job_type": "voice.transcribe",
      "transcription_id": "uuid",
      "session_id": "uuid",
      "tenant_id": "tn_abc123",
      "s3_key": "voice/tn_abc123/.../chunk-0.webm",
      "language": "es",
      "whisper_model": "whisper-1"
    }
    ```
14. Increment Redis rate limit counter for audio uploads.
15. Write audit log (action: create, resource: voice_transcription, PHI: yes).
16. Return 202 Accepted with transcription_id and current session duration stats.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| audio | MIME type must be audio/webm or audio/ogg | El archivo de audio no es valido. Se aceptan formatos WebM y OGG. |
| audio | File size must be <= 150 MB | El archivo de audio supera el limite de 150 MB. |
| duration_seconds | Integer between 1 and 600 | La duracion debe estar entre 1 y 600 segundos. |
| chunk_index | Integer >= 0 | El indice del fragmento debe ser un numero positivo. |
| session total | existing + new duration <= 1800 seconds | Esta grabacion superaria el limite de 30 minutos por sesion. |

**Business Rules:**

- Audio files are stored in S3 under a tenant-isolated path prefix. No cross-tenant access is possible.
- The S3 lifecycle policy deletes audio files after 24 hours regardless of session status. This is a PHI data minimization requirement.
- The `whisper_model` used is read from tenant voice settings (V-05). For MVP, only `whisper-1` (which maps to Whisper Large v3 in OpenAI's API) is supported.
- Estimated cost is computed server-side as `duration_seconds / 60 * 0.006` (OpenAI Whisper pricing at $0.006/min as of MVP). Actual cost is stored after the worker receives the API response.
- The inactivity timer (30 min) is reset on every audio upload to allow long evaluation sessions where dictation is intermittent.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| S3 upload succeeds but RabbitMQ publish fails | Roll back transcription record insert; return 500; audio file in S3 will be cleaned up by 24h lifecycle rule |
| Worker receives the job but Whisper API is down | Worker retries with exponential backoff (max 3 attempts, 30s base); on exhaustion, sets transcription status to 'failed' |
| Same chunk_index uploaded twice (client retry) | Insert is idempotent by (session_id, chunk_index) unique constraint; second upload returns 202 with the existing transcription_id |
| Audio file is valid format but contains only silence | Whisper returns an empty string; stored as empty transcription; parse step (V-03) will produce no findings; frontend shows warning |
| Session expires during S3 upload (very large file) | After upload, step 6 will find status != 'open'; return 409; S3 object will be cleaned by lifecycle |

---

## GET /api/v1/voice/sessions/{session_id}/status

**Rate Limiting:**
- Inherits global rate limit (100/min per user)

### Request

#### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

#### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| session_id | Yes | UUID v4 | Must exist in tenant | The voice session to check | 9f3a1d7c-2b4e-4f8a-bc1d-7e6f9a0b3c5e |

#### Query Parameters

None.

### Response

#### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "session_id": "uuid",
  "session_status": "string",
  "transcriptions": [
    {
      "transcription_id": "uuid",
      "chunk_index": "integer",
      "status": "string",
      "text": "string | null",
      "duration_seconds": "integer",
      "whisper_cost_usd": "number | null",
      "created_at": "string (ISO 8601 datetime)",
      "completed_at": "string (ISO 8601 datetime) | null"
    }
  ],
  "total_duration_seconds": "integer",
  "all_completed": "boolean",
  "any_failed": "boolean"
}
```

**Example:**
```json
{
  "session_id": "9f3a1d7c-2b4e-4f8a-bc1d-7e6f9a0b3c5e",
  "session_status": "open",
  "transcriptions": [
    {
      "transcription_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "chunk_index": 0,
      "status": "completed",
      "text": "Diente treinta y seis oclusal caries... no perdon cuarenta y seis oclusal caries. Diente once vestibular fractura parcial.",
      "duration_seconds": 180,
      "whisper_cost_usd": 0.018,
      "created_at": "2026-02-24T15:05:00Z",
      "completed_at": "2026-02-24T15:05:45Z"
    }
  ],
  "total_duration_seconds": 180,
  "all_completed": true,
  "any_failed": false
}
```

#### Error Responses

##### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

##### 403 Forbidden
**When:** Session belongs to another tenant.

##### 404 Not Found
**When:** session_id does not exist in the tenant.

---

### Business Logic (GET status)

**Step-by-step process:**

1. Resolve tenant from JWT.
2. Check user role (must be doctor or assistant).
3. Fetch session and all its transcription records: `SELECT vs.*, vt.* FROM voice_sessions vs LEFT JOIN voice_transcriptions vt ON vt.session_id = vs.id WHERE vs.id = :sid ORDER BY vt.chunk_index ASC`.
4. If session not found (or belongs to different tenant), return 404.
5. Compute `all_completed = all(t.status == 'completed' for t in transcriptions)`.
6. Compute `any_failed = any(t.status == 'failed' for t in transcriptions)`.
7. Return session status with all transcription records. Omit `text` field if status is 'processing' (set to null).
8. Write audit log (action: read, resource: voice_session, PHI: yes).

**Caching for polling:** Status endpoint results are cached in Redis for 3 seconds to prevent thundering herd during rapid frontend polling. Cache key: `tenant:{tenant_id}:voice:session_status:{session_id}`. Invalidated by worker on transcription completion.

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `voice_transcriptions`: INSERT — new transcription record per audio chunk upload
- `voice_sessions`: UPDATE — `total_duration_seconds`, `expires_at` reset on each upload

**Worker side effects (not part of HTTP response):**
- `voice_transcriptions`: UPDATE — `status`, `text`, `whisper_cost_usd`, `completed_at` populated by worker after Whisper API call
- `voice_cost_tracking`: INSERT — per-call cost record for billing analytics

**Example query (SQLAlchemy):**
```python
transcription = VoiceTranscription(
    id=uuid.uuid4(),
    session_id=session.id,
    chunk_index=data.chunk_index,
    s3_key=s3_key,
    duration_seconds=data.duration_seconds,
    status="processing",
    estimated_cost_usd=data.duration_seconds / 60 * 0.006,
)
db_session.add(transcription)

# Update session
stmt = (
    update(VoiceSession)
    .where(VoiceSession.id == session.id)
    .values(
        total_duration_seconds=VoiceSession.total_duration_seconds + data.duration_seconds,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
)
await db_session.execute(stmt)
```

### Cache Operations

**Cache keys affected:**
- `voice:audio_uploads:{user_id}`: INCREMENT — rate limit counter
- `tenant:{tenant_id}:voice:session_status:{session_id}`: INVALIDATE — on worker completion

**Cache TTL:**
- Rate limit counter: remainder of current hour
- Status cache: 3 seconds (short TTL to support polling without excessive DB reads)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| voice.transcription | voice.transcribe | { transcription_id, session_id, tenant_id, s3_key, language, whisper_model } | After successful S3 upload |

**Worker behavior (voice.transcription queue):**
1. Download audio from S3.
2. Call OpenAI Whisper API: `POST https://api.openai.com/v1/audio/transcriptions` with `model=whisper-1`, `language=es`, `response_format=text`.
3. Store result: `UPDATE voice_transcriptions SET status='completed', text=:text, whisper_cost_usd=:cost, completed_at=NOW()`.
4. Insert cost tracking record.
5. Invalidate status cache key in Redis.
6. If Whisper API fails after max retries: `UPDATE voice_transcriptions SET status='failed', error_message=:msg`.

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** create (on POST audio), read (on GET status)
- **Resource:** voice_transcription
- **PHI involved:** Yes (audio contains patient clinical speech; transcription text is clinical data)

### Notifications

**Notifications triggered:** No (status is polled by frontend; no push notification needed for MVP)

---

## Performance

### Expected Response Time
- **Target (POST audio):** < 3000ms (S3 upload is the bottleneck; 150 MB at 50 Mbps = ~24s, but typical clinical audio is 5–20 MB)
- **Maximum acceptable (POST audio):** < 30000ms
- **Target (GET status):** < 100ms (served from Redis cache for 3s TTL)
- **Maximum acceptable (GET status):** < 300ms

### Caching Strategy
- **Strategy:** Short-TTL Redis cache for polling endpoint
- **Cache key:** `tenant:{tenant_id}:voice:session_status:{session_id}`
- **TTL:** 3 seconds
- **Invalidation:** Worker explicitly deletes key after updating transcription status

### Database Performance

**Queries executed (POST):** 5 (add-on check, session fetch, duration check, transcription insert, session update)

**Queries executed (GET status):** 1 (JOIN query on voice_sessions + voice_transcriptions)

**Indexes required:**
- `voice_transcriptions.session_id` — INDEX (for status polling JOIN)
- `voice_transcriptions.(session_id, chunk_index)` — UNIQUE (idempotency for duplicate uploads)
- `voice_transcriptions.status` — INDEX (for worker status queries)

**N+1 prevention:** Status endpoint uses a single JOIN query to fetch session + all transcriptions. No loop queries.

### Pagination

**Pagination:** No (a session has at most a few chunks; no pagination needed on transcription list)

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| audio (file) | MIME type check (Content-Type + magic bytes), size limit | Validate both declared MIME and actual file magic bytes to prevent MIME spoofing |
| duration_seconds | Pydantic integer, range 1–600 | Server-side only; client value is advisory (actual duration verified by Whisper) |
| chunk_index | Pydantic non-negative integer | Used only for ordering; not trusted for gap detection |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Transcription text is returned as-is (raw clinical speech). Frontend must HTML-escape before rendering. API response is JSON; Pydantic serialization escapes by default.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Audio file (contains patient clinical speech, suction sounds, incidental patient identifiers spoken aloud), transcription text (clinical findings verbatim)

**Storage:** Audio stored encrypted at rest in S3 (AES-256 server-side encryption). Auto-deleted after 24 hours via S3 lifecycle policy.

**Audit requirement:** All write and read access logged. Transcription text is NOT logged in plaintext — only session_id and transcription_id are logged.

**Transmission:** HTTPS only; audio file transmitted over TLS. S3 pre-signed URLs are not exposed to the frontend (server-to-S3 upload is server-side).

---

## Testing

### Test Cases

#### Happy Path
1. Upload 3-minute audio chunk, receive 202, poll for completion
   - **Given:** Open session, doctor authenticated, Voice add-on active
   - **When:** POST audio with WebM file (duration_seconds=180, chunk_index=0)
   - **Then:** 202 Accepted, transcription_id returned, status=processing; after worker runs, GET status returns status=completed with transcription text

2. Multiple chunks to same session
   - **Given:** Open session, 2 audio chunks recorded
   - **When:** POST chunk 0, then POST chunk 1
   - **Then:** Both return 202 with respective chunk_index; GET status shows both transcriptions

3. Session expiry timer reset on upload
   - **Given:** Session created 25 minutes ago (5 min before expiry)
   - **When:** POST audio
   - **Then:** 202 Accepted, session expires_at is now 30 minutes from upload time

#### Edge Cases
1. Duplicate chunk upload (client retry)
   - **Given:** Chunk 0 already uploaded (status=processing)
   - **When:** POST same audio with chunk_index=0 again
   - **Then:** 202 Accepted with the existing transcription_id (idempotent)

2. Audio with only silence
   - **Given:** 30-second audio file with no speech
   - **When:** Worker processes via Whisper
   - **Then:** transcription.text = "" (empty string); status = completed; parse step (V-03) produces no findings

#### Error Cases
1. Audio format is MP4 (not WebM or OGG)
   - **Given:** File with MIME type audio/mp4
   - **When:** POST audio
   - **Then:** 400 Bad Request with format error

2. Session duration limit exceeded
   - **Given:** Session already has 1700 seconds of audio, new chunk is 200 seconds
   - **When:** POST audio
   - **Then:** 422 Unprocessable Entity with duration exceeded details

3. Session not open (already applied)
   - **Given:** Session with status = applied
   - **When:** POST audio
   - **Then:** 409 Conflict with current_status

4. Whisper API unavailable (worker side)
   - **Given:** OpenAI API returns 503 on transcription call
   - **When:** Worker processes job
   - **Then:** Retry 3 times with exponential backoff; after exhaustion, transcription.status = failed

5. S3 upload fails
   - **Given:** S3 service returns 503
   - **When:** POST audio
   - **Then:** 500 Internal Server Error; no transcription record created; no RabbitMQ message published

### Test Data Requirements

**Users:** doctor (primary), assistant, patient role user (negative test)

**Patients/Entities:** Open voice session, closed/applied voice session (for 409 test), session with 1700s of audio (for 422 test)

**Files:** Sample WebM audio files (silent, with Spanish speech, with background noise), MP4 file (for format rejection test)

### Mocking Strategy

- OpenAI Whisper API: Mock with `respx` or `pytest-httpx`; return `{"text": "diente cuarenta y seis oclusal caries"}` for happy path; return 503 for error tests
- S3 / MinIO: Use LocalStack or MinIO in Docker for integration tests; mock `boto3` for unit tests
- RabbitMQ: Mock publish call with `unittest.mock`; assert payload structure; integration tests use real RabbitMQ container
- Redis: Use `fakeredis` for rate limit and cache tests

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST audio returns 202 with transcription_id and status=processing
- [ ] Audio file stored in S3 under tenant-isolated path `voice/{tenant_id}/{session_id}/`
- [ ] S3 lifecycle rule configured for 24-hour auto-deletion
- [ ] RabbitMQ message published to `voice.transcription` queue with correct payload
- [ ] Worker calls Whisper API with language=es and updates transcription with text and cost
- [ ] GET status returns all transcriptions for the session with current statuses
- [ ] GET status served from Redis cache (3s TTL) during active polling
- [ ] Session expires_at reset to 30 minutes on each upload
- [ ] Duplicate chunk_index upload returns 202 with existing transcription_id (idempotent)
- [ ] Session duration limit (30 min) enforced with 422 on violation
- [ ] Invalid audio format returns 400
- [ ] Whisper API failure sets transcription status to failed after retries
- [ ] Audio upload rate limit (20/hour per user) enforced
- [ ] Audit log entries written for upload and status access
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- LLM parsing of transcription text (V-03)
- Applying parsed findings to odontogram (V-04)
- Voice settings (V-05)
- WebSocket real-time status push (future enhancement — MVP uses polling)
- Audio recording capture in the browser (frontend concern, separate frontend spec)
- Speaker diarization (distinguishing dentist voice from patient voice — future enhancement)
- Fine-tuning Whisper on dental vocabulary (out of scope for MVP)
- Long-term archival of audio beyond 24 hours

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
- [x] Uses tenant schema isolation (S3 path + DB search_path)
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match M1-TECHNICAL-SPEC.md conventions

### Hook 3: Security & Privacy
- [x] Auth level stated (role + tenant context)
- [x] Input sanitization defined (MIME check + Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access
- [x] S3 encryption and auto-deletion stated

### Hook 4: Performance & Scalability
- [x] Response time target defined (separate for POST and GET)
- [x] Caching strategy stated (3s TTL for polling endpoint)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (voice.transcription queue)

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy for external services (Whisper, S3, RabbitMQ, Redis)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec — Voice-to-Odontogram MVP |
