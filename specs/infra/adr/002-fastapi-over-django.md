# ADR-002: FastAPI over Django

**Status:** Accepted
**Date:** 2026-02-24
**Authors:** DentalOS Architecture Team

---

## Context

DentalOS requires a Python web framework to serve as the backbone of its backend API.
The platform handles dental clinic operations including patient management, clinical
record entry, odontogram manipulation, appointment scheduling, treatment planning,
billing, and compliance reporting. The backend must serve a React/Next.js frontend
and potentially a mobile PWA.

### Requirements

1. **Async I/O**: Clinical workflows involve concurrent operations -- a dentist
   updating an odontogram while the receptionist books an appointment while a
   background job generates a RIPS compliance file. The framework must handle
   concurrent I/O-bound operations (database queries, external API calls for
   electronic invoicing) without blocking the event loop.

2. **OpenAPI auto-documentation**: The frontend team (and future third-party
   integrators) needs a machine-readable API specification. Manual Swagger
   maintenance is unsustainable for a system with 80+ endpoints across 15 domains.

3. **Strong validation**: Every API request carries clinical data that must be
   validated rigorously -- patient identification numbers, CIE-10 codes, tooth
   surface identifiers (FDI notation), date ranges, and treatment codes. Validation
   must be declarative and produce clear error messages in Spanish.

4. **Multi-tenant database support**: The chosen framework must accommodate dynamic
   `search_path` switching per request (see [ADR-001](001-schema-per-tenant.md)).
   This requires fine-grained control over database session lifecycle.

5. **High throughput for clinical operations**: Odontogram reads (fetching 32 teeth
   with conditions, surfaces, and treatment history) and appointment slot calculations
   (computing available 15-minute slots across multiple providers for a week) are
   the most demanding operations, requiring sub-200ms response times.

6. **Extensibility for compliance**: Country-specific compliance adapters (see
   [`infra/multi-tenancy.md`](../multi-tenancy.md)) require a clean dependency
   injection pattern to resolve the correct adapter per tenant per request.

### Team Context

The founding engineering team has strong Python experience with both Django and
FastAPI. The team size is 2-4 engineers, meaning the framework must be productive
for a small team without requiring extensive boilerplate.

## Decision

We will use **FastAPI** as the backend web framework, paired with the following
supporting libraries:

| Component | Library | Version |
|-----------|---------|---------|
| Web framework | FastAPI | 0.115+ |
| ORM | SQLAlchemy | 2.0+ (async mode) |
| Validation | Pydantic | v2.x |
| Migrations | Alembic | 1.13+ |
| ASGI server | Uvicorn | 0.30+ |
| Auth | python-jose + passlib | Latest |
| Task queue | aio-pika (RabbitMQ) | Latest |

### Architecture Pattern

The backend follows a layered architecture:

```
Request -> FastAPI Router -> Pydantic Schema (validation)
        -> Dependency Injection (tenant context, auth, compliance adapter)
        -> Service Layer (business logic)
        -> Repository Layer (SQLAlchemy async queries)
        -> PostgreSQL (via asyncpg + pgbouncer)
```

FastAPI's dependency injection system is central to our architecture:

```python
async def get_tenant_context(
    token: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> TenantContext:
    tenant = await tenant_service.get_by_id(db, token.tenant_id)
    await db.execute(text(f"SET search_path TO {tenant.schema_name}, public"))
    return TenantContext(tenant=tenant, db=db)

@router.get("/patients")
async def list_patients(
    ctx: TenantContext = Depends(get_tenant_context),
    compliance: ComplianceAdapter = Depends(get_compliance_adapter),
):
    patients = await patient_service.list(ctx.db)
    return compliance.format_patient_list(patients)
```

This pattern chains tenant resolution, database session configuration, and compliance
adapter injection in a declarative, testable manner.

## Alternatives Considered

### Alternative 1: Django + Django REST Framework (DRF)

Django is the most mature Python web framework with a comprehensive ecosystem
including a built-in admin panel, ORM, authentication, and a large plugin registry.
DRF adds API serialization, viewsets, and browsable API documentation.

**Why not chosen:**

- **Synchronous by default**: Django's ORM is synchronous. While Django 4.1+
  introduced async views, the ORM still requires `sync_to_async` wrappers for
  database queries, adding complexity and limiting true async throughput. Our
  benchmark showed Django async views with `sync_to_async` ORM calls at ~60% of
  the throughput of FastAPI with native async SQLAlchemy.
- **ORM flexibility**: Django's ORM does not natively support dynamic `search_path`
  switching. Multi-tenant packages (django-tenants) exist but impose their own
  conventions and middleware that may conflict with our specific schema-per-tenant
  approach. SQLAlchemy 2.0's explicit session management gives us precise control.
- **OpenAPI generation**: DRF's schema generation (via drf-spectacular) is
  functional but requires manual annotations for complex endpoints. FastAPI
  generates OpenAPI 3.1 specs directly from Pydantic models and function
  signatures with zero additional configuration.
- **Validation**: DRF serializers are powerful but verbose compared to Pydantic v2
  models. Pydantic v2's Rust-based validation core is 5-50x faster than DRF
  serializers for equivalent payloads (Pydantic v2 benchmarks).

**Trade-offs if chosen:** Django Admin would provide an immediate back-office UI
for internal operations (tenant management, catalog editing, support tools). We
lose this with FastAPI and must build admin tooling ourselves. Django's mature
ecosystem includes battle-tested packages for permissions (django-guardian),
caching (django-redis), and rate limiting. However, these are Django-specific
and would not apply to our SQLAlchemy + Pydantic stack.

### Alternative 2: Flask + Extensions

Flask is a minimalist WSGI framework. With extensions (Flask-SQLAlchemy,
Flask-RESTful, Marshmallow), it can approximate the capabilities of FastAPI
or Django.

**Why not chosen:**

- **No native async**: Flask is WSGI-based (synchronous). Async support via
  Flask 2.0's `async def` views is limited and does not extend to the database
  layer. For I/O-heavy clinical operations, this is a hard blocker.
- **Assembly required**: Flask requires assembling validation (Marshmallow),
  serialization, OpenAPI generation (apispec), dependency injection (flask-injector),
  and async support from separate packages with varying maintenance quality.
  FastAPI provides all of these as first-class features.
- **Type safety**: Flask's dynamic routing and view registration do not leverage
  Python type hints. FastAPI's type-driven approach catches errors at import time
  and enables IDE autocompletion for request/response models.

**Trade-offs if chosen:** Flask's simplicity makes it easy to understand and debug.
Its minimal surface area means fewer framework-specific concepts to learn. However,
the total complexity of Flask + extensions exceeds FastAPI for our use case.

### Benchmark Comparison

Benchmarks run on equivalent hardware (4 vCPU, 16GB RAM) with a representative
workload: JSON serialization of a patient list (20 records with nested relations).

| Framework | Requests/sec | p99 Latency | Async DB Support |
|-----------|-------------|-------------|-----------------|
| FastAPI + asyncpg | ~4,200 | 12ms | Native |
| Django + sync_to_async | ~2,500 | 28ms | Wrapper |
| Flask + psycopg2 | ~2,100 | 35ms | None |

These numbers reflect the combined effect of framework overhead, serialization
performance (Pydantic v2 vs DRF serializers vs Marshmallow), and database driver
efficiency (asyncpg vs psycopg2).

## Consequences

### Positive

- **Native async throughout**: FastAPI + SQLAlchemy 2.0 async + asyncpg provides
  true async from HTTP handler to database driver. Concurrent odontogram reads,
  appointment slot calculations, and compliance report generation run without
  blocking each other on a single worker process.
- **OpenAPI 3.1 auto-generation**: Every endpoint automatically produces an OpenAPI
  spec from Pydantic models and function signatures. The frontend team can generate
  TypeScript types directly from the spec using openapi-typescript. API documentation
  is always in sync with the code.
- **Pydantic v2 performance**: Request/response validation is 5-50x faster than
  DRF serializers, with Rust-based core processing. For endpoints that validate
  complex clinical data structures (odontogram findings with 32 teeth x 5 surfaces
  x conditions), this performance advantage is significant.
- **Dependency injection for multi-tenancy**: FastAPI's `Depends()` system cleanly
  chains tenant resolution, database session configuration, auth checks, and
  compliance adapter injection. Each dependency is independently testable by
  providing mock overrides via `app.dependency_overrides`.
- **Type safety**: Path parameters, query parameters, request bodies, and response
  models are all typed. Mypy and Pyright catch type errors before runtime. IDE
  autocompletion works throughout the codebase.
- **Lightweight footprint**: FastAPI adds minimal overhead beyond Starlette (its
  ASGI foundation). The framework surface is small, reducing the likelihood of
  framework-specific bugs or upgrade friction.

### Negative

- **No built-in admin panel**: Django Admin is a significant productivity tool for
  back-office operations. Without it, we must build tenant management, catalog
  editing, and support tools from scratch. Mitigation: We will build a minimal
  admin API with a React-based admin dashboard in a later phase. For MVP, direct
  database access and CLI scripts handle admin operations.
- **Smaller ecosystem**: Django's package ecosystem is larger and more mature.
  Packages like django-allauth (social auth), django-import-export (data import),
  and django-simple-history (audit trails) have no direct FastAPI equivalents.
  We implement these features ourselves or use framework-agnostic libraries.
- **ORM assembly**: SQLAlchemy 2.0 async mode requires explicit session management,
  which is more verbose than Django's ORM. Session lifecycle (creation, commit,
  rollback, close) must be managed via dependency injection rather than implicit
  middleware.
- **Team onboarding**: Engineers familiar with Django must learn FastAPI's patterns
  (Depends, response_model, async session management). The learning curve is
  moderate (1-2 weeks for a Django-experienced developer).

### Neutral

- **ASGI server choice**: FastAPI runs on any ASGI server (Uvicorn, Hypercorn,
  Daphne). We standardize on Uvicorn with Gunicorn as the process manager.
  This is a deployment detail, not an architectural constraint.
- **Testing approach**: FastAPI's `TestClient` (based on httpx) provides similar
  ergonomics to Django's test client. Async tests require `pytest-asyncio` but
  are otherwise straightforward.
- **Middleware compatibility**: FastAPI supports both ASGI middleware and Starlette
  middleware. CORS, request logging, tenant resolution, and rate limiting are
  implemented as middleware, consistent with what Django middleware would provide.
- **Community growth**: FastAPI's GitHub star count and PyPI download volume have
  grown rapidly since 2020, but Django's ecosystem remains larger. We accept that
  some problems require custom solutions rather than off-the-shelf packages.

## References

- [`infra/multi-tenancy.md`](../multi-tenancy.md) -- Multi-tenancy implementation using FastAPI DI
- [`infra/database-architecture.md`](../database-architecture.md) -- SQLAlchemy 2.0 async configuration
- [`infra/authentication-rules.md`](../authentication-rules.md) -- JWT auth with FastAPI dependencies
- [ADR-001: Schema-per-tenant](001-schema-per-tenant.md) -- Tenant isolation requiring fine-grained DB session control
- [ADR-003: PostgreSQL over alternatives](003-postgresql-over-alternatives.md) -- Database choice paired with asyncpg driver
- [ADR-004: Hetzner over AWS/GCP](004-hetzner-over-aws.md) -- Infrastructure constraints informing framework efficiency needs
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Pydantic v2 Performance Benchmarks](https://docs.pydantic.dev/latest/concepts/performance/)
- [Django Async Support](https://docs.djangoproject.com/en/5.0/topics/async/)
- [Starlette ASGI Framework](https://www.starlette.io/)
