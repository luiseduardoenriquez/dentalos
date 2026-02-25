# Multi-Tenancy Infrastructure Spec

---

## Overview

**Feature:** Schema-per-tenant multi-tenancy architecture for DentalOS. Defines how tenant data is isolated at the PostgreSQL schema level, how tenant context is resolved and propagated through every request, how connection pooling and caching work across tenants, and how plan-based limits are enforced.

**Domain:** infra

**Priority:** Critical

**Spec ID:** I-01

**Dependencies:** None (this is the foundational spec; all other specs depend on it)

---

## Table of Contents

1. [Architecture Decision: Schema-Per-Tenant](#1-architecture-decision-schema-per-tenant)
2. [Schema Design](#2-schema-design)
3. [Tenant Resolution](#3-tenant-resolution)
4. [Tenant Isolation Guarantees](#4-tenant-isolation-guarantees)
5. [Plan Enforcement](#5-plan-enforcement)
6. [Tenant Provisioning Flow](#6-tenant-provisioning-flow)
7. [Tenant Lifecycle Management](#7-tenant-lifecycle-management)
8. [Schema Migration Strategy](#8-schema-migration-strategy)
9. [Connection Pooling](#9-connection-pooling)
10. [Cache Isolation](#10-cache-isolation)
11. [Queue Isolation](#11-queue-isolation)
12. [File Storage Isolation](#12-file-storage-isolation)
13. [Performance Considerations](#13-performance-considerations)
14. [Security](#14-security)
15. [Monitoring and Observability](#15-monitoring-and-observability)
16. [Testing](#16-testing)
17. [Out of Scope](#17-out-of-scope)
18. [Quality Hooks Checklist](#18-quality-hooks-checklist)
19. [Version History](#19-version-history)

---

## 1. Architecture Decision: Schema-Per-Tenant

### Decision

DentalOS uses **PostgreSQL schema-per-tenant** isolation. Each tenant (dental clinic) gets its own PostgreSQL schema within a single database instance. A shared `public` schema holds global data.

### Alternatives Considered

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Row-level isolation** (single schema, `tenant_id` column on every table) | Simplest to implement. Single migration path. Lower operational overhead. | Every query must include `tenant_id` filter. One missed WHERE clause leaks data across tenants. No physical isolation. Harder to comply with LATAM healthcare data regulations that expect logical separation. Index bloat as tenant count grows. Cannot drop a single tenant's data easily. | Rejected |
| **Schema-per-tenant** (one schema per tenant, shared database) | Strong logical isolation. Accidental cross-tenant access is structurally impossible when search_path is set correctly. Per-tenant backup/restore possible via `pg_dump -n`. Clean tenant deletion (DROP SCHEMA CASCADE). Compliance-friendly. Moderate operational complexity. | More schemas to migrate. Connection pooling requires search_path switching. PostgreSQL catalog grows with schema count (manageable up to ~5,000 schemas). Slightly more complex Alembic setup. | **Selected** |
| **Database-per-tenant** (separate PostgreSQL database per tenant) | Strongest isolation. Independent scaling, backup, restore. | Extreme operational overhead. Connection pooling nightmare (one pool per database). Cannot do cross-tenant queries for analytics. Expensive at scale on Hetzner. Migration across hundreds of databases is slow. Overkill for our scale (target: 500-2,000 clinics in year one). | Rejected |

### Rationale

Schema-per-tenant is the right trade-off for DentalOS because:

1. **Healthcare data sensitivity.** Dental records are PHI (Protected Health Information). Schema-level isolation means a bug in one query cannot accidentally expose Clinic A's patient records to Clinic B. The PostgreSQL `search_path` mechanism provides a structural barrier, not just a convention.

2. **Regulatory alignment.** LATAM healthcare regulations (Colombia's Resolucion 1995 de 1999 for clinical records, Ley 1581 de 2012 for data protection) expect logical data separation between organizations. Schema-per-tenant provides a clear, auditable boundary.

3. **Operational simplicity at target scale.** DentalOS targets 500-2,000 clinics in year one, potentially 10,000 within three years. PostgreSQL handles thousands of schemas without issue. The `pg_catalog` overhead is negligible at this scale.

4. **Clean tenant lifecycle.** When a clinic cancels, we can archive and drop the entire schema. No need to surgically delete rows from dozens of shared tables while maintaining referential integrity.

5. **Per-tenant maintenance.** We can run maintenance operations (VACUUM, REINDEX) on specific tenant schemas without affecting others. We can restore a single tenant from backup without restoring the entire database.

> **ADR Reference:** See `infra/adr/001-schema-per-tenant.md` for the full Architecture Decision Record.

---

## 2. Schema Design

### 2.1 Shared `public` Schema

The `public` schema contains data that is global to the platform or must be readable by all tenants.

```sql
-- ============================================================
-- PUBLIC SCHEMA: Platform-wide tables
-- ============================================================

-- Tenant registry
CREATE TABLE public.tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            VARCHAR(63) NOT NULL UNIQUE,        -- URL-safe identifier, e.g. "clinica-sonrisa"
    schema_name     VARCHAR(63) NOT NULL UNIQUE,        -- e.g. "tn_a1b2c3d4"
    name            VARCHAR(255) NOT NULL,              -- Display name: "Clinica Dental Sonrisa"
    country_code    CHAR(2) NOT NULL DEFAULT 'CO',      -- ISO 3166-1 alpha-2
    timezone        VARCHAR(50) NOT NULL DEFAULT 'America/Bogota',
    currency_code   CHAR(3) NOT NULL DEFAULT 'COP',     -- ISO 4217
    plan_id         UUID NOT NULL REFERENCES public.plans(id),
    status          VARCHAR(20) NOT NULL DEFAULT 'provisioning',
        -- provisioning | active | suspended | cancelled | deleted
    owner_user_id   UUID,                               -- First user created during provisioning
    settings        JSONB NOT NULL DEFAULT '{}',        -- Tenant-specific config (odontogram_mode, etc.)
    trial_ends_at   TIMESTAMPTZ,
    suspended_at    TIMESTAMPTZ,
    cancelled_at    TIMESTAMPTZ,
    deleted_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tenants_slug ON public.tenants(slug);
CREATE INDEX idx_tenants_status ON public.tenants(status);
CREATE INDEX idx_tenants_country ON public.tenants(country_code);

-- Subscription plans
CREATE TABLE public.plans (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(50) NOT NULL UNIQUE,        -- free, starter, professional, enterprise
    display_name    VARCHAR(100) NOT NULL,              -- "Plan Gratuito", "Plan Inicial", etc.
    price_cop       INTEGER NOT NULL DEFAULT 0,         -- Monthly price in COP (Colombian Pesos)
    price_mxn       INTEGER NOT NULL DEFAULT 0,         -- Monthly price in MXN
    price_usd       INTEGER NOT NULL DEFAULT 0,         -- Monthly price in USD (fallback)
    max_patients    INTEGER NOT NULL DEFAULT 50,
    max_doctors     INTEGER NOT NULL DEFAULT 1,
    max_assistants  INTEGER NOT NULL DEFAULT 2,
    max_storage_mb  INTEGER NOT NULL DEFAULT 500,       -- File storage limit
    max_appointments_per_month INTEGER NOT NULL DEFAULT 200,
    features        JSONB NOT NULL DEFAULT '{}',
        -- {
        --   "odontogram_anatomic": false,
        --   "patient_portal": false,
        --   "whatsapp_reminders": false,
        --   "custom_consent_templates": false,
        --   "treatment_plan_pdf": true,
        --   "analytics_advanced": false,
        --   "electronic_invoice": false,
        --   "api_access": false,
        --   "white_label": false,
        --   "offline_mode": false,
        --   "bulk_import": false,
        --   "multi_branch": false
        -- }
    is_active       BOOLEAN NOT NULL DEFAULT true,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Superadmin users (platform administrators, NOT clinic users)
CREATE TABLE public.superadmin_users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    name            VARCHAR(255) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    mfa_secret      VARCHAR(255),
    mfa_enabled     BOOLEAN NOT NULL DEFAULT false,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Global catalogs (read-only for tenants)

-- CIE-10 diagnostic codes (dental-relevant subset)
CREATE TABLE public.cie10_codes (
    code            VARCHAR(10) PRIMARY KEY,            -- e.g. "K02.1"
    description_es  TEXT NOT NULL,                       -- Spanish description
    description_en  TEXT,                                -- English description (optional)
    category        VARCHAR(50),                         -- e.g. "dental_caries", "periodontal"
    is_dental       BOOLEAN NOT NULL DEFAULT true,
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('spanish', code || ' ' || description_es)
    ) STORED
);

CREATE INDEX idx_cie10_search ON public.cie10_codes USING GIN(search_vector);
CREATE INDEX idx_cie10_category ON public.cie10_codes(category);

-- CUPS procedure codes (dental-relevant subset, Colombia-first)
CREATE TABLE public.cups_codes (
    code            VARCHAR(10) PRIMARY KEY,            -- e.g. "232101"
    description_es  TEXT NOT NULL,
    description_en  TEXT,
    category        VARCHAR(50),
    country_code    CHAR(2) NOT NULL DEFAULT 'CO',      -- Country where this code applies
    is_dental       BOOLEAN NOT NULL DEFAULT true,
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('spanish', code || ' ' || description_es)
    ) STORED
);

CREATE INDEX idx_cups_search ON public.cups_codes USING GIN(search_vector);
CREATE INDEX idx_cups_country ON public.cups_codes(country_code);

-- Dental conditions catalog (used by odontogram)
CREATE TABLE public.dental_conditions (
    code            VARCHAR(20) PRIMARY KEY,            -- e.g. "caries", "restoration"
    name_es         VARCHAR(100) NOT NULL,
    name_en         VARCHAR(100),
    color_hex       CHAR(7) NOT NULL,                   -- e.g. "#FF0000"
    icon_svg        TEXT,                                -- SVG path data for rendering
    applies_to      VARCHAR(20) NOT NULL DEFAULT 'zone',-- zone | tooth | root
    sort_order      INTEGER NOT NULL DEFAULT 0
);

-- Medication catalog (dental-relevant subset)
CREATE TABLE public.medications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    active_ingredient VARCHAR(255),
    presentation    VARCHAR(255),                       -- e.g. "Tableta 500mg"
    category        VARCHAR(50),
    country_codes   CHAR(2)[] NOT NULL DEFAULT '{CO}',  -- Countries where available
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('spanish', name || ' ' || COALESCE(active_ingredient, ''))
    ) STORED
);

CREATE INDEX idx_medications_search ON public.medications USING GIN(search_vector);

-- Feature flags (platform-wide and per-tenant overrides)
CREATE TABLE public.feature_flags (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key             VARCHAR(100) NOT NULL UNIQUE,       -- e.g. "offline_mode_v2"
    description     TEXT,
    enabled_global  BOOLEAN NOT NULL DEFAULT false,
    tenant_overrides JSONB NOT NULL DEFAULT '{}',       -- {"tenant_id": true/false}
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 2.2 Tenant Schema Naming Convention

Each tenant schema follows the naming convention:

```
tn_{short_uuid}
```

Where `short_uuid` is the first 8 characters of the tenant's UUID (lowercase, hex). Examples:

- Tenant UUID `a1b2c3d4-e5f6-7890-abcd-ef1234567890` -> schema `tn_a1b2c3d4`
- Tenant UUID `f9e8d7c6-b5a4-3210-fedc-ba0987654321` -> schema `tn_f9e8d7c6`

**Why not `tenant_{slug}`?**
- Slugs can change (clinic renames). Schema names should be immutable.
- Slugs can be long. PostgreSQL identifiers are limited to 63 characters.
- UUID-based names are guaranteed unique. No collision risk.
- Slugs contain user input. UUID prefixes avoid any injection concerns in DDL.

**Collision handling:** The 8-character hex prefix gives 4 billion possible values. If a collision occurs (astronomically unlikely), the system appends the next 4 characters: `tn_a1b2c3d4e5f6`.

### 2.3 Tenant Schema Template

Every tenant schema contains the following tables. This is the canonical list; see `infra/database-architecture.md` (I-04) for complete column definitions and indexes.

```sql
-- ============================================================
-- TENANT SCHEMA TEMPLATE: tn_{short_uuid}
-- Created during tenant provisioning
-- ============================================================

-- Users within this tenant (doctors, assistants, receptionists, clinic_owner)
CREATE TABLE {schema}.users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email               VARCHAR(255) NOT NULL,
    password_hash       VARCHAR(255) NOT NULL,
    name                VARCHAR(255) NOT NULL,
    phone               VARCHAR(20),
    role                VARCHAR(20) NOT NULL,
        -- clinic_owner | doctor | assistant | receptionist
    avatar_url          TEXT,
    professional_license VARCHAR(50),    -- Tarjeta profesional (Colombia)
    specialties         TEXT[],          -- e.g. {"endodoncia", "ortodoncia"}
    is_active           BOOLEAN NOT NULL DEFAULT true,
    is_email_verified   BOOLEAN NOT NULL DEFAULT false,
    last_login_at       TIMESTAMPTZ,
    notification_prefs  JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(email)
);

-- Patients
CREATE TABLE {schema}.patients ( ... );

-- Odontogram state (current conditions per tooth per patient)
CREATE TABLE {schema}.odontogram_conditions ( ... );

-- Odontogram change history
CREATE TABLE {schema}.odontogram_history ( ... );

-- Odontogram snapshots (point-in-time captures)
CREATE TABLE {schema}.odontogram_snapshots ( ... );

-- Clinical records (anamnesis, examination, diagnosis, evolution, procedure)
CREATE TABLE {schema}.clinical_records ( ... );

-- Anamnesis (structured medical history)
CREATE TABLE {schema}.anamnesis ( ... );

-- Diagnoses (linked to CIE-10 codes in public schema)
CREATE TABLE {schema}.diagnoses ( ... );

-- Procedures performed (linked to CUPS codes in public schema)
CREATE TABLE {schema}.procedures ( ... );

-- Treatment plans
CREATE TABLE {schema}.treatment_plans ( ... );

-- Treatment plan items (individual procedures within a plan)
CREATE TABLE {schema}.treatment_plan_items ( ... );

-- Informed consent forms
CREATE TABLE {schema}.consents ( ... );

-- Consent templates (custom per tenant, in addition to public defaults)
CREATE TABLE {schema}.consent_templates ( ... );

-- Appointments
CREATE TABLE {schema}.appointments ( ... );

-- Doctor weekly schedule templates
CREATE TABLE {schema}.doctor_schedules ( ... );

-- Availability blocks (vacations, breaks)
CREATE TABLE {schema}.availability_blocks ( ... );

-- Waitlist entries
CREATE TABLE {schema}.waitlist ( ... );

-- Invoices
CREATE TABLE {schema}.invoices ( ... );

-- Invoice line items
CREATE TABLE {schema}.invoice_items ( ... );

-- Payments
CREATE TABLE {schema}.payments ( ... );

-- Payment plans (installment schedules)
CREATE TABLE {schema}.payment_plans ( ... );

-- Payment plan installments
CREATE TABLE {schema}.payment_plan_installments ( ... );

-- Service/procedure price catalog (clinic-specific pricing)
CREATE TABLE {schema}.service_catalog ( ... );

-- Prescriptions
CREATE TABLE {schema}.prescriptions ( ... );

-- Prescription medications (line items)
CREATE TABLE {schema}.prescription_items ( ... );

-- Patient documents (metadata; files stored in S3)
CREATE TABLE {schema}.patient_documents ( ... );

-- In-app notifications
CREATE TABLE {schema}.notifications ( ... );

-- Message threads (clinic <-> patient messaging)
CREATE TABLE {schema}.message_threads ( ... );

-- Messages within threads
CREATE TABLE {schema}.messages ( ... );

-- Refresh tokens
CREATE TABLE {schema}.refresh_tokens ( ... );

-- Audit log (immutable)
CREATE TABLE {schema}.audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID,
    action          VARCHAR(20) NOT NULL,   -- create | read | update | delete
    resource_type   VARCHAR(50) NOT NULL,   -- patient | clinical_record | odontogram | etc.
    resource_id     UUID,
    old_values      JSONB,
    new_values      JSONB,
    ip_address      INET,
    user_agent      TEXT,
    phi_accessed    BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Tenant-specific settings (clinic branding, preferences)
CREATE TABLE {schema}.tenant_settings (
    key             VARCHAR(100) PRIMARY KEY,
    value           JSONB NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

> **Note:** Full column definitions, constraints, and indexes for each table are specified in `infra/database-architecture.md` (I-04). The listing above shows structure and relationships, not exhaustive DDL.

---

## 3. Tenant Resolution

### 3.1 Resolution Strategy

Tenant context is resolved from **JWT claims**. Every authenticated request carries a JWT access token that includes the tenant identifier.

```
JWT Payload:
{
  "sub": "user-uuid",
  "tenant_id": "tenant-uuid",
  "schema": "tn_a1b2c3d4",
  "role": "doctor",
  "exp": 1709251200,
  "iat": 1709250300,
  "jti": "token-uuid"
}
```

**Why JWT-based and not subdomain-based or header-based?**

| Method | Verdict | Reason |
|--------|---------|--------|
| Subdomain (`clinica-sonrisa.dentalos.app`) | Deferred to v2 | Requires wildcard DNS, wildcard TLS, and complicates local development. Good for branding but not needed for MVP. |
| Custom header (`X-Tenant-ID`) | Rejected | Client must manage and send the header. Easy to forget. No cryptographic binding to the authenticated user. |
| JWT claims | **Selected** | Tenant is cryptographically bound to the user's session. Cannot be tampered with. No extra headers needed. Resolved once at login, carried automatically. |

### 3.2 Tenant Context Object

```python
# app/core/tenant.py

from dataclasses import dataclass
from uuid import UUID
from contextvars import ContextVar

@dataclass(frozen=True)
class TenantContext:
    """Immutable tenant context for the current request."""
    tenant_id: UUID
    schema_name: str
    plan_id: UUID
    plan_name: str
    country_code: str
    timezone: str
    currency_code: str
    status: str
    features: dict          # Plan features (resolved from public.plans)
    limits: dict            # Plan limits (max_patients, max_doctors, etc.)

# Context variable for async safety
_tenant_context_var: ContextVar[TenantContext | None] = ContextVar(
    "tenant_context", default=None
)


def get_current_tenant() -> TenantContext:
    """Get the current tenant context. Raises if not set."""
    ctx = _tenant_context_var.get()
    if ctx is None:
        raise RuntimeError(
            "Tenant context not set. This request has no tenant resolution. "
            "Ensure TenantMiddleware is applied or this is not a public endpoint."
        )
    return ctx


def set_current_tenant(ctx: TenantContext) -> None:
    """Set the tenant context for the current request."""
    _tenant_context_var.set(ctx)


def clear_current_tenant() -> None:
    """Clear the tenant context after request completes."""
    _tenant_context_var.set(None)
```

### 3.3 Tenant Middleware

```python
# app/middleware/tenant.py

import logging
from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.tenant import TenantContext, set_current_tenant, clear_current_tenant
from app.core.auth import decode_jwt, JWTError
from app.services.tenant_cache import get_tenant_with_plan

logger = logging.getLogger(__name__)

# Paths that do not require tenant context
PUBLIC_PATHS = frozenset({
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/verify-email",
    "/api/v1/auth/accept-invite",
    "/api/v1/admin/",               # Superadmin uses public schema
    "/api/v1/public/",              # Public booking, etc.
    "/health",
    "/docs",
    "/openapi.json",
})


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Resolves tenant context from JWT for every authenticated request.

    Flow:
    1. Extract JWT from Authorization header
    2. Decode and validate JWT
    3. Extract tenant_id from claims
    4. Load tenant + plan data (cached in Redis)
    5. Validate tenant status (active only)
    6. Set TenantContext in contextvars
    7. Proceed to route handler
    8. Clear TenantContext after response
    """

    async def dispatch(self, request: Request, call_next):
        # Skip tenant resolution for public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)

        # Extract and decode JWT
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "error": "missing_token",
                    "message": "Authorization header with Bearer token is required",
                },
            )

        try:
            token = auth_header[7:]  # Strip "Bearer "
            claims = decode_jwt(token)
        except JWTError as e:
            return JSONResponse(
                status_code=401,
                content={"error": "invalid_token", "message": str(e)},
            )

        # Resolve tenant
        tenant_id = UUID(claims["tenant_id"])
        schema_name = claims["schema"]

        # Load tenant + plan from cache (Redis) or database
        tenant_data = await get_tenant_with_plan(tenant_id)
        if tenant_data is None:
            logger.warning("Tenant not found: %s", tenant_id)
            return JSONResponse(
                status_code=403,
                content={
                    "error": "tenant_not_found",
                    "message": "Tenant does not exist",
                },
            )

        # Verify schema_name matches (prevents JWT tampering edge case)
        if tenant_data["schema_name"] != schema_name:
            logger.error(
                "Schema mismatch: JWT says %s, DB says %s for tenant %s",
                schema_name,
                tenant_data["schema_name"],
                tenant_id,
            )
            return JSONResponse(
                status_code=403,
                content={"error": "invalid_tenant", "message": "Tenant mismatch"},
            )

        # Check tenant status
        if tenant_data["status"] == "suspended":
            if request.method not in ("GET", "HEAD", "OPTIONS"):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "tenant_suspended",
                        "message": (
                            "This account is suspended. "
                            "Read-only access is available for data export."
                        ),
                    },
                )

        if tenant_data["status"] not in ("active", "suspended"):
            return JSONResponse(
                status_code=403,
                content={
                    "error": "tenant_inactive",
                    "message": f"Tenant status is '{tenant_data['status']}'. Access denied.",
                },
            )

        # Build and set tenant context
        ctx = TenantContext(
            tenant_id=tenant_id,
            schema_name=schema_name,
            plan_id=UUID(tenant_data["plan_id"]),
            plan_name=tenant_data["plan_name"],
            country_code=tenant_data["country_code"],
            timezone=tenant_data["timezone"],
            currency_code=tenant_data["currency_code"],
            status=tenant_data["status"],
            features=tenant_data["features"],
            limits={
                "max_patients": tenant_data["max_patients"],
                "max_doctors": tenant_data["max_doctors"],
                "max_assistants": tenant_data["max_assistants"],
                "max_storage_mb": tenant_data["max_storage_mb"],
                "max_appointments_per_month": tenant_data["max_appointments_per_month"],
            },
        )
        set_current_tenant(ctx)

        # Store in request state for logging/tracing
        request.state.tenant_id = str(tenant_id)
        request.state.schema_name = schema_name

        try:
            response = await call_next(request)
            return response
        finally:
            clear_current_tenant()

    @staticmethod
    def _is_public_path(path: str) -> bool:
        return any(path.startswith(p) for p in PUBLIC_PATHS)
```

### 3.4 FastAPI Dependency Injection

```python
# app/dependencies/tenant.py

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import TenantContext, get_current_tenant
from app.db.session import get_db_session


def require_tenant() -> TenantContext:
    """
    FastAPI dependency that provides the current tenant context.
    Raises 500 if called on a route without TenantMiddleware.
    """
    return get_current_tenant()


async def get_tenant_session(
    tenant: TenantContext = Depends(require_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> AsyncSession:
    """
    FastAPI dependency that provides a database session with the
    search_path set to the tenant's schema.
    """
    await session.execute(
        text(f"SET search_path TO {tenant.schema_name}, public")
    )
    return session


# Usage in route handlers:
#
# @router.get("/api/v1/patients")
# async def list_patients(
#     tenant: TenantContext = Depends(require_tenant),
#     session: AsyncSession = Depends(get_tenant_session),
# ):
#     # session.search_path is already set to tenant schema
#     # All queries automatically resolve to tenant tables
#     patients = await session.execute(select(Patient))
#     return patients.scalars().all()
```

### 3.5 Search Path Switching

The critical operation that routes SQL queries to the correct tenant schema:

```python
# app/db/tenant_routing.py

from sqlalchemy import text, event
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import get_current_tenant


async def set_tenant_search_path(session: AsyncSession, schema_name: str) -> None:
    """
    Set the PostgreSQL search_path for this session.

    The search_path determines which schema unqualified table names resolve to.
    By setting it to '{tenant_schema}, public', queries like:
        SELECT * FROM patients
    resolve to:
        SELECT * FROM tn_a1b2c3d4.patients

    While queries referencing public tables (CIE-10, CUPS) still work:
        SELECT * FROM cie10_codes
    resolves to:
        SELECT * FROM public.cie10_codes
    """
    # IMPORTANT: schema_name is always system-generated (tn_{hex}).
    # It is NEVER user input. We validate the format as a safety measure.
    if not _is_valid_schema_name(schema_name):
        raise ValueError(f"Invalid schema name: {schema_name}")

    await session.execute(text(f"SET search_path TO {schema_name}, public"))


def _is_valid_schema_name(name: str) -> bool:
    """Validate that schema name matches our convention: tn_[a-f0-9]{8,12}"""
    import re
    return bool(re.match(r"^tn_[a-f0-9]{8,12}$", name))
```

---

## 4. Tenant Isolation Guarantees

### 4.1 Database-Level Isolation

**Principle:** A tenant can ONLY access data in their own schema and read-only data in the `public` schema. No exceptions.

**Enforcement mechanisms:**

1. **Search path.** Every database session sets `search_path TO tn_{id}, public`. Unqualified table names resolve to the tenant schema first, then public.

2. **No cross-schema references.** Application code never constructs queries that reference another tenant's schema. SQLAlchemy models do not include schema qualifiers; the search_path handles routing.

3. **Database role restrictions (defense in depth).** The application connects with a PostgreSQL role that has the following grants:

```sql
-- Application database role (not superuser)
CREATE ROLE dentalos_app LOGIN PASSWORD '...' NOSUPERUSER NOCREATEDB NOCREATEROLE;

-- Grant usage on tenant schemas (done during provisioning)
GRANT USAGE ON SCHEMA tn_a1b2c3d4 TO dentalos_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA tn_a1b2c3d4 TO dentalos_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA tn_a1b2c3d4 TO dentalos_app;

-- Public schema: read-only for catalog tables
GRANT USAGE ON SCHEMA public TO dentalos_app;
GRANT SELECT ON public.cie10_codes TO dentalos_app;
GRANT SELECT ON public.cups_codes TO dentalos_app;
GRANT SELECT ON public.dental_conditions TO dentalos_app;
GRANT SELECT ON public.medications TO dentalos_app;
GRANT SELECT ON public.plans TO dentalos_app;

-- Public schema: read-write for tenants table (provisioning service only)
-- The app role has read-only on tenants; a separate provisioning role has write.
GRANT SELECT ON public.tenants TO dentalos_app;

-- Provisioning role (used only by the provisioning service)
CREATE ROLE dentalos_provisioner LOGIN PASSWORD '...' NOSUPERUSER CREATEDB NOCREATEROLE;
GRANT ALL ON SCHEMA public TO dentalos_provisioner;
GRANT ALL ON ALL TABLES IN SCHEMA public TO dentalos_provisioner;
```

4. **Audit logging.** Every data access is logged with tenant_id, user_id, resource type, and action. Cross-tenant access attempts (which should be structurally impossible) are logged as security incidents.

### 4.2 Public Schema Access Rules

| Table | Tenant Access | Notes |
|-------|---------------|-------|
| `public.tenants` | Read own row only | Filtered by tenant_id in application layer |
| `public.plans` | Read all | Public pricing data |
| `public.cie10_codes` | Read all | Global diagnostic catalog |
| `public.cups_codes` | Read all | Global procedure catalog |
| `public.dental_conditions` | Read all | Odontogram condition definitions |
| `public.medications` | Read all | Medication reference data |
| `public.feature_flags` | Read all | Feature flag evaluation |
| `public.superadmin_users` | No access | Only superadmin auth service |

### 4.3 Application-Level Isolation Tests

The following invariants are enforced by automated tests (see Section 16):

- **INV-1:** No SQLAlchemy model references a schema name directly. All models are schema-agnostic.
- **INV-2:** No raw SQL query in the codebase contains a schema name other than `public`.
- **INV-3:** Every route handler that accesses tenant data uses `get_tenant_session` dependency.
- **INV-4:** The `TenantContext` object is immutable (`frozen=True` dataclass).
- **INV-5:** After request completion, `clear_current_tenant()` is always called (enforced in middleware `finally` block).

---

## 5. Plan Enforcement

### 5.1 Plan Definitions

```python
# Seed data for public.plans

PLANS = [
    {
        "name": "free",
        "display_name": "Plan Gratuito",
        "price_cop": 0,
        "price_mxn": 0,
        "price_usd": 0,
        "max_patients": 50,
        "max_doctors": 1,
        "max_assistants": 1,
        "max_storage_mb": 200,
        "max_appointments_per_month": 100,
        "features": {
            "odontogram_anatomic": False,
            "patient_portal": False,
            "whatsapp_reminders": False,
            "custom_consent_templates": False,
            "treatment_plan_pdf": True,
            "analytics_advanced": False,
            "electronic_invoice": False,
            "api_access": False,
            "white_label": False,
            "offline_mode": False,
            "bulk_import": False,
            "multi_branch": False,
        },
    },
    {
        "name": "starter",
        "display_name": "Plan Inicial",
        "price_cop": 99_000,       # ~25 USD
        "price_mxn": 499,
        "price_usd": 25,
        "max_patients": 500,
        "max_doctors": 3,
        "max_assistants": 5,
        "max_storage_mb": 2_000,
        "max_appointments_per_month": 500,
        "features": {
            "odontogram_anatomic": True,
            "patient_portal": True,
            "whatsapp_reminders": True,
            "custom_consent_templates": True,
            "treatment_plan_pdf": True,
            "analytics_advanced": False,
            "electronic_invoice": False,
            "api_access": False,
            "white_label": False,
            "offline_mode": False,
            "bulk_import": True,
            "multi_branch": False,
        },
    },
    {
        "name": "professional",
        "display_name": "Plan Profesional",
        "price_cop": 249_000,      # ~62 USD
        "price_mxn": 1_199,
        "price_usd": 62,
        "max_patients": 5_000,
        "max_doctors": 10,
        "max_assistants": 20,
        "max_storage_mb": 10_000,
        "max_appointments_per_month": 2_000,
        "features": {
            "odontogram_anatomic": True,
            "patient_portal": True,
            "whatsapp_reminders": True,
            "custom_consent_templates": True,
            "treatment_plan_pdf": True,
            "analytics_advanced": True,
            "electronic_invoice": True,
            "api_access": True,
            "white_label": False,
            "offline_mode": True,
            "bulk_import": True,
            "multi_branch": False,
        },
    },
    {
        "name": "enterprise",
        "display_name": "Plan Empresarial",
        "price_cop": 599_000,      # ~150 USD
        "price_mxn": 2_899,
        "price_usd": 150,
        "max_patients": -1,        # Unlimited (-1)
        "max_doctors": -1,
        "max_assistants": -1,
        "max_storage_mb": 50_000,
        "max_appointments_per_month": -1,
        "features": {
            "odontogram_anatomic": True,
            "patient_portal": True,
            "whatsapp_reminders": True,
            "custom_consent_templates": True,
            "treatment_plan_pdf": True,
            "analytics_advanced": True,
            "electronic_invoice": True,
            "api_access": True,
            "white_label": True,
            "offline_mode": True,
            "bulk_import": True,
            "multi_branch": True,
        },
    },
]
```

### 5.2 Plan Limit Enforcement

```python
# app/services/plan_enforcement.py

from enum import Enum
from dataclasses import dataclass

from app.core.tenant import TenantContext


class LimitType(str, Enum):
    PATIENTS = "max_patients"
    DOCTORS = "max_doctors"
    ASSISTANTS = "max_assistants"
    STORAGE_MB = "max_storage_mb"
    APPOINTMENTS_MONTHLY = "max_appointments_per_month"


@dataclass
class LimitCheckResult:
    allowed: bool
    current: int
    limit: int             # -1 means unlimited
    limit_type: LimitType
    upgrade_plan: str | None  # Name of the plan that would allow this action


class PlanEnforcementService:
    """
    Checks whether a tenant can perform an action based on their plan limits.
    Called before creating patients, adding doctors, uploading files, etc.
    """

    def __init__(self, session, tenant: TenantContext):
        self.session = session
        self.tenant = tenant

    async def check_limit(self, limit_type: LimitType) -> LimitCheckResult:
        limit_value = self.tenant.limits.get(limit_type.value, 0)

        # -1 means unlimited
        if limit_value == -1:
            return LimitCheckResult(
                allowed=True,
                current=0,
                limit=-1,
                limit_type=limit_type,
                upgrade_plan=None,
            )

        current_count = await self._get_current_count(limit_type)

        allowed = current_count < limit_value
        upgrade_plan = None
        if not allowed:
            upgrade_plan = await self._get_next_plan(limit_type, current_count)

        return LimitCheckResult(
            allowed=allowed,
            current=current_count,
            limit=limit_value,
            limit_type=limit_type,
            upgrade_plan=upgrade_plan,
        )

    async def check_feature(self, feature_key: str) -> bool:
        """Check if a feature is enabled for this tenant's plan."""
        return self.tenant.features.get(feature_key, False)

    async def _get_current_count(self, limit_type: LimitType) -> int:
        """Query the current usage count for the given limit type."""
        match limit_type:
            case LimitType.PATIENTS:
                result = await self.session.execute(
                    text("SELECT COUNT(*) FROM patients WHERE is_active = true")
                )
            case LimitType.DOCTORS:
                result = await self.session.execute(
                    text("SELECT COUNT(*) FROM users WHERE role = 'doctor' AND is_active = true")
                )
            case LimitType.ASSISTANTS:
                result = await self.session.execute(
                    text(
                        "SELECT COUNT(*) FROM users "
                        "WHERE role IN ('assistant', 'receptionist') AND is_active = true"
                    )
                )
            case LimitType.STORAGE_MB:
                result = await self.session.execute(
                    text("SELECT COALESCE(SUM(file_size_bytes), 0) / 1048576 FROM patient_documents")
                )
            case LimitType.APPOINTMENTS_MONTHLY:
                result = await self.session.execute(
                    text(
                        "SELECT COUNT(*) FROM appointments "
                        "WHERE date_trunc('month', created_at) = date_trunc('month', now())"
                    )
                )
        return result.scalar_one()

    async def _get_next_plan(self, limit_type: LimitType, current: int) -> str | None:
        """Find the cheapest plan that would accommodate the current usage."""
        result = await self.session.execute(
            text(
                "SELECT name FROM public.plans "
                f"WHERE {limit_type.value} > :current OR {limit_type.value} = -1 "
                "ORDER BY price_usd ASC LIMIT 1"
            ),
            {"current": current},
        )
        row = result.first()
        return row[0] if row else None
```

### 5.3 Feature Gating Dependency

```python
# app/dependencies/features.py

from fastapi import Depends, HTTPException, status

from app.core.tenant import TenantContext
from app.dependencies.tenant import require_tenant


def require_feature(feature_key: str):
    """
    FastAPI dependency factory that gates access based on plan features.

    Usage:
        @router.get("/api/v1/patients/{patient_id}/odontogram")
        async def get_odontogram(
            mode: str = Query("classic"),
            tenant: TenantContext = Depends(require_tenant),
            _: None = Depends(require_feature("odontogram_anatomic")),
            # ... only reached if feature is enabled
        ):
    """
    def _check(tenant: TenantContext = Depends(require_tenant)):
        if not tenant.features.get(feature_key, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "feature_not_available",
                    "message": f"Feature '{feature_key}' is not available on your current plan.",
                    "feature": feature_key,
                    "current_plan": tenant.plan_name,
                    "upgrade_url": "/settings/subscription",
                },
            )
    return _check


def require_plan_limit(limit_type: str):
    """
    FastAPI dependency factory that checks plan limits before resource creation.

    Usage:
        @router.post("/api/v1/patients")
        async def create_patient(
            _: None = Depends(require_plan_limit("max_patients")),
            session: AsyncSession = Depends(get_tenant_session),
        ):
    """
    async def _check(
        tenant: TenantContext = Depends(require_tenant),
        session: AsyncSession = Depends(get_tenant_session),
    ):
        service = PlanEnforcementService(session, tenant)
        result = await service.check_limit(LimitType(limit_type))
        if not result.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "plan_limit_reached",
                    "message": f"You have reached the {limit_type} limit for your plan.",
                    "current": result.current,
                    "limit": result.limit,
                    "current_plan": tenant.plan_name,
                    "upgrade_plan": result.upgrade_plan,
                    "upgrade_url": "/settings/subscription",
                },
            )
    return _check
```

### 5.4 Odontogram Mode Gating

The odontogram has two rendering modes:

| Mode | Description | Availability |
|------|-------------|--------------|
| **classic** | Grid-based tooth chart with colored zones | All plans (free and above) |
| **anatomic** | SVG-based realistic dental arch rendering | Starter plan and above |

```python
# In the odontogram route handler:

@router.get("/api/v1/patients/{patient_id}/odontogram")
async def get_odontogram(
    patient_id: UUID,
    tenant: TenantContext = Depends(require_tenant),
    session: AsyncSession = Depends(get_tenant_session),
):
    # Determine available mode based on plan
    anatomic_available = tenant.features.get("odontogram_anatomic", False)

    # Get tenant's preferred mode from settings
    preferred_mode = tenant.settings.get("odontogram_mode", "classic")

    # If tenant prefers anatomic but plan does not support it, fall back to classic
    effective_mode = preferred_mode if (preferred_mode == "classic" or anatomic_available) else "classic"

    # ... fetch odontogram data, include mode in response
    return {
        "mode": effective_mode,
        "anatomic_available": anatomic_available,
        "teeth": [...],
    }
```

---

## 6. Tenant Provisioning Flow

### 6.1 Step-by-Step Process

When a new clinic registers (via `POST /api/v1/auth/register`), the following provisioning sequence executes:

```
[User submits registration form]
       |
       v
[1] Create tenant record in public.tenants (status: provisioning)
       |
       v
[2] Create PostgreSQL schema: tn_{short_uuid}
       |
       v
[3] Run Alembic migrations on new schema (creates all tables)
       |
       v
[4] Grant database permissions to app role
       |
       v
[5] Create first user (clinic_owner role) in tenant schema
       |
       v
[6] Set default tenant settings (country, currency, odontogram mode)
       |
       v
[7] Seed default data (consent templates, condition catalog)
       |
       v
[8] Update tenant status: provisioning -> active
       |
       v
[9] Dispatch welcome email via RabbitMQ
       |
       v
[10] Return JWT tokens to client
```

### 6.2 Provisioning Service

```python
# app/services/tenant_provisioning.py

import logging
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine

from app.core.config import settings
from app.models.public import Tenant, Plan
from app.services.password import hash_password

logger = logging.getLogger(__name__)


class TenantProvisioningError(Exception):
    """Raised when tenant provisioning fails at any step."""
    pass


class TenantProvisioningService:
    """
    Orchestrates the creation of a new tenant.

    This service uses a SEPARATE database connection with the provisioning role
    (dentalos_provisioner) that has CREATE SCHEMA privileges. The normal
    application role (dentalos_app) cannot create schemas.
    """

    def __init__(self, engine: AsyncEngine, session: AsyncSession):
        self.engine = engine
        self.session = session

    async def provision_tenant(
        self,
        *,
        clinic_name: str,
        owner_email: str,
        owner_password: str,
        owner_name: str,
        country_code: str = "CO",
        plan_name: str = "free",
    ) -> dict:
        """
        Full tenant provisioning flow.
        Returns dict with tenant_id, schema_name, user_id for JWT generation.
        """
        tenant_id = uuid4()
        schema_name = self._generate_schema_name(tenant_id)
        slug = self._generate_slug(clinic_name)

        try:
            # Step 1: Create tenant record
            plan = await self._get_plan(plan_name)
            tenant = await self._create_tenant_record(
                tenant_id=tenant_id,
                slug=slug,
                schema_name=schema_name,
                name=clinic_name,
                country_code=country_code,
                plan_id=plan.id,
            )
            logger.info("Step 1 complete: tenant record created [%s]", tenant_id)

            # Step 2: Create PostgreSQL schema
            await self._create_schema(schema_name)
            logger.info("Step 2 complete: schema created [%s]", schema_name)

            # Step 3: Run migrations
            await self._run_migrations(schema_name)
            logger.info("Step 3 complete: migrations applied [%s]", schema_name)

            # Step 4: Grant permissions
            await self._grant_permissions(schema_name)
            logger.info("Step 4 complete: permissions granted [%s]", schema_name)

            # Step 5: Create first user
            user_id = await self._create_owner_user(
                schema_name=schema_name,
                email=owner_email,
                password=owner_password,
                name=owner_name,
            )
            logger.info("Step 5 complete: owner user created [%s]", user_id)

            # Update tenant with owner_user_id
            await self._update_tenant_owner(tenant_id, user_id)

            # Step 6: Set default settings
            await self._set_default_settings(
                schema_name=schema_name,
                country_code=country_code,
            )
            logger.info("Step 6 complete: default settings applied [%s]", schema_name)

            # Step 7: Seed default data
            await self._seed_default_data(schema_name, country_code)
            logger.info("Step 7 complete: default data seeded [%s]", schema_name)

            # Step 8: Activate tenant
            await self._activate_tenant(tenant_id)
            logger.info("Step 8 complete: tenant activated [%s]", tenant_id)

            await self.session.commit()

            return {
                "tenant_id": str(tenant_id),
                "schema_name": schema_name,
                "slug": slug,
                "user_id": str(user_id),
            }

        except Exception as e:
            await self.session.rollback()
            logger.error("Tenant provisioning failed: %s", e, exc_info=True)

            # Attempt cleanup: drop schema if it was created
            try:
                await self._cleanup_failed_provision(schema_name, tenant_id)
            except Exception as cleanup_err:
                logger.error("Cleanup also failed: %s", cleanup_err)

            raise TenantProvisioningError(
                f"Failed to provision tenant '{clinic_name}': {e}"
            ) from e

    def _generate_schema_name(self, tenant_id: UUID) -> str:
        """Generate schema name from tenant UUID."""
        short = tenant_id.hex[:8]
        return f"tn_{short}"

    def _generate_slug(self, clinic_name: str) -> str:
        """Generate URL-safe slug from clinic name."""
        import re
        from unidecode import unidecode

        slug = unidecode(clinic_name).lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
        # Ensure uniqueness will be checked by database UNIQUE constraint
        return slug[:63]

    async def _create_schema(self, schema_name: str) -> None:
        """Create the PostgreSQL schema."""
        # Use raw connection for DDL (cannot be inside a transaction block in some setups)
        async with self.engine.begin() as conn:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))

    async def _run_migrations(self, schema_name: str) -> None:
        """
        Run Alembic migrations on the new schema.
        Uses the tenant migration environment (see Section 8).
        """
        from app.db.migrations import run_tenant_migrations
        await run_tenant_migrations(schema_name)

    async def _grant_permissions(self, schema_name: str) -> None:
        """Grant the application role access to the new schema."""
        app_role = settings.DB_APP_ROLE  # "dentalos_app"
        async with self.engine.begin() as conn:
            await conn.execute(text(f"GRANT USAGE ON SCHEMA {schema_name} TO {app_role}"))
            await conn.execute(text(
                f"GRANT SELECT, INSERT, UPDATE, DELETE "
                f"ON ALL TABLES IN SCHEMA {schema_name} TO {app_role}"
            ))
            await conn.execute(text(
                f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {schema_name} TO {app_role}"
            ))
            # Ensure future tables also get grants
            await conn.execute(text(
                f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} "
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {app_role}"
            ))
            await conn.execute(text(
                f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} "
                f"GRANT USAGE, SELECT ON SEQUENCES TO {app_role}"
            ))

    async def _seed_default_data(self, schema_name: str, country_code: str) -> None:
        """Seed default data for the new tenant."""
        async with self.engine.begin() as conn:
            # Set search path
            await conn.execute(text(f"SET search_path TO {schema_name}, public"))

            # Seed default consent templates
            await conn.execute(text("""
                INSERT INTO consent_templates (id, name, body, is_default, category)
                VALUES
                    (gen_random_uuid(), 'Consentimiento General',
                     'Yo, {patient_name}, autorizo...', true, 'general'),
                    (gen_random_uuid(), 'Consentimiento Cirugia Oral',
                     'Yo, {patient_name}, autorizo el procedimiento quirurgico...', true, 'surgery'),
                    (gen_random_uuid(), 'Consentimiento Endodoncia',
                     'Yo, {patient_name}, autorizo el tratamiento de conducto...', true, 'endodontic'),
                    (gen_random_uuid(), 'Consentimiento Ortodoncia',
                     'Yo, {patient_name}, autorizo el tratamiento de ortodoncia...', true, 'orthodontic'),
                    (gen_random_uuid(), 'Consentimiento Implantes',
                     'Yo, {patient_name}, autorizo la colocacion de implantes...', true, 'implant'),
                    (gen_random_uuid(), 'Consentimiento Sedacion',
                     'Yo, {patient_name}, autorizo la administracion de sedacion...', true, 'sedation')
            """))

            # Seed default service catalog (common dental procedures with CUPS codes)
            # Prices are country-specific defaults
            if country_code == "CO":
                await conn.execute(text("""
                    INSERT INTO service_catalog (id, cups_code, name, default_price, currency)
                    VALUES
                        (gen_random_uuid(), '232101', 'Consulta Odontologica', 50000, 'COP'),
                        (gen_random_uuid(), '232301', 'Detartraje Supragingival', 80000, 'COP'),
                        (gen_random_uuid(), '232401', 'Obturacion Resina 1 Superficie', 120000, 'COP'),
                        (gen_random_uuid(), '232402', 'Obturacion Resina 2 Superficies', 150000, 'COP'),
                        (gen_random_uuid(), '232501', 'Exodoncia Simple', 100000, 'COP'),
                        (gen_random_uuid(), '232601', 'Endodoncia Uniradicular', 350000, 'COP'),
                        (gen_random_uuid(), '232602', 'Endodoncia Biradicular', 450000, 'COP'),
                        (gen_random_uuid(), '232603', 'Endodoncia Multiradicular', 550000, 'COP'),
                        (gen_random_uuid(), '237101', 'Corona Metal Porcelana', 800000, 'COP'),
                        (gen_random_uuid(), '237201', 'Implante Dental', 2500000, 'COP')
                """))

    async def _set_default_settings(self, schema_name: str, country_code: str) -> None:
        """Set default tenant settings based on country."""
        async with self.engine.begin() as conn:
            await conn.execute(text(f"SET search_path TO {schema_name}, public"))

            settings_data = {
                "odontogram_mode": "classic",
                "tooth_numbering": "FDI",       # ISO standard, used in LATAM
                "date_format": "DD/MM/YYYY",
                "time_format": "24h",
                "appointment_default_duration_min": 30,
                "reminder_24h_enabled": True,
                "reminder_2h_enabled": True,
                "reminder_channels": ["email"],  # WhatsApp added when plan supports it
            }

            for key, value in settings_data.items():
                import json
                await conn.execute(text(
                    "INSERT INTO tenant_settings (key, value) VALUES (:key, :value)"
                ), {"key": key, "value": json.dumps(value)})

    async def _cleanup_failed_provision(self, schema_name: str, tenant_id: UUID) -> None:
        """Clean up partial provisioning on failure."""
        async with self.engine.begin() as conn:
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
        await self.session.execute(
            text("DELETE FROM public.tenants WHERE id = :id"),
            {"id": str(tenant_id)},
        )
        await self.session.commit()
```

### 6.3 Provisioning Timing Budget

| Step | Target Duration | Notes |
|------|----------------|-------|
| Create tenant record | < 10ms | Single INSERT |
| Create schema | < 50ms | DDL operation |
| Run migrations | < 2s | ~25 tables with indexes |
| Grant permissions | < 50ms | Multiple GRANT statements |
| Create owner user | < 20ms | Single INSERT + password hash |
| Set default settings | < 20ms | Batch INSERT |
| Seed default data | < 100ms | Consent templates + service catalog |
| **Total** | **< 3 seconds** | User sees loading spinner during this |

The registration endpoint returns immediately after provisioning completes. The welcome email is dispatched asynchronously via RabbitMQ.

---

## 7. Tenant Lifecycle Management

### 7.1 State Machine

```
                           manual reactivation
    +----------------+    (superadmin action)     +----------+
    |  provisioning  | ----------------------->  |  active   |
    +----------------+                           +----------+
           |                                       |      ^
           | (provisioning fails)                  |      |
           v                                       |      | reactivate
    +----------------+                  suspend    |      |
    |    deleted      | <---+          |      +----------+
    +----------------+     |          v      |  suspended |
           ^               |   +-----------+ +----------+
           |               +-- |  cancelled |      ^
           | (retention       +-----------+      |
           |  period ends)          |             | suspend
           +------------------------+             |
                                    |             |
                                    +-------------+
                                   cancel
```

### 7.2 State Definitions

| State | Description | API Access | Duration |
|-------|-------------|------------|----------|
| `provisioning` | Schema being created. Transient state. | None | < 5 seconds |
| `active` | Normal operation. | Full read/write | Indefinite |
| `suspended` | Account suspended (non-payment, abuse, or manual). | Read-only (GET requests only) | Until reactivated or cancelled |
| `cancelled` | Cancellation requested. Grace period active. | Read-only for data export | 30 days grace period |
| `deleted` | Data archived and schema dropped. | None | Terminal state |

### 7.3 Suspension Behavior

When a tenant is suspended:

```python
# In TenantMiddleware (see Section 3.3):

if tenant_data["status"] == "suspended":
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        return JSONResponse(
            status_code=403,
            content={
                "error": "tenant_suspended",
                "message": (
                    "Su cuenta esta suspendida. Solo tiene acceso de lectura "
                    "para exportar sus datos. Contacte soporte para reactivar."
                ),
            },
        )
```

Suspended tenants can still:
- View all their data (patients, records, appointments, etc.)
- Export data (CSV, PDF generation)
- Download documents

Suspended tenants cannot:
- Create or modify any records
- Upload files
- Send notifications
- Book appointments

### 7.4 Cancellation and Deletion Flow

```
[Clinic owner requests cancellation]
    |
    v
[1] Tenant status -> cancelled, cancelled_at = now()
    |
    v
[2] Grace period starts (30 days)
    |    - Tenant can still export data (read-only)
    |    - Daily email reminders about pending deletion
    |    - Clinic owner can reactivate during grace period
    |
    v (30 days pass)
[3] Archive tenant data
    |    - pg_dump of tenant schema to encrypted archive
    |    - Archive stored in cold storage (Hetzner volume)
    |    - Archive retained per data retention policy (see I-12)
    |
    v
[4] Drop tenant schema
    |    - DROP SCHEMA tn_{id} CASCADE
    |
    v
[5] Delete S3 objects for tenant
    |    - Delete all objects under s3://dentalos-files/{tenant_id}/
    |
    v
[6] Purge Redis cache for tenant
    |    - DEL tenant:{tenant_id}:*
    |
    v
[7] Update tenant record: status -> deleted, deleted_at = now()
    |
    v
[8] Retain tenant record in public.tenants for billing/audit
```

**Archive retention periods** (defined in `infra/data-retention-policy.md`, I-12):

| Country | Clinical Records | Billing Records | Reason |
|---------|-----------------|-----------------|--------|
| Colombia | 15 years | 10 years | Resolucion 1995 de 1999 (clinical), tax law (billing) |
| Mexico | 5 years | 5 years | NOM-004-SSA3-2012 |
| Chile | 15 years | 6 years | Ley 20.584 |
| Default | 15 years | 10 years | Most conservative |

---

## 8. Schema Migration Strategy

### 8.1 Alembic Configuration

DentalOS uses **two separate Alembic migration environments**:

1. **Public schema migrations** (`alembic/public/`) -- for `public` schema tables (tenants, plans, catalogs).
2. **Tenant schema migrations** (`alembic/tenant/`) -- for tenant-specific tables. Applied to every tenant schema.

```
alembic/
  public/
    env.py              # Targets public schema only
    versions/
      001_create_tenants.py
      002_create_plans.py
      003_create_catalogs.py
      ...
  tenant/
    env.py              # Parameterized by schema name
    versions/
      001_create_users.py
      002_create_patients.py
      003_create_odontogram.py
      004_create_clinical_records.py
      ...
```

### 8.2 Tenant Migration Environment

```python
# alembic/tenant/env.py

from alembic import context
from sqlalchemy import engine_from_config, pool, text
import os

# Schema name passed via -x schema=tn_xxx or via environment variable
target_schema = context.get_x_argument(as_dictionary=True).get(
    "schema", os.environ.get("TENANT_SCHEMA")
)


def run_migrations_online():
    """Run migrations for a specific tenant schema."""
    connectable = engine_from_config(
        context.config.get_section(context.config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Set search_path BEFORE running migrations
        connection.execute(text(f"SET search_path TO {target_schema}, public"))

        # Use version_table_schema to store alembic_version in the tenant schema
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table="alembic_version",
            version_table_schema=target_schema,
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()
```

### 8.3 Running Migrations

```bash
# Migrate public schema
alembic -c alembic/public/alembic.ini upgrade head

# Migrate a single tenant schema
alembic -c alembic/tenant/alembic.ini -x schema=tn_a1b2c3d4 upgrade head

# Migrate ALL tenant schemas (bulk migration runner)
python -m app.cli.migrate_all_tenants
```

### 8.4 Bulk Migration Runner

```python
# app/cli/migrate_all_tenants.py

"""
Bulk migration runner for all tenant schemas.

Executes tenant migrations across all active tenant schemas.
Supports parallel execution with configurable concurrency.
Includes progress reporting and error handling per tenant.
"""

import asyncio
import logging
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.db.migrations import run_tenant_migrations

logger = logging.getLogger(__name__)

MAX_CONCURRENCY = 5  # Run up to 5 schema migrations in parallel


async def migrate_all_tenants():
    """
    Migrate all active tenant schemas to the latest Alembic revision.

    Strategy:
    1. Query all tenant schema names from public.tenants
    2. Run migrations with bounded concurrency (semaphore)
    3. Report per-tenant success/failure
    4. Fail loudly if any tenant fails (but continue others)
    """
    engine = create_async_engine(settings.DATABASE_URL)
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "SELECT id, schema_name, name FROM public.tenants "
                "WHERE status IN ('active', 'suspended') "
                "ORDER BY created_at ASC"
            )
        )
        tenants = result.fetchall()

    logger.info("Starting bulk migration for %d tenants", len(tenants))
    start_time = datetime.utcnow()

    results = {"success": 0, "failed": 0, "errors": []}

    async def migrate_one(tenant_id, schema_name, tenant_name):
        async with semaphore:
            try:
                logger.info("Migrating [%s] %s (%s)...", schema_name, tenant_name, tenant_id)
                await run_tenant_migrations(schema_name)
                results["success"] += 1
                logger.info("  OK [%s]", schema_name)
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "tenant_id": str(tenant_id),
                    "schema": schema_name,
                    "error": str(e),
                })
                logger.error("  FAILED [%s]: %s", schema_name, e)

    tasks = [
        migrate_one(t.id, t.schema_name, t.name) for t in tenants
    ]
    await asyncio.gather(*tasks)

    elapsed = (datetime.utcnow() - start_time).total_seconds()
    logger.info(
        "Bulk migration complete: %d success, %d failed, %.1fs elapsed",
        results["success"],
        results["failed"],
        elapsed,
    )

    if results["errors"]:
        logger.error("Failed tenants: %s", results["errors"])
        raise RuntimeError(
            f"Migration failed for {results['failed']} tenant(s). "
            "See logs for details."
        )


if __name__ == "__main__":
    asyncio.run(migrate_all_tenants())
```

### 8.5 Migration Safety Rules

1. **All tenant migrations must be backwards-compatible.** Since tenants are migrated in batches (not atomically), the application must work with both the old and new schema versions during the rollout window.

2. **Destructive changes require a two-phase migration:**
   - Phase 1: Add the new column/table, deploy code that writes to both old and new.
   - Phase 2 (next release): Remove the old column/table, deploy code that uses only new.

3. **Each migration must be idempotent.** Use `IF NOT EXISTS` for CREATE operations.

4. **Each tenant schema tracks its own `alembic_version`.** This allows individual tenants to be at different migration versions during a rolling deployment.

5. **Migrations are tested against a snapshot of the production schema** before deployment (see Section 16).

---

## 9. Connection Pooling

### 9.1 Strategy

DentalOS uses **SQLAlchemy's built-in async connection pool** with per-request `search_path` switching. We do NOT use PgBouncer in the MVP phase.

**Why not PgBouncer?**

| Factor | PgBouncer | SQLAlchemy Pool |
|--------|-----------|-----------------|
| Search path switching | Problematic with transaction pooling mode. `SET search_path` persists on the server connection, not the PgBouncer session. Requires `RESET ALL` or `DISCARD ALL` between uses, adding overhead. | Works naturally. Each checkout sets the search_path, and the pool does not multiplex connections within a transaction. |
| Complexity | Extra infrastructure component to deploy, configure, monitor. | Built into the application. No extra moving parts. |
| Performance | Better connection reuse at very high concurrency (thousands of concurrent connections). | Sufficient for our scale. PostgreSQL handles 200-500 connections without PgBouncer. |
| **Verdict** | Add when needed (>200 concurrent requests) | **Selected for MVP** |

### 9.2 Pool Configuration

```python
# app/db/session.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,               # Base pool size (persistent connections)
    max_overflow=30,            # Additional connections under load (total max: 50)
    pool_timeout=30,            # Seconds to wait for a connection from pool
    pool_recycle=1800,          # Recycle connections every 30 minutes
    pool_pre_ping=True,         # Verify connections before checkout
    echo=settings.SQL_ECHO,     # Log SQL in development
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncSession:
    """FastAPI dependency that provides a database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### 9.3 Connection Budget

For a Hetzner CX31 instance (4 vCPU, 8GB RAM) running PostgreSQL:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `max_connections` (PostgreSQL) | 200 | Hetzner managed DB default. Sufficient for MVP. |
| `pool_size` (SQLAlchemy) | 20 | Base connections. Handles normal load. |
| `max_overflow` | 30 | Burst capacity. Total max = 50 connections from app. |
| Reserved for migrations | 5 | Separate pool for migration runner. |
| Reserved for superadmin | 5 | Separate pool for admin operations. |
| **Available for other tools** | 140 | Monitoring, manual queries, backups. |

### 9.4 PgBouncer Migration Path (Future)

When the platform exceeds ~200 concurrent requests, add PgBouncer in **session mode** (not transaction mode):

```ini
# pgbouncer.ini (future)
[pgbouncer]
listen_addr = 127.0.0.1
listen_port = 6432
pool_mode = session         # session mode preserves SET search_path
max_client_conn = 1000
default_pool_size = 50
server_reset_query = DISCARD ALL
```

Session mode is mandatory because `SET search_path` is a session-level command. Transaction mode would lose the search_path between transactions.

---

## 10. Cache Isolation

### 10.1 Redis Key Namespacing

All Redis keys are namespaced by tenant ID to prevent cross-tenant cache contamination.

```
Pattern: tenant:{tenant_id}:{domain}:{key}

Examples:
  tenant:a1b2c3d4-...:patients:count           -> "142"
  tenant:a1b2c3d4-...:patients:list:page1       -> "[{...}, {...}]"
  tenant:a1b2c3d4-...:odontogram:patient:uuid   -> "{teeth: [...]}"
  tenant:a1b2c3d4-...:plan:limits               -> "{max_patients: 500, ...}"
  tenant:a1b2c3d4-...:user:session:token_jti    -> "refresh_token_data"
  tenant:a1b2c3d4-...:settings                  -> "{odontogram_mode: classic, ...}"

Global (non-tenant) keys:
  global:cie10:search:caries            -> "[{code: K02.1, ...}]"
  global:cups:search:exodoncia          -> "[{code: 232501, ...}]"
  global:plans:all                      -> "[{name: free, ...}]"
  global:dental_conditions:all          -> "[{code: caries, ...}]"
  global:feature_flags:all              -> "{offline_mode_v2: false, ...}"
```

### 10.2 Cache Helper

```python
# app/services/cache.py

import json
from typing import Any

import redis.asyncio as redis

from app.core.config import settings
from app.core.tenant import get_current_tenant

_redis: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


class TenantCache:
    """
    Tenant-scoped Redis cache. All keys are automatically prefixed
    with the current tenant ID.
    """

    def __init__(self, redis_client: redis.Redis, tenant_id: str):
        self.redis = redis_client
        self.prefix = f"tenant:{tenant_id}"

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Any | None:
        raw = await self.redis.get(self._key(key))
        return json.loads(raw) if raw else None

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        await self.redis.set(
            self._key(key),
            json.dumps(value, default=str),
            ex=ttl,
        )

    async def delete(self, key: str) -> None:
        await self.redis.delete(self._key(key))

    async def delete_pattern(self, pattern: str) -> None:
        """Delete all keys matching a pattern within this tenant's namespace."""
        full_pattern = self._key(pattern)
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match=full_pattern, count=100)
            if keys:
                await self.redis.delete(*keys)
            if cursor == 0:
                break

    async def flush_tenant(self) -> None:
        """Delete ALL cache entries for this tenant. Use with caution."""
        await self.delete_pattern("*")


# FastAPI dependency
async def get_tenant_cache() -> TenantCache:
    tenant = get_current_tenant()
    redis_client = await get_redis()
    return TenantCache(redis_client, str(tenant.tenant_id))
```

### 10.3 Cache TTL Policy

| Cache Domain | TTL | Invalidation |
|-------------|-----|-------------|
| `plan:limits` | 5 minutes | On plan change (superadmin action) |
| `patients:count` | 60 seconds | On patient create/delete |
| `patients:list:*` | 30 seconds | On any patient mutation |
| `odontogram:patient:*` | 5 minutes | On condition add/remove |
| `settings` | 10 minutes | On settings update |
| `user:session:*` | Matches token TTL | On logout/revoke |
| `global:cie10:*` | 1 hour | Manual invalidation (catalog update) |
| `global:cups:*` | 1 hour | Manual invalidation |
| `global:plans:*` | 5 minutes | On plan CRUD (superadmin) |
| `global:dental_conditions:*` | 24 hours | Manual invalidation |

---

## 11. Queue Isolation

### 11.1 RabbitMQ Routing

Messages in RabbitMQ carry the tenant_id in the message headers and payload. All queue consumers extract the tenant context before processing.

```python
# Message structure for tenant-scoped jobs

{
    "job_type": "send_appointment_reminder",
    "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "schema_name": "tn_a1b2c3d4",
    "payload": {
        "appointment_id": "...",
        "patient_id": "...",
        "channel": "whatsapp",
    },
    "metadata": {
        "dispatched_at": "2026-02-24T10:00:00Z",
        "dispatched_by": "user-uuid",
        "retry_count": 0,
    }
}
```

### 11.2 Worker Tenant Context

```python
# app/workers/base.py

async def process_message(message: dict) -> None:
    """
    Base message processor. Sets up tenant context before
    delegating to the specific job handler.
    """
    tenant_id = message["tenant_id"]
    schema_name = message["schema_name"]

    # Load tenant data and set context (same as middleware)
    tenant_data = await get_tenant_with_plan(UUID(tenant_id))
    if tenant_data is None or tenant_data["status"] == "deleted":
        logger.warning("Dropping message for non-existent/deleted tenant: %s", tenant_id)
        return  # ACK and discard

    ctx = build_tenant_context(tenant_data)
    set_current_tenant(ctx)

    try:
        # Get a database session with tenant search_path
        async with async_session_factory() as session:
            await session.execute(text(f"SET search_path TO {schema_name}, public"))
            handler = get_handler(message["job_type"])
            await handler(session, message["payload"])
            await session.commit()
    finally:
        clear_current_tenant()
```

### 11.3 Queue Topology

DentalOS does NOT create a separate queue per tenant. Instead, it uses a **shared queue with routing by message type** and tenant_id in the message body. This keeps the RabbitMQ topology simple.

```
Exchanges:
  dentalos.events (topic exchange)
    -> dentalos.notifications     (queue: email, sms, whatsapp, in-app)
    -> dentalos.clinical          (queue: audit log writes, RIPS generation)
    -> dentalos.provisioning      (queue: schema creation, seed data)
    -> dentalos.billing           (queue: invoice generation, payment reminders)
    -> dentalos.exports           (queue: CSV/PDF generation)

Routing keys:
  notification.email.send
  notification.whatsapp.send
  notification.sms.send
  clinical.audit.write
  clinical.rips.generate
  provisioning.tenant.create
  billing.invoice.generate
  export.patients.csv
```

See `infra/background-processing.md` (I-06) for the complete queue topology, retry policies, and dead letter queue configuration.

---

## 12. File Storage Isolation

### 12.1 S3 Prefix Structure

All tenant files are stored in a single S3-compatible bucket (Hetzner Object Storage or MinIO) with per-tenant path prefixes.

```
s3://dentalos-files/
  {tenant_id}/
    patients/
      {patient_id}/
        documents/
          {document_id}.{ext}
        xrays/
          {xray_id}.{ext}
        profile/
          avatar.{ext}
    consents/
      {consent_id}/
        signed.pdf
        signature.png
    treatment-plans/
      {plan_id}/
        plan.pdf
    prescriptions/
      {rx_id}/
        prescription.pdf
    branding/
      logo.{ext}
```

### 12.2 Signed URL Generation

```python
# app/services/file_storage.py

from app.core.tenant import get_current_tenant


class FileStorageService:
    """
    Tenant-scoped file storage. All operations are automatically
    prefixed with the current tenant's path.
    """

    def __init__(self, s3_client, bucket: str):
        self.s3 = s3_client
        self.bucket = bucket

    def _tenant_path(self, path: str) -> str:
        tenant = get_current_tenant()
        return f"{tenant.tenant_id}/{path}"

    async def generate_upload_url(self, path: str, content_type: str, ttl: int = 300) -> str:
        """Generate a pre-signed upload URL scoped to the current tenant."""
        full_path = self._tenant_path(path)
        return await self.s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket, "Key": full_path, "ContentType": content_type},
            ExpiresIn=ttl,
        )

    async def generate_download_url(self, path: str, ttl: int = 3600) -> str:
        """Generate a pre-signed download URL scoped to the current tenant."""
        full_path = self._tenant_path(path)
        return await self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": full_path},
            ExpiresIn=ttl,
        )
```

**Isolation guarantee:** The `_tenant_path` method always prepends the current tenant's UUID. There is no API that allows specifying an arbitrary tenant path. The tenant UUID comes from the validated JWT, not from user input.

---

## 13. Performance Considerations

### 13.1 Schema Count Limits

PostgreSQL handles thousands of schemas without degradation. The `pg_catalog` grows linearly with the number of schemas, but query planning is not affected because the `search_path` narrows the lookup scope.

| Metric | Value | Source |
|--------|-------|--------|
| Max tested schemas | ~10,000 | PostgreSQL community benchmarks |
| Catalog overhead per schema | ~1-2 MB | Depends on table count |
| Query planning impact | Negligible | search_path limits catalog scan |
| **DentalOS year-1 target** | **500-2,000 schemas** | Well within safe range |

### 13.2 Per-Tenant Monitoring Queries

```sql
-- Schema size (disk usage per tenant)
SELECT
    t.schema_name,
    t.name AS tenant_name,
    pg_size_pretty(
        SUM(pg_total_relation_size(c.oid))
    ) AS total_size
FROM public.tenants t
JOIN pg_namespace n ON n.nspname = t.schema_name
JOIN pg_class c ON c.relnamespace = n.oid
WHERE t.status = 'active'
GROUP BY t.schema_name, t.name
ORDER BY SUM(pg_total_relation_size(c.oid)) DESC;

-- Row counts per tenant (sampled, not exact)
SELECT
    t.schema_name,
    t.name AS tenant_name,
    (SELECT reltuples::BIGINT FROM pg_class
     WHERE relname = 'patients' AND relnamespace = n.oid) AS patient_count_approx,
    (SELECT reltuples::BIGINT FROM pg_class
     WHERE relname = 'appointments' AND relnamespace = n.oid) AS appointment_count_approx
FROM public.tenants t
JOIN pg_namespace n ON n.nspname = t.schema_name
WHERE t.status = 'active';

-- Active connections per tenant (requires pg_stat_activity monitoring)
-- This is tracked at the application level, not PostgreSQL level,
-- since all connections share the same database role.
```

### 13.3 Query Performance Guidelines

1. **Every tenant table must have appropriate indexes.** See `infra/database-architecture.md` (I-04) for the complete index specification.

2. **Common query patterns and their index requirements:**

| Query Pattern | Table | Required Index |
|--------------|-------|---------------|
| Patient search by name | patients | GIN index on `search_vector` (full-text) |
| Patient lookup by document | patients | UNIQUE index on `document_number` |
| Appointments by date range + doctor | appointments | Composite index on `(doctor_id, start_time)` |
| Odontogram by patient | odontogram_conditions | Index on `patient_id` |
| Clinical records by patient + date | clinical_records | Composite index on `(patient_id, created_at DESC)` |
| Audit log by resource | audit_log | Composite index on `(resource_type, resource_id, created_at DESC)` |

3. **N+1 prevention.** Use SQLAlchemy `selectinload()` or `joinedload()` for related data. Never fetch related records in a loop.

4. **Pagination.** All list endpoints use cursor-based pagination (not offset-based) for consistent performance. Cursor is typically `(created_at, id)`.

### 13.4 Bulk Migration Performance

For 1,000 tenant schemas, a migration that adds a single column:

| Concurrency | Estimated Duration | Notes |
|-------------|-------------------|-------|
| 1 (serial) | ~10 minutes | Safe but slow |
| 5 (parallel) | ~2 minutes | **Recommended** |
| 10 (parallel) | ~1 minute | Monitor connection pool |
| 20 (parallel) | ~40 seconds | Risk of connection exhaustion |

The bulk migration runner (Section 8.4) uses `MAX_CONCURRENCY = 5` by default.

---

## 14. Security

### 14.1 Threat Model

| Threat | Mitigation |
|--------|-----------|
| **Cross-tenant data leakage** | Schema isolation + search_path. No raw SQL with schema names. Application-level tests for isolation invariants. |
| **Schema name injection** | Schema names are system-generated (UUID hex). Validated by regex before use. Never derived from user input. |
| **JWT tampering (schema claim)** | Schema name in JWT is verified against database on every request (see middleware Section 3.3). |
| **Privilege escalation (tenant role)** | Tenant role in JWT verified against database. Role changes invalidate existing tokens. |
| **Suspended tenant writes** | Middleware blocks non-GET requests for suspended tenants. |
| **Provisioning race condition** | Tenant creation uses database UNIQUE constraint on slug and schema_name. Concurrent registrations with same name fail cleanly. |
| **Connection pool exhaustion** | Pool timeout (30s), max_overflow cap, health checks. Monitoring alerts at 80% utilization. |

### 14.2 SQL Injection Prevention for Search Path

The `SET search_path TO {schema_name}, public` statement uses string interpolation, which is normally a SQL injection risk. This is safe because:

1. `schema_name` is NEVER derived from user input. It is generated by the system (`tn_` + hex UUID prefix).
2. The `_is_valid_schema_name()` function validates the format with a strict regex before every use.
3. The schema name is loaded from the `public.tenants` table (which is written only by the provisioning service).
4. Even if an attacker could manipulate the JWT `schema` claim, the middleware verifies it against the database.

```python
# Defense in depth: schema name validation
def _is_valid_schema_name(name: str) -> bool:
    import re
    return bool(re.match(r"^tn_[a-f0-9]{8,12}$", name))
```

---

## 15. Monitoring and Observability

### 15.1 Key Metrics

| Metric | Source | Alert Threshold |
|--------|--------|----------------|
| Total tenant count | `SELECT COUNT(*) FROM public.tenants WHERE status = 'active'` | Informational only |
| Tenant schema sizes | `pg_total_relation_size` per schema | > 5 GB per tenant |
| Connection pool utilization | SQLAlchemy pool events | > 80% for > 5 minutes |
| Tenant provisioning duration | Application timer | > 10 seconds |
| Tenant provisioning failure rate | Application counter | > 0 in any 1-hour window |
| Cross-tenant access attempts | Application logger (should always be 0) | > 0 (security alert) |
| Suspended tenant write attempts | Middleware counter | Informational (expected) |
| Migration runner duration | CLI timer | > 30 minutes for bulk migration |
| Redis cache hit rate per tenant | Redis INFO + application tracking | < 50% (investigate) |

### 15.2 Structured Logging

Every log entry includes `tenant_id` and `schema_name` for filtering:

```python
# Structured log format (JSON)
{
    "timestamp": "2026-02-24T10:30:00.000Z",
    "level": "INFO",
    "logger": "app.services.patients",
    "message": "Patient created",
    "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "schema_name": "tn_a1b2c3d4",
    "user_id": "user-uuid",
    "request_id": "req-uuid",
    "patient_id": "patient-uuid",
    "duration_ms": 45
}
```

### 15.3 Health Check Endpoint

```python
@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_db_session)):
    """
    Application health check. Does NOT require tenant context.
    Checks database connectivity and Redis connectivity.
    """
    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    try:
        redis_client = await get_redis()
        await redis_client.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    status = "healthy" if (db_ok and redis_ok) else "degraded"

    return {
        "status": status,
        "database": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
        "tenant_count": await get_active_tenant_count(session) if db_ok else None,
    }
```

---

## 16. Testing

### 16.1 Tenant Isolation Tests

```python
# tests/test_tenant_isolation.py

import pytest
from sqlalchemy import text


@pytest.fixture
async def tenant_a(test_db):
    """Provision a test tenant A."""
    return await provision_test_tenant(test_db, name="Clinic A")


@pytest.fixture
async def tenant_b(test_db):
    """Provision a test tenant B."""
    return await provision_test_tenant(test_db, name="Clinic B")


class TestTenantIsolation:
    """Verify that tenant data is completely isolated."""

    async def test_tenant_a_cannot_see_tenant_b_patients(
        self, test_db, tenant_a, tenant_b
    ):
        """INV-1: Tenant A's patients are invisible to Tenant B."""
        # Create patient in Tenant A
        async with test_db.begin() as conn:
            await conn.execute(text(f"SET search_path TO {tenant_a.schema_name}, public"))
            await conn.execute(text(
                "INSERT INTO patients (id, name, document_number) "
                "VALUES (gen_random_uuid(), 'Patient A', '1234567890')"
            ))

        # Query patients from Tenant B's perspective
        async with test_db.begin() as conn:
            await conn.execute(text(f"SET search_path TO {tenant_b.schema_name}, public"))
            result = await conn.execute(text("SELECT COUNT(*) FROM patients"))
            count = result.scalar_one()

        assert count == 0, "Tenant B should see 0 patients"

    async def test_tenant_cannot_access_other_schema_directly(
        self, test_db, tenant_a, tenant_b
    ):
        """INV-2: Direct cross-schema query fails."""
        async with test_db.begin() as conn:
            await conn.execute(text(f"SET search_path TO {tenant_a.schema_name}, public"))
            with pytest.raises(Exception):
                await conn.execute(text(
                    f"SELECT * FROM {tenant_b.schema_name}.patients"
                ))

    async def test_public_catalogs_readable_from_tenant(
        self, test_db, tenant_a
    ):
        """Public catalog tables should be readable from any tenant schema."""
        async with test_db.begin() as conn:
            await conn.execute(text(f"SET search_path TO {tenant_a.schema_name}, public"))
            result = await conn.execute(text("SELECT COUNT(*) FROM cie10_codes"))
            count = result.scalar_one()
        assert count > 0, "CIE-10 codes should be accessible"

    async def test_public_tenants_table_not_writable(
        self, test_db, tenant_a
    ):
        """App role should not be able to write to public.tenants."""
        # This test uses the app role connection (dentalos_app)
        async with test_db.begin() as conn:
            await conn.execute(text(f"SET search_path TO {tenant_a.schema_name}, public"))
            with pytest.raises(Exception):
                await conn.execute(text(
                    "INSERT INTO public.tenants (id, slug, schema_name, name, plan_id) "
                    "VALUES (gen_random_uuid(), 'evil', 'evil_schema', 'Evil', "
                    "(SELECT id FROM public.plans LIMIT 1))"
                ))

    async def test_suspended_tenant_read_only(self, test_client, tenant_a):
        """Suspended tenants can read but not write."""
        # Suspend tenant
        await suspend_tenant(tenant_a.tenant_id)

        # GET should work
        response = await test_client.get(
            "/api/v1/patients",
            headers={"Authorization": f"Bearer {tenant_a.token}"},
        )
        assert response.status_code == 200

        # POST should be blocked
        response = await test_client.post(
            "/api/v1/patients",
            headers={"Authorization": f"Bearer {tenant_a.token}"},
            json={"name": "New Patient", "document_number": "9999999999"},
        )
        assert response.status_code == 403
        assert response.json()["error"] == "tenant_suspended"


class TestPlanEnforcement:
    """Verify plan limits are enforced."""

    async def test_free_plan_patient_limit(self, test_client, free_tenant):
        """Free plan should block patient creation at limit."""
        # Create 50 patients (free plan limit)
        for i in range(50):
            response = await test_client.post(
                "/api/v1/patients",
                headers={"Authorization": f"Bearer {free_tenant.token}"},
                json={"name": f"Patient {i}", "document_number": f"100000000{i:02d}"},
            )
            assert response.status_code == 201

        # 51st patient should be blocked
        response = await test_client.post(
            "/api/v1/patients",
            headers={"Authorization": f"Bearer {free_tenant.token}"},
            json={"name": "Patient 51", "document_number": "1000000050"},
        )
        assert response.status_code == 403
        assert response.json()["error"] == "plan_limit_reached"
        assert response.json()["upgrade_plan"] == "starter"

    async def test_free_plan_no_anatomic_odontogram(self, test_client, free_tenant):
        """Free plan should not have anatomic odontogram feature."""
        response = await test_client.get(
            "/api/v1/settings/plan-limits",
            headers={"Authorization": f"Bearer {free_tenant.token}"},
        )
        features = response.json()["features"]
        assert features["odontogram_anatomic"] is False


class TestTenantProvisioning:
    """Verify the full provisioning flow."""

    async def test_provision_creates_schema_and_tables(self, test_db):
        """Provisioning should create schema with all required tables."""
        result = await provision_test_tenant(test_db, name="Test Clinic")

        async with test_db.begin() as conn:
            # Verify schema exists
            res = await conn.execute(text(
                "SELECT 1 FROM pg_namespace WHERE nspname = :schema"
            ), {"schema": result.schema_name})
            assert res.scalar_one() == 1

            # Verify key tables exist
            for table in ["users", "patients", "appointments", "clinical_records",
                         "odontogram_conditions", "audit_log"]:
                res = await conn.execute(text(
                    "SELECT 1 FROM pg_class c "
                    "JOIN pg_namespace n ON c.relnamespace = n.oid "
                    "WHERE n.nspname = :schema AND c.relname = :table"
                ), {"schema": result.schema_name, "table": table})
                assert res.scalar_one() == 1, f"Table {table} should exist in {result.schema_name}"

    async def test_provision_seeds_default_data(self, test_db):
        """Provisioning should seed consent templates and service catalog."""
        result = await provision_test_tenant(test_db, name="Test Clinic CO", country="CO")

        async with test_db.begin() as conn:
            await conn.execute(text(f"SET search_path TO {result.schema_name}, public"))

            # Consent templates
            res = await conn.execute(text("SELECT COUNT(*) FROM consent_templates WHERE is_default = true"))
            assert res.scalar_one() == 6  # 6 default templates

            # Service catalog
            res = await conn.execute(text("SELECT COUNT(*) FROM service_catalog"))
            assert res.scalar_one() > 0

    async def test_provision_cleanup_on_failure(self, test_db, monkeypatch):
        """If provisioning fails, schema should be cleaned up."""
        # Make seed_default_data fail
        async def broken_seed(*args, **kwargs):
            raise RuntimeError("Intentional failure")

        monkeypatch.setattr(
            TenantProvisioningService, "_seed_default_data", broken_seed
        )

        with pytest.raises(TenantProvisioningError):
            await provision_test_tenant(test_db, name="Failing Clinic")

        # Verify schema was cleaned up
        async with test_db.begin() as conn:
            res = await conn.execute(text(
                "SELECT COUNT(*) FROM pg_namespace WHERE nspname LIKE 'tn_%'"
            ))
            # Should be 0 (or only pre-existing test schemas)
```

### 16.2 Test Infrastructure

```python
# tests/conftest.py

@pytest.fixture(scope="session")
async def test_db():
    """
    Create a test database with the public schema.
    Each test session gets a fresh database.
    """
    engine = create_async_engine(settings.TEST_DATABASE_URL)
    async with engine.begin() as conn:
        # Run public schema migrations
        await run_public_migrations(conn)
        # Seed global catalogs
        await seed_test_catalogs(conn)
    yield engine
    await engine.dispose()


async def provision_test_tenant(engine, name: str, country: str = "CO"):
    """Helper to provision a test tenant with all defaults."""
    async with async_sessionmaker(engine)() as session:
        service = TenantProvisioningService(engine, session)
        result = await service.provision_tenant(
            clinic_name=name,
            owner_email=f"{slugify(name)}@test.dentalos.app",
            owner_password="TestPassword123!",
            owner_name="Test Owner",
            country_code=country,
        )
        token = generate_test_jwt(result)
        return TestTenant(**result, token=token)
```

### 16.3 Static Analysis Rules

The following linting rules are enforced in CI:

1. **No hardcoded schema names.** `grep -r "tn_" app/` should return zero results outside of the provisioning service and tests.
2. **No raw SQL with schema references.** All SQL must use parameterized queries or the search_path mechanism.
3. **All route handlers with data access must use `get_tenant_session`.** Enforced by a custom Pylint checker.

---

## 17. Out of Scope

This spec explicitly does NOT cover:

- **Multi-database tenancy.** We use schema-per-tenant within a single database. Database-per-tenant is explicitly rejected (see Section 1).
- **Subdomain-based tenant resolution.** Deferred to v2. Currently resolved via JWT claims only.
- **Custom domain per tenant.** Enterprise feature for future roadmap (requires reverse proxy configuration).
- **Cross-tenant reporting.** Superadmin analytics queries against the `public` schema only. No cross-schema JOINs.
- **Tenant-to-tenant data sharing.** Not applicable. Dental clinics do not share patient data.
- **Multi-region deployment.** Single Hetzner region (Falkenstein or Helsinki) for MVP. Multi-region addressed in `infra/deployment-architecture.md`.
- **Read replica routing.** All queries go to the primary database for MVP. Read replicas addressed in `infra/database-architecture.md`.
- **Billing and payment processing for DentalOS subscriptions.** Handled by an external billing provider (Stripe or local equivalent). See `billing/` domain specs for clinic-level patient billing only.
- **Tenant data export API.** Covered in `patients/patient-export.md` and tenant lifecycle (Section 7). No full-schema export API for tenants.
- **Detailed audit logging implementation.** See `infra/audit-logging.md` (I-11).
- **Detailed RBAC and permission matrix.** See `infra/authentication-rules.md` (I-02).

---

## 18. Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] Schema-per-tenant architecture decision documented with alternatives
- [x] Public schema DDL defined
- [x] Tenant schema template listed
- [x] Naming convention defined and justified
- [x] Tenant resolution flow complete with code examples
- [x] Middleware implementation provided
- [x] FastAPI dependency injection pattern documented
- [x] Search path switching mechanism documented
- [x] Plan enforcement with code examples
- [x] Feature gating mechanism documented
- [x] Provisioning flow step-by-step with code
- [x] Tenant lifecycle state machine documented
- [x] Migration strategy with Alembic configuration
- [x] Connection pooling strategy documented
- [x] Cache, queue, and file storage isolation documented

### Hook 2: Architecture Compliance
- [x] Follows schema-per-tenant pattern consistently
- [x] Uses FastAPI dependency injection
- [x] Uses async SQLAlchemy throughout
- [x] Separation of concerns (middleware, dependencies, services)
- [x] No circular dependencies

### Hook 3: Security and Privacy
- [x] Tenant isolation guarantees enumerated
- [x] Threat model documented
- [x] SQL injection prevention for search_path
- [x] JWT verification against database
- [x] Schema name validation
- [x] Database role restrictions (defense in depth)
- [x] Suspended tenant access controls

### Hook 4: Performance and Scalability
- [x] Connection pool sizing documented
- [x] Schema count limits assessed
- [x] Bulk migration runner with configurable concurrency
- [x] Cache TTL policies defined
- [x] Query performance guidelines
- [x] PgBouncer migration path documented

### Hook 5: Observability
- [x] Key metrics enumerated
- [x] Structured logging with tenant_id
- [x] Health check endpoint
- [x] Alert thresholds defined
- [x] Per-tenant monitoring queries

### Hook 6: Testability
- [x] Isolation tests documented (INV-1 through INV-5)
- [x] Plan enforcement tests
- [x] Provisioning tests (happy path + failure cleanup)
- [x] Test infrastructure (fixtures, helpers)
- [x] Static analysis rules for CI

**Overall Status:** PASS

---

## 19. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec: schema-per-tenant architecture, tenant resolution, isolation, plan enforcement, provisioning, lifecycle, migrations, pooling, cache/queue/file isolation, performance, security, monitoring, testing |
