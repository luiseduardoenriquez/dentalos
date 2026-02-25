# DentalOS -- Architecture Decision Records (ADR) Log

> This document serves as the index and summary of all Architecture Decision Records for DentalOS.
> Each ADR captures a significant architectural choice, its context, and its consequences.
> Full ADR documents are stored in `infra/adr/`.

**Version:** 1.0
**Date:** 2026-02-24

---

## ADR Index

| # | Title | Status | Date | File | Decision Summary |
|---|-------|--------|------|------|-----------------|
| ADR-001 | Schema-per-tenant vs Row-level isolation | Accepted | 2026-02-24 | [`infra/adr/001-schema-per-tenant.md`](infra/adr/001-schema-per-tenant.md) | Schema-per-tenant for PostgreSQL multi-tenancy |
| ADR-002 | FastAPI over Django | Accepted | 2026-02-24 | [`infra/adr/002-fastapi-over-django.md`](infra/adr/002-fastapi-over-django.md) | FastAPI for async performance, OpenAPI, and type safety |
| ADR-003 | PostgreSQL over alternatives | Accepted | 2026-02-24 | [`infra/adr/003-postgresql-over-alternatives.md`](infra/adr/003-postgresql-over-alternatives.md) | PostgreSQL for schemas, full-text search, and JSONB |
| ADR-004 | Hetzner over AWS/GCP | Accepted | 2026-02-24 | [`infra/adr/004-hetzner-over-aws.md`](infra/adr/004-hetzner-over-aws.md) | Hetzner Cloud for cost efficiency and LATAM proximity |
| ADR-005 | SVG-based odontogram rendering | Accepted | 2026-02-24 | [`infra/adr/005-odontogram-svg-architecture.md`](infra/adr/005-odontogram-svg-architecture.md) | SVG for precision, interactivity, and scalability |
| ADR-006 | Offline sync with Service Workers + IndexedDB | Proposed | 2026-02-24 | [`infra/adr/006-offline-sync-strategy.md`](infra/adr/006-offline-sync-strategy.md) | PWA offline-first for LATAM internet reliability |
| ADR-007 | Country compliance adapter pattern | Accepted | 2026-02-24 | [`infra/adr/007-country-compliance-adapters.md`](infra/adr/007-country-compliance-adapters.md) | Plugin/adapter pattern per country for regulatory compliance |
| ADR-008 | RabbitMQ over Celery+Redis | Accepted | 2026-02-24 | [`infra/adr/008-rabbitmq-over-celery-redis.md`](infra/adr/008-rabbitmq-over-celery-redis.md) | RabbitMQ for routing flexibility, priorities, and DLQ |

---

## ADR Summaries

### ADR-001: Schema-per-tenant vs Row-level isolation

**File:** [`infra/adr/001-schema-per-tenant.md`](infra/adr/001-schema-per-tenant.md)
**Status:** Accepted

**Context:** DentalOS serves multiple dental clinics from a single application instance. Each clinic's data -- patient records, odontograms, clinical histories -- constitutes Protected Health Information that must be strictly isolated. We evaluated two PostgreSQL multi-tenancy strategies: schema-per-tenant (each tenant gets a dedicated PostgreSQL schema) and row-level isolation (all tenants share tables with a `tenant_id` column and Row-Level Security policies).

**Decision:** Adopt schema-per-tenant. Each tenant receives its own PostgreSQL schema (e.g., `tenant_abc123`) with identical table structures. A shared `public` schema holds cross-tenant data such as the tenant registry, subscription plans, and catalog tables (CIE-10, CUPS).

**Consequences:** Strong isolation guarantees simplify compliance audits and eliminate the risk of cross-tenant data leaks through query bugs. Per-tenant schema migrations are straightforward via Alembic. The trade-off is increased operational complexity: connection pooling via pgbouncer is mandatory, and tenant provisioning requires DDL operations. The approach scales well to hundreds of tenants; beyond 500-1000, we may need to evaluate database-per-tenant sharding.

---

### ADR-002: FastAPI over Django

**File:** [`infra/adr/002-fastapi-over-django.md`](infra/adr/002-fastapi-over-django.md)
**Status:** Accepted

**Context:** We needed a Python web framework for the DentalOS backend. The primary candidates were Django (with Django REST Framework) and FastAPI. Key requirements included async I/O support for handling concurrent clinical operations, automatic OpenAPI documentation for the frontend team, strong type safety through Pydantic, and high request throughput for operations like odontogram rendering and real-time appointment updates.

**Decision:** Use FastAPI as the backend framework, paired with SQLAlchemy 2.0 (async mode) for ORM, Pydantic v2 for validation, and Alembic for migrations.

**Consequences:** FastAPI provides native async/await support, automatic OpenAPI 3.1 spec generation, and Pydantic-based request/response validation out of the box. The async-first architecture handles concurrent odontogram reads and appointment slot calculations efficiently. The trade-off is that FastAPI has a smaller ecosystem than Django (no built-in admin panel, no ORM), requiring us to assemble components ourselves. However, this aligns with our need for fine-grained control over the multi-tenant database layer.

---

### ADR-003: PostgreSQL over alternatives

**File:** [`infra/adr/003-postgresql-over-alternatives.md`](infra/adr/003-postgresql-over-alternatives.md)
**Status:** Accepted

**Context:** We evaluated PostgreSQL, MySQL, and MongoDB for DentalOS's primary data store. The dental domain has highly structured, relational data (patients have clinical records, which contain diagnoses, treatments, and tooth references). Multi-tenancy requires schema-level isolation. Full-text search is needed for patient lookup, CIE-10 codes, and CUPS codes. Flexible data storage is needed for anamnesis forms and odontogram condition metadata.

**Decision:** PostgreSQL as the sole primary database. Leverage native schemas for tenant isolation, `tsvector`/`tsquery` for full-text search (Spanish language configuration), and JSONB columns for semi-structured data (odontogram metadata, custom form fields, anamnesis responses).

**Consequences:** PostgreSQL's schema feature directly enables our multi-tenancy strategy without application-level hacks. Full-text search in Spanish eliminates the need for Elasticsearch in the MVP. JSONB provides document-like flexibility where needed (e.g., storing variable anamnesis questionnaire responses per country) without sacrificing relational integrity for core entities. The mature ecosystem of tools (pgbouncer, pg_dump, WAL archiving, Alembic) supports our operational requirements.

---

### ADR-004: Hetzner over AWS/GCP

**File:** [`infra/adr/004-hetzner-over-aws.md`](infra/adr/004-hetzner-over-aws.md)
**Status:** Accepted

**Context:** DentalOS targets dental practices in LATAM, a price-sensitive market. Infrastructure cost directly impacts the viability of the freemium pricing model. We compared Hetzner Cloud, AWS, and GCP across cost, performance, data center locations, and managed service availability. A comparable configuration (4 vCPU, 16 GB RAM, managed PostgreSQL, load balancer, S3-compatible storage) was priced across all three providers.

**Decision:** Host DentalOS on Hetzner Cloud. Use Hetzner's Ashburn (US-East) data center initially, with migration to a LATAM-proximate region as Hetzner expands or as latency requirements dictate.

**Consequences:** Hetzner is 4-6x cheaper than AWS/GCP for equivalent compute and storage. This allows DentalOS to offer a viable free tier and keeps infrastructure costs below $200/month for the MVP phase. The trade-off is a smaller managed services ecosystem: we self-manage RabbitMQ, Redis, and some monitoring tooling that would be managed services on AWS. Hetzner provides managed PostgreSQL, S3-compatible object storage, and load balancers, which covers our critical needs. If DentalOS scales beyond what Hetzner can handle, the architecture (Docker containers, standard PostgreSQL, S3-compatible storage) is portable to any cloud.

---

### ADR-005: SVG-based odontogram rendering

**File:** [`infra/adr/005-odontogram-svg-architecture.md`](infra/adr/005-odontogram-svg-architecture.md)
**Status:** Accepted

**Context:** The odontogram is the centerpiece UI of DentalOS -- dentists interact with it dozens of times per day. We evaluated three rendering approaches: HTML/CSS with div-based tooth representations, HTML5 Canvas for bitmap rendering, and SVG (Scalable Vector Graphics) for vector-based rendering. Requirements included per-surface click targets (5 surfaces per tooth), visual condition indicators (colors, patterns, overlays), responsive scaling from tablet to desktop, printability, and the ability to support both Classic (grid) and Anatomic (arch) layout modes.

**Decision:** Render the odontogram using inline SVG with React components. Each tooth is a composite SVG group (`<g>`) containing surface paths, condition overlays, and interactive hit areas. The SVG viewBox provides resolution-independent scaling.

**Consequences:** SVG provides pixel-perfect rendering at any zoom level, critical for dental professionals who need precise visual feedback. Individual SVG elements are DOM nodes, enabling React state management per surface and standard event handling (click, hover, right-click context menus). SVG renders natively to PDF/print without rasterization artifacts. The trade-off is that SVG rendering of 32 teeth with 5 surfaces each (160+ interactive elements) requires careful performance optimization (React memoization, virtualization of off-screen teeth on mobile). The SVG approach also produces clean, accessible markup that can be enhanced with ARIA labels for condition status.

---

### ADR-006: Offline sync with Service Workers + IndexedDB

**File:** [`infra/adr/006-offline-sync-strategy.md`](infra/adr/006-offline-sync-strategy.md)
**Status:** Proposed

**Context:** Many dental clinics in LATAM operate with unreliable internet connectivity. A dentist mid-procedure cannot wait for a network request to record a finding on the odontogram. DentalOS must function during connectivity gaps and synchronize data when the connection returns. We evaluated three approaches: optimistic UI with retry queues, full offline-first with local database, and a hybrid approach with Service Workers and IndexedDB.

**Decision:** Implement a PWA with Service Workers for asset caching and IndexedDB for data persistence. Clinical writes (odontogram updates, clinical record entries) are queued in IndexedDB when offline and synchronized via a background sync queue when connectivity returns. Conflict resolution uses last-write-wins with server timestamp arbitration for most resources, with merge logic for odontogram concurrent edits.

**Consequences:** Dentists can continue clinical work during internet outages, which is a significant competitive differentiator in the LATAM market. The trade-off is substantial frontend complexity: the sync engine must handle conflict resolution, partial sync failures, and version reconciliation. This is scoped as a post-MVP enhancement (Low priority, Sprint 13+). The MVP will use optimistic UI with retry logic for short connectivity gaps, while the full offline-first implementation arrives later.

---

### ADR-007: Country compliance adapter pattern

**File:** [`infra/adr/007-country-compliance-adapters.md`](infra/adr/007-country-compliance-adapters.md)
**Status:** Accepted

**Context:** DentalOS targets five LATAM countries (Colombia, Mexico, Chile, Argentina, Peru), each with distinct regulatory requirements for clinical records, electronic invoicing, and health data reporting. Colombia requires RDA-compliant odontograms and RIPS reporting. Mexico requires NOM-024 health records and CFDI invoicing. Chile requires DTE invoicing. Rather than scattering country-specific logic throughout the codebase, we need an extensible architecture.

**Decision:** Implement a country compliance adapter pattern. Define a `ComplianceAdapter` interface with methods for each regulatory concern (validate clinical record, generate invoice, export reporting data, format odontogram). Each country has a concrete adapter implementation (e.g., `ColombiaComplianceAdapter`, `MexicoComplianceAdapter`). The adapter is resolved at runtime from the tenant's `country` setting and injected via FastAPI dependency injection.

**Consequences:** Adding a new country requires implementing a new adapter class without modifying existing code (Open/Closed Principle). Country-specific validation rules, document formats, and code systems (CIE-10 subsets, CUPS vs country-equivalent) are encapsulated in the adapter. The trade-off is the upfront cost of defining the adapter interface broadly enough to accommodate future countries while keeping it practical for the MVP (Colombia-first). The interface will evolve as we onboard Mexico and Chile. Each adapter is independently testable with country-specific test fixtures.

---

### ADR-008: RabbitMQ over Celery+Redis

**File:** [`infra/adr/008-rabbitmq-over-celery-redis.md`](infra/adr/008-rabbitmq-over-celery-redis.md)
**Status:** Accepted

**Context:** DentalOS requires asynchronous task processing for email delivery, WhatsApp notifications, RIPS file generation, electronic invoice submission, audit log writes, and appointment reminders. We evaluated two approaches: Celery with Redis as the broker (the common Python stack) and direct RabbitMQ with a lightweight consumer framework (e.g., aio-pika).

**Decision:** Use RabbitMQ as the message broker with aio-pika for async Python consumers. Define explicit exchanges, queues, and routing keys for each task domain. Redis remains in the stack exclusively for caching and rate limiting.

**Consequences:** RabbitMQ provides native support for message priorities (urgent notifications vs batch RIPS generation), dead letter queues (failed messages are preserved for inspection and replay), exchange-based routing (route messages by tenant, by country, by task type), and acknowledgment-based delivery guarantees. The trade-off versus Celery is that we lose Celery's convenient task decorator API and must manage queue topology ourselves. However, RabbitMQ's operational visibility (management UI, queue metrics) and message durability guarantees are critical for healthcare-related tasks where lost messages could mean lost clinical data or missed compliance reporting deadlines. Each queue has explicit retry policies and DLQ routing.

---

## How to Write an ADR

Architecture Decision Records capture significant technical decisions made during the design and development of DentalOS. An ADR should be written whenever a decision:

- Affects the system's structure or architecture
- Is difficult or costly to reverse
- Involves a trade-off between competing concerns
- Will be questioned by future team members ("why did we do it this way?")

### ADR Template

Save new ADRs to `infra/adr/NNN-short-name.md` using this structure:

```markdown
# ADR-NNN: [Title]

**Status:** [Proposed | Accepted | Deprecated | Superseded by ADR-XXX]
**Date:** YYYY-MM-DD
**Authors:** [Who proposed this decision]

---

## Context

Describe the situation that motivates this decision. What problem are we facing?
What constraints exist? What forces are at play (technical, business, regulatory, team)?

Be specific. Include numbers, benchmarks, or references where relevant.

## Decision

State the decision clearly and concisely. What are we going to do?

Use active voice: "We will use X" rather than "X was chosen."

## Alternatives Considered

List the alternatives that were evaluated. For each alternative, briefly explain:
- What it is
- Why it was not chosen
- What its trade-offs would have been

## Consequences

### Positive
- What becomes easier or better as a result of this decision?

### Negative
- What becomes harder or worse? What are the trade-offs?
- What risks does this introduce?

### Neutral
- What other effects does this have that are neither clearly positive nor negative?

## References

- Links to relevant documentation, benchmarks, or prior art
- Links to related ADRs
```

### ADR Lifecycle

| Status | Meaning |
|--------|---------|
| **Proposed** | Under discussion, not yet agreed upon |
| **Accepted** | Team has agreed, implementation can proceed |
| **Deprecated** | No longer relevant but kept for historical context |
| **Superseded** | Replaced by a newer ADR (link to replacement) |

### Naming Convention

- File name: `NNN-short-descriptive-name.md`
- NNN is a zero-padded three-digit number: `001`, `002`, ..., `099`, `100`
- Use kebab-case for the descriptive name
- The ADR number is never reused, even if the ADR is deprecated

### When to Update This Log

- When a new ADR is created, add it to the index table and write a summary paragraph
- When an ADR status changes (e.g., Proposed to Accepted), update the status in the index
- When an ADR is superseded, add the replacement reference

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial ADR log with 8 foundational decisions |
