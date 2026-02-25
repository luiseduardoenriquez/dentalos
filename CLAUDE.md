# DentalOS — Development Guide

Multi-tenant dental SaaS for LATAM (Colombia first). North star: "Si no es más rápido que el papel, fallamos."

**Stack:** Python 3.12 + FastAPI | SQLAlchemy 2.0 + PostgreSQL 16 | Redis 7 | RabbitMQ 3 | Next.js 16 + TailwindCSS | Hetzner Cloud
**UI language:** Spanish (es-419). **Code/comments:** English.

---

## Agent Model Selection — MANDATORY

When launching agents via the Task tool, you MUST choose the appropriate model based on task complexity. This is a hard rule — never default to one model for everything.

| Model | When to use | Examples |
|-------|------------|---------|
| **haiku** | Trivial lookups, quick searches, simple file reads | Find a file, search for a keyword, read a config |
| **sonnet** | Mechanical/repetitive work, clear patterns, boilerplate | Create files following existing conventions, write CRUD endpoints, run tests, lint/format, update checklists, write unit tests with clear patterns, standard migrations, search + replace refactors |
| **opus** | Architectural decisions, complex logic, security-critical code, hard debugging | Design APIs with edge cases, multi-domain integration, tenant isolation logic, auth/RBAC implementation, code reviews of critical systems, performance optimization, complex business rules |

**Rule of thumb:** If the task follows an existing pattern or has a clear template → **sonnet**. If it requires judgment, trade-offs, or novel design → **opus**. If it's just a lookup → **haiku**. When in doubt, prefer sonnet over opus — don't waste tokens.

---

## Architecture

Schema-per-tenant PostgreSQL isolation. Each clinic = one schema (`tn_{id}`). Shared `public` schema for global data (tenants, plans, catalogs).

```
Browser → Cloudflare → Hetzner LB (TLS) → FastAPI (port 8000) → PostgreSQL
                                          → Redis (cache/sessions)
                                          → RabbitMQ (async jobs)
Next.js (port 3000) ─── SSR + Static ───→ FastAPI API
```

**Key ADRs** (in `specs/infra/adr/`):
- 001: Schema-per-tenant over row-level isolation
- 007: Country compliance adapters (pluggable per country)
- 008: RabbitMQ over Celery+Redis for healthcare workloads

---

## Project Structure

```
backend/
  app/
    api/v1/          # Route handlers by domain (auth/, patients/, odontogram/, ...)
    core/            # Config, security, database, cache, queue
    models/          # SQLAlchemy models
    schemas/         # Pydantic request/response models
    services/        # Business logic layer
    workers/         # RabbitMQ consumer workers
    events/          # Event handlers (cache invalidation, audit)
  migrations/        # Alembic migrations
  tests/             # factories/, unit/, integration/, e2e/
frontend/
  app/               # Next.js App Router: (public)/, (dashboard)/, (portal)/, (admin)/
  components/        # Shared React components
  lib/               # API client, hooks, utils
specs/               # 371 spec files — see DENTALOS-SDD-MASTER-INDEX.md
```

---

## Backend Conventions

### FastAPI Endpoint Pattern

```python
@router.post("/patients", response_model=PatientResponse, status_code=201, tags=["patients"])
async def create_patient(
    patient: PatientCreate,                          # Pydantic input
    current_user: User = Depends(get_current_user),  # JWT auth
    tenant: TenantContext = Depends(resolve_tenant),  # Tenant resolution
    db: AsyncSession = Depends(get_tenant_db),        # Tenant-scoped DB
) -> PatientResponse:
    """Create a new patient in the current tenant."""
```

**Rules:**
- ALL endpoints `async def`, ALL input via Pydantic v2 — never raw `dict`
- ALL DB via SQLAlchemy 2.0 async — **raw SQL prohibited** unless code-review approved
- Business logic in `services/`, route handlers only: parse → call service → return
- Dependency injection for auth, tenant, DB — never import globally
- Schema naming: `{Entity}Create`, `{Entity}Update`, `{Entity}Response`
- All JSON fields snake_case — **no camelCase anywhere**

---

## Database Conventions

### Naming

| Element | Convention | Example |
|---------|-----------|---------|
| Tables | snake_case, plural | `patients`, `clinical_records` |
| Columns | snake_case | `first_name`, `created_at` |
| Foreign keys | `{referenced_table_singular}_id` | `patient_id`, `doctor_id` |
| Indexes | `idx_{table}_{columns}` | `idx_patients_document_number` |
| Constraints | `chk_{table}_{rule}` | `chk_appointments_status` |

### Column Types

| Data | PostgreSQL | Python | Notes |
|------|-----------|--------|-------|
| IDs | `UUID` | `uuid.UUID` | `gen_random_uuid()`, never auto-increment |
| Money | `INTEGER` | `int` | **Always cents** — never floats |
| Timestamps | `TIMESTAMPTZ` | `datetime` | **Always UTC**, display in tenant TZ |
| Enums | `VARCHAR(20)` + CHECK | `str` | snake_case: `in_progress`, `cancelled` |
| JSON | `JSONB` | `dict` | Settings, features, metadata |
| Booleans | `BOOLEAN` | `bool` | Prefix: `is_active`, `has_portal_access` |

### Required on Every Table

```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid(), created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
```

### Soft Delete — Clinical data is NEVER hard-deleted (regulatory)

Add `is_active BOOLEAN DEFAULT true` + `deleted_at TIMESTAMPTZ`. Returns 404 unless `?include_deleted=true` (clinic_owner/superadmin only).

### Migrations — Alembic runs against ALL tenant schemas. Never modify a deployed migration.

---

## API Conventions

**Base:** `/api/v1/` | **Resources:** plural, kebab-case (`/clinical-records`) | **Max nesting:** 2 levels
**Actions:** `POST /api/v1/{resource}/{id}/{verb}` (cancel, confirm, sign)

| Namespace | Pattern | Auth |
|-----------|---------|------|
| Standard | `/api/v1/{resource}` | JWT (staff) |
| Public | `/api/v1/public/{slug}/...` | None |
| Portal | `/api/v1/portal/...` | JWT (patient) |
| Admin | `/api/v1/admin/...` | JWT (superadmin) |
| Catalog | `/api/v1/catalog/...` | JWT (read-only) |

**Methods:** GET→200 | POST→201 (create) or 200 (action) | PUT→200 | DELETE→200 (soft). MVP uses PUT only, no PATCH.

**Pagination:** `?page=1&page_size=20` → `{"items": [...], "total": 42, "page": 1, "page_size": 20}`. Cursor-based for audit logs, notifications.

**Errors:** `{"error": "DOMAIN_error_name", "message": "...", "details": {}}`. Domains: `AUTH`, `TENANT`, `PATIENT`, `ODONTOGRAM`, `CLINICAL`, `APPOINTMENT`, `BILLING`, `CONSENT`, `SYSTEM`, `VALIDATION`.

---

## Auth & Multi-Tenancy

### JWT (RS256)

| Token | TTL | Storage |
|-------|-----|---------|
| Access (JWT) | 15 min | Client memory (JS variable) |
| Refresh (opaque UUID) | 30 days | HttpOnly cookie + DB (hashed) |

**JWT Claims:**
```json
{
  "sub": "usr_{user_id}",
  "tid": "tn_{tenant_id}",
  "role": "doctor",
  "perms": ["patients:read", "patients:write", "odontogram:write"],
  "aud": "dentalos-api",
  "jti": "tok_{unique_id}"
}
```

### RBAC Roles

| Role | Code | Scope |
|------|------|-------|
| Clinic Owner | `clinic_owner` | Full clinic access |
| Doctor | `doctor` | Full clinical access |
| Assistant | `assistant` | Clinical support (no delete) |
| Receptionist | `receptionist` | Scheduling, billing, intake |
| Patient | `patient` | Own data only (portal) |
| Superadmin | `superadmin` | Platform-wide (separate table) |

Permission check chain: `get_current_user` → `require_role()` → `resolve_tenant()` → `require_permission()`

### Tenant Resolution

```
JWT tid claim → Redis cache (TTL 5min) → public.tenants lookup
→ SET search_path TO tn_{schema_name}, public
```

All Redis keys prefixed: `dentalos:{tenant_id_short}:{domain}:{resource}:{id}`
All S3 paths prefixed: `/{tenant_id}/`
All RabbitMQ messages include `tenant_id` in envelope.

### Multi-Clinic Users

One user can belong to 2-6 clinics via `public.user_tenant_memberships`. Clinic selector shown at login. JWT is issued per-tenant.

---

## Frontend Conventions

- **Framework:** Next.js 16 App Router with route groups: `(public)`, `(dashboard)`, `(portal)`, `(admin)`. Note: `proxy.ts` replaces `middleware.ts` in v16.
- **Styling:** TailwindCSS with custom design tokens. Primary: teal/cyan (`primary-600: #0891B2`). Secondary: slate.
- **State:** React Query (TanStack Query) for server state. Zustand for client state.
- **Forms:** React Hook Form + Zod validation (mirrors Pydantic schemas)
- **Components:** shadcn/ui base, customized with DentalOS design tokens
- **Language:** All UI text in Spanish (es-419). Hardcoded strings → i18n keys for future locales.
- **Responsive:** Tablet-first design. Min viewport: 768px for dashboard, 320px for portal.
- **Dark mode:** Supported. Odontogram anatomic view uses dark theme by default.

---

## Testing

### Backend (pytest)

```
pytest tests/                      # Run all
pytest tests/unit/                 # Unit only
pytest tests/integration/          # Integration only
pytest -m "not slow"               # Skip slow tests
pytest -x --tb=short               # Stop on first failure
```

- **Coverage target:** 80% minimum (`--cov-fail-under=80`)
- **Async mode:** `asyncio_mode = "auto"` in pyproject.toml
- **Factories:** factory_boy with `faker` locale `es_CO` for realistic LATAM data
- **Test DB:** Separate PostgreSQL on port 5433 (RAM-backed tmpfs)
- **Markers:** `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.slow`
- **Mocking:** `respx` for HTTP, `moto` for S3, `freezegun` for time

### Frontend (Vitest + Testing Library)

- Unit: Vitest + React Testing Library
- E2E: Playwright
- Component stories: Storybook (optional)

---

## Caching (Redis)

**Key pattern:** `dentalos:{tid}:{domain}:{resource}:{id}`

| Category | Key Example | TTL |
|----------|-------------|-----|
| Session | `...:auth:session:{uid}` | 15 min |
| Permissions | `...:auth:permissions:{uid}` | 5 min |
| Tenant meta | `...:config:tenant_meta` | 5 min |
| Plan limits | `...:config:plan_limits` | 10 min |
| Odontogram | `...:clinical:odontogram:{pid}` | 2 min |
| Appointment slots | `...:appointment:slots:{did}:{date}` | 1 min |
| Catalog search | `dentalos:shared:catalog:cie10:search:{q}` | 24 h |

Redis is a **performance enhancement**, not a hard dependency. If down, fallthrough to PostgreSQL.

---

## Queue (RabbitMQ)

**Exchange:** `dentalos.direct` (direct) + `dentalos.dlx` (dead letter)

| Queue | Workers | Purpose |
|-------|---------|---------|
| `notifications` | 2 | Email, WhatsApp, SMS, in-app |
| `clinical` | 2 | PDF generation, RIPS, odontogram snapshots |
| `import` | 1 | CSV import, bulk export, tenant seeding |
| `maintenance` | 1 | Audit archive, analytics aggregation, cleanup |

**Message envelope:**
```json
{
  "message_id": "uuid-v4",
  "tenant_id": "tn_abc123",
  "job_type": "email.send",
  "payload": {},
  "priority": 5,
  "retry_count": 0,
  "max_retries": 3
}
```

Retry policy: 3 retries with exponential backoff → dead letter queue on failure.

---

## Security

### PHI (Protected Health Information) Rules

- **Never log:** patient names, document numbers, phone numbers, clinical notes, diagnoses, email addresses
- **Never return in errors:** SQL fragments, schema names, stack traces, internal IDs
- **Never store raw:** refresh tokens (SHA-256 hash only), passwords (bcrypt)
- All clinical data encrypted at rest (PostgreSQL TDE) and in transit (TLS 1.2+)

### Input Validation

- ALL string fields: `.strip()` + reject null bytes
- Rich text fields: sanitize with `bleach` (allowed tags: `b, i, u, br, p, ul, ol, li, strong, em`)
- Structured fields use regex validation:

| Field | Pattern |
|-------|---------|
| Colombian cedula | `^[0-9]{6,12}$` |
| Phone (LATAM) | `^\+?[0-9]{7,15}$` |
| FDI tooth number | `^[1-8][1-8]$` |
| CIE-10 code | `^[A-Z][0-9]{2}(\.[0-9]{1,4})?$` |
| CUPS code | `^[0-9]{6}$` |

### File Uploads

- S3-compatible storage (Hetzner Object / MinIO for dev)
- Max file size: 10MB (images), 25MB (documents)
- Allowed types: JPEG, PNG, PDF, DICOM
- Virus scan before storage
- Signed URLs for access (expire in 15min)
- Path isolation: `/{tenant_id}/{patient_id}/{file_type}/{uuid}.{ext}`

---

## Dev Commands

```bash
# Infrastructure
docker compose up -d               # Start PostgreSQL, Redis, RabbitMQ, MinIO

# Backend
cd backend
python -m uvicorn app.main:app --reload --port 8000  # Dev server
alembic upgrade head               # Run migrations
alembic revision --autogenerate -m "description"      # Create migration
pytest                              # Run all tests
pytest --cov=app --cov-report=html  # Coverage report

# Frontend
cd frontend
npm run dev                         # Next.js dev server (port 3000)
npm run build                       # Production build
npm run test                        # Vitest
npm run lint                        # ESLint + Prettier
```

---

## Spec Reference

371 spec files live in `specs/`. Always consult the relevant spec before implementing a feature.

**Finding specs:**
- Master index: `specs/DENTALOS-SDD-MASTER-INDEX.md`
- Infrastructure: `specs/infra/{topic}.md` (multi-tenancy, auth, DB, caching, queues, security)
- ADRs: `specs/infra/adr/001-*.md` through `008-*.md`
- Domain specs: `specs/{domain}/{feature}.md` (patients, odontogram, appointments, billing, etc.)
- Frontend specs: `specs/frontend/{domain}/{component}.md`
- API conventions: `specs/API-VERSIONING-CONVENTIONS.md`

**When implementing a feature:**
1. Read the domain spec (e.g., `specs/patients/patients-api.md`)
2. Check the API conventions (`specs/API-VERSIONING-CONVENTIONS.md`)
3. Check the error handling spec (`specs/infra/error-handling.md`) for error codes
4. Check the testing spec (`specs/infra/testing-setup.md`) for test patterns
5. Follow this CLAUDE.md for code conventions

### MANDATORY: Update Checklist After Every Completed Task

**After finishing any implementation task** (a spec item, a sub-task, or a full sprint block), you MUST mark the corresponding checkbox as done (`[x]`) in `specs/IMPLEMENTATION-CHECKLIST.md`. This is NOT optional. A task is not considered done until its checklist entry is checked off. Do not wait until the end of a session — update the checklist immediately after each item is completed.
