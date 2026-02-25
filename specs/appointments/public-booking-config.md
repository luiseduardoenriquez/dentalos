# AP-16 Public Booking Configuration Spec

---

## Overview

**Feature:** Return the configuration data needed to render a public booking page for a specific tenant clinic. This is a public GET endpoint that provides clinic branding, available doctors, service types, business hours, and booking constraints. The response is cached for 5 minutes to reduce database load when the booking page is shared widely. No authentication required.

**Domain:** appointments

**Priority:** Medium

**Dependencies:** AP-15 (public-booking.md), infra/multi-tenancy.md, infra/caching.md, U-01 (user-list.md), infra/rate-limiting.md

---

## Authentication

- **Level:** Public
- **Tenant context:** Not required — tenant resolved from `tenant_slug` URL parameter
- **Roles allowed:** None — public endpoint, no JWT required
- **Special rules:** Tenant must be active. Inactive tenants return 404. No sensitive internal data (user IDs, internal settings, financial data) is exposed.

---

## Endpoint

```
GET /api/v1/public/booking/{tenant_slug}/config
```

**Rate Limiting:**
- 60 requests per minute per IP address (generous limit since this is a page-load call)
- Redis sliding window: `dentalos:rl:public_config:{ip}` (TTL 60s)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Accept | No | string | Desired response format | application/json |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| tenant_slug | Yes | string | Lowercase alphanumeric, hyphens allowed, max 63 chars | Tenant identifier from shareable URL | clinica-san-jose |

### Query Parameters

None.

### Request Body Schema

None — GET request.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "clinic": {
    "name": "string",
    "logo_url": "string | null — publicly accessible HTTPS URL",
    "address": "string | null",
    "city": "string | null",
    "phone": "string | null",
    "email": "string | null",
    "website": "string | null",
    "booking_instructions": "string | null — custom text for the booking page, max 500 chars"
  },
  "doctors": [
    {
      "id": "uuid — doctor's internal ID for use in booking request",
      "first_name": "string",
      "last_name": "string",
      "specialty": "string | null",
      "avatar_url": "string | null — publicly accessible HTTPS URL",
      "bio": "string | null — short professional bio, max 300 chars",
      "accepts_online_booking": "boolean"
    }
  ],
  "service_types": [
    {
      "value": "string — enum value to send in booking request",
      "label": "string — human-readable label in es-419",
      "duration_minutes": "integer — estimated duration"
    }
  ],
  "business_hours": [
    {
      "day_of_week": "integer — 0=Monday, 6=Sunday",
      "day_label": "string — e.g. Lunes",
      "is_open": "boolean",
      "open_time": "string | null — HH:MM 24h format",
      "close_time": "string | null — HH:MM 24h format"
    }
  ],
  "booking_config": {
    "min_advance_booking_hours": "integer — minimum hours before appointment can be booked",
    "max_advance_booking_days": "integer — how far in advance a patient can book",
    "slot_interval_minutes": "integer — granularity of available slots, e.g. 30",
    "timezone": "string — IANA timezone, e.g. America/Bogota",
    "currency": "string — ISO 4217",
    "public_booking_enabled": "boolean"
  }
}
```

**Example:**
```json
{
  "clinic": {
    "name": "Clinica Dental San Jose",
    "logo_url": "https://cdn.dentalos.app/tenants/clinica-san-jose/logo.png",
    "address": "Calle 45 #12-34, Chapinero",
    "city": "Bogota",
    "phone": "+5716001234",
    "email": "contacto@clinicasanjose.com",
    "website": "https://clinicasanjose.com",
    "booking_instructions": "Por favor llegue 10 minutos antes de su cita. Traiga su documento de identidad."
  },
  "doctors": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "first_name": "Carlos",
      "last_name": "Mendez",
      "specialty": "Odontologia General",
      "avatar_url": "https://cdn.dentalos.app/tenants/clinica-san-jose/doctors/carlos-mendez.jpg",
      "bio": "Odontologo con 12 anos de experiencia en odontologia general y estetica.",
      "accepts_online_booking": true
    },
    {
      "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "first_name": "Ana",
      "last_name": "Reyes",
      "specialty": "Ortodoncia",
      "avatar_url": null,
      "bio": null,
      "accepts_online_booking": true
    }
  ],
  "service_types": [
    { "value": "consultation", "label": "Consulta General", "duration_minutes": 30 },
    { "value": "procedure", "label": "Procedimiento", "duration_minutes": 60 },
    { "value": "follow_up", "label": "Control", "duration_minutes": 20 }
  ],
  "business_hours": [
    { "day_of_week": 0, "day_label": "Lunes", "is_open": true, "open_time": "08:00", "close_time": "17:00" },
    { "day_of_week": 1, "day_label": "Martes", "is_open": true, "open_time": "08:00", "close_time": "17:00" },
    { "day_of_week": 2, "day_label": "Miercoles", "is_open": true, "open_time": "08:00", "close_time": "17:00" },
    { "day_of_week": 3, "day_label": "Jueves", "is_open": true, "open_time": "08:00", "close_time": "17:00" },
    { "day_of_week": 4, "day_label": "Viernes", "is_open": true, "open_time": "08:00", "close_time": "16:00" },
    { "day_of_week": 5, "day_label": "Sabado", "is_open": false, "open_time": null, "close_time": null },
    { "day_of_week": 6, "day_label": "Domingo", "is_open": false, "open_time": null, "close_time": null }
  ],
  "booking_config": {
    "min_advance_booking_hours": 2,
    "max_advance_booking_days": 60,
    "slot_interval_minutes": 30,
    "timezone": "America/Bogota",
    "currency": "COP",
    "public_booking_enabled": true
  }
}
```

### Error Responses

#### 404 Not Found
**When:** `tenant_slug` does not match any active tenant. Also returned for inactive tenants to prevent enumeration.

**Example:**
```json
{
  "error": "not_found",
  "message": "La clinica no fue encontrada."
}
```

#### 429 Too Many Requests
**When:** IP has exceeded 60 requests per minute. See `infra/rate-limiting.md`.

**Example:**
```json
{
  "error": "rate_limit_exceeded",
  "message": "Demasiadas solicitudes. Por favor espera un momento.",
  "retry_after_seconds": 30
}
```

#### 500 Internal Server Error
**When:** Unexpected database or cache failure.

---

## Business Logic

**Step-by-step process:**

1. Check IP-based rate limit via Redis: key `dentalos:rl:public_config:{ip}`. If exceeded, return 429.
2. Validate `tenant_slug` format (regex `^[a-z0-9-]{1,63}$`). If invalid format, return 404 (avoid information leakage).
3. Check Redis cache: key `dentalos:public_config:{tenant_slug}`. If cache hit, return cached response with `Cache-Control: public, max-age=300` header.
4. If cache miss, resolve tenant from `public.tenants` table `WHERE slug = :tenant_slug AND is_active = true`. If not found, return 404.
5. Set `search_path` to tenant schema for subsequent queries.
6. Load clinic profile from `tenant_settings` or `tenants` table: name, logo_url, address, city, phone, email, website, booking_instructions.
7. Load active doctors with `accepts_online_booking = true`: query `users` table `WHERE role = 'doctor' AND is_active = true AND accepts_online_booking = true`, select only public fields (id, first_name, last_name, specialty, avatar_url, bio). Order by last_name ASC.
8. Build `service_types` array from tenant's enabled appointment types and their configured default durations. Emergency type is excluded from public booking by default (configurable).
9. Load clinic business hours from `clinic_business_hours` table (7 records, one per day_of_week). If not configured, use system defaults (Mon-Fri 08:00-17:00).
10. Load booking configuration from `tenant_settings`: min_advance_booking_hours, max_advance_booking_days, slot_interval_minutes, timezone, currency. Apply defaults where not set.
11. Build response object. Ensure no internal IDs (other than doctor IDs needed for booking), no financial data, no PHI are included.
12. Serialize and store in Redis cache: key `dentalos:public_config:{tenant_slug}`, TTL = 300s (5 minutes).
13. Return 200 with `Cache-Control: public, max-age=300` and `ETag` header (MD5 of response body) to support conditional GET.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| tenant_slug (URL) | Regex `^[a-z0-9-]{1,63}$`, must resolve to active tenant | La clinica no fue encontrada. |

**Business Rules:**

- Only doctors with `accepts_online_booking = true` are returned in the doctors list. Doctors can opt out of online booking independently of their active status.
- The `emergency` service type is excluded from the public booking service_types list by default. If a clinic explicitly enables it, it appears.
- Business hours returned are the clinic-level hours, not individual doctor schedules. The availability slot picker (AP-09) handles per-doctor availability.
- Doctor UUIDs are intentionally exposed to allow the booking form to send `doctor_id` in the POST request. However, no other internal IDs are included in this response.
- `logo_url` and `avatar_url` must be fully qualified HTTPS URLs pointing to the CDN. If not configured, null is returned (frontend uses placeholder).
- The response includes `public_booking_enabled` in the `booking_config` object so the frontend can show an appropriate message if booking is disabled after the page has loaded.
- This endpoint returns the same response regardless of whether the request comes from the booking page frontend or any other HTTP client. No personalization.
- If a tenant has no doctors with `accepts_online_booking = true`, `doctors` array is empty. Booking is effectively disabled even if `public_booking_enabled = true`.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Tenant has no configured business hours | Returns Mon-Fri 08:00-17:00 as system defaults |
| All doctors have accepts_online_booking=false | Returns empty doctors array; public_booking_enabled may still be true |
| Tenant logo_url is not configured | Returns null for logo_url; frontend uses placeholder |
| Tenant timezone not configured | Defaults to America/Bogota |
| slug matches inactive tenant | Returns 404 (same as not found) |
| Cache key exists but response deserialization fails | Evict stale key, rebuild from DB, re-cache |

---

## Side Effects

### Database Changes

**No write operations** — this is a read-only endpoint.

### Cache Operations

**Cache keys affected:**
- `dentalos:public_config:{tenant_slug}`: SET on cache miss — full response JSON stored

**Cache TTL:** 300 seconds (5 minutes)

**Cache invalidation:** When clinic profile, doctor list, or booking settings change (handled by the respective update endpoints via cache key deletion). Key pattern: `dentalos:public_config:{tenant_slug}`.

**Example cache set (Python):**
```python
import json
cache_key = f"dentalos:public_config:{tenant_slug}"
await redis.set(cache_key, json.dumps(response_data), ex=300)
```

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None — read-only endpoint.

### Audit Log

**Audit entry:** No — read-only public endpoint, no PHI accessed.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 50ms (cache hit)
- **Target:** < 200ms (cache miss)
- **Maximum acceptable:** < 400ms (cache miss under load)

### Caching Strategy
- **Strategy:** Full response Redis cache with 5-minute TTL
- **Cache key:** `dentalos:public_config:{tenant_slug}`
- **TTL:** 300 seconds
- **Invalidation:** Explicit key deletion when tenant settings, doctor profile, or business hours are updated

### Database Performance

**Queries executed (cache miss only):** 4 (tenant lookup, clinic settings, doctors list, business hours)

**Indexes required:**
- `tenants.slug` — UNIQUE INDEX (public schema)
- `users.(tenant_id, role, is_active, accepts_online_booking)` — COMPOSITE INDEX
- `clinic_business_hours.tenant_id` — INDEX

**N+1 prevention:** Doctors loaded in a single query with all public fields. Business hours loaded with a single query returning all 7 rows.

### Pagination

**Pagination:** No — returns complete configuration in a single response. Doctor list is bounded by clinic size (typically 1-20 doctors).

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| tenant_slug | Pydantic regex `^[a-z0-9-]{1,63}$` | Prevents path traversal and injection |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs are escaped by default via Pydantic serialization. Stored content (clinic bio, booking_instructions) was sanitized with bleach at write time.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for this read-only public API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None. Doctor names and specialties are professional/public information. Patient data is never included.

**Audit requirement:** Not required — public read-only, no PHI.

### Data Exposure Controls

The following fields are **explicitly excluded** from this endpoint's response to prevent information leakage:
- Doctor user IDs beyond what is needed for booking (`user_id` is used as `id` in the doctors array — this is intentional and required)
- Internal tenant settings (billing config, DIAN settings, webhook secrets)
- Doctor email addresses and personal phone numbers
- Appointment history or patient counts
- Any financial or compliance-related configuration

---

## Testing

### Test Cases

#### Happy Path
1. Config request for active tenant with 2 doctors
   - **Given:** Tenant `clinica-san-jose` is active, has 2 doctors with accepts_online_booking=true, business hours Mon-Fri configured
   - **When:** GET /api/v1/public/booking/clinica-san-jose/config
   - **Then:** 200 OK, doctors array has 2 entries, business_hours has 7 entries, booking_config populated

2. Cache hit on second request
   - **Given:** First request populated Redis cache
   - **When:** Second GET within 5 minutes
   - **Then:** 200 OK, response served from cache (0 DB queries), response identical

3. Tenant with no configured business hours returns defaults
   - **Given:** Tenant has no `clinic_business_hours` records
   - **When:** GET config
   - **Then:** business_hours array contains Mon-Fri open 08:00-17:00, Sat-Sun closed

#### Edge Cases
1. All doctors have accepts_online_booking=false
   - **Given:** Tenant with 3 doctors, all with accepts_online_booking=false
   - **When:** GET config
   - **Then:** 200 OK, `doctors: []`, `public_booking_enabled: true` (settings unchanged)

2. Cache eviction and rebuild on settings update
   - **Given:** Config cached, then clinic updates booking_instructions
   - **When:** Cache key is deleted by update endpoint, then GET config
   - **Then:** Fresh DB query, new booking_instructions in response, re-cached

#### Error Cases
1. Unknown tenant slug
   - **Given:** Slug `nonexistent-clinic` does not exist
   - **When:** GET /api/v1/public/booking/nonexistent-clinic/config
   - **Then:** 404 Not Found

2. Inactive tenant slug
   - **Given:** Tenant with slug `old-clinic` exists but `is_active = false`
   - **When:** GET request
   - **Then:** 404 Not Found (same as missing)

3. Rate limit exceeded
   - **Given:** IP has made 60 requests in the last minute
   - **When:** 61st request
   - **Then:** 429 Too Many Requests

### Test Data Requirements

**Tenants:** One active tenant with full profile (logo, address, business hours, 2 doctors); one inactive tenant; one active tenant with no configured business hours; one active tenant with all doctors opting out of online booking

**Doctors:** Two active doctors with accepts_online_booking=true; one with accepts_online_booking=false

### Mocking Strategy

- Redis: Use `fakeredis` to test both cache hit and cache miss paths
- Database: SQLite in-memory for integration tests; seed clinic_business_hours and users tables

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET /api/v1/public/booking/{tenant_slug}/config returns 200 with full config object
- [ ] Only doctors with accepts_online_booking=true appear in response
- [ ] Business hours returned from DB or system defaults if not configured
- [ ] Response cached for 5 minutes with correct Cache-Control header
- [ ] Cache is populated on miss and served on subsequent requests within TTL
- [ ] No PHI, internal IDs (beyond doctor ID for booking), or financial data exposed
- [ ] Unknown/inactive tenant returns 404
- [ ] Cache invalidated when related settings change
- [ ] All test cases pass
- [ ] Performance targets met (< 50ms cache hit, < 200ms cache miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Per-doctor availability slot listing (see AP-09 availability-get.md)
- Actual booking submission (see AP-15 public-booking.md)
- Booking configuration management by clinic staff (see AP-17, AP-18)
- Doctor schedule configuration (see U-07 doctor-schedule.md)
- Authenticated clinic staff viewing their own public booking page config (use admin settings instead)
- Multi-language support (es-419 only for MVP)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (URL param only)
- [x] All outputs defined (full response model)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated (minimal — slug format)
- [x] Error cases enumerated
- [x] Auth requirements explicit (public, no JWT)
- [x] Side effects listed (cache write only)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (appointments domain, public sub-domain)
- [x] Uses tenant schema isolation (resolved from slug)
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (public, no PHI exposed)
- [x] Input sanitization defined
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No internal data exposed (explicit exclusion list documented)
- [x] Audit trail not required (no PHI, no writes)

### Hook 4: Performance & Scalability
- [x] Response time targets defined (50ms cache, 200ms miss)
- [x] Full response caching with 5min TTL
- [x] DB queries optimized (4 queries on miss, indexes listed)
- [x] Pagination N/A (bounded response size)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id, cache hit/miss flag)
- [x] No PHI in logs
- [x] Error tracking (Sentry-compatible)
- [x] Cache hit rate monitorable via Redis metrics

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy (fakeredis, seeded DB)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
