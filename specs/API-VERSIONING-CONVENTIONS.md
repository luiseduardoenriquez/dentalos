# DentalOS -- API Versioning and Conventions

> Defines the URL structure, naming conventions, versioning strategy, and response formats for all DentalOS API endpoints.
> All backend specs MUST follow these conventions.

**Version:** 1.0
**Date:** 2026-02-24
**Tech Stack:** Python + FastAPI + Pydantic v2

---

## 1. Base URLs

| Environment | Base URL | Notes |
|-------------|----------|-------|
| **Production** | `https://api.dentalos.app/api/v1/` | Behind load balancer, HTTPS enforced |
| **Staging** | `https://api-staging.dentalos.app/api/v1/` | Mirror of production, test data only |
| **Local development** | `http://localhost:8000/api/v1/` | Docker Compose environment |

All endpoints are prefixed with `/api/v1/`. There is no trailing-slash ambiguity -- FastAPI is configured with `redirect_slashes=True`.

---

## 2. Path Conventions

### 2.1 General Rules

- All path segments are **lowercase**
- Multi-word segments use **kebab-case**: `/clinical-records`, `/treatment-plans`
- Resource nouns are **plural**: `/patients`, `/appointments`, `/invoices`
- Path parameters use **snake_case** with UUID type: `{patient_id}`, `{appointment_id}`

### 2.2 Resource Patterns

**Standard CRUD:**

```
GET    /api/v1/patients                          # List patients
POST   /api/v1/patients                          # Create patient
GET    /api/v1/patients/{patient_id}              # Get patient detail
PUT    /api/v1/patients/{patient_id}              # Update patient (full)
DELETE /api/v1/patients/{patient_id}              # Delete patient (soft)
```

**Nested resources** (parent-child relationship):

```
GET    /api/v1/patients/{patient_id}/clinical-records
POST   /api/v1/patients/{patient_id}/clinical-records
GET    /api/v1/patients/{patient_id}/clinical-records/{record_id}
GET    /api/v1/patients/{patient_id}/odontogram
PUT    /api/v1/patients/{patient_id}/odontogram
GET    /api/v1/patients/{patient_id}/treatment-plans
GET    /api/v1/patients/{patient_id}/consents
```

**Maximum nesting depth:** 2 levels. If deeper nesting is needed, promote the sub-resource to a top-level endpoint with a filter parameter.

```
# Correct (2 levels):
GET /api/v1/patients/{patient_id}/clinical-records/{record_id}

# Incorrect (3 levels -- too deep):
GET /api/v1/patients/{patient_id}/clinical-records/{record_id}/attachments/{attachment_id}

# Instead, use:
GET /api/v1/attachments/{attachment_id}?clinical_record_id={record_id}
```

### 2.3 Custom Actions

When an operation does not map cleanly to CRUD, use a **verb as the final path segment**:

```
POST   /api/v1/appointments/{appointment_id}/cancel
POST   /api/v1/appointments/{appointment_id}/confirm
POST   /api/v1/appointments/{appointment_id}/reschedule
POST   /api/v1/consents/{consent_id}/sign
POST   /api/v1/invoices/{invoice_id}/void
POST   /api/v1/patients/{patient_id}/odontogram/bulk-update
```

Custom actions always use **POST**, even when the operation is idempotent.

### 2.4 Endpoint Namespaces

| Namespace | Pattern | Purpose | Auth |
|-----------|---------|---------|------|
| **Standard** | `/api/v1/{resource}` | Core API for authenticated clinic users | JWT required, tenant context from token |
| **Public** | `/api/v1/public/{tenant_slug}/...` | Patient-facing, no auth required | No JWT, tenant from URL slug |
| **Portal** | `/api/v1/portal/...` | Patient portal (logged-in patients) | JWT required, patient role |
| **Admin** | `/api/v1/admin/...` | Superadmin platform management | JWT required, superadmin role |
| **Catalog** | `/api/v1/catalog/...` | Shared reference data (CIE-10, CUPS) | JWT required, read-only |

**Examples:**

```
# Standard (authenticated clinic staff)
GET  /api/v1/patients
POST /api/v1/appointments

# Public (no auth, patient booking)
GET  /api/v1/public/clinica-sonrisa/available-slots
POST /api/v1/public/clinica-sonrisa/booking

# Portal (authenticated patient)
GET  /api/v1/portal/appointments
GET  /api/v1/portal/clinical-records
POST /api/v1/portal/consents/{consent_id}/sign

# Admin (superadmin)
GET  /api/v1/admin/tenants
POST /api/v1/admin/tenants
GET  /api/v1/admin/tenants/{tenant_id}/usage

# Catalog (shared data)
GET  /api/v1/catalog/cie10?q=caries
GET  /api/v1/catalog/cups?q=endodoncia
```

---

## 3. HTTP Methods

| Method | Usage | Request Body | Idempotent | Response |
|--------|-------|-------------|------------|----------|
| **GET** | Read a resource or list | None | Yes | 200 with resource data |
| **POST** | Create a resource or trigger an action | Required | No | 201 for creation, 200 for actions |
| **PUT** | Full update of a resource | Required (all fields) | Yes | 200 with updated resource |
| **PATCH** | Partial update (post-MVP) | Required (changed fields only) | Yes | 200 with updated resource |
| **DELETE** | Soft delete a resource | None | Yes | 200 with confirmation |

**MVP simplification:** Use PUT for all updates. PATCH is deferred to post-MVP to reduce surface area. PUT requests must include all required fields; the server will reject incomplete payloads.

**Soft delete convention:** DELETE requests set `is_active = false` and `deleted_at = now()` rather than removing records. Clinical data is NEVER hard-deleted (regulatory requirement). A soft-deleted resource returns 404 on subsequent GET requests unless `?include_deleted=true` is passed (clinic_owner and superadmin only).

---

## 4. Naming Rules

### 4.1 JSON Fields

All request and response JSON fields use **snake_case**:

```json
{
  "patient_id": "550e8400-e29b-41d4-a716-446655440000",
  "first_name": "Maria",
  "last_name": "Garcia",
  "date_of_birth": "1990-05-15",
  "phone_number": "+573001234567",
  "created_at": "2026-03-15T10:30:00Z",
  "is_active": true
}
```

**camelCase is NOT used anywhere in the API.** This follows Python/FastAPI convention and avoids the need for serialization transformers.

### 4.2 Entity Identifiers

- All entity IDs are **UUID v4** (not auto-increment integers)
- Generated server-side using Python's `uuid.uuid4()`
- Represented as strings in JSON: `"550e8400-e29b-41d4-a716-446655440000"`
- Stored as `UUID` type in PostgreSQL (not varchar)
- Path parameters: `{entity_id}` (e.g., `{patient_id}`, `{appointment_id}`)

### 4.3 Date and Time

All dates and times follow **ISO 8601** format:

| Type | Format | Example |
|------|--------|---------|
| DateTime (with timezone) | `YYYY-MM-DDTHH:mm:ssZ` | `2026-03-15T10:30:00Z` |
| Date only | `YYYY-MM-DD` | `2026-03-15` |
| Time only | `HH:mm:ss` | `10:30:00` |

- All timestamps stored and returned in **UTC**
- Frontend converts to the tenant's configured timezone for display
- Timezone is stored per tenant (e.g., `America/Bogota`, `America/Mexico_City`)

### 4.4 Enumerations

Enum values use **snake_case** strings (not integers):

```json
{
  "status": "in_progress",
  "role": "clinic_owner",
  "appointment_type": "general_consultation",
  "tooth_condition": "caries"
}
```

---

## 5. Query Parameters

### 5.1 Pagination

**Offset-based (default for most endpoints):**

| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| `page` | integer | 1 | -- | Page number (1-indexed) |
| `page_size` | integer | 20 | 100 | Items per page |

```
GET /api/v1/patients?page=2&page_size=20
```

**Cursor-based (for large or real-time datasets):**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cursor` | string | null | Opaque cursor from previous response |
| `page_size` | integer | 20 | Items per page |

```
GET /api/v1/audit-logs?cursor=eyJpZCI6MTAwfQ&page_size=50
```

Cursor-based pagination is used for: audit logs, notifications, activity feeds.

### 5.2 Filtering

Filters use direct query parameter names matching the resource fields:

```
GET /api/v1/patients?status=active&doctor_id=uuid
GET /api/v1/appointments?date=2026-03-15&status=confirmed
GET /api/v1/clinical-records?patient_id=uuid&date_from=2026-01-01&date_to=2026-03-31
```

**Date range convention:** Use `{field}_from` and `{field}_to` for range filters:
```
?created_at_from=2026-01-01&created_at_to=2026-03-31
```

### 5.3 Sorting

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sort_by` | string | `created_at` | Field to sort by |
| `sort_order` | string | `desc` | `asc` or `desc` |

```
GET /api/v1/patients?sort_by=last_name&sort_order=asc
GET /api/v1/appointments?sort_by=start_time&sort_order=asc
```

Only indexed fields are allowed as sort targets. The API returns 400 if an unsortable field is specified.

### 5.4 Search

Full-text search uses the `q` parameter:

```
GET /api/v1/patients?q=garcia
GET /api/v1/catalog/cie10?q=caries
GET /api/v1/catalog/cups?q=endodoncia
```

Search uses PostgreSQL full-text search (`tsvector`/`tsquery`) with Spanish language configuration. Minimum query length: 2 characters.

---

## 6. Versioning Strategy

### 6.1 Approach

DentalOS uses **URL path versioning**:

```
/api/v1/patients
/api/v2/patients    (future)
```

**Why path versioning over header versioning:**
- Explicit and visible in URLs, logs, and documentation
- Easy to route at the load balancer level
- No ambiguity about which version a client is using
- Simpler for frontend integration

### 6.2 Version Lifecycle

| Version | Status | Notes |
|---------|--------|-------|
| `v1` | Active (MVP and beyond) | Only version for initial launch |
| `v2` | Future | Created only when breaking changes are unavoidable |

### 6.3 What Constitutes a Breaking Change

**Breaking (requires new version):**
- Removing a field from a response
- Changing a field's type (e.g., string to integer)
- Renaming a field
- Changing the URL path of an endpoint
- Changing authentication requirements
- Changing the meaning of an existing enum value

**Non-breaking (allowed within v1):**
- Adding a new optional field to a request
- Adding a new field to a response
- Adding a new endpoint
- Adding a new enum value
- Adding a new query parameter
- Changing error messages (not error codes)

### 6.4 Deprecation Policy (Post-MVP)

When v2 is introduced:
1. v1 endpoints receive a `Deprecation` header: `Deprecation: true`
2. v1 continues to work for a minimum of 6 months
3. Usage metrics track v1 vs v2 adoption
4. v1 is sunset only when adoption drops below 5%

---

## 7. Response Format

### 7.1 Single Resource (Success)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "first_name": "Maria",
  "last_name": "Garcia",
  "email": "maria@example.com",
  "status": "active",
  "created_at": "2026-03-15T10:30:00Z",
  "updated_at": "2026-03-15T10:30:00Z"
}
```

No envelope for single resources. The resource is the top-level JSON object.

### 7.2 List Response (Success)

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "first_name": "Maria",
      "last_name": "Garcia"
    },
    {
      "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
      "first_name": "Carlos",
      "last_name": "Lopez"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

**Cursor-based list response:**

```json
{
  "items": [...],
  "next_cursor": "eyJpZCI6MTAwfQ",
  "has_more": true
}
```

### 7.3 Action Response (Success)

For non-CRUD actions (cancel, confirm, sign):

```json
{
  "status": "success",
  "message": "Appointment cancelled successfully",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "cancelled",
    "cancelled_at": "2026-03-15T10:30:00Z"
  }
}
```

### 7.4 Error Response

All errors follow a consistent structure:

```json
{
  "error": "error_code",
  "message": "Human-readable description of the error",
  "details": {}
}
```

**Error code conventions:**
- snake_case strings (not numeric codes)
- Prefixed by domain when domain-specific: `patient_not_found`, `appointment_conflict`
- Generic codes for cross-cutting errors: `invalid_input`, `unauthorized`, `forbidden`, `not_found`, `rate_limit_exceeded`

**Validation error example (422):**

```json
{
  "error": "validation_failed",
  "message": "One or more fields failed validation",
  "details": {
    "email": ["Invalid email format"],
    "phone_number": ["Phone number must start with country code"],
    "date_of_birth": ["Date cannot be in the future"]
  }
}
```

**Authentication error (401):**

```json
{
  "error": "token_expired",
  "message": "Access token has expired. Use refresh token to obtain a new one.",
  "details": {}
}
```

**Authorization error (403):**

```json
{
  "error": "insufficient_permissions",
  "message": "Your role does not have permission to perform this action",
  "details": {
    "required_role": "clinic_owner",
    "current_role": "receptionist"
  }
}
```

**Plan limit error (403):**

```json
{
  "error": "plan_limit_reached",
  "message": "You have reached the maximum number of patients for your plan",
  "details": {
    "limit": 100,
    "current": 100,
    "upgrade_url": "/settings/billing/upgrade"
  }
}
```

### 7.5 HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Successful GET, PUT, DELETE, or action |
| 201 | Created | Successful POST that creates a resource |
| 204 | No Content | Successful operation with no response body (rare) |
| 400 | Bad Request | Malformed request syntax, invalid JSON |
| 401 | Unauthorized | Missing or invalid authentication token |
| 403 | Forbidden | Authenticated but insufficient permissions or plan limits |
| 404 | Not Found | Resource does not exist or is soft-deleted |
| 409 | Conflict | Duplicate resource (e.g., duplicate email, scheduling conflict) |
| 422 | Unprocessable Entity | Pydantic validation failure |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unhandled server error (logged to Sentry) |
| 503 | Service Unavailable | Maintenance mode or dependency failure |

---

## 8. Request Headers

### 8.1 Required Headers

| Header | Value | Required For | Notes |
|--------|-------|-------------|-------|
| `Authorization` | `Bearer {access_token}` | All authenticated endpoints | JWT access token |
| `Content-Type` | `application/json` | POST, PUT, PATCH requests | Always JSON |

### 8.2 Automatic Headers (Set by Backend)

| Header | Value | Description |
|--------|-------|-------------|
| `X-Request-ID` | UUID | Unique request identifier for tracing |
| `X-Tenant-ID` | UUID | Resolved tenant, included in response for debugging |
| `X-RateLimit-Limit` | integer | Maximum requests allowed in window |
| `X-RateLimit-Remaining` | integer | Requests remaining in current window |
| `X-RateLimit-Reset` | ISO 8601 | When the rate limit window resets |

---

## 9. OpenAPI / Swagger Documentation

FastAPI auto-generates interactive API documentation:

| Path | Tool | Notes |
|------|------|-------|
| `/docs` | Swagger UI | Interactive API explorer with "Try it out" |
| `/redoc` | ReDoc | Clean read-only documentation |
| `/openapi.json` | OpenAPI 3.1 spec | Machine-readable, for code generation |

**Requirements for all endpoints:**
- Every endpoint MUST have a Pydantic request model (for POST/PUT)
- Every endpoint MUST have a Pydantic response model
- Every endpoint MUST have a docstring (appears in Swagger)
- Every endpoint MUST declare its response status codes
- Tags group endpoints by domain: `patients`, `appointments`, `odontogram`, etc.

**FastAPI example:**

```python
@router.post(
    "/patients",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["patients"],
    summary="Create a new patient",
    responses={
        409: {"model": ErrorResponse, "description": "Patient with this email already exists"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
    },
)
async def create_patient(
    patient: PatientCreate,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_tenant_db),
) -> PatientResponse:
    """
    Create a new patient in the current tenant.

    Requires role: clinic_owner, doctor, assistant, or receptionist.
    """
    ...
```

---

## 10. CORS Configuration

```python
ALLOWED_ORIGINS = [
    "https://app.dentalos.app",          # Production frontend
    "https://app-staging.dentalos.app",   # Staging frontend
    "http://localhost:3000",              # Local Next.js dev
]

CORS_SETTINGS = {
    "allow_origins": ALLOWED_ORIGINS,
    "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    "allow_headers": ["Authorization", "Content-Type"],
    "allow_credentials": True,
    "max_age": 86400,  # 24 hours preflight cache
}
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial API conventions document |
