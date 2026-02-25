# ADR-003: PostgreSQL over alternatives

**Status:** Accepted
**Date:** 2026-02-24
**Authors:** DentalOS Architecture Team

---

## Context

DentalOS requires a primary database to store and manage dental clinic data. The
data model is fundamentally relational: patients have clinical records, which contain
diagnoses (CIE-10 codes), treatments (CUPS codes), and tooth-level findings. An
odontogram links teeth to surfaces to conditions to treatments in a graph of foreign
key relationships. Appointments reference patients, providers, and treatment plans.
Billing references appointments, treatments, and insurance policies.

### Data Characteristics

- **Highly relational**: The core domain has 30+ tables with complex foreign key
  relationships. A single patient view joins patients, clinical_records,
  odontogram_findings, treatment_plans, appointments, and consents.
- **Multi-tenant**: Per [ADR-001](001-schema-per-tenant.md), we use schema-per-tenant
  isolation. The database must natively support schemas as first-class objects.
- **Full-text search in Spanish**: Clinicians search for patients by name, ID number,
  and clinical notes. CIE-10 diagnosis descriptions and CUPS procedure codes must
  be searchable in Spanish. Searching "caries" must match "caries dental", "caries
  de dentina", and "caries de cemento" across 14,000+ CIE-10 codes.
- **Semi-structured data**: Anamnesis (medical history) forms vary by country and
  clinic. Odontogram condition metadata (color, pattern, surface coverage) is
  semi-structured. Colombia requires specific cardiovascular history questions;
  Mexico requires NOM-024 compliant fields.
- **Audit trail**: Every clinical data modification must be logged with previous
  value, new value, user, timestamp, and tenant context -- a regulatory requirement.
- **Data volume**: Per-tenant: 10,000-50,000 rows/year. Aggregate across 2,000
  tenants: 20M-100M rows. Read-heavy (80/20) with write spikes during morning hours.

### Operational Requirements

- Backup granularity: full-database and per-tenant backup (compliance/offboarding).
- Hosting: Hetzner Cloud offers managed PostgreSQL (per [ADR-004](004-hetzner-over-aws.md)).
- Connection pooling via pgbouncer for multi-tenant connection management.
- WAL archiving for point-in-time recovery (healthcare compliance expectation).

## Decision

We will use **PostgreSQL 16+** as the sole primary database for DentalOS, leveraging
the following PostgreSQL-specific features:

### 1. Native Schemas for Tenant Isolation

Each tenant gets a dedicated schema (`tn_<id>`), and the `search_path` session
variable routes queries to the correct schema. This is a first-class PostgreSQL
feature with mature tooling (pg_dump `--schema`, Alembic, pgbouncer).

### 2. Full-Text Search with Spanish Configuration

We will use `tsvector`/`tsquery` with the `spanish` text search configuration:

```sql
ALTER TABLE patients ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (
        to_tsvector('spanish',
            coalesce(first_name,'') || ' ' || coalesce(last_name,'') || ' ' ||
            coalesce(document_number,'') || ' ' || coalesce(email,''))
    ) STORED;
CREATE INDEX idx_patients_search ON patients USING GIN (search_vector);
```

PostgreSQL's Spanish stemmer handles LATAM morphology ("dientes" -> "dient",
"odontologico"/"odontologia" -> "odontolog"). Accent-insensitive search uses
the `unaccent` extension so "Garcia" matches "Garcia".

### 3. JSONB for Semi-Structured Data

JSONB columns store flexible, queryable data where the schema varies by context:

```sql
CREATE TABLE clinical_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id),
    anamnesis JSONB NOT NULL DEFAULT '{}',  -- varies by country/clinic
    metadata JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_clinical_anamnesis ON clinical_records USING GIN (anamnesis);
```

JSONB provides document-like flexibility for anamnesis forms and odontogram metadata
without sacrificing relational integrity for core entities.

### 4. WAL Archiving and Per-Schema Backup

WAL archiving to Hetzner Object Storage enables point-in-time recovery (30-day
retention). Per-schema `pg_dump --schema=tn_<id>` satisfies data portability
requirements under Colombia's Ley 1581 and Mexico's LFPDPPP.

## Alternatives Considered

### Alternative 1: MySQL 8.0+

**Why not chosen:**

- **No native schemas for multi-tenancy**: MySQL conflates "database" and "schema".
  Our schema-per-tenant approach would require database-per-tenant, introducing
  connection pool complexity (see [ADR-001](001-schema-per-tenant.md) Alternative 2).
- **Inferior full-text search**: No built-in Spanish stemmer. `ngram` parsers
  produce lower-quality results for Spanish medical terminology.
- **Weaker JSON support**: MySQL's JSON stores data as text internally (not binary
  like JSONB). No GIN indexes on JSON paths.
- **No managed MySQL on Hetzner**: Self-management increases operational burden.

**Trade-offs if chosen:** Broader hosting availability, larger DBA talent pool in
LATAM, simpler replication setup. InnoDB is mature for OLTP workloads.

### Alternative 2: MongoDB

**Why not chosen:**

- **Relational data model mismatch**: The dental domain is fundamentally relational.
  A single odontogram query is a 4-table join in PostgreSQL; in MongoDB it would be
  a deeply nested document or multiple `$lookup` round-trips.
- **No schema-per-tenant**: Multi-tenancy would require collection prefixes
  (fragile), separate databases (connection overhead), or `tenant_id` fields
  (rejected in [ADR-001](001-schema-per-tenant.md)).
- **Transaction limitations**: Multi-document transactions have higher overhead.
  Clinical workflows (create patient + clinical record + odontogram) need atomicity.
- **Compliance complexity**: `mongodump` cannot per-tenant export without
  application-level filtering.

**Trade-offs if chosen:** Flexible schema simplifies anamnesis storage. Built-in
horizontal scaling via sharding. MongoDB Atlas provides mature global managed service.

### Alternative 3: CockroachDB

**Why not chosen:**

- **Overkill for our scale**: Distributed architecture targets multi-region HA.
  Year-one scale (20M-100M rows, single region) does not justify the complexity.
- **Limited schema support**: Limitations on concurrent DDL could complicate
  multi-tenant migrations.
- **Cost**: ~$600/month minimum, 3-4x our Hetzner PostgreSQL budget.

**Trade-offs if chosen:** Built-in distributed transactions and multi-region
replication. Worth revisiting at 10,000+ tenants across multiple regions.

## Consequences

### Positive

- **Single database for all needs**: PostgreSQL serves as relational database,
  full-text search engine (eliminating Elasticsearch for MVP), and semi-structured
  data store. This reduces operational complexity and infrastructure cost.
- **Mature multi-tenancy support**: Native schemas, `search_path`, pg_dump
  `--schema`, and Alembic integration provide a complete multi-tenancy toolkit.
- **Spanish full-text search out of the box**: The `spanish` text search config
  with `unaccent` handles LATAM dental terminology without external services.
- **JSONB flexibility**: Anamnesis forms and odontogram metadata evolve without
  migrations, while core relational data maintains strict integrity.
- **Compliance-ready**: WAL archiving, per-schema pg_dump, PITR, and audit logging
  via triggers satisfy LATAM healthcare regulatory requirements.
- **Ecosystem maturity**: pgbouncer, pg_stat_statements, Alembic, asyncpg,
  SQLAlchemy -- battle-tested tools for every operational need.

### Negative

- **Single-node ceiling**: Vertical scaling only. At extreme scale (10,000+ tenants,
  1B+ rows), we may need read replicas or table partitioning. Not a year-one concern.
- **FTS limitations**: Lacks typo tolerance, phonetic matching, and faceted search
  that Elasticsearch provides. May need a dedicated search service later.
- **JSONB query performance**: Complex nested JSONB queries are slower than
  relational queries. Mitigated by using JSONB only for genuinely variable data.
- **Operational knowledge required**: Team must understand VACUUM, ANALYZE, index
  bloat, and connection limits even with managed PostgreSQL.

### Neutral

- **Dual driver approach**: `asyncpg` for async access (SQLAlchemy 2.0 async engine)
  and `psycopg2` for synchronous Alembic migrations. Standard in the ecosystem.
- **Extension usage**: `uuid-ossp`, `unaccent`, and `pg_trgm` are bundled with
  standard PostgreSQL and available on Hetzner managed PostgreSQL.
- **Version targeting**: PostgreSQL 16+ for `MERGE` statement, improved logical
  replication, and `pg_stat_io`.

## References

- [`infra/database-architecture.md`](../database-architecture.md) -- Complete database schema and conventions
- [`infra/multi-tenancy.md`](../multi-tenancy.md) -- Schema-per-tenant implementation details
- [`infra/authentication-rules.md`](../authentication-rules.md) -- User/tenant data model in public schema
- [ADR-001: Schema-per-tenant](001-schema-per-tenant.md) -- Multi-tenancy requiring PostgreSQL schemas
- [ADR-002: FastAPI over Django](002-fastapi-over-django.md) -- Framework using asyncpg driver
- [ADR-004: Hetzner over AWS/GCP](004-hetzner-over-aws.md) -- Hosting provider with managed PostgreSQL
- [PostgreSQL 16 Release Notes](https://www.postgresql.org/docs/16/release-16.html)
- [PostgreSQL Full-Text Search](https://www.postgresql.org/docs/16/textsearch.html)
- [PostgreSQL JSONB Documentation](https://www.postgresql.org/docs/16/datatype-json.html)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)
- [pgbouncer Documentation](https://www.pgbouncer.org/)
- ICD-10 (CIE-10) Classification -- WHO International Classification of Diseases
- CUPS -- Clasificacion Unica de Procedimientos en Salud (Colombia)
