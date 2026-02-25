# DentalOS -- Master Technical Specification (M1)

> **Spec ID:** R-03
> **Status:** Draft
> **Version:** 1.0
> **Last Updated:** 2026-02-24

---

## Purpose

This is the master technical reference for DentalOS -- a multi-tenant SaaS platform for dental practices in Latin America. It provides the high-level architecture, complete data model summary, permission matrix, API surface overview, and integration map. Developers should consult this document daily and follow the cross-references to detailed specs for implementation guidance.

**Stack:** Python 3.12 + FastAPI + SQLAlchemy 2.0 + PostgreSQL 16 (schema-per-tenant) + Redis + RabbitMQ + Next.js 14 + TailwindCSS
**Hosting:** Hetzner Cloud (Frankfurt / Falkenstein)
**Target Market:** Dental practices in LATAM (Colombia first, then Mexico, Chile, Argentina, Peru)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Data Model Summary](#2-data-model-summary)
3. [Entity Relationship Diagram](#3-entity-relationship-diagram)
4. [Permission Matrix (RBAC)](#4-permission-matrix-rbac)
5. [API Architecture](#5-api-architecture)
6. [Authentication Architecture Summary](#6-authentication-architecture-summary)
7. [Multi-Tenancy Architecture Summary](#7-multi-tenancy-architecture-summary)
8. [External Integrations](#8-external-integrations)
9. [Performance Targets](#9-performance-targets)
10. [Infrastructure References](#10-infrastructure-references)
11. [Sprint Roadmap Summary](#11-sprint-roadmap-summary)
12. [Version History](#12-version-history)

---

## 1. Architecture Overview

### 1.1 System Architecture Diagram

```
                              +------------------+
                              |   DNS / CDN      |
                              |  (Cloudflare)    |
                              +--------+---------+
                                       |
                              +--------v---------+
                              |  Hetzner Load    |
                              |  Balancer (TLS)  |
                              +--------+---------+
                                       |
                    +------------------+------------------+
                    |                                     |
           +--------v---------+              +------------v----------+
           |  Next.js Frontend |              |   FastAPI Backend     |
           |  (SSR + Static)   |              |   (Uvicorn workers)   |
           |  Port 3000        |              |   Port 8000           |
           +-------------------+              +---+--------+----+----+
                                                  |        |    |
                            +---------------------+        |    +-------------+
                            |                              |                  |
                   +--------v--------+          +----------v---+    +---------v--------+
                   |   PostgreSQL    |          |    Redis      |    |    RabbitMQ       |
                   |   (Primary)     |          |    Sentinel   |    |    Broker         |
                   |                 |          |               |    |                   |
                   |  public schema  |          |  db0: cache   |    |  notifications    |
                   |  tn_* schemas   |          |  db1: sessions|    |  clinical         |
                   |                 |          |  db2: rates   |    |  import/export    |
                   +--------+--------+          |  db3: jobs    |    |  maintenance      |
                            |                   +--------------+    +-------------------+
                   +--------v--------+
                   |   PostgreSQL    |                        +-----------------------+
                   |   (Replica)     |                        |  S3-Compatible Store  |
                   |   (read-only)   |                        |  (Hetzner Object)     |
                   +-----------------+                        |  X-rays, photos, PDFs |
                                                              +-----------------------+
```

### 1.2 Component Interaction

```
+-------------+     HTTPS      +------------------+     SQL        +----------------+
|  Next.js    | -------------> |  FastAPI API      | ------------> |  PostgreSQL    |
|  Frontend   | <------------- |  /api/v1/dentalos | <------------ |  (per-tenant)  |
+-------------+     JSON       +--------+---------+     Results    +----------------+
                                        |
                               +--------+--------+-----------+
                               |                 |           |
                        +------v-----+   +-------v----+ +----v----------+
                        |   Redis    |   | RabbitMQ   | | S3 Storage    |
                        |   Cache    |   | Queues     | | Files         |
                        +------------+   +------+-----+ +---------------+
                                                |
                                         +------v-----+
                                         |  Workers   |
                                         |  (async)   |
                                         +------------+
                                                |
                             +------------------+------------------+
                             |                  |                  |
                      +------v------+   +-------v------+  +-------v------+
                      |  WhatsApp   |   |  SMTP Email  |  |  DIAN/SAT    |
                      |  Business   |   |  Provider    |  |  E-Invoicing |
                      +-------------+   +--------------+  +--------------+
```

### 1.3 Request Lifecycle

Every authenticated API request follows this exact path:

```
Browser (Next.js)
  -> HTTPS request with Bearer token
  -> Cloudflare CDN (static cache, DDoS protection)
  -> Hetzner Load Balancer (TLS termination)
  -> Uvicorn / FastAPI worker process
     -> Middleware chain:
        1. CORS validation
        2. HTTPS redirect enforcement
        3. Rate limiting (Redis db2, sliding window)
        4. Request ID injection (X-Request-ID)
        5. JWT authentication (RS256 verify)
        6. Tenant resolution (JWT tid -> Redis cache -> schema_name)
        7. SET search_path TO tn_{schema}, public
     -> Route handler (business logic)
        -> SQLAlchemy 2.0 async session
        -> PostgreSQL query (tenant schema)
        -> Redis cache (read-through / write-through)
     -> Response serialization (Pydantic v2)
  -> JSON response to client
```

> **Detailed specs:** `infra/security-policy.md` (middleware), `infra/authentication-rules.md` (JWT), `infra/multi-tenancy.md` (tenant resolution), `infra/rate-limiting.md` (rate limits)

---

## 2. Data Model Summary

DentalOS has **41 tables** across two schema types: a shared `public` schema (6 tables) and a per-tenant schema (35 tables). The complete DDL with all columns, constraints, indexes, and triggers is defined in `infra/database-architecture.md`. This section provides the high-level inventory only.

### 2.1 Shared Schema (`public`) -- 6 Tables

These tables exist once in the database and are readable by all tenants.

| # | Table | Description |
|---|-------|-------------|
| 1 | `tenants` | Clinic registrations: slug, schema_name, country, plan, status, settings, timezone |
| 2 | `plans` | Subscription tiers (free, starter, professional, enterprise) with feature limits |
| 3 | `superadmin_users` | Platform operators who manage tenants, not tied to any single clinic |
| 4 | `catalog_cie10` | ICD-10 / CIE-10 diagnostic codes (international dental/medical classification) |
| 5 | `catalog_cups` | CUPS procedure codes (Colombian Unified Procedure Classification, extensible) |
| 6 | `catalog_medications` | Standardized medication database for prescriptions (active ingredient, form, dosage) |

### 2.2 Tenant Schema (`tn_*`) -- 35 Tables

Each tenant gets an identical copy of these tables in their own PostgreSQL schema.

**Authentication and Users (3 tables)**

| # | Table | Description |
|---|-------|-------------|
| 1 | `users` | Staff members: email, password_hash, role, status, profile data |
| 2 | `user_sessions` | Active refresh tokens and session metadata per user |
| 3 | `user_invites` | Pending invitations to join the clinic (email, role, expiry) |

**Patient Management (2 tables)**

| # | Table | Description |
|---|-------|-------------|
| 4 | `patients` | Patient demographics: name, document_id, DOB, contact, insurance, emergency contact |
| 5 | `patient_documents` | Uploaded files per patient: X-rays, photos, consent scans (S3 references) |

**Odontogram (4 tables)**

| # | Table | Description |
|---|-------|-------------|
| 6 | `odontogram_states` | Current state of each tooth per patient (32 adult + 20 deciduous positions) |
| 7 | `odontogram_conditions` | Active conditions on a tooth/surface: caries, fracture, restoration, etc. |
| 8 | `odontogram_history` | Immutable changelog of every condition change with before/after values |
| 9 | `odontogram_snapshots` | Point-in-time JSON snapshots of the full odontogram (for treatment plans, legal) |

**Clinical Records (3 tables)**

| # | Table | Description |
|---|-------|-------------|
| 10 | `clinical_records` | Visit-level clinical encounter: subjective, objective, assessment, plan (SOAP) |
| 11 | `anamnesis` | Medical history questionnaire: allergies, medications, conditions, habits |
| 12 | `diagnoses` | CIE-10 diagnoses linked to clinical records, with tooth references |

**Procedures and Treatment Plans (3 tables)**

| # | Table | Description |
|---|-------|-------------|
| 13 | `procedures` | Individual dental procedures performed, linked to CUPS codes and teeth |
| 14 | `treatment_plans` | Grouped plan of proposed procedures with status tracking |
| 15 | `treatment_plan_items` | Individual line items in a treatment plan, each referencing a procedure code |

**Consents (2 tables)**

| # | Table | Description |
|---|-------|-------------|
| 16 | `consent_templates` | Reusable informed consent form templates (markdown content, version) |
| 17 | `consents` | Signed consent records per patient: template reference, signature data, timestamp |

**Appointments and Scheduling (5 tables)**

| # | Table | Description |
|---|-------|-------------|
| 18 | `appointments` | Scheduled appointments: patient, doctor, datetime, duration, status, notes |
| 19 | `appointment_reminders` | Scheduled reminders per appointment: channel (WhatsApp/email/SMS), send time, status |
| 20 | `doctor_schedules` | Recurring weekly availability per doctor (day_of_week, start_time, end_time) |
| 21 | `availability_blocks` | One-off overrides: vacations, blocked slots, extended hours |
| 22 | `waitlist` | Patients waiting for a cancelled slot (patient, preferred doctor, date range) |

**Billing and Payments (6 tables)**

| # | Table | Description |
|---|-------|-------------|
| 23 | `invoices` | Patient invoices: total, tax, status (draft/sent/paid/overdue/cancelled) |
| 24 | `invoice_items` | Line items per invoice, linked to procedures or service catalog |
| 25 | `payments` | Payment records: amount, method (cash/card/transfer), reference number |
| 26 | `payment_plans` | Installment plans for patients: total, number of installments, frequency |
| 27 | `payment_plan_installments` | Individual installments: due date, amount, status (pending/paid/overdue) |
| 28 | `service_catalog` | Clinic-defined price list for procedures and services |

**Prescriptions (2 tables)**

| # | Table | Description |
|---|-------|-------------|
| 29 | `prescriptions` | Prescription header: patient, doctor, date, notes |
| 30 | `prescription_items` | Individual medications: name, dosage, frequency, duration, instructions |

**Communication (3 tables)**

| # | Table | Description |
|---|-------|-------------|
| 31 | `message_threads` | Conversation threads between clinic staff and patients |
| 32 | `messages` | Individual messages within threads: sender, content, timestamp, read status |
| 33 | `notifications` | System notifications per user: type, title, body, read status, action URL |

**System (2 tables)**

| # | Table | Description |
|---|-------|-------------|
| 34 | `audit_log` | Immutable log of all data access and modifications (healthcare compliance) |
| 35 | `tenant_settings` | Key-value configuration specific to this tenant (extends public.tenants.settings) |

> **Complete DDL:** `infra/database-architecture.md` (all columns, constraints, indexes, triggers, and migration strategy)

---

## 3. Entity Relationship Diagram

ASCII diagram showing the major relationships between entities. Foreign keys shown as arrows.

```
                                    +------------------+
                                    |     users        |
                                    |------------------|
                                    | id (PK)          |
                                    | role             |
                                    | email            |
                                    +---+---------+----+
                                        |         |
                            (doctor_id) |         | (doctor_id)
                                        |         |
         +------------------------------+    +----+--------------+
         |                                   |                   |
         v                                   v                   v
+--------+----------+    +------------------+-+    +-------------+-------+
|  appointments     |    | doctor_schedules   |    | availability_blocks |
|-------------------|    |--------------------|    |---------------------|
| patient_id (FK)   |    | user_id (FK)       |    | user_id (FK)        |
| doctor_id (FK)    |    | day_of_week        |    | date, type          |
| datetime, status  |    | start/end time     |    +---------------------+
+---+---------------+    +--------------------+
    |
    v
+---+---------------------+
| appointment_reminders   |
|-------------------------|
| appointment_id (FK)     |
| channel, send_at        |
+-------------------------+


+-------------------+
|    patients       |<-----------------------------------------------------+
|-------------------|                                                       |
| id (PK)          +-----------+-----------+----------+----------+         |
| name, document   |           |           |          |          |         |
+--+----+-----+----+           |           |          |          |         |
   |    |     |                |           |          |          |         |
   |    |     |                |           |          |          |         |
   v    |     v                v           v          v          |         |
+--+--+ | +---+-------+ +-----+-----+ +---+----+ +---+------+  |         |
|odon.| | |clinical_  | |treatment_ | |consents| |invoices  |  |         |
|state| | |records    | |plans      | |--------| |----------|  |         |
|-----| | |-----------| |-----------| |template| |total     |  |         |
|tooth| | |SOAP notes | |status     | |signed  | |status    |  |         |
+--+--+ | +---+---+---+ +----+------+ +--------+ +---+------+  |         |
   |    |     |   |           |                       |         |         |
   v    |     v   v           v                       v         |         |
+--+--+ | +--+--++----+ +----+----------+     +------+------+  |         |
|odon.| | |diag-||proc-| |treatment_    |     |invoice_items|  |         |
|cond.| | |noses||edur.| |plan_items    |     |-------------|  |         |
|-----| | |----||-----| |-------------|     |procedure_ref|  |         |
|code | | |CIE ||CUPS | |procedure_ref|     +------+------+  |         |
|surf.| | +----++--+--+ +-------------+            |         |         |
+--+--+ |         |                                 v         |         |
   |    |         |                          +------+------+  |         |
   v    |         |                          |  payments   |  |         |
+--+--+ |         |                          |-------------|  |         |
|odon.| |         |                          |amount,method|  |         |
|hist.| |         |                          +-------------+  |         |
+-----+ |         |                                           |         |
        |         |                          +-------------+  |         |
        v         |                          |payment_plans+--+         |
+-------+------+  |                          |-------------|            |
|patient_docs  |  |                          |installments |            |
|--------------|  |                          +-------------+            |
|file_url, type|  |                                                     |
+--------------+  |     +----------------+                              |
                  |     |prescriptions   +------------------------------+
                  |     |----------------|
                  |     |doctor_id (FK)  |
                  |     +-------+--------+
                  |             |
                  |             v
                  |     +-------+----------+
                  |     |prescription_items|
                  |     |------------------|
                  |     |medication, dose  |
                  |     +------------------+
                  |
                  |     +----------------+
                  +---->|message_threads |
                        |----------------|
                        |patient_id (FK) |
                        +-------+--------+
                                |
                                v
                        +-------+--------+
                        |   messages     |
                        |----------------|
                        |sender_id, body |
                        +----------------+


Shared (public) schema:
+----------+     +---------+     +--------------+     +----------+     +------------+
| tenants  |---->|  plans  |     | catalog_cie10|     |catalog_  |     |catalog_    |
|          |     |         |     |              |     |cups      |     |medications |
+----------+     +---------+     +--------------+     +----------+     +------------+
```

> **Detailed schema:** `infra/database-architecture.md` for full column definitions and all foreign key constraints

---

## 4. Permission Matrix (RBAC)

Five roles exist within each tenant. Permissions are encoded in JWT claims and enforced by FastAPI dependencies.

**Roles:**
- **clinic_owner** -- Clinic administrator with full access to all tenant data
- **doctor** -- Licensed dentist with full clinical access
- **assistant** -- Dental assistant working under doctor supervision
- **receptionist** -- Front desk staff handling scheduling, billing, and patient intake
- **patient** -- Patient portal access (read own data, limited actions)

### 4.1 Permission Legend

| Symbol | Meaning |
|--------|---------|
| C | Create |
| R | Read |
| U | Update |
| D | Delete |
| E | Export |
| CRUD | All four operations |
| CRUDE | All five operations |
| -- | No access |
| own | Only own records |

### 4.2 Authentication and Users

| Entity | clinic_owner | doctor | assistant | receptionist | patient |
|--------|-------------|--------|-----------|-------------|---------|
| `users` | CRUDE | R (own) | R (own) | R (all staff) | -- |
| `user_sessions` | R, D | R, D (own) | R, D (own) | R, D (own) | R, D (own) |
| `user_invites` | CRUD | -- | -- | -- | -- |

### 4.3 Patient Management

| Entity | clinic_owner | doctor | assistant | receptionist | patient |
|--------|-------------|--------|-----------|-------------|---------|
| `patients` | CRUDE | CRUDE | CRU | CRU | R (own) |
| `patient_documents` | CRUDE | CRUDE | CRU | CR | R (own) |

### 4.4 Odontogram

| Entity | clinic_owner | doctor | assistant | receptionist | patient |
|--------|-------------|--------|-----------|-------------|---------|
| `odontogram_states` | CRUD | CRUD | CRU | R | R (own) |
| `odontogram_conditions` | CRUD | CRUD | CRU | R | R (own) |
| `odontogram_history` | R | R | R | -- | R (own) |
| `odontogram_snapshots` | CRUDE | CRUDE | R | -- | R (own) |

### 4.5 Clinical Records

| Entity | clinic_owner | doctor | assistant | receptionist | patient |
|--------|-------------|--------|-----------|-------------|---------|
| `clinical_records` | CRUDE | CRUDE | CRU | -- | R (own) |
| `anamnesis` | CRUDE | CRUDE | CRU | R | R (own) |
| `diagnoses` | CRUDE | CRUD | R | -- | R (own) |
| `procedures` | CRUDE | CRUD | R | R | R (own) |

### 4.6 Treatment Plans

| Entity | clinic_owner | doctor | assistant | receptionist | patient |
|--------|-------------|--------|-----------|-------------|---------|
| `treatment_plans` | CRUDE | CRUD | R | R | R (own) |
| `treatment_plan_items` | CRUDE | CRUD | R | R | R (own) |

### 4.7 Consents

| Entity | clinic_owner | doctor | assistant | receptionist | patient |
|--------|-------------|--------|-----------|-------------|---------|
| `consent_templates` | CRUD | R | R | R | -- |
| `consents` | CRUDE | CR | CR | R | R (own), sign |

### 4.8 Appointments and Scheduling

| Entity | clinic_owner | doctor | assistant | receptionist | patient |
|--------|-------------|--------|-----------|-------------|---------|
| `appointments` | CRUDE | R, U (own) | CRUD | CRUD | R (own), C (request) |
| `appointment_reminders` | CRUD | R | R | CRU | -- |
| `doctor_schedules` | CRUD | RU (own) | R | R | R (public slots) |
| `availability_blocks` | CRUD | CRU (own) | R | R | -- |
| `waitlist` | CRUD | R | CRU | CRU | C (own), R (own) |

### 4.9 Billing and Payments

| Entity | clinic_owner | doctor | assistant | receptionist | patient |
|--------|-------------|--------|-----------|-------------|---------|
| `invoices` | CRUDE | R | R | CRUD | R (own) |
| `invoice_items` | CRUDE | R | R | CRUD | R (own) |
| `payments` | CRUDE | R | -- | CRU | R (own) |
| `payment_plans` | CRUDE | R | -- | CRU | R (own) |
| `payment_plan_installments` | CRUDE | R | -- | RU | R (own) |
| `service_catalog` | CRUDE | R | R | R | R |

### 4.10 Prescriptions

| Entity | clinic_owner | doctor | assistant | receptionist | patient |
|--------|-------------|--------|-----------|-------------|---------|
| `prescriptions` | CRUDE | CRUD | R | R | R (own) |
| `prescription_items` | CRUDE | CRUD | R | R | R (own) |

### 4.11 Communication

| Entity | clinic_owner | doctor | assistant | receptionist | patient |
|--------|-------------|--------|-----------|-------------|---------|
| `message_threads` | CRUD | CRU | CRU | CRU | CR (own) |
| `messages` | CRUD | CRU | CRU | CRU | CR (own) |
| `notifications` | CRUD | R (own), D (own) | R (own), D (own) | R (own), D (own) | R (own), D (own) |

### 4.12 System

| Entity | clinic_owner | doctor | assistant | receptionist | patient |
|--------|-------------|--------|-----------|-------------|---------|
| `audit_log` | R, E | R (own actions) | -- | -- | -- |
| `tenant_settings` | CRUD | R | R | R | -- |

> **Implementation details:** `infra/authentication-rules.md` (JWT claims, FastAPI dependencies, permission enforcement patterns)

---

## 5. API Architecture

### 5.1 Base Configuration

| Setting | Value |
|---------|-------|
| Base URL | `/api/v1/dentalos/` |
| Content type | `application/json` |
| Authentication | `Authorization: Bearer <access_token>` |
| Versioning | URL path (`v1`) |
| Pagination | Cursor-based (`?cursor=<token>&limit=20`) |
| Sorting | `?sort_by=<field>&sort_dir=asc|desc` |
| Error format | `{"error": "<CODE>", "message": "<human>", "details": {...}}` |

### 5.2 Endpoint Namespace Summary

Total estimated endpoints: **~172**

| # | Namespace | Prefix | Endpoints | Description |
|---|-----------|--------|-----------|-------------|
| 1 | Auth | `/auth/` | ~12 | Login, logout, refresh, password reset, invite accept |
| 2 | Tenants | `/tenants/` | ~8 | Tenant registration, settings, onboarding (owner only) |
| 3 | Users | `/users/` | ~10 | Staff CRUD, invite, role management, profile |
| 4 | Patients | `/patients/` | ~14 | Patient CRUD, search, documents, merge, export |
| 5 | Odontogram | `/odontogram/` | ~12 | Tooth states, conditions, history, snapshots |
| 6 | Clinical Records | `/clinical-records/` | ~14 | SOAP records, anamnesis, diagnoses, procedures |
| 7 | Treatment Plans | `/treatment-plans/` | ~10 | Plan CRUD, items, status workflow, PDF export |
| 8 | Consents | `/consents/` | ~8 | Templates CRUD, consent creation, signing, PDF |
| 9 | Appointments | `/appointments/` | ~18 | Booking, reschedule, cancel, slots, schedules, waitlist |
| 10 | Billing | `/billing/` | ~16 | Invoices, payments, payment plans, service catalog |
| 11 | Notifications | `/notifications/` | ~6 | List, mark read, preferences |
| 12 | Messages | `/messages/` | ~8 | Threads, send, read status |
| 13 | Prescriptions | `/prescriptions/` | ~8 | CRUD, items, PDF generation |
| 14 | Analytics | `/analytics/` | ~10 | Dashboard stats, revenue, appointments, patient flow |
| 15 | Admin | `/admin/` | ~8 | Superadmin: tenant management, platform metrics |
| 16 | Portal | `/portal/` | ~14 | Patient-facing: own records, appointments, consents, messages |
| 17 | Compliance | `/compliance/` | ~6 | RIPS export, audit log queries, data retention |

> **Detailed endpoints:** Each domain has its own spec (e.g., `patients/patients-api.md`, `appointments/appointments-api.md`).
> **Versioning conventions:** `API-VERSIONING-CONVENTIONS.md`

---

## 6. Authentication Architecture Summary

DentalOS uses **JWT-based stateless authentication** with a dual-token scheme.

### 6.1 Token Configuration

| Property | Access Token | Refresh Token |
|----------|-------------|---------------|
| Format | JWT (RS256 signed) | Opaque UUID v4 |
| TTL | 15 minutes | 30 days |
| Storage | Client memory (JS variable) | HttpOnly secure cookie + DB |
| Rotation | New pair on each refresh | Single-use (rotate on use) |
| Revocation | Blacklist in Redis (JTI) | Delete from DB |

### 6.2 JWT Claims

```json
{
  "sub": "usr_{user_id}",
  "tid": "tn_{tenant_id}",
  "role": "doctor",
  "perms": ["patients:read", "patients:write", "odontogram:write", "clinical_records:write"],
  "email": "doctor@clinica.co",
  "name": "Dr. Maria Rodriguez",
  "iat": 1708790400,
  "exp": 1708791300,
  "iss": "dentalos",
  "aud": "dentalos-api",
  "jti": "tok_{unique_id}"
}
```

### 6.3 FastAPI Dependency Chain

```python
# Simplified dependency chain (pseudocode)
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Validate JWT, extract claims, return user context."""

async def require_role(*roles: str) -> Callable:
    """Factory: returns dependency that checks user.role is in allowed roles."""

async def resolve_tenant(user: User = Depends(get_current_user)) -> TenantContext:
    """Resolve tenant schema from user.tid, set search_path."""

async def require_permission(permission: str) -> Callable:
    """Factory: checks specific permission in user.perms array."""
```

### 6.4 Patient Portal Authentication

Patient portal uses the same JWT system but with:
- Audience claim: `"dentalos-portal"` (vs `"dentalos-api"` for staff)
- Separate login endpoint: `/api/v1/dentalos/portal/auth/login`
- Magic link or PIN-based auth (no password by default)
- Permissions restricted to `own` records only

> **Full specification:** `infra/authentication-rules.md`

---

## 7. Multi-Tenancy Architecture Summary

DentalOS uses **PostgreSQL schema-per-tenant** isolation. Each dental clinic is a tenant with its own PostgreSQL schema containing identical table structures.

### 7.1 Schema Layout

| Schema | Purpose | Example |
|--------|---------|---------|
| `public` | Shared global data (tenants, plans, catalogs) | `public.tenants` |
| `tn_{tenant_id_short}` | Tenant-specific data (first 12 chars of UUID) | `tn_a1b2c3d4e5f6.patients` |

### 7.2 Tenant Resolution Flow

```
Request with JWT
  -> Extract tid claim from access token
  -> Check Redis cache: key "tenant:{tid}:schema" (TTL 5min)
     -> HIT:  return cached schema_name
     -> MISS: SELECT schema_name FROM public.tenants WHERE id = :tid AND status = 'active'
              -> Cache result in Redis
  -> Execute: SET search_path TO tn_{schema_name}, public;
  -> All subsequent queries in this request use the tenant schema
```

### 7.3 Isolation Guarantees

- **Structural:** `search_path` ensures queries cannot reference other tenant schemas
- **Connection-level:** Each request sets its own search_path; no shared state between requests
- **Cache-level:** All Redis keys are prefixed with `tn:{tenant_id}:` to prevent cross-tenant cache reads
- **Queue-level:** RabbitMQ messages include `tenant_id` in headers; workers set search_path before processing
- **Storage-level:** S3 paths use `/{tenant_id}/` prefix for file isolation

### 7.4 Provisioning

When a new clinic signs up:

1. Insert row into `public.tenants` with status `provisioning`
2. Create schema: `CREATE SCHEMA tn_{short_id}`
3. Run all Alembic migrations against new schema
4. Seed default data (consent templates, service catalog)
5. Create owner user account in tenant schema
6. Update tenant status to `active`
7. Invalidate Redis cache

> **Full specification:** `infra/multi-tenancy.md`, `infra/database-architecture.md`

---

## 8. External Integrations

### 8.1 Integration Map

| Integration | Protocol | Purpose | Sprint |
|-------------|----------|---------|--------|
| **WhatsApp Business API** | REST / Webhooks | Appointment reminders, confirmations, post-treatment instructions | Sprint 10 |
| **DIAN** (Colombia) | REST / SOAP | Electronic invoicing (facturacion electronica) for Colombian tax authority | Sprint 15 |
| **SAT / CFDI** (Mexico) | REST via PAC provider | Electronic invoicing (CFDI) for Mexican tax authority | Sprint 17 |
| **SII / DTE** (Chile) | REST / SOAP | Electronic invoicing (DTE) for Chilean tax authority | Sprint 18 |
| **SMTP Provider** | SMTP / REST API | Transactional email: invites, password reset, appointment confirmations, invoices | Sprint 3 |
| **S3-Compatible Storage** | S3 API | File uploads: X-rays, intraoral photos, consent PDFs, clinical documents | Sprint 4 |

### 8.2 Integration Architecture Pattern

All external integrations follow the same adapter pattern:

```
FastAPI Route Handler
  -> Publish message to RabbitMQ (async, non-blocking)
  -> Worker picks up message
     -> Resolve integration adapter based on tenant.country
     -> Execute API call with retry logic (exponential backoff)
     -> Log result to audit_log
     -> Update entity status (e.g., reminder.status = 'sent')
     -> On failure: dead letter queue after 3 retries
```

### 8.3 Country-Specific Adapters

E-invoicing uses a pluggable adapter pattern. Each country registers an adapter that implements the `InvoicingAdapter` interface:

```python
class InvoicingAdapter(Protocol):
    async def generate_invoice(self, invoice: Invoice) -> ExternalInvoiceResult: ...
    async def cancel_invoice(self, external_id: str) -> bool: ...
    async def get_status(self, external_id: str) -> InvoiceStatus: ...
```

Active adapters: `CODianAdapter`, `MXSatAdapter`, `CLSiiAdapter`

> **ADR:** `infra/adr/007-country-compliance-adapters.md`

---

## 9. Performance Targets

These are the p95 latency targets that the system must meet under normal load (20 concurrent users per tenant).

### 9.1 API Response Latency (p95)

| Operation Category | Target | Notes |
|--------------------|--------|-------|
| **Read endpoints** (GET) | < 200ms | Includes cache lookup |
| **Write endpoints** (POST/PUT/PATCH) | < 500ms | Includes DB write + cache invalidation |
| **Delete endpoints** (DELETE) | < 300ms | Soft delete only |
| **Search** (patients, CIE-10, CUPS) | < 300ms | Full-text search with trigram indexes |
| **Odontogram load** (cached) | < 100ms | Full odontogram from Redis |
| **Odontogram load** (cold) | < 300ms | Full odontogram from PostgreSQL + cache write |
| **Appointment slot calculation** | < 200ms | Compute available slots for a date range |
| **Analytics dashboard** | < 1000ms | Aggregation queries with materialized views |
| **PDF generation** (prescription, invoice) | < 3000ms | Async via RabbitMQ, returns job ID |

### 9.2 Throughput Targets

| Metric | Target |
|--------|--------|
| Concurrent users per tenant | 20+ |
| Total concurrent platform users | 2,000+ |
| Requests per second (platform) | 500+ |
| Background jobs per minute | 200+ |
| Max tenants per database instance | 2,000 |

### 9.3 Availability

| Metric | Target |
|--------|--------|
| Uptime SLA | 99.9% (8.7h downtime/year) |
| Recovery Time Objective (RTO) | < 1 hour |
| Recovery Point Objective (RPO) | < 5 minutes |
| Deployment downtime | Zero (blue-green) |

> **Caching strategy:** `infra/caching-strategy.md`
> **Database optimization:** `infra/database-architecture.md` (indexes, connection pooling)

---

## 10. Infrastructure References

Complete table of all infrastructure specs with their IDs and descriptions.

| Spec ID | File | Description |
|---------|------|-------------|
| I-01 | `infra/multi-tenancy.md` | Schema-per-tenant architecture, tenant provisioning, isolation guarantees, plan enforcement |
| I-02 | `infra/authentication-rules.md` | JWT RS256 auth, RBAC, token lifecycle, password policy, invite flow, patient portal auth |
| I-03 | `infra/error-handling.md` | Error response format, HTTP status codes, error code registry, exception handling patterns |
| I-04 | `infra/database-architecture.md` | Complete DDL (41 tables), schema design, Alembic migrations, connection pooling, backups |
| I-05 | `infra/caching-strategy.md` | Redis architecture, tenant-namespaced keys, TTL policies, cache invalidation, warming |
| I-06 | `infra/background-processing.md` | RabbitMQ queues, worker topology, task types, retry policies, dead letter exchanges |
| I-07 | `infra/rate-limiting.md` | Sliding window rate limits, per-user/IP/tenant, plan-based limits, endpoint overrides |
| I-08 | `infra/testing-setup.md` | pytest config, factory patterns, fixtures, mocking, CI/CD pipeline, coverage targets |
| I-09 | `infra/local-development.md` | Docker Compose stack, dev servers, seed data, environment variables, developer tooling |
| I-10 | `infra/security-policy.md` | TLS, CORS, CSP, input validation, SQL injection prevention, PHI handling, file upload security |
| I-11 | `infra/audit-logging.md` | Immutable audit trail, clinical data access logging, healthcare compliance (Res. 1995/1999) |
| I-12 | `infra/data-retention-policy.md` | Clinical record retention (15yr CO), right to deletion vs retention, tenant cancellation |
| I-13 | `infra/hipaa-latam-compliance.md` | Country compliance adapters (CO, MX, CL, AR, PE), regulatory validation engine |
| I-14 | `infra/deployment-architecture.md` | Hetzner Cloud topology, Docker, CI/CD (GitHub Actions), blue-green deploys, rollback |
| I-15 | `infra/monitoring-observability.md` | Structured logging, APM, health checks, Sentry error tracking, custom metrics |
| I-16 | `infra/backup-disaster-recovery.md` | PostgreSQL WAL archiving, PITR, cross-region backup, RTO/RPO, DR runbook |
| I-17 | `infra/file-storage.md` | S3-compatible object storage, tenant-isolated paths, virus scanning, signed URLs |
| I-28 | `infra/design-system.md` | Color palette, typography, spacing, component library, dental-specific UI components |

> **ADR index:** `ADR-LOG.md`
> **Full master index:** `DENTALOS-SDD-MASTER-INDEX.md`

---

## 11. Sprint Roadmap Summary

### Phase 1: Foundation (Sprint 1-4 / Month 1-2) -- Priority: Critical

| Sprint | Focus | Key Deliverables |
|--------|-------|-----------------|
| **Sprint 1** | Infrastructure | Multi-tenant schema, PostgreSQL setup, Redis, RabbitMQ, Docker Compose, CI/CD |
| **Sprint 2** | Authentication | JWT auth, login/logout/refresh, RBAC middleware, invite flow, password reset |
| **Sprint 3** | Patient Management | Patient CRUD, search, document uploads, transactional email setup |
| **Sprint 4** | Design System | TailwindCSS config, component library, layout shells, responsive framework |

### Phase 2: Clinical Core (Sprint 5-8 / Month 3-4) -- Priority: High

| Sprint | Focus | Key Deliverables |
|--------|-------|-----------------|
| **Sprint 5** | Odontogram | SVG-based interactive odontogram, tooth states, conditions, history tracking |
| **Sprint 6** | Clinical Records | SOAP notes, anamnesis, CIE-10 diagnosis search, procedure logging |
| **Sprint 7** | CUPS Integration | Procedure catalog (CUPS codes), treatment plan creation, plan status workflow |
| **Sprint 8** | Treatment Plans | Treatment plan items, cost estimation, PDF export, patient approval flow |

### Phase 3: Operations (Sprint 9-12 / Month 5-6) -- Priority: Medium

| Sprint | Focus | Key Deliverables |
|--------|-------|-----------------|
| **Sprint 9** | Appointments | Scheduling engine, doctor availability, slot calculation, booking workflow |
| **Sprint 10** | Notifications | WhatsApp Business integration, appointment reminders, notification preferences |
| **Sprint 11** | Patient Portal | Portal auth (magic link), own records view, appointment requests, consent signing |
| **Sprint 12** | Basic Billing | Invoice generation, payment recording, service catalog, payment plans |

### Phase 4: Compliance and Launch (Sprint 13-20 / Month 7-10) -- Priority: Low

| Sprint | Focus | Key Deliverables |
|--------|-------|-----------------|
| **Sprint 13** | Prescriptions | Prescription CRUD, medication catalog, PDF generation, digital signature |
| **Sprint 14** | Messaging | Clinic-patient messaging threads, read receipts, notification integration |
| **Sprint 15** | Colombia Compliance | RIPS export, DIAN e-invoicing, Res. 1995 audit compliance validation |
| **Sprint 16** | Analytics | Dashboard KPIs, revenue reports, appointment analytics, patient flow metrics |
| **Sprint 17** | Mexico Expansion | SAT/CFDI e-invoicing adapter, Mexican regulatory requirements |
| **Sprint 18** | Chile Expansion | SII/DTE e-invoicing adapter, Chilean regulatory requirements |
| **Sprint 19** | Offline Support | Service Workers, IndexedDB sync, conflict resolution, offline odontogram |
| **Sprint 20** | Beta Launch | Performance testing, security audit, beta onboarding, production deployment |

> **Detailed backlogs:** `M2-BACKLOG.md` (Sprint 5-8), `M3-BACKLOG.md` (Sprint 9-12), `M4-BACKLOG.md` (Sprint 13-16), `M5-BACKLOG.md` (Sprint 17-20)

---

## 12. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-24 | DentalOS Team | Initial master technical specification |

---

*This document is the primary technical reference for DentalOS. For implementation details, always consult the domain-specific specs linked throughout this document. The complete spec index is maintained in `DENTALOS-SDD-MASTER-INDEX.md`.*
