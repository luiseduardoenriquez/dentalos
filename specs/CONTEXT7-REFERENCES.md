# Context7 Documentation References — DentalOS

Quick-reference map of Context7 library IDs for every technology in the DentalOS stack.
All IDs verified against Context7 on 2026-02-25.

Agents should consult this file before implementing features to query up-to-date docs.

---

## Context7 Library ID Map

### Backend — Core

| Technology | Version | Context7 Library ID | Score | Snippets | Notes |
|---|---|---|---|---|---|
| **FastAPI** | 0.133.0 | `/websites/fastapi_tiangolo` | 91.4 | 21,400 | Primary docs. Endpoint patterns, DI, security, middleware |
| **FastAPI (reference)** | — | `/websites/fastapi_tiangolo_reference` | 72.8 | 1,682 | API reference only. Specific class/function lookup |
| **FastAPI (repo)** | — | `/fastapi/fastapi` | 86.5 | 1,405 | Source-level. Versions available: 0.115–0.128 |
| **SQLAlchemy** | 2.0.47 | `/websites/sqlalchemy_en_21` | 89.6 | 14,826 | **Primary.** 2.1 docs cover 2.0 patterns. Async session, schema events, search_path |
| **SQLAlchemy ORM** | — | `/websites/sqlalchemy_en_20_orm` | 79.1 | 4,541 | ORM-specific. Relationships, mapping, identity patterns |
| **SQLAlchemy Core** | — | `/websites/sqlalchemy_en_20_core` | 92.5 | — | SQL expression language. MetaData, schema reflection |
| **Pydantic v2** | 2.12.5 | `/llmstxt/pydantic_dev_llms-full_txt` | 87.6 | 3,391 | **Primary.** Validators, computed_field, model_config, JSON serialization |
| **Pydantic v2 (2.12 pinned)** | 2.12 | `/websites/pydantic_dev_2_12` | 83.5 | 2,770 | Version-specific. Use when you need exact 2.12 behavior |
| **Alembic** | 1.18.4 | `/sqlalchemy/alembic` | 81.5 | 363 | Migrations, autogenerate, multi-schema. **Note:** ID unverified in Context7 resolve (no exact match returned) — test before relying on it |
| **AsyncPG** | 0.31.0 | `/magicstack/asyncpg` | 83.7 | 51 | Repo source. Connection pools, prepared statements |
| **AsyncPG (docs)** | — | `/websites/magicstack_github_io_asyncpg_current` | 70.9 | 502 | Website docs. More content but lower score |
| **Psycopg 3** | 3.3.3 | `/websites/psycopg_psycopg3` | 81.8 | 949 | **Primary.** Async ops, COPY, connection pooling, server-side binding |
| **Boto3 (S3)** | 1.42.56 | `/boto/boto3` | 82.7 | 388 | S3 ops, presigned URLs. Use for MinIO/Hetzner Object Storage |
| **Redis (Python)** | 7.x | `/redis/redis-py` | 89.3 | 460 | Async client, pipelines, pub/sub, caching. Version available: v6.4.0 |
| **aio-pika** | 9.6.1 | `/mosquito/aio-pika` | — | 93 | Async RabbitMQ. Exchanges, queues, consumers, dead letter |
| **python-jose** | 3.5.0 | `/mpdavis/python-jose` | 81.0 | 53 | JWT RS256 generation/verification |
| **authlib joserfc** | — | `/authlib/joserfc` | 88.2 | 132 | **Modern alternative** to python-jose. JWS, JWE, JWK, JWT. Consider if python-jose gives issues |
| **Passlib** | 1.7.4 | — | — | — | No Context7 entry. Use FastAPI security docs for bcrypt |

### Backend — Testing

| Technology | Version | Context7 Library ID | Score | Snippets | Notes |
|---|---|---|---|---|---|
| **pytest** | 9.0.x | `/websites/pytest_en_stable` | 84.7 | 4,087 | **Primary.** Fixtures, markers, async mode, parametrize, conftest |
| **pytest (repo)** | 9.0.0 | `/pytest-dev/pytest` | 91.6 | 1,490 | Source-level. Internal API/plugin patterns |

### Frontend — Core

| Technology | Version | Context7 Library ID | Score | Snippets | Notes |
|---|---|---|---|---|---|
| **Next.js** | 16.x | `/vercel/next.js` | 92.8 | 2,111 | **Primary.** App Router, Server Components, `proxy.ts` (replaces middleware). Pin `/vercel/next.js/v16.1.6` for exact version |
| **Next.js (llmstxt)** | — | `/llmstxt/nextjs_llms-full_txt` | 74.4 | 40,721 | Most content. Routing, SSR, API routes. Lower score but massive coverage |
| **Next.js (website)** | — | `/websites/nextjs` | 81.2 | 5,094 | Alternative doc source |
| **TailwindCSS v4** | 4.x | `/websites/tailwindcss` | 73.3 | 2,369 | v4 utility-first. Design tokens, responsive, dark mode |
| **TailwindCSS v3** | 3.x | `/websites/v3_tailwindcss` | 88.3 | 1,760 | **Higher score.** Use if project stays on v3 |
| **TailwindCSS (repo)** | — | `/tailwindlabs/tailwindcss.com` | 79.1 | 1,983 | Documentation site source |
| **shadcn/ui** | shadcn 3.5.0 | `/shadcn-ui/ui` | 78.0 | 982 | **Primary.** Components, data table, forms, theming. Versions: 0.9.0–3.5.0 |
| **shadcn/ui (website)** | — | `/websites/ui_shadcn` | 68.0 | 1,838 | More content but lower score |
| **TanStack Query v5** | v5.84.1 | `/tanstack/query` | 92.9 | 1,177 | **Primary.** useQuery, useMutation, optimistic updates. Also has v4.29.19 |
| **TanStack Query (docs)** | v5 | `/websites/tanstack_query_v5` | 78.5 | 1,519 | v5-specific website docs |
| **Zustand** | v5.0.8 | `/pmndrs/zustand` | 77.0 | 691 | **Primary.** Store, middleware, persist, devtools. Also has v4.3.3 |
| **React Hook Form** | v7.66.0 | `/websites/react-hook-form` | 85.4 | 259 | **Primary.** useForm, Controller, validation, Zod resolver |
| **React Hook Form (docs repo)** | — | `/react-hook-form/documentation` | 82.7 | 473 | More content. Good for advanced patterns |
| **React Hook Form (source)** | v7.66.0 | `/react-hook-form/react-hook-form` | 84.9 | 322 | Source-level |
| **Zod v3** | v3.24.2 | `/websites/v3_zod_dev` | 88.4 | 8,255 | **Primary.** Schema validation, parsing, transforms, discriminated unions |
| **Zod (repo)** | v3.24.2 / v4.0.1 | `/colinhacks/zod` | 85.2 | 861 | Source-level. Pin to v3.24.2 unless migrating to Zod 4 |
| **Zod 4** | v4.0.1 | `/websites/zod_dev_v4` | 61.0 | 389 | Future option. New perf improvements + Zod Mini. Low score for now |

### Frontend — Testing

| Technology | Version | Context7 Library ID | Score | Snippets | Notes |
|---|---|---|---|---|---|
| **Vitest** | latest | `/websites/vitest_dev` | 87.2 | 2,539 | **Primary.** Config, mocking, coverage, React Testing Library |
| **Vitest (repo)** | v3.2.4 / v4.0.7 | `/vitest-dev/vitest` | 78.0 | 2,408 | Source-level. Has version tags |
| **Playwright (JS)** | latest | `/microsoft/playwright.dev` | 90.1 | 6,434 | **Primary for frontend E2E.** Cross-browser testing |
| **Playwright (Python)** | latest | `/websites/playwright_dev_python` | 92.0 | 2,543 | **Use for backend E2E.** Pytest plugin, Python API |
| **Playwright (website)** | latest | `/websites/playwright_dev` | 81.7 | 6,155 | General docs. Selectors, assertions, fixtures |

---

## Version Decision Notes

| Technology | Current in pyproject/package.json | Latest in Context7 | Recommendation |
|---|---|---|---|
| **Next.js** | 16.x | v16.1.6 available | **Start with 16.x.** Greenfield project — no migration cost. v16 is stable (released Oct 2025). Key changes: `proxy.ts` replaces `middleware.ts`, Cache Components, improved Server Actions |
| **TailwindCSS** | TBD (not yet set up) | v3 (score 88.3) vs v4 (score 73.3) | **Start with v4** — it's the current default for new projects. v3 docs are better scored but v4 is production-ready |
| **Zod** | TBD | v3.24.2 (score 88.4) vs v4.0.1 (score 61.0) | **Use Zod v3.** v4 docs are sparse. Migrate later when docs mature |
| **TanStack Query** | TBD | v5.84.1 | **Use v5.** Pin to latest v5 |
| **Zustand** | TBD | v5.0.8 | **Use v5.** Latest stable |
| **shadcn/ui** | TBD | shadcn 3.5.0 | **Use latest shadcn CLI** (3.5.0) |
| **React Hook Form** | TBD | v7.66.0 | **Use v7.** Latest stable |
| **python-jose vs authlib** | python-jose 3.5.0 | authlib/joserfc score 88.2 | **Keep python-jose** — it's in our specs already. Note authlib as fallback if jose causes issues |
| **Alembic** | 1.18.4 | No clean Context7 match | **Use SQLAlchemy docs** for migration patterns if `/sqlalchemy/alembic` fails |

---

## Per-Sprint Context7 Query Guide

### Sprint 1-2: Foundation Infrastructure

```
# Multi-tenancy + DB architecture
query-docs /websites/sqlalchemy_en_21 "async engine, schema per tenant, set search_path, connection events, multi-schema migrations"
query-docs /websites/psycopg_psycopg3 "async connection pool configuration PostgreSQL"

# Authentication (JWT RS256)
query-docs /websites/fastapi_tiangolo "JWT RS256 authentication, OAuth2 password bearer, Security dependency, HTTPBearer"
query-docs /mpdavis/python-jose "JWT encode decode RS256 private public key"
query-docs /llmstxt/pydantic_dev_llms-full_txt "BaseModel validators email password field constraints"

# Redis caching
query-docs /redis/redis-py "async Redis client pipeline TTL key patterns namespacing"

# RabbitMQ
query-docs /mosquito/aio-pika "async RabbitMQ exchange queue consumer dead letter retry"

# Alembic migrations
query-docs /sqlalchemy/alembic "multi-schema migration run_migrations_online env.py configuration"

# Testing
query-docs /websites/pytest_en_stable "async fixtures conftest factory parametrize markers coverage"
```

### Sprint 3-4: Core Entities

```
# Patient CRUD + Users
query-docs /websites/fastapi_tiangolo "CRUD endpoints pagination filtering dependency injection async database session"
query-docs /websites/sqlalchemy_en_21 "async session query filter pagination relationships eager loading"
query-docs /llmstxt/pydantic_dev_llms-full_txt "model inheritance response model exclude fields computed_field"

# Frontend Design System
query-docs /shadcn-ui/ui "installation Next.js button input select dialog toast data-table theming dark-mode"
query-docs /websites/tailwindcss "design tokens custom colors responsive breakpoints dark mode configuration"
query-docs /vercel/next.js "App Router route groups layout proxy.ts server components client components Cache Components"

# State Management
query-docs /tanstack/query "QueryClient provider useQuery configuration staleTime gcTime"
query-docs /pmndrs/zustand "store creation with TypeScript persist middleware devtools"

# Forms
query-docs /websites/react-hook-form "useForm register validation Zod resolver Controller"
query-docs /websites/v3_zod_dev "object schema string email min max regex custom validation"
```

### Sprint 5-6: Clinical Core (Odontogram)

```
# Complex models + relationships
query-docs /websites/sqlalchemy_en_21 "JSON JSONB column type, hybrid properties, relationship cascade, history tracking"
query-docs /llmstxt/pydantic_dev_llms-full_txt "nested models discriminated unions complex validation custom types"

# Full-text search (CIE-10, CUPS catalogs)
query-docs /websites/sqlalchemy_en_21 "PostgreSQL full text search tsvector tsquery func"
query-docs /redis/redis-py "cache patterns TTL search result caching"
```

### Sprint 7-8: Clinical Core 2 (Treatment Plans, Consents, Signatures)

```
# PDF generation + file storage
query-docs /boto/boto3 "S3 presigned URL upload download multipart"

# Complex business logic + transactions
query-docs /websites/fastapi_tiangolo "background tasks file upload streaming response"
query-docs /websites/sqlalchemy_en_21 "transaction management nested transactions savepoint"
```

### Sprint 9-10: Agenda + Voice

```
# Calendar/scheduling
query-docs /websites/sqlalchemy_en_21 "date range queries timezone TIMESTAMPTZ overlapping intervals"

# Voice pipeline (external APIs)
query-docs /websites/fastapi_tiangolo "background tasks WebSocket async file upload"

# Frontend calendar
query-docs /tanstack/query "infinite queries polling refetch interval real-time updates"
query-docs /pmndrs/zustand "complex state calendar view state management"
```

### Sprint 11-12: Operations (Billing, Portal, Messaging)

```
# Patient portal (separate auth)
query-docs /vercel/next.js "proxy.ts authentication route protection cookies session management"
query-docs /websites/fastapi_tiangolo "multiple auth schemes dependency overrides"

# Real-time messaging
query-docs /tanstack/query "polling optimistic updates mutation invalidation"
```

### Sprint 13-14: Compliance (RIPS, DIAN)

```
# XML/report generation
query-docs /websites/fastapi_tiangolo "streaming response file generation background tasks"
query-docs /websites/sqlalchemy_en_21 "complex aggregation queries group by window functions"

# External API integrations (DIAN/MATIAS)
query-docs /boto/boto3 "HTTP client configuration retry policies"
```

### Sprint 15-16: Advanced (Analytics, Import/Export, Inventory)

```
# Analytics + aggregation
query-docs /websites/sqlalchemy_en_21 "aggregate functions window functions materialized views"

# Bulk import/export
query-docs /websites/fastapi_tiangolo "file upload large file streaming BackgroundTasks"
query-docs /websites/sqlalchemy_en_21 "bulk insert bulk update executemany"

# Frontend charts
query-docs /tanstack/query "prefetching parallel queries dependent queries"
```

---

## Usage Instructions for Agents

When implementing any feature:

1. **Before coding**, query Context7 for the relevant technology using the library ID from this map
2. **Use the primary ID** (highest score) unless you need version-specific or domain-specific docs
3. **Query format**: `query-docs {libraryId} "{specific question about what you're implementing}"`
4. **Be specific** in queries — "How to set up async session with schema per tenant" beats "async"
5. **Cross-reference** when a feature spans multiple technologies (e.g., FastAPI + SQLAlchemy + Pydantic for an endpoint)

### Example workflow for implementing an endpoint

```
# 1. Check FastAPI patterns
query-docs /websites/fastapi_tiangolo "dependency injection async endpoint Pydantic response model"

# 2. Check SQLAlchemy for the query pattern
query-docs /websites/sqlalchemy_en_21 "async session select filter relationships eager loading"

# 3. Check Pydantic for schema design
query-docs /llmstxt/pydantic_dev_llms-full_txt "model validators field constraints response serialization"

# 4. Check pytest for test patterns
query-docs /websites/pytest_en_stable "async test fixtures mock database factory"
```

### Quick-pick: Primary IDs by Domain

| Domain | Primary Library ID |
|---|---|
| API endpoints | `/websites/fastapi_tiangolo` |
| Database/ORM | `/websites/sqlalchemy_en_21` |
| Schemas/validation (BE) | `/llmstxt/pydantic_dev_llms-full_txt` |
| Migrations | `/sqlalchemy/alembic` |
| Caching | `/redis/redis-py` |
| Queues | `/mosquito/aio-pika` |
| JWT auth | `/mpdavis/python-jose` |
| File storage | `/boto/boto3` |
| Tests (backend) | `/websites/pytest_en_stable` |
| Frontend framework | `/vercel/next.js` (v16) |
| Styling | `/websites/tailwindcss` (v4) or `/websites/v3_tailwindcss` (v3) |
| Components | `/shadcn-ui/ui` |
| Server state | `/tanstack/query` |
| Client state | `/pmndrs/zustand` |
| Forms | `/websites/react-hook-form` |
| Schema validation (FE) | `/websites/v3_zod_dev` |
| Tests (frontend) | `/websites/vitest_dev` |
| E2E tests (JS) | `/microsoft/playwright.dev` |
| E2E tests (Python) | `/websites/playwright_dev_python` |
