# ADR-001: Schema-per-tenant vs Row-level isolation

**Status:** Accepted
**Date:** 2026-02-24
**Authors:** DentalOS Architecture Team

---

## Context

DentalOS is a multi-tenant SaaS platform serving dental clinics across Latin America.
Each clinic's data contains Protected Health Information (PHI), including patient
demographics, clinical records, odontograms, treatment plans, radiographic images
metadata, and prescription histories. Regulatory frameworks in our target markets --
Colombia's Resolucion de Datos Abiertos (RDA) and Ley 1581 de 2012 (Habeas Data),
Mexico's NOM-024-SSA3-2012 and Ley Federal de Proteccion de Datos Personales -- mandate
strict controls over the storage, access, and portability of health data.

The application stack consists of Python 3.12, FastAPI, SQLAlchemy 2.0 (async),
Alembic for migrations, and PostgreSQL 16+ as the primary database. Connection
pooling is handled by pgbouncer.

We need to select a multi-tenancy isolation strategy that satisfies the following
requirements:

1. **Data isolation**: A bug in application code must not leak one clinic's patient
   data to another clinic. Cross-tenant data exposure in a healthcare context is
   both a regulatory violation and a trust-destroying event.
2. **Compliance portability**: Regulators or clinic owners may request a full data
   export of a single clinic's records. The export must be complete and verifiable.
3. **Performance**: Each clinic generates 50-200 patient records per month, with
   peak concurrent users of 5-15 per clinic. Target scale is 500-2,000 clinics
   in year one.
4. **Migration simplicity**: Schema changes must propagate to all tenants reliably.
   A failed migration on one tenant must not block others.
5. **Operational simplicity**: The team is small (2-4 engineers). The strategy
   must not require a dedicated DBA for day-to-day operations.

### Scale Analysis

At 500 clinics (year-one low estimate), the system manages 500 PostgreSQL schemas.
At 2,000 clinics (year-one high estimate), the system manages 2,000 schemas.
PostgreSQL handles thousands of schemas without degradation -- the catalog queries
for schema resolution are O(1) hash lookups. The bottleneck is connection count:
each schema switch requires a `SET search_path` statement, which pgbouncer handles
efficiently in transaction-mode pooling.

Estimated data volume per tenant per year: ~10,000-50,000 rows across all tables
(patients, appointments, clinical records, odontogram entries, treatments). At 2,000
tenants, total row count is 20M-100M rows -- well within single-instance PostgreSQL
capacity.

## Decision

We will use **schema-per-tenant** isolation for DentalOS. Each tenant receives a
dedicated PostgreSQL schema with the naming convention `tn_<tenant_short_id>` (e.g.,
`tn_a1b2c3d4e5f6`). The `tn_` prefix prevents collisions with PostgreSQL system
schemas and provides a clear namespace.

### Schema Structure

- **`public` schema (shared):** Contains cross-tenant reference data:
  - `tenants` -- tenant registry (id, name, slug, plan, country, schema_name, status)
  - `plans` -- subscription plan definitions
  - `catalog_cie10` -- International Classification of Diseases, 10th revision
  - `catalog_cups` -- Colombian Unified Procedure Coding System
  - `catalog_medications` -- standardized medication catalog
  - `catalog_tooth_conditions` -- odontogram condition master list
  - `users` -- all users across tenants (with `tenant_id` FK), enabling cross-tenant
    auth operations (login, password reset) without schema switching

- **`tn_<id>` schemas (per-tenant):** Contains tenant-specific clinical data:
  - `patients`, `patient_contacts`, `patient_insurance`
  - `clinical_records`, `clinical_record_entries`
  - `odontograms`, `odontogram_findings`
  - `treatment_plans`, `treatment_plan_items`
  - `appointments`, `appointment_slots`
  - `invoices`, `invoice_items`, `payments`
  - `consents`, `consent_signatures`
  - `prescriptions`, `prescription_items`
  - `audit_log` -- per-tenant audit trail

### Connection Management

We will use pgbouncer in **transaction-mode pooling**. On each request:

1. FastAPI middleware resolves the tenant from the JWT token or subdomain.
2. A dependency-injected `TenantContext` object carries the `schema_name`.
3. The SQLAlchemy session executes `SET search_path TO tn_<id>, public` at the
   start of each transaction.
4. At transaction commit/rollback, pgbouncer returns the connection to the pool
   with the search_path reset.

This approach allows a pool of 50-100 connections to serve 2,000 tenants, because
each connection is bound to a tenant only for the duration of a single transaction.

### Alembic Multi-Tenant Migration Strategy

Alembic migrations run in two modes:

1. **Shared migrations:** Applied to the `public` schema. Standard Alembic with
   `target_metadata` pointing to shared models.
2. **Tenant migrations:** Applied iteratively to each `tn_<id>` schema. A custom
   Alembic `env.py` loops over all active tenant schemas from the `tenants` table:

```python
def run_tenant_migrations():
    tenants = get_all_active_tenants()
    for tenant in tenants:
        with engine.connect() as conn:
            conn.execute(text(f"SET search_path TO {tenant.schema_name}, public"))
            context.configure(connection=conn, target_metadata=tenant_metadata)
            context.run_migrations()
```

Each tenant schema maintains its own `alembic_version` table, allowing independent
migration tracking. If a migration fails on tenant #347, tenants #1-346 are already
migrated and functional, and tenant #348+ can proceed after the issue is resolved.

## Alternatives Considered

### Alternative 1: Row-level isolation (tenant_id column + RLS)

All tenants share the same tables. Every table has a `tenant_id` column, and
PostgreSQL Row-Level Security (RLS) policies enforce isolation:

```sql
CREATE POLICY tenant_isolation ON patients
    USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

**Why not chosen:**

- **Accidental exposure risk**: A single missing `WHERE tenant_id = ...` clause or
  a misconfigured RLS policy exposes PHI across tenants. In healthcare, this risk
  is unacceptable. Schema isolation provides defense-in-depth: even if application
  code has a bug, the database schema boundary prevents cross-tenant access.
- **Query complexity**: Every query, index, and migration must account for
  `tenant_id`. Composite indexes (`tenant_id, patient_id`) increase index size
  and complicate query planning.
- **Compliance exports**: Extracting a single tenant's data requires filtering
  every table by `tenant_id`. With schema-per-tenant, `pg_dump -n tn_abc123`
  produces a complete, verifiable export in one command.
- **RLS performance**: At scale, RLS policies add overhead to every query plan.
  Benchmarks show 5-15% overhead for complex joins with RLS active.

**Trade-offs if chosen:** Simpler initial setup, no schema management overhead,
easier cross-tenant analytics. Appropriate for non-healthcare SaaS where data
isolation is a convenience rather than a regulatory requirement.

### Alternative 2: Database-per-tenant

Each tenant gets a completely separate PostgreSQL database instance.

**Why not chosen:**

- **Connection overhead**: Each database requires its own connection pool.
  At 2,000 tenants, this means 2,000 separate connection pools or a complex
  multi-database pgbouncer configuration.
- **Cost**: Managed PostgreSQL pricing is per-instance. At 2,000 tenants,
  the cost is prohibitive on any cloud provider.
- **Migration complexity**: Alembic must connect to 2,000 separate databases
  to run migrations, dramatically increasing deployment time and failure surface.
- **Cross-tenant queries impossible**: Shared catalog lookups (CIE-10, CUPS)
  would require either data duplication or federation.

**Trade-offs if chosen:** Maximum isolation, simplest per-tenant backup/restore,
independent scaling per tenant. Appropriate for enterprise deployments where each
tenant pays enough to justify dedicated infrastructure.

## Consequences

### Positive

- **Defense-in-depth isolation**: Even if application code has a bug that omits
  tenant filtering, the PostgreSQL schema boundary prevents data leakage. This is
  the strongest isolation guarantee short of database-per-tenant.
- **Simple compliance exports**: `pg_dump --schema=tn_abc123` produces a complete,
  self-contained backup of any tenant's data. This directly satisfies LATAM data
  portability requirements (Colombia Ley 1581, Article 17 -- right of data access).
- **Independent tenant lifecycle**: Tenant provisioning creates a schema; tenant
  deletion drops a schema. No risk of orphaned rows in shared tables.
- **Clean Alembic workflow**: Each tenant schema has its own `alembic_version`,
  enabling independent migration tracking and rollback per tenant.
- **Query simplicity**: Application code does not need `tenant_id` filters on
  every query. The `search_path` ensures all queries implicitly target the
  correct tenant's tables.
- **Index efficiency**: Indexes are per-tenant and smaller, leading to faster
  index scans and lower memory pressure on the buffer pool.

### Negative

- **Schema proliferation**: At 2,000 tenants, PostgreSQL's `pg_catalog` contains
  2,000 schema entries and 2,000 x N table entries. While PostgreSQL handles this
  well, `\dt *.*` in psql becomes unwieldy. Monitoring and tooling must be schema-aware.
- **Migration time**: Running Alembic across 2,000 schemas is sequential in the
  basic implementation. At 50ms per schema, a migration takes ~100 seconds. We will
  implement parallel migration execution (batches of 50 schemas) when tenant count
  exceeds 500.
- **Connection pool complexity**: pgbouncer must be configured in transaction mode,
  and `SET search_path` adds a round-trip per transaction. Measured overhead: <1ms.
- **Cross-tenant analytics**: Reporting across all tenants (e.g., platform-wide
  appointment volume) requires querying each schema individually or maintaining a
  separate analytics pipeline. We plan to use a read replica with a materialized
  view aggregation job for platform analytics.
- **Provisioning latency**: Creating a new tenant schema with all tables takes
  2-5 seconds. This is acceptable for a sign-up flow but requires async handling.

### Neutral

- **No impact on API design**: The tenant resolution happens at the middleware/
  dependency injection level. API endpoints are tenant-agnostic in their code.
- **Backup strategy**: Full database backups (pg_basebackup) capture all schemas.
  Per-tenant backups (pg_dump --schema) are an additional capability, not a
  replacement for full backups.
- **Monitoring granularity**: Per-schema metrics (table sizes, row counts, slow
  queries) provide natural tenant-level observability without additional tagging.

## References

- [`infra/multi-tenancy.md`](../multi-tenancy.md) -- Full multi-tenancy implementation specification
- [`infra/database-architecture.md`](../database-architecture.md) -- Database schema design and conventions
- [`infra/authentication-rules.md`](../authentication-rules.md) -- Tenant resolution from JWT tokens
- [ADR-002: FastAPI over Django](002-fastapi-over-django.md) -- Framework choice enabling DI-based tenant context
- [ADR-003: PostgreSQL over alternatives](003-postgresql-over-alternatives.md) -- Database choice enabling native schemas
- [ADR-004: Hetzner over AWS/GCP](004-hetzner-over-aws.md) -- Infrastructure choice affecting managed PostgreSQL availability
- [PostgreSQL Schemas Documentation](https://www.postgresql.org/docs/16/ddl-schemas.html)
- [pgbouncer Transaction Mode](https://www.pgbouncer.org/config.html#pool-mode)
- [Alembic Multi-Schema Migrations](https://alembic.sqlalchemy.org/en/latest/cookbook.html)
- Colombia Ley 1581 de 2012 -- Habeas Data (personal data protection)
- Colombia Resolucion 1995 de 1999 -- Clinical records management
- Mexico NOM-024-SSA3-2012 -- Health information systems
- Mexico Ley Federal de Proteccion de Datos Personales en Posesion de Particulares
