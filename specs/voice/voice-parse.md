# Voice Parse Spec

> **Spec ID:** V-03
> **Status:** Draft
> **Last Updated:** 2026-02-24

---

## Overview

**Feature:** Takes the raw transcription text produced by Whisper (V-02) and submits it to Claude Haiku (LLM) with a specialized dental clinical prompt. The LLM extracts structured clinical findings in JSON format, handles mid-sentence self-corrections ("diente 36... no, 46"), filters non-clinical speech (assistant instructions, background exclamations), validates FDI tooth numbers, and returns a proposed change set for human confirmation before any odontogram data is written. This endpoint is the intelligence layer of the Voice-to-Odontogram pipeline.

**Domain:** voice

**Priority:** High

**Dependencies:** V-01 (voice-capture.md), V-02 (voice-transcription.md), V-04 (voice-apply.md), V-05 (voice-settings.md), I-06 (background-processing.md), I-01 (multi-tenancy.md)

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, assistant
- **Tenant context:** Required — resolved from JWT
- **Special rules:** The session must belong to the tenant resolved from JWT. At least one transcription in the session must have `status = 'completed'` before parse can be called. Plan add-on check: Voice add-on must be active.

---

## Endpoint

```
POST /api/v1/voice/sessions/{session_id}/parse
```

**Rate Limiting:**
- 30 requests per hour per user
- Rate limit key: `voice:parse:{user_id}`
- LLM inference costs approximately $0.001–$0.005 per parse call (Claude Haiku pricing)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Request format | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| session_id | Yes | UUID v4 | Must exist in tenant | The voice session whose transcription will be parsed | 9f3a1d7c-2b4e-4f8a-bc1d-7e6f9a0b3c5e |

### Query Parameters

None.

### Request Body Schema

```json
{
  "transcription_ids": "string[] (optional) — list of UUID v4. If omitted, all completed transcriptions in the session are concatenated in chunk_index order.",
  "override_text": "string (optional) — max 10000 chars. If provided, bypasses transcription lookup and parses this text directly. Used when the user has manually corrected the transcription in the UI before parsing.",
  "patient_context": {
    "dentition_type": "string (optional) — enum: adult | pediatric | mixed. Used to validate tooth number ranges.",
    "age_years": "integer (optional) — used to contextualize findings (e.g., deciduous teeth for children)"
  }
}
```

**Example Request (minimal — parse all completed transcriptions):**
```json
{}
```

**Example Request (with override text):**
```json
{
  "override_text": "Diente cuarenta y seis oclusal caries. Diente once vestibular fractura parcial. Aspira por favor.",
  "patient_context": {
    "dentition_type": "adult"
  }
}
```

**Example Request (specific transcription chunks):**
```json
{
  "transcription_ids": [
    "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "c3d4e5f6-a7b8-9012-cdef-123456789012"
  ]
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "parse_id": "uuid",
  "session_id": "uuid",
  "status": "string",
  "input_text": "string",
  "findings": [
    {
      "tooth": "integer",
      "zone": "string | null",
      "condition": "string",
      "confidence": "number (0.0–1.0)",
      "raw_phrase": "string"
    }
  ],
  "corrections": "string[]",
  "filtered_speech": "string[]",
  "notes": "string | null",
  "warnings": "string[]",
  "llm_model": "string",
  "llm_cost_usd": "number",
  "created_at": "string (ISO 8601 datetime)"
}
```

**Example:**
```json
{
  "parse_id": "d4e5f6a7-b8c9-0123-def0-234567890123",
  "session_id": "9f3a1d7c-2b4e-4f8a-bc1d-7e6f9a0b3c5e",
  "status": "completed",
  "input_text": "Diente treinta y seis oclusal caries... no perdon cuarenta y seis oclusal caries. Diente once vestibular fractura parcial. Aspira por favor. Hay sensibilidad reportada por el paciente en el cuadrante inferior derecho.",
  "findings": [
    {
      "tooth": 46,
      "zone": "oclusal",
      "condition": "caries",
      "confidence": 0.95,
      "raw_phrase": "cuarenta y seis oclusal caries"
    },
    {
      "tooth": 11,
      "zone": "vestibular",
      "condition": "fractura",
      "confidence": 0.88,
      "raw_phrase": "diente once vestibular fractura parcial"
    }
  ],
  "corrections": [
    "Diente 36 corregido a 46 por el hablante ('no perdon cuarenta y seis')"
  ],
  "filtered_speech": [
    "Aspira por favor"
  ],
  "notes": "El paciente reporta sensibilidad en el cuadrante inferior derecho.",
  "warnings": [],
  "llm_model": "claude-haiku-20240307",
  "llm_cost_usd": 0.0008,
  "created_at": "2026-02-24T15:10:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** override_text exceeds 10000 characters, or transcription_ids contains invalid UUIDs.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "El texto de transcripcion supera el limite de 10,000 caracteres.",
  "details": {
    "max_chars": 10000,
    "received_chars": 12543
  }
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token. Standard auth failure — see infra/authentication-rules.md.

#### 402 Payment Required
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

#### 403 Forbidden
**When:** User role is not doctor or assistant.

#### 404 Not Found
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

#### 409 Conflict
**When:** No completed transcriptions found in the session to parse (all are still processing or failed).

**Example:**
```json
{
  "error": "no_completed_transcriptions",
  "message": "No hay transcripciones completadas en esta sesion. Espere a que el procesamiento de audio finalice.",
  "details": {
    "session_id": "9f3a1d7c-2b4e-4f8a-bc1d-7e6f9a0b3c5e",
    "transcription_statuses": {
      "processing": 1,
      "completed": 0,
      "failed": 0
    }
  }
}
```

#### 422 Unprocessable Entity
**When:** Specified transcription_ids contain IDs that do not belong to this session.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Errores de validacion.",
  "details": {
    "transcription_ids": ["El ID 'abc-123' no pertenece a esta sesion."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit of 30 parse requests per hour exceeded. See `infra/rate-limiting.md`.

#### 502 Bad Gateway
**When:** LLM API (Claude Haiku) is unreachable or returns an unrecoverable error.

**Example:**
```json
{
  "error": "llm_unavailable",
  "message": "El servicio de procesamiento de lenguaje no esta disponible. Intente nuevamente en unos momentos.",
  "details": {
    "retry_after_seconds": 30
  }
}
```

#### 500 Internal Server Error
**When:** Unexpected failure during LLM response parsing or database operation.

---

## Business Logic

**Step-by-step process:**

1. Validate request body against Pydantic schema.
2. Resolve tenant from JWT; set `search_path` to tenant schema.
3. Check user role (must be doctor or assistant).
4. Check Voice add-on status.
5. Fetch session from `voice_sessions` where `id = :sid`. If not found, return 404.
6. If `override_text` is provided: use it as `input_text` directly (skip transcription lookup).
7. If `override_text` is not provided: query `voice_transcriptions` where `session_id = :sid AND status = 'completed'`. If `transcription_ids` filter was given, further filter to those IDs. Verify all requested IDs belong to the session. If no completed transcriptions found, return 409. Concatenate `text` fields ordered by `chunk_index ASC`, separated by a space.
8. Validate `input_text` is not empty after concatenation.
9. Check user rate limit (parse calls): Redis key `voice:parse:{user_id}`. If >= 30, return 429.
10. Read tenant voice settings to determine `language` (default: "es").
11. Fetch patient context: query `patients` + `odontogram_states` for the session's `patient_id` to get `dentition_type` and `birthdate`. If `patient_context` was provided in the request body, use that instead (request overrides DB).
12. Build LLM prompt (see Prompt Engineering section below).
13. Call Claude Haiku API synchronously (not queued — response is needed in real-time for UX flow):
    ```
    POST https://api.anthropic.com/v1/messages
    model: claude-haiku-20240307
    max_tokens: 2048
    ```
14. Parse LLM JSON response. If LLM returns malformed JSON, retry once. If retry fails, return 502.
15. Validate LLM output: verify tooth numbers are within valid FDI range for dentition type. Flag out-of-range teeth in `warnings` (do not reject — dentist may correct manually).
16. Store parse result in `voice_parse_results` table.
17. Record actual LLM cost: `input_tokens * 0.00000025 + output_tokens * 0.00000125` (Claude Haiku pricing).
18. Increment Redis rate limit counter.
19. Write audit log (action: create, resource: voice_parse_result, PHI: yes).
20. Return 200 with structured findings for human review.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| override_text | Max 10000 chars if provided | El texto supera el limite de 10,000 caracteres. |
| transcription_ids | Each must be valid UUID v4 | ID de transcripcion no valido. |
| transcription_ids | Each must belong to the session | El ID no pertenece a esta sesion. |
| patient_context.dentition_type | Enum: adult, pediatric, mixed | Tipo de denticion no valido. |
| patient_context.age_years | Integer >= 0 | La edad debe ser un numero positivo. |

**Business Rules:**

- Parse is synchronous (not queued) because the user is actively waiting for findings to review. Target latency is < 5 seconds for Claude Haiku on typical dental dictation (100–500 tokens input).
- The LLM is instructed to return ONLY valid JSON. If the response is not valid JSON after one retry, the endpoint returns 502.
- Confidence scores in the output are LLM-generated estimates. The frontend uses them to highlight low-confidence findings (< 0.75) for closer user attention.
- FDI tooth number validation: adult range 11–48 (permanent teeth), pediatric range 51–85 (deciduous teeth). Mixed dentition allows both ranges. Numbers outside all valid ranges are included with a warning rather than rejected.
- The `filtered_speech` array contains phrases the LLM identified as non-clinical (assistant instructions, patient conversation, exclamations). These are preserved for the audit log but excluded from `findings`.
- The `notes` field captures clinical observations that are not tooth-specific findings (e.g., "paciente refiere sensibilidad"). These are proposed as text additions to the evolution note, not odontogram findings.
- A session can be parsed multiple times (e.g., after the user manually edits the transcription text in the UI). Each parse creates a new `voice_parse_results` record. Only the most recent parse is used for the apply step (V-04).

**Prompt Engineering:**

The dental clinical prompt is stored as a versioned template in the application code (`app/voice/prompts/dental_parse_v1.txt`). It is NOT stored in the database (to avoid prompt injection via user-supplied data).

Prompt structure:
```
[SYSTEM]
Eres un asistente dental clinico especializado en odontologia. Extraes hallazgos clinicos de transcripciones de dictado dental en español.

Reglas:
1. Usa numeracion FDI (11-48 para denticion permanente, 51-85 para decidua).
2. Detecta y aplica auto-correcciones del hablante (frases como "no, quise decir", "perdon", "mejor dicho").
3. Filtra instrucciones al asistente (aspira, luz, pasa, alcanzame, etc.) y conversacion no clinica.
4. Convierte numeros hablados a numericos (cuarenta y seis → 46).
5. Devuelve UNICAMENTE JSON valido. Sin texto adicional.

Zonas validas: oclusal, mesial, distal, vestibular, palatino, lingual, cervical, incisal, apical, interproximal

Condiciones validas: caries, fractura, obturacion, corona, endodoncia, extraccion, implante, protesis, movilidad, erosion, abrasion, abfraccion, hipersensibilidad, mancha, calcificacion, reabsorcion, periapical, ausente, sano, sellante, furca, bolsa_periodontal, recesion, edema, fistula, quiste

Tipo de denticion del paciente: {dentition_type}
Edad del paciente: {age_years} años

[USER]
Transcripcion:
{input_text}

Responde con este JSON exacto:
{
  "findings": [{"tooth": integer, "zone": string|null, "condition": string, "confidence": float, "raw_phrase": string}],
  "corrections": [string],
  "filtered_speech": [string],
  "notes": string|null
}
```

The `{input_text}` placeholder is filled with the sanitized transcription text. Prompt injection is prevented by stripping any text that contains JSON-like structures from the input before insertion (validated via regex).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Transcription text is empty string | Return 200 with empty findings array, warnings: ["La transcripcion esta vacia. No se encontraron hallazgos clinicos."] |
| LLM returns tooth number 0 or negative | Include in findings with confidence 0.0 and warning: "Numero de diente invalido: {tooth}" |
| LLM returns condition not in the valid list | Include finding as-is with confidence reduced by 0.2 and add to warnings |
| All speech was filtered (dentist only gave instructions) | Return 200 with empty findings, filtered_speech populated, notes may be non-null |
| LLM JSON is malformed on first response | Retry once with explicit "return only JSON, no prose" instruction; if still malformed, return 502 |
| Input text > 8000 tokens (very long session) | Truncate to 8000 tokens from the end (most recent speech is most relevant); add warning: "Texto truncado por longitud" |
| Dentist corrects self multiple times for same tooth | LLM resolves the final corrected value; all intermediate values listed in corrections[] |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `voice_parse_results`: INSERT — new parse result record with full LLM output

**Example query (SQLAlchemy):**
```python
parse_result = VoiceParseResult(
    id=uuid.uuid4(),
    session_id=session.id,
    input_text=input_text,
    findings=findings_json,          # JSONB column
    corrections=corrections_list,    # JSONB column
    filtered_speech=filtered_list,   # JSONB column
    notes=notes_text,
    warnings=warnings_list,          # JSONB column
    llm_model="claude-haiku-20240307",
    llm_cost_usd=computed_cost,
    prompt_version="dental_parse_v1",
    created_by=current_user.id,
)
db_session.add(parse_result)
```

**Also affected:**
- `voice_cost_tracking`: INSERT — LLM cost record (alongside Whisper costs from V-02, enables per-tenant cost analytics)

### Cache Operations

**Cache keys affected:** None (parse results are not cached; each call may have different input due to override_text)

**Cache TTL:** N/A

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None. Parse is synchronous for real-time UX. The LLM call blocks the HTTP request.

**Rationale:** Claude Haiku responds in < 2 seconds for typical dental dictation. Async queuing would introduce unnecessary UX latency and complexity for the confirmation workflow. If Haiku latency degrades in future, this can be migrated to async with polling.

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** create
- **Resource:** voice_parse_result
- **PHI involved:** Yes (input_text contains patient clinical speech; findings contain clinical diagnoses)

**Note:** The full `input_text` and `findings` are NOT stored in the audit log body to limit PHI in the audit store. Only `parse_id`, `session_id`, `patient_id`, `user_id`, `tenant_id`, and `finding_count` are logged.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 5000ms (dominated by LLM API call latency; Claude Haiku is fast)
- **Maximum acceptable:** < 12000ms
- **Note:** For inputs > 2000 tokens, response may approach 8–10s. Frontend should show a loading indicator.

### Caching Strategy
- **Strategy:** No response caching (each parse is unique; override_text makes caching impractical)
- **Cache key:** N/A
- **TTL:** N/A
- **Invalidation:** N/A

### Database Performance

**Queries executed:** 4 (add-on check, session fetch, transcription fetch + concatenate, parse result insert)

**Indexes required:**
- `voice_parse_results.session_id` — INDEX (to retrieve latest parse result in V-04 apply step)
- `voice_parse_results.created_by` — INDEX (for user-level cost analytics)
- `voice_parse_results.created_at` — INDEX (for ordered retrieval of latest parse per session)

**N+1 prevention:** Transcriptions fetched in a single query ordered by chunk_index. No loop queries.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| override_text | Pydantic max_length=10000, strip() | Prevent excessively large LLM requests |
| override_text | Regex strip of `\{.*?\}` JSON-like blocks | Prevent prompt injection via user-supplied override text |
| transcription_ids | Pydantic UUID v4 list validator | No arbitrary strings in SQL queries |
| patient_context fields | Pydantic enum + integer validators | Constrained to known values |

**Prompt Injection Prevention:**
- `input_text` (derived from Whisper transcriptions or override_text) is inserted into the prompt inside a clearly delimited `[USER]` block.
- Any text resembling LLM instruction patterns (e.g., "Ignora las instrucciones anteriores", "System:", "SYSTEM:") is detected and flagged in `warnings` before being sent to the LLM. The text is still parsed — not rejected — since dentists may legitimately say similar phrases.
- The `override_text` field has an additional sanitization pass: strip curly braces `{}` and backtick sequences ` ``` ` to prevent JSON injection into the prompt template.

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs (findings, corrections, filtered_speech) are escaped via Pydantic serialization. Frontend must not render these as HTML without additional sanitization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** input_text (patient clinical speech), findings (clinical diagnoses linked to a patient), notes (clinical observations)

**LLM data transmission:** Input text is sent to Anthropic's API. Tenants must be informed of this in the Voice add-on terms of service. No patient name, date of birth, or explicit identifiers are included in the LLM prompt — only clinical tooth findings language. The session_id is not sent to Anthropic.

**Audit requirement:** Write access logged. The full input_text and findings JSON are stored in `voice_parse_results` (tenant DB) but are not propagated to the audit log store in plaintext.

---

## Testing

### Test Cases

#### Happy Path
1. Parse session with one completed transcription chunk
   - **Given:** Session with one completed transcription: "Diente cuarenta y seis oclusal caries"
   - **When:** POST /api/v1/voice/sessions/{session_id}/parse with empty body
   - **Then:** 200 OK, findings contains `{tooth: 46, zone: "oclusal", condition: "caries", confidence >= 0.8}`, filtered_speech is empty, corrections is empty

2. Parse with self-correction in transcription
   - **Given:** Transcription text: "Diente treinta y seis oclusal caries... no perdon cuarenta y seis oclusal caries"
   - **When:** POST parse
   - **Then:** findings contains tooth 46 (not 36), corrections contains the correction description, tooth 36 is absent from findings

3. Parse with mixed clinical and non-clinical speech
   - **Given:** Transcription: "Diente once fractura vestibular. Aspira por favor. El paciente dice que le duele al frio."
   - **When:** POST parse
   - **Then:** findings = [{tooth:11, zone:vestibular, condition:fractura}], filtered_speech = ["Aspira por favor"], notes contains the patient report

4. Parse with override_text (user edited transcription)
   - **Given:** Session with transcription, user provides override_text in request body
   - **When:** POST parse with override_text
   - **Then:** override_text is used as input, original transcription text is ignored

5. Multiple chunks concatenated in order
   - **Given:** Session with chunk 0 ("Diente once caries oclusal") and chunk 1 ("Diente cuarenta y seis fractura")
   - **When:** POST parse with no transcription_ids filter
   - **Then:** Both chunks parsed, findings contains two entries ordered by appearance in text

#### Edge Cases
1. Empty transcription text
   - **Given:** Transcription text is empty string (silent audio)
   - **When:** POST parse
   - **Then:** 200 OK, findings = [], warnings contains empty transcription message

2. All speech filtered (only assistant instructions spoken)
   - **Given:** Transcription: "Aspira. Luz por favor. Pasa el explorador."
   - **When:** POST parse
   - **Then:** 200 OK, findings = [], filtered_speech = ["Aspira", "Luz por favor", "Pasa el explorador"]

3. Invalid tooth number from LLM (out of FDI range)
   - **Given:** LLM returns tooth 99 (not a valid FDI number)
   - **When:** parse result processed
   - **Then:** Finding included with confidence 0.0, warnings = ["Numero de diente invalido: 99"]

4. Parse called again after previous parse (re-parse)
   - **Given:** Session already has a parse result
   - **When:** POST parse again
   - **Then:** 200 OK with a new parse_id; new result stored; both records in DB (V-04 uses most recent)

#### Error Cases
1. No completed transcriptions
   - **Given:** Session has one transcription with status=processing
   - **When:** POST parse
   - **Then:** 409 Conflict with transcription_statuses breakdown

2. LLM API returns malformed JSON (both attempts)
   - **Given:** Claude Haiku mock returns "Aqui estan los hallazgos: [...]" (prose, not JSON)
   - **When:** POST parse
   - **Then:** 502 Bad Gateway with retry_after_seconds

3. transcription_ids contains an ID from a different session
   - **Given:** transcription_ids = [valid UUID from session A] when parsing session B
   - **When:** POST parse
   - **Then:** 422 Unprocessable Entity

4. Rate limit exceeded (31st parse in hour)
   - **Given:** User has made 30 parse calls in the current hour
   - **When:** POST parse
   - **Then:** 429 Too Many Requests

### Test Data Requirements

**Users:** doctor, assistant

**Patients/Entities:** Voice sessions with various transcription states (completed, processing, failed, mixed). Pre-built transcription text fixtures covering: single finding, multi-finding, self-correction, mixed clinical/non-clinical, empty.

### Mocking Strategy

- Anthropic Claude Haiku API: Mock with `respx` or `pytest-httpx`; return valid JSON fixtures for happy path; return malformed JSON for error test; return 529 (overloaded) for 502 test
- Redis: `fakeredis` for rate limit tests
- Database: Real PostgreSQL via pytest-asyncio for integration tests; SQLAlchemy async fixtures for unit tests

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST parse returns 200 with structured findings JSON
- [ ] Self-corrections in speech are correctly resolved (corrected tooth is in findings, original in corrections[])
- [ ] Non-clinical speech is classified into filtered_speech[] and excluded from findings
- [ ] FDI tooth numbers validated against dentition type; out-of-range numbers flagged in warnings (not rejected)
- [ ] override_text bypasses transcription lookup when provided
- [ ] Multiple chunks concatenated in chunk_index order when no filter given
- [ ] LLM cost recorded in voice_parse_results.llm_cost_usd
- [ ] No completed transcriptions returns 409 with status breakdown
- [ ] LLM malformed JSON retried once; 502 returned on persistent failure
- [ ] Rate limit (30/hour per user) enforced
- [ ] Parse can be called multiple times on same session; each produces a new parse_id
- [ ] Audit log entry written (parse_id, session_id, finding_count — no PHI in audit log body)
- [ ] Prompt injection patterns in override_text sanitized and warned
- [ ] All test cases pass
- [ ] Performance target met (< 5s for typical dental dictation, < 12s maximum)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Applying parsed findings to the odontogram (V-04)
- Voice settings (V-05)
- Fine-tuning the LLM on dental vocabulary (out of scope for MVP)
- Speaker diarization (dentist vs. patient voice separation)
- Structured output streaming (streaming LLM response to frontend in real-time)
- Batch parsing of multiple sessions simultaneously
- Custom condition code mappings per tenant (future enhancement — MVP uses the fixed condition list)
- Multi-language support beyond Spanish variants (future enhancement)

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
- [x] Database models match M1-TECHNICAL-SPEC.md conventions

### Hook 3: Security & Privacy
- [x] Auth level stated (role + tenant context)
- [x] Input sanitization defined (Pydantic + prompt injection prevention)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors (only identifiers in audit log)
- [x] Audit trail for clinical data access
- [x] LLM data transmission policy stated (no patient identifiers sent)

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 5s target, < 12s max)
- [x] Caching strategy stated (N/A — each parse is unique)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] LLM cost tracking per call

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy for external services (Claude Haiku)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec — Voice-to-Odontogram MVP |
