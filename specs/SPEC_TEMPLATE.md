# [Feature Name] Spec

> **Instructions:** Replace all `[placeholders]` with actual values. Delete this instruction block before finalizing.
>
> **Quality Check:** Run Quality Hooks before marking spec as complete.

---

## Overview

**Feature:** [Brief description in 1-2 sentences]

**Domain:** [tenants | auth | users | patients | odontogram | clinical-records | treatment-plans | consents | appointments | notifications | billing | compliance | analytics | portal | admin | messages | prescriptions]

**Priority:** [Critical | High | Medium | Low]

**Dependencies:** [List other specs this depends on, or "None"]

---

## Authentication

- **Level:** [Public | Authenticated | Privileged]
- **Roles allowed:** [if Privileged: clinic_owner, doctor, assistant, receptionist, patient, superadmin]
- **Tenant context:** [Required — resolved from JWT | Not required (superadmin/public)]
- **Special rules:** [Any auth edge cases, or "None"]

---

## Endpoint

```
[METHOD] /api/v1/[path]
```

**Rate Limiting:**
- [X] requests per [minute/hour] per [user/IP/tenant]
- [Or: "Inherits global rate limit (100/min per user)"]

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | [Yes/No] | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | [Yes/No] | string | Request format | application/json |
| X-Tenant-ID | [Yes/No] | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| [param] | [Yes/No] | [type] | [constraints] | [description] | [example] |

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| [param] | [Yes/No] | [type] | [constraints] | [description] | [example] |

### Request Body Schema

```json
{
  "field_name": "type (required/optional)",
  "example_field": "string (required)",
  "optional_field": "number (optional)"
}
```

**Example Request:**
```json
{
  "field_name": "example_value"
}
```

---

## Response

### Success Response

**Status:** [200 OK | 201 Created | 204 No Content]

**Schema:**
```json
{
  "field_name": "type",
  "example_field": "string"
}
```

**Example:**
```json
{
  "id": "uuid",
  "status": "success"
}
```

### Error Responses

#### 400 Bad Request
**When:** [Describe when this occurs]

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Email format is invalid",
  "details": {}
}
```

#### 401 Unauthorized
**When:** [Describe when this occurs, or "Standard auth failure — see infra/authentication-rules.md"]

#### 403 Forbidden
**When:** [Describe when this occurs]

#### 404 Not Found
**When:** [Describe when this occurs]

#### 409 Conflict
**When:** [Describe when this occurs, e.g., duplicate records]

#### 422 Unprocessable Entity
**When:** [Describe when this occurs, e.g., validation failures]

**Example:**
```json
{
  "error": "validation_failed",
  "message": "Validation errors occurred",
  "details": {
    "field_name": ["error message 1", "error message 2"]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** [Describe when this occurs]

---

## Business Logic

**Step-by-step process:**

1. [First step — e.g., "Validate input against Pydantic schema"]
2. [Second step — e.g., "Resolve tenant from JWT claims"]
3. [Third step — e.g., "Check user permissions via RBAC"]
4. [Continue with all steps...]
5. [Final step — e.g., "Return response"]

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| [field_name] | [rule description] | [error message] |

**Business Rules:**

- [Rule 1 — e.g., "Only clinic_owner can invite new users"]
- [Rule 2]

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| [scenario description] | [what should happen] |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- [table_name]: [INSERT | UPDATE | DELETE] — [description]

**Example query (SQLAlchemy):**
```python
stmt = insert(TableModel).values(field1=value1, field2=value2)
await session.execute(stmt)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:[key_pattern]`: [SET | DELETE | INVALIDATE] — [description]

**Cache TTL:** [duration, or "N/A"]

### Queue Jobs (RabbitMQ)

**Jobs dispatched:**

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| [queue_name] | [job_type] | { field: value } | [trigger condition] |

### Audit Log

**Audit entry:** [Yes | No — see infra/audit-logging.md]

**If Yes:**
- **Action:** [create | read | update | delete]
- **Resource:** [entity type]
- **PHI involved:** [Yes | No]

### Notifications

**Notifications triggered:** [Yes | No]

**If Yes:**

| Channel | Template | Recipient | Trigger |
|---------|----------|-----------|---------|
| [email/whatsapp/sms/in-app] | [template_name] | [user/patient/clinic] | [when sent] |

---

## Performance

### Expected Response Time
- **Target:** < [X]ms
- **Maximum acceptable:** < [Y]ms

### Caching Strategy
- **Strategy:** [Redis cache | No caching | Query cache]
- **Cache key:** `tenant:{tenant_id}:[pattern]`
- **TTL:** [duration]
- **Invalidation:** [when cache is cleared]

### Database Performance

**Queries executed:** [number, or "1-2"]

**Indexes required:**
- `[table].[field]` — [type: UNIQUE | INDEX | GIN (full-text)]

**N+1 prevention:** [strategy, or "Not applicable"]

### Pagination

**Pagination:** [Yes | No]

**If Yes:**
- **Style:** [cursor-based | offset-based]
- **Default page size:** [number]
- **Max page size:** [number]

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| [field_name] | [Pydantic validator / strip_tags / bleach] | [notes] |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL unless explicitly justified.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization.

### CSRF Protection

**Strategy:** [JWT-based (stateless) — CSRF not applicable for API | Cookie-based — CSRF token required]

### Data Privacy (PHI)

**PHI fields in this endpoint:** [List fields containing Protected Health Information, or "None"]

**Audit requirement:** [All access logged | Write-only logged | Not required]

---

## Testing

### Test Cases

#### Happy Path
1. [Test case 1]
   - **Given:** [preconditions]
   - **When:** [action]
   - **Then:** [expected result]

#### Edge Cases
1. [Test case 1]
   - **Given:** [preconditions]
   - **When:** [action]
   - **Then:** [expected result]

#### Error Cases
1. [Test case 1]
   - **Given:** [preconditions]
   - **When:** [action]
   - **Then:** [expected result]

### Test Data Requirements

**Users:** [List required user accounts/roles]

**Patients/Entities:** [List required test data]

### Mocking Strategy

- [External service 1]: [mock approach]
- [External service 2]: [mock approach]

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed
- [ ] Audit logging verified (if PHI)

---

## Out of Scope

**This spec explicitly does NOT cover:**

- [Item 1]
- [Item 2]

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [ ] All inputs defined (Pydantic schemas)
- [ ] All outputs defined (response models)
- [ ] API contract defined (OpenAPI compatible)
- [ ] Validation rules stated
- [ ] Error cases enumerated
- [ ] Auth requirements explicit (role + tenant)
- [ ] Side effects listed
- [ ] Examples provided

### Hook 2: Architecture Compliance
- [ ] Follows service boundaries (domain separation)
- [ ] Uses tenant schema isolation
- [ ] Matches FastAPI conventions (async, dependency injection)
- [ ] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [ ] Auth level stated (role + tenant context)
- [ ] Input sanitization defined (Pydantic)
- [ ] SQL injection prevented (SQLAlchemy ORM)
- [ ] No PHI exposure in logs or errors
- [ ] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [ ] Response time target defined
- [ ] Caching strategy stated (tenant-namespaced)
- [ ] DB queries optimized (indexes listed)
- [ ] Pagination applied where needed

### Hook 5: Observability
- [ ] Structured logging (JSON, tenant_id included)
- [ ] Audit log entries defined
- [ ] Error tracking (Sentry-compatible)
- [ ] Queue job monitoring

### Hook 6: Testability
- [ ] Test cases enumerated (happy + edge + error)
- [ ] Test data requirements specified
- [ ] Mocking strategy for external services
- [ ] Acceptance criteria stated

**Overall Status:** [PASS | NEEDS REVISION]

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | [date] | Initial spec |
