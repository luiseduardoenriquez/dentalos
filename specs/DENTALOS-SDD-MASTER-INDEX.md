# DentalOS -- SDD Master Index (Spec-Driven Development)

## Overview

This document is the **complete master index** of every specification required to build DentalOS, a cloud-native multi-tenant SaaS platform for dental practices in Latin America.

**Product:** DentalOS
**Tech Stack:** React/Next.js + TailwindCSS (Frontend) | Python + FastAPI (Backend) | PostgreSQL schema-per-tenant | Redis | RabbitMQ | Hetzner Cloud
**Target Market:** Dental practices in LATAM (Colombia first, then Mexico, Chile, Argentina, Peru)
**Date:** 2026-02-24
**Version:** 1.1

---

## Business Model

| Plan | Price | Limits | Notes |
|------|-------|--------|-------|
| Free | $0/mo | 50 patients, 1 doctor | Forever free tier |
| Starter | $19/doctor/mo | Unlimited patients | Small practice |
| Pro | $39/doctor/mo | Unlimited patients | Growing practice |
| Clinica | $69/location/mo | Includes 3 doctors; +$15/additional doctor | Multi-doctor clinic |
| Enterprise | Custom | Custom | Large groups, chains |

### Add-ons
| Add-on | Price | Description |
|--------|-------|-------------|
| AI Voice-to-Chart | $10/doctor/mo | Voice dictation to odontogram and clinical records |
| AI Radiograph Analysis | $20/doctor/mo | AI-assisted X-ray reading |
| Telehealth | $15/mo | Video consultation module |
| Marketing | $15/mo | Automated patient reactivation campaigns |

---

## Priority Legend

| Priority | Sprint Range | Timeframe | Description |
|----------|-------------|-----------|-------------|
| **Critical** | Sprint 1-4 | Month 1-2 | Foundation: multi-tenant arch, auth, patient CRUD, design system |
| **High** | Sprint 5-8 | Month 3-4 | Core clinical: odontogram, clinical records, CIE-10/CUPS |
| **Medium** | Sprint 9-12 | Month 5-6 | Operations: agenda, WhatsApp, patient portal, basic billing |
| **Low** | Sprint 13-20 | Month 7-10 | Compliance, offline, electronic invoicing, beta, launch |

---

## Dependency Notation

- `->` means "depends on"
- Specs without dependencies can be developed in parallel
- Infrastructure specs are global prerequisites

---

# SECTION 1: ROOT-LEVEL DOCUMENTS

These are master documents that govern the entire project.

| # | File Path | Description | Priority |
|---|-----------|-------------|----------|
| R-01 | `SPEC_TEMPLATE.md` | Backend API spec template adapted for FastAPI + PostgreSQL. All backend specs follow this format. | Critical |
| R-02 | `FRONTEND_SPEC_TEMPLATE.md` | Frontend screen/component spec template for Next.js + TailwindCSS. All frontend specs follow this format. | Critical |
| R-03 | `M1-TECHNICAL-SPEC.md` | Complete data model documentation: all entities, schemas, relationships, permissions matrix, indexes, cache strategy. PostgreSQL schema-per-tenant design. | Critical |
| R-04 | `M1-NAVIGATION-MAP.md` | User flows and screen map for all roles (clinic owner, doctor, assistant, receptionist, patient). Route definitions, state machines, flow diagrams. | Critical |
| R-05 | `IMPLEMENTATION-CHECKLIST.md` | Sprint-by-sprint implementation checklist with acceptance criteria, test counts, dependency tracking. Living document updated throughout development. | Critical |
| R-06 | `M2-BACKLOG.md` | Prioritized backlog for Sprint 5-8 (clinical features). Task breakdown, estimates, acceptance criteria. | High |
| R-07 | `M3-BACKLOG.md` | Prioritized backlog for Sprint 9-12 (operations features). | Medium |
| R-08 | `M4-BACKLOG.md` | Prioritized backlog for Sprint 13-16 (compliance, offline). | Low |
| R-09 | `M5-BACKLOG.md` | Prioritized backlog for Sprint 17-20 (beta, launch). | Low |
| R-10 | `ADR-LOG.md` | Architecture Decision Records index. Links to individual ADRs in `infra/adr/`. | Critical |
| R-11 | `DOMAIN-GLOSSARY.md` | Dental domain glossary: CIE-10, CUPS, RDA, RIPS, odontogram terminology, tooth numbering systems (FDI, Universal, Palmer), clinical condition codes. Spanish/English. | Critical |
| R-12 | `API-VERSIONING-CONVENTIONS.md` | API path conventions, versioning strategy, naming rules for DentalOS (`/api/v1/dentalos/...`). | Critical |

---

# SECTION 2: INFRASTRUCTURE SPECS (`infra/`)

Cross-cutting concerns that apply to all features.

## 2.1 Core Architecture

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| I-01 | `infra/multi-tenancy.md` | **Schema-per-tenant architecture.** Tenant provisioning, schema creation, migration strategy, connection pooling, tenant resolution from request (subdomain/header), tenant isolation guarantees, shared vs tenant-specific tables, plan enforcement at DB level. | Critical | None |
| I-02 | `infra/authentication-rules.md` | **Global authentication and authorization rules.** JWT-based auth with FastAPI, access token (15min) + refresh token (30d), token rotation, RBAC roles (clinic_owner, doctor, assistant, receptionist, patient, superadmin), permission matrix, multi-tenant auth context. | Critical | I-01 |
| I-03 | `infra/error-handling.md` | **Global error handling strategy.** HTTP status codes, error response schema `{error, message, details}`, error codes registry, backend exception handling (Python/FastAPI), frontend error handling (React Query), logging patterns, security constraints. | Critical | None |
| I-04 | `infra/database-architecture.md` | **PostgreSQL architecture.** Schema-per-tenant implementation, shared `public` schema (tenants, plans, superadmin), tenant schema template, migration runner (Alembic per-tenant), connection pool (pgbouncer), read replicas, backup strategy. | Critical | I-01 |
| I-05 | `infra/caching-strategy.md` | **Redis caching strategy.** Cache key namespacing per tenant, TTL policies, cache invalidation rules, session cache, odontogram state cache, appointment slot cache, plan limits cache. | Critical | I-01 |
| I-06 | `infra/background-processing.md` | **RabbitMQ task queue architecture.** Queue topology, worker processes, task types (email, SMS, WhatsApp, RIPS generation, invoice generation, audit log writes), retry policies, dead letter queues, priority queues. | Critical | None |
| I-07 | `infra/rate-limiting.md` | **Rate limiting rules.** Per-tenant, per-user, per-IP limits. Endpoint-specific overrides. Redis-based implementation. Plan-based rate limits (free tier stricter). | Critical | I-01, I-05 |
| I-08 | `infra/testing-setup.md` | **Testing infrastructure.** pytest setup, test database per tenant, factory patterns (patients, teeth, appointments), mocking external services (WhatsApp, SMS, invoicing), CI/CD test pipeline, coverage targets. | Critical | None |
| I-09 | `infra/local-development.md` | **Local development environment.** Docker Compose stack (PostgreSQL, Redis, RabbitMQ), FastAPI dev server, Next.js dev server, seed data, tenant provisioning script, environment variables. | Critical | I-04, I-05, I-06 |

## 2.2 Security and Compliance

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| I-10 | `infra/security-policy.md` | **Security policy.** HTTPS enforcement, CORS configuration, CSP headers, input sanitization (Python), SQL injection prevention (SQLAlchemy), XSS prevention, CSRF tokens, file upload validation, PHI (Protected Health Information) handling, encryption at rest and in transit. | Critical | None |
| I-11 | `infra/audit-logging.md` | **Healthcare audit logging.** Every clinical data read/write logged. Immutable audit trail per tenant. Fields: who, what, when, where (IP), action, resource, old_value, new_value. Required for RDA compliance. Separate audit schema. | Critical | I-01 |
| I-12 | `infra/data-retention-policy.md` | **Data retention and deletion rules.** Clinical records retention (15 years Colombia, varies by country), patient data deletion (right to be forgotten vs clinical retention mandate), tenant data lifecycle on cancellation. | High | I-11 |
| I-13 | `infra/hipaa-latam-compliance.md` | **Regulatory compliance engine architecture.** Country adapter pattern: each country (CO, MX, CL, AR, PE) has a compliance adapter. Adapter interface defines required validations, document formats, code systems. Pluggable per tenant setting. | High | I-01 |

## 2.3 Infrastructure and DevOps

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| I-14 | `infra/deployment-architecture.md` | **Hetzner Cloud deployment.** VPS topology, load balancer, PostgreSQL managed DB, Redis instance, RabbitMQ cluster, Docker containers, CI/CD pipeline (GitHub Actions), blue-green deployments, rollback strategy. | Critical | None |
| I-15 | `infra/monitoring-observability.md` | **Monitoring and observability.** Structured logging (JSON), log aggregation, APM (application performance monitoring), health checks, uptime monitoring, error tracking (Sentry), custom metrics (tenant count, active users, appointments/day). | High | I-14 |
| I-16 | `infra/backup-disaster-recovery.md` | **Backup and disaster recovery.** PostgreSQL WAL archiving, point-in-time recovery, cross-region backup, RTO/RPO targets, disaster recovery runbook. Critical for healthcare data. | High | I-04 |
| I-17 | `infra/file-storage.md` | **File storage architecture.** S3-compatible object storage (Hetzner/MinIO). Tenant-isolated buckets. File types: X-rays, intraoral photos, consent form PDFs, clinical documents, profile photos. Virus scanning, size limits, allowed MIME types, signed URLs for access. | High | I-01 |

## 2.4 Offline and Sync

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| I-18 | `infra/offline-sync-strategy.md` | **Offline-first architecture.** Service Workers, IndexedDB schema, sync queue, conflict resolution (last-write-wins vs merge), priority sync (clinical data first), bandwidth-aware sync, sync status indicators. Critical for clinics with unreliable internet. | Low | I-01 |
| I-19 | `infra/pwa-configuration.md` | **PWA setup.** Service worker registration, manifest.json, offline fallback pages, cache strategies (cache-first for static, network-first for API), push notification setup. | Low | I-18 |

## 2.5 Architecture Decision Records

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| I-20 | `infra/adr/001-schema-per-tenant.md` | ADR: Why schema-per-tenant over row-level isolation. | Critical | None |
| I-21 | `infra/adr/002-fastapi-over-django.md` | ADR: Why FastAPI over Django for the backend. | Critical | None |
| I-22 | `infra/adr/003-postgresql-over-alternatives.md` | ADR: Why PostgreSQL (not MongoDB, MySQL). | Critical | None |
| I-23 | `infra/adr/004-hetzner-over-aws.md` | ADR: Why Hetzner Cloud over AWS/GCP for LATAM SaaS. | Critical | None |
| I-24 | `infra/adr/005-odontogram-svg-architecture.md` | ADR: SVG-based odontogram rendering approach. | High | None |
| I-25 | `infra/adr/006-offline-sync-strategy.md` | ADR: Offline sync approach (Service Workers + IndexedDB). | Low | None |
| I-26 | `infra/adr/007-country-compliance-adapters.md` | ADR: Plugin/adapter pattern for multi-country compliance. | High | None |
| I-27 | `infra/adr/008-rabbitmq-over-celery-redis.md` | ADR: Why RabbitMQ over Celery+Redis for task queuing. | Critical | None |

## 2.6 Design System

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| I-28 | `infra/design-system.md` | **DentalOS Design System.** Color palette (dental/medical theme), typography scale, spacing system, component library (buttons, inputs, cards, modals, tables, toasts), icon set, dental-specific components (tooth selector, condition badges, status pills). TailwindCSS configuration. | Critical | None |
| I-29 | `infra/responsive-breakpoints.md` | **Responsive design rules.** Breakpoints, mobile-first approach, tablet optimization for clinical use (many dentists use tablets), touch target sizes, dental chart responsive behavior. | Critical | I-28 |

---

# SECTION 3: BACKEND API SPECS (by domain)

## 3.1 Tenant Management (`tenants/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| T-01 | `tenants/tenant-provision.md` | `POST /api/v1/superadmin/tenants` -- Create new tenant. Provisions PostgreSQL schema, creates admin user, sets default configuration, assigns plan. Superadmin only. | Critical | I-01, I-04 |
| T-02 | `tenants/tenant-get.md` | `GET /api/v1/superadmin/tenants/{tenant_id}` -- Get tenant details. Schema info, plan, usage stats, active users. Superadmin only. | Critical | T-01 |
| T-03 | `tenants/tenant-list.md` | `GET /api/v1/superadmin/tenants` -- List all tenants with pagination, filters (plan, status, country). Superadmin only. | Critical | T-01 |
| T-04 | `tenants/tenant-update.md` | `PUT /api/v1/superadmin/tenants/{tenant_id}` -- Update tenant settings: plan, status (active/suspended/cancelled), country, max_doctors, max_patients. Superadmin only. | Critical | T-01 |
| T-05 | `tenants/tenant-suspend.md` | `POST /api/v1/superadmin/tenants/{tenant_id}/suspend` -- Suspend tenant. Blocks all API access except read-only for data export. Superadmin only. | High | T-01 |
| T-06 | `tenants/tenant-settings-get.md` | `GET /api/v1/settings` -- Get current tenant settings. Odontogram mode (classic/anatomic), country, plan level, enabled features, branding. Authenticated (clinic_owner). | Critical | T-01 |
| T-07 | `tenants/tenant-settings-update.md` | `PUT /api/v1/settings` -- Update tenant settings. Clinic name, address, phone, logo, odontogram mode preference, notification preferences. Clinic_owner only. | Critical | T-06 |
| T-08 | `tenants/tenant-usage-stats.md` | `GET /api/v1/settings/usage` -- Get current plan usage. Patient count, doctor count, storage used, appointments this month. For plan limit enforcement and upgrade prompts. | Critical | T-01 |
| T-09 | `tenants/plan-limits-check.md` | `GET /api/v1/settings/plan-limits` -- Check if tenant can perform action (add patient, add doctor). Returns allowed/blocked with upgrade prompt data. Internal use by other services. | Critical | T-01, T-08 |
| T-10 | `tenants/tenant-onboarding.md` | `POST /api/v1/onboarding` -- Multi-step onboarding wizard data. Step 1: clinic info. Step 2: first doctor. Step 3: configure odontogram. Step 4: import patients (optional). Updates tenant settings progressively. | Critical | T-06, T-07 |

## 3.2 Authentication (`auth/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| A-01 | `auth/register.md` | `POST /api/v1/auth/register` -- Register new clinic (creates tenant + first user as clinic_owner). Collects: email, password, name, clinic_name, country, phone. Creates tenant schema, provisions admin user. Rate limited: 3/hour per IP. | Critical | I-01, I-02, T-01 |
| A-02 | `auth/login.md` | `POST /api/v1/auth/login` -- Login with email + password. Resolves tenant from email, validates credentials, returns JWT access token + refresh token. Rate limited: 5/15min per IP. | Critical | I-02 |
| A-03 | `auth/refresh-token.md` | `POST /api/v1/auth/refresh-token` -- Rotate access + refresh tokens. Single-use refresh tokens, replay detection, revocation on reuse. | Critical | I-02 |
| A-04 | `auth/me.md` | `GET /api/v1/auth/me` -- Get current user profile with tenant context. Returns user data, role, tenant info, plan level, active permissions. | Critical | I-02 |
| A-05 | `auth/forgot-password.md` | `POST /api/v1/auth/forgot-password` -- Send password reset email. Rate limited: 3/hour per IP. Does not reveal if email exists. | Critical | I-02 |
| A-06 | `auth/reset-password.md` | `POST /api/v1/auth/reset-password` -- Reset password via token. Validates token, updates password, revokes all refresh tokens. | Critical | A-05 |
| A-07 | `auth/change-password.md` | `POST /api/v1/auth/change-password` -- Change password (authenticated). Requires current password. Revokes other sessions. | Critical | I-02 |
| A-08 | `auth/logout.md` | `POST /api/v1/auth/logout` -- Revoke refresh token, clear session. | Critical | I-02 |
| A-09 | `auth/invite-user.md` | `POST /api/v1/auth/invite` -- Invite user to tenant. Clinic_owner or admin sends invite email with role assignment (doctor, assistant, receptionist). Creates pending user record. | Critical | I-02, A-01 |
| A-10 | `auth/accept-invite.md` | `POST /api/v1/auth/accept-invite` -- Accept invitation. Set password, complete profile. Activates user in tenant. | Critical | A-09 |
| A-11 | `auth/verify-email.md` | `POST /api/v1/auth/verify-email` -- Verify email address via token sent during registration. | High | A-01 |

## 3.3 User Management (`users/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| U-01 | `users/get-profile.md` | `GET /api/v1/users/me` -- Get own profile. Full user data including role, specialties (for doctors), working hours, notification preferences. | Critical | I-02 |
| U-02 | `users/update-profile.md` | `PUT /api/v1/users/me` -- Update own profile. Name, phone, avatar, professional license number (for doctors), specialties. | Critical | U-01 |
| U-03 | `users/list-team.md` | `GET /api/v1/users` -- List all users in tenant. Filterable by role, status (active/inactive/pending). Clinic_owner and admin only. | Critical | I-02 |
| U-04 | `users/get-team-member.md` | `GET /api/v1/users/{user_id}` -- Get specific team member profile. Clinic_owner and admin only. | Critical | U-03 |
| U-05 | `users/update-team-member.md` | `PUT /api/v1/users/{user_id}` -- Update team member. Change role, deactivate account. Clinic_owner only (cannot modify own role). | Critical | U-04 |
| U-06 | `users/deactivate-user.md` | `POST /api/v1/users/{user_id}/deactivate` -- Deactivate team member. Soft delete. Preserves clinical records for audit. Clinic_owner only. | High | U-05 |
| U-07 | `users/doctor-schedule-get.md` | `GET /api/v1/users/{user_id}/schedule` -- Get doctor's working schedule (weekly template). Used by appointment booking. | Medium | U-01 |
| U-08 | `users/doctor-schedule-update.md` | `PUT /api/v1/users/{user_id}/schedule` -- Set doctor's weekly schedule. Day-of-week, start/end times, break times, appointment duration defaults. | Medium | U-07 |
| U-09 | `users/notification-preferences.md` | `PUT /api/v1/users/me/notifications` -- Update notification preferences. Email, SMS, WhatsApp, in-app toggles per event type (appointment reminder, new patient, etc.). | Medium | U-01 |

## 3.4 Patient Management (`patients/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| P-01 | `patients/patient-create.md` | `POST /api/v1/patients` -- Create patient. Fields: name, ID document (cedula/CURP/RUT), birthdate, gender, phone, email, address, emergency contact, health insurance, allergies, medical conditions. Plan limit check. | Critical | I-01, T-09 |
| P-02 | `patients/patient-get.md` | `GET /api/v1/patients/{patient_id}` -- Get patient full profile. Includes basic info, medical summary, last visit date, active treatment plans count, balance. | Critical | P-01 |
| P-03 | `patients/patient-list.md` | `GET /api/v1/patients` -- List patients with search, pagination, filters (active/inactive, date range, doctor, has_balance). Full-text search on name, document, phone, email. | Critical | P-01 |
| P-04 | `patients/patient-update.md` | `PUT /api/v1/patients/{patient_id}` -- Update patient profile. All fields from create except ID document (immutable after creation). | Critical | P-02 |
| P-05 | `patients/patient-deactivate.md` | `POST /api/v1/patients/{patient_id}/deactivate` -- Soft-delete patient. Clinical records preserved. Can be reactivated. | High | P-02 |
| P-06 | `patients/patient-search.md` | `GET /api/v1/patients/search` -- Quick search endpoint. Optimized for typeahead. Searches name, document number, phone. Returns minimal data (id, name, document, phone, avatar). Max 10 results. | Critical | P-01 |
| P-07 | `patients/patient-medical-history.md` | `GET /api/v1/patients/{patient_id}/medical-history` -- Full medical history timeline. Ordered list of all clinical events: appointments, diagnoses, treatments, odontogram changes, prescriptions, X-rays. Paginated. | High | P-01, CR-01, OD-01 |
| P-08 | `patients/patient-import.md` | `POST /api/v1/patients/import` -- Bulk import patients from CSV/Excel. Validation, duplicate detection (by document number), error report. Async processing via queue. | High | P-01, I-06 |
| P-09 | `patients/patient-export.md` | `GET /api/v1/patients/export` -- Export patient list to CSV. Filtered by same params as list. Streaming response. | High | P-03 |
| P-10 | `patients/patient-merge.md` | `POST /api/v1/patients/merge` -- Merge duplicate patient records. Clinic_owner only. Preserves all clinical data from both records under primary patient. Audit logged. | Low | P-01, I-11 |
| P-11 | `patients/patient-portal-access.md` | `POST /api/v1/patients/{patient_id}/portal-access` -- Grant/revoke patient portal access. Sends invitation email/WhatsApp with registration link. | Medium | P-01, A-09 |
| P-12 | `patients/patient-documents.md` | `GET /api/v1/patients/{patient_id}/documents` -- List all documents for patient (X-rays, consent forms, lab results, referrals). Filterable by type, date. | High | P-01, I-17 |
| P-13 | `patients/patient-document-upload.md` | `POST /api/v1/patients/{patient_id}/documents` -- Upload document for patient. Type (xray, consent, lab_result, referral, other), file (image/pdf), description, date. Stored in tenant-isolated bucket. | High | I-17 |
| P-14 | `patients/patient-document-delete.md` | `DELETE /api/v1/patients/{patient_id}/documents/{doc_id}` -- Delete patient document. Audit logged. Clinic_owner and doctor only. | High | P-12 |
| P-15 | `patients/patient-referral.md` | `POST /api/v1/patients/{patient_id}/referrals` -- Create inter-specialist referral within clinic. From doctor_id to doctor_id, reason, priority, notes. Both doctors sign their procedures. | Medium | P-01, U-03 |
| P-16 | `patients/patient-photo-tooth.md` | `POST /api/v1/patients/{patient_id}/odontogram/teeth/{tooth_number}/photos` -- Attach intraoral photo to specific tooth. Quick upload from camera (2 taps). Links to tooth in odontogram. | High | OD-10, I-17 |

## 3.5 Odontogram (`odontogram/`)

This is the **core differentiator** of DentalOS.

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| OD-01 | `odontogram/odontogram-get.md` | `GET /api/v1/patients/{patient_id}/odontogram` -- Get current odontogram state. Returns all 32 teeth (adult) or 20 teeth (pediatric), each with 6 zones (mesial, distal, vestibular, lingual/palatino, oclusal + root), current conditions per zone, and rendering mode (classic/anatomic based on tenant setting). | High | P-01, T-06 |
| OD-02 | `odontogram/odontogram-update-condition.md` | `POST /api/v1/patients/{patient_id}/odontogram/conditions` -- Add/update condition on tooth zone. Body: tooth_number (FDI notation), zone, condition_code, notes. Creates history entry. 12 conditions: caries, restoration, extraction, absent, crown, endodontic, implant, fracture, sealant, fluorosis, temporary, prosthesis. | High | OD-01 |
| OD-03 | `odontogram/odontogram-remove-condition.md` | `DELETE /api/v1/patients/{patient_id}/odontogram/conditions/{condition_id}` -- Remove condition from tooth zone. Creates history entry (removal). Doctor only. | High | OD-02 |
| OD-04 | `odontogram/odontogram-history.md` | `GET /api/v1/patients/{patient_id}/odontogram/history` -- Get odontogram change history. Timeline of all changes with who, when, what changed. Filterable by tooth, condition type, date range, doctor. | High | OD-02 |
| OD-05 | `odontogram/odontogram-snapshot.md` | `POST /api/v1/patients/{patient_id}/odontogram/snapshots` -- Create point-in-time snapshot of odontogram. Used before/after treatment comparison. Links to clinical record or treatment plan. | High | OD-01 |
| OD-06 | `odontogram/odontogram-snapshot-get.md` | `GET /api/v1/patients/{patient_id}/odontogram/snapshots/{snapshot_id}` -- Get specific snapshot for comparison view. | High | OD-05 |
| OD-07 | `odontogram/odontogram-snapshot-list.md` | `GET /api/v1/patients/{patient_id}/odontogram/snapshots` -- List all snapshots. Paginated, ordered by date. | High | OD-05 |
| OD-08 | `odontogram/odontogram-compare.md` | `GET /api/v1/patients/{patient_id}/odontogram/compare` -- Compare two snapshots side by side. Returns diff of conditions between two points in time. | High | OD-05, OD-06 |
| OD-09 | `odontogram/odontogram-conditions-catalog.md` | `GET /api/v1/odontogram/conditions` -- Get catalog of all available dental conditions with codes, colors, SVG rendering data. Static reference data. Public within tenant. | High | None |
| OD-10 | `odontogram/odontogram-tooth-detail.md` | `GET /api/v1/patients/{patient_id}/odontogram/teeth/{tooth_number}` -- Get detailed info for single tooth. All conditions, full history, linked treatments, X-rays associated with this tooth. | High | OD-01 |
| OD-11 | `odontogram/odontogram-bulk-update.md` | `POST /api/v1/patients/{patient_id}/odontogram/bulk` -- Bulk update multiple teeth/zones in one operation. Used for initial examination entry. Transactional (all or nothing). | High | OD-02 |
| OD-12 | `odontogram/odontogram-pediatric-toggle.md` | `POST /api/v1/patients/{patient_id}/odontogram/dentition` -- Toggle between adult (32 teeth) and pediatric (20 teeth) dentition. Based on patient age or manual override. | High | OD-01 |

## 3.6 Clinical Records (`clinical-records/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| CR-01 | `clinical-records/record-create.md` | `POST /api/v1/patients/{patient_id}/clinical-records` -- Create clinical record entry. Type: anamnesis, examination, diagnosis, evolution_note, procedure. Links to appointment if created during one. Doctor and assistant roles. | High | P-01, I-11 |
| CR-02 | `clinical-records/record-get.md` | `GET /api/v1/patients/{patient_id}/clinical-records/{record_id}` -- Get single clinical record with all details. | High | CR-01 |
| CR-03 | `clinical-records/record-list.md` | `GET /api/v1/patients/{patient_id}/clinical-records` -- List clinical records. Filterable by type, date range, doctor. Paginated. | High | CR-01 |
| CR-04 | `clinical-records/record-update.md` | `PUT /api/v1/patients/{patient_id}/clinical-records/{record_id}` -- Update clinical record. Only within 24h of creation (or clinic_owner override). All edits audit-logged with old/new values. | High | CR-01, I-11 |
| CR-05 | `clinical-records/anamnesis-create.md` | `POST /api/v1/patients/{patient_id}/anamnesis` -- Create or update patient anamnesis (medical history questionnaire). Structured fields: current medications, allergies, chronic conditions, surgical history, family history, habits (smoking, alcohol), pregnancy status. | High | P-01 |
| CR-06 | `clinical-records/anamnesis-get.md` | `GET /api/v1/patients/{patient_id}/anamnesis` -- Get current anamnesis. Returns latest version with history of changes. | High | CR-05 |
| CR-07 | `clinical-records/diagnosis-create.md` | `POST /api/v1/patients/{patient_id}/diagnoses` -- Create diagnosis. Fields: CIE-10 code (autocomplete), description, tooth_number (optional), severity, status (active/resolved), linked_conditions. Doctor only. | High | P-01, CR-10 |
| CR-08 | `clinical-records/diagnosis-list.md` | `GET /api/v1/patients/{patient_id}/diagnoses` -- List patient diagnoses. Filter by status (active/resolved/all), date range. | High | CR-07 |
| CR-09 | `clinical-records/diagnosis-update.md` | `PUT /api/v1/patients/{patient_id}/diagnoses/{diagnosis_id}` -- Update diagnosis status, add notes. Audit logged. | High | CR-07 |
| CR-10 | `clinical-records/cie10-search.md` | `GET /api/v1/catalog/cie10` -- Search CIE-10 codes. Dental-relevant subset. Full-text search on code and description (Spanish). Typeahead optimized. Cached. | High | None |
| CR-11 | `clinical-records/cups-search.md` | `GET /api/v1/catalog/cups` -- Search CUPS procedure codes. Dental-relevant subset. Full-text search. Colombia-specific but base for other country procedure codes. | High | None |
| CR-12 | `clinical-records/procedure-create.md` | `POST /api/v1/patients/{patient_id}/procedures` -- Record completed procedure. Fields: CUPS code, description, tooth_number, zones, materials used, doctor_id, duration, notes. Links to treatment plan item if from plan. Updates odontogram automatically if applicable. | High | P-01, CR-11, OD-02 |
| CR-13 | `clinical-records/procedure-list.md` | `GET /api/v1/patients/{patient_id}/procedures` -- List procedures. Filter by date, doctor, CUPS code, tooth. | High | CR-12 |
| CR-14 | `clinical-records/procedure-get.md` | `GET /api/v1/patients/{patient_id}/procedures/{procedure_id}` -- Get procedure detail. | High | CR-12 |
| CR-15 | `clinical-records/evolution-template-list.md` | `GET /api/v1/evolution-templates` -- List procedure templates (resina, endodoncia, exodoncia, etc.). Built-in + custom per tenant. Template has steps with editable variables in brackets. | High | None |
| CR-16 | `clinical-records/evolution-template-create.md` | `POST /api/v1/evolution-templates` -- Create custom evolution template. JSON body with ordered steps, variable fields, procedure type, complexity variants. Clinic_owner and doctor. | High | CR-15 |
| CR-17 | `clinical-records/evolution-template-get.md` | `GET /api/v1/evolution-templates/{template_id}` -- Get template detail with all steps and variables. | High | CR-15 |

## 3.7 Treatment Plans (`treatment-plans/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| TP-01 | `treatment-plans/plan-create.md` | `POST /api/v1/patients/{patient_id}/treatment-plans` -- Create treatment plan. Fields: title, description, diagnoses (linked), priority, estimated_duration. Items added separately. | High | P-01, CR-07 |
| TP-02 | `treatment-plans/plan-get.md` | `GET /api/v1/patients/{patient_id}/treatment-plans/{plan_id}` -- Get treatment plan with items, progress, costs. | High | TP-01 |
| TP-03 | `treatment-plans/plan-list.md` | `GET /api/v1/patients/{patient_id}/treatment-plans` -- List treatment plans. Filter by status (draft/active/completed/cancelled). | High | TP-01 |
| TP-04 | `treatment-plans/plan-update.md` | `PUT /api/v1/patients/{patient_id}/treatment-plans/{plan_id}` -- Update plan metadata. Status transitions: draft -> active -> completed. | High | TP-01 |
| TP-05 | `treatment-plans/plan-item-add.md` | `POST /api/v1/patients/{patient_id}/treatment-plans/{plan_id}/items` -- Add item to plan. Fields: procedure_code (CUPS), tooth_number, zone, description, estimated_cost, priority_order. | High | TP-01, CR-11 |
| TP-06 | `treatment-plans/plan-item-update.md` | `PUT /api/v1/patients/{patient_id}/treatment-plans/{plan_id}/items/{item_id}` -- Update plan item. Change status (pending/scheduled/completed/cancelled), update cost, reorder. | High | TP-05 |
| TP-07 | `treatment-plans/plan-item-complete.md` | `POST /api/v1/patients/{patient_id}/treatment-plans/{plan_id}/items/{item_id}/complete` -- Mark plan item as completed. Links to procedure record. Updates plan progress percentage. | High | TP-05, CR-12 |
| TP-08 | `treatment-plans/plan-approve.md` | `POST /api/v1/patients/{patient_id}/treatment-plans/{plan_id}/approve` -- Patient approves treatment plan. Digital signature (drawn or typed). Stores approval timestamp, IP, signature image. Required for informed consent. | High | TP-01 |
| TP-09 | `treatment-plans/plan-pdf.md` | `GET /api/v1/patients/{patient_id}/treatment-plans/{plan_id}/pdf` -- Generate treatment plan PDF. Includes procedures, costs, odontogram snapshot, patient info. Clinic branding. | High | TP-02, OD-05 |
| TP-10 | `treatment-plans/plan-share.md` | `POST /api/v1/patients/{patient_id}/treatment-plans/{plan_id}/share` -- Share treatment plan with patient via email/WhatsApp. Generates temporary access link for patient portal. | Medium | TP-09 |

## 3.8 Informed Consent (`consents/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| IC-01 | `consents/consent-template-list.md` | `GET /api/v1/consent-templates` -- List consent form templates. Built-in (general dental, surgery, sedation, orthodontics, implants) + custom per tenant. | High | None |
| IC-02 | `consents/consent-template-create.md` | `POST /api/v1/consent-templates` -- Create custom consent template. Rich text body, required fields, signature positions. Clinic_owner only. | High | IC-01 |
| IC-03 | `consents/consent-template-get.md` | `GET /api/v1/consent-templates/{template_id}` -- Get consent template detail. | High | IC-01 |
| IC-04 | `consents/consent-create.md` | `POST /api/v1/patients/{patient_id}/consents` -- Create consent form for patient from template. Pre-fills patient data. Status: draft. | High | IC-01, P-01 |
| IC-05 | `consents/consent-sign.md` | `POST /api/v1/patients/{patient_id}/consents/{consent_id}/sign` -- Patient signs consent. Accepts signature (base64 drawn signature or typed name). Records timestamp, IP, device info. Generates signed PDF. Immutable after signing. | High | IC-04 |
| IC-06 | `consents/consent-get.md` | `GET /api/v1/patients/{patient_id}/consents/{consent_id}` -- Get consent detail including signature status and signed PDF link. | High | IC-04 |
| IC-07 | `consents/consent-list.md` | `GET /api/v1/patients/{patient_id}/consents` -- List patient consents. Filter by status (draft/signed), template type, date. | High | IC-04 |
| IC-08 | `consents/consent-pdf.md` | `GET /api/v1/patients/{patient_id}/consents/{consent_id}/pdf` -- Download signed consent PDF. | High | IC-05 |
| IC-09 | `consents/consent-void.md` | `POST /api/v1/patients/{patient_id}/consents/{consent_id}/void` -- Void a signed consent (error correction). Creates audit entry. Clinic_owner only. Original preserved. | Low | IC-05, I-11 |

## 3.9 Appointments & Agenda (`appointments/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| AP-01 | `appointments/appointment-create.md` | `POST /api/v1/appointments` -- Create appointment. Fields: patient_id, doctor_id, start_time, end_time, type (consultation, procedure, emergency, follow_up), notes, treatment_plan_item_id (optional). Validates against doctor schedule and existing appointments. | Medium | P-01, U-07 |
| AP-02 | `appointments/appointment-get.md` | `GET /api/v1/appointments/{appointment_id}` -- Get appointment detail with patient info, doctor info, linked procedures. | Medium | AP-01 |
| AP-03 | `appointments/appointment-list.md` | `GET /api/v1/appointments` -- List appointments. Filters: doctor_id, patient_id, date_range, status (scheduled/confirmed/in_progress/completed/cancelled/no_show). Calendar view support (returns grouped by date). | Medium | AP-01 |
| AP-04 | `appointments/appointment-update.md` | `PUT /api/v1/appointments/{appointment_id}` -- Update appointment. Reschedule (validates availability), change type, add notes. Sends notification to patient if time changed. | Medium | AP-01 |
| AP-05 | `appointments/appointment-cancel.md` | `POST /api/v1/appointments/{appointment_id}/cancel` -- Cancel appointment. Reason field. Triggers notification to patient. Frees slot for waitlist. | Medium | AP-01 |
| AP-06 | `appointments/appointment-confirm.md` | `POST /api/v1/appointments/{appointment_id}/confirm` -- Patient confirms appointment. Can be triggered by patient (portal) or staff. | Medium | AP-01 |
| AP-07 | `appointments/appointment-complete.md` | `POST /api/v1/appointments/{appointment_id}/complete` -- Mark appointment as completed. Links to clinical records created during appointment. | Medium | AP-01, CR-01 |
| AP-08 | `appointments/appointment-no-show.md` | `POST /api/v1/appointments/{appointment_id}/no-show` -- Mark patient as no-show. Increments no-show counter on patient record. | Medium | AP-01 |
| AP-09 | `appointments/availability-get.md` | `GET /api/v1/appointments/availability` -- Get available slots. Params: doctor_id, date_range, duration. Returns array of available time slots. Used by booking UI and patient self-booking. | Medium | U-07, AP-01 |
| AP-10 | `appointments/availability-block.md` | `POST /api/v1/appointments/availability/block` -- Block time slot (vacation, break, meeting). Doctor or admin. Creates unavailable block. | Medium | U-07 |
| AP-11 | `appointments/appointment-drag-drop.md` | `PUT /api/v1/appointments/{appointment_id}/reschedule` -- Quick reschedule (drag-and-drop in calendar). Validates new slot availability. Minimal payload (new start_time, new doctor_id optional). | Medium | AP-01, AP-09 |
| AP-12 | `appointments/waitlist-add.md` | `POST /api/v1/appointments/waitlist` -- Add patient to waitlist. Preferred doctor, preferred time ranges, procedure type. Notified when matching slot opens. | Medium | P-01 |
| AP-13 | `appointments/waitlist-list.md` | `GET /api/v1/appointments/waitlist` -- List waitlist entries. Filter by doctor, date range. | Medium | AP-12 |
| AP-14 | `appointments/waitlist-notify.md` | `POST /api/v1/appointments/waitlist/{entry_id}/notify` -- Notify waitlist patient of available slot. Sends WhatsApp/SMS/email. | Medium | AP-12 |
| AP-15 | `appointments/public-booking.md` | `POST /api/v1/public/booking/{tenant_slug}` -- Patient self-booking via shareable link. Public endpoint. Selects doctor, picks available slot, provides basic info. Creates appointment + patient record if new. | Medium | AP-09, P-01 |
| AP-16 | `appointments/public-booking-config.md` | `GET /api/v1/public/booking/{tenant_slug}/config` -- Get booking page configuration. Clinic name, logo, available doctors, available services, business hours. Public endpoint. | Medium | T-06 |
| AP-17 | `appointments/reminder-config.md` | `GET /api/v1/settings/reminders` -- Get reminder configuration. Timing (24h, 2h before), channels (WhatsApp, SMS, email), message templates. | Medium | T-06 |
| AP-18 | `appointments/reminder-config-update.md` | `PUT /api/v1/settings/reminders` -- Update reminder configuration. Clinic_owner only. | Medium | AP-17 |

## 3.10 Notifications (`notifications/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| N-01 | `notifications/notification-list.md` | `GET /api/v1/notifications` -- List in-app notifications for current user. Paginated. Filter by read/unread. | Medium | I-02 |
| N-02 | `notifications/notification-mark-read.md` | `POST /api/v1/notifications/{notification_id}/read` -- Mark notification as read. | Medium | N-01 |
| N-03 | `notifications/notification-mark-all-read.md` | `POST /api/v1/notifications/read-all` -- Mark all notifications as read for current user. | Medium | N-01 |
| N-04 | `notifications/notification-preferences.md` | `GET /api/v1/notifications/preferences` -- Get user notification preferences by channel and event type. | Medium | U-09 |
| N-05 | `notifications/notification-send-engine.md` | Internal spec (not an endpoint). **Notification dispatch engine.** Accepts event type + recipient + data. Routes to appropriate channels (in-app, email, WhatsApp, SMS) based on user preferences. Queue-based async delivery. | Medium | I-06, U-09 |

## 3.11 Billing & Invoicing (`billing/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| B-01 | `billing/invoice-create.md` | `POST /api/v1/patients/{patient_id}/invoices` -- Create invoice. Line items from procedures or treatment plan items. Tax calculation based on country. Currency per tenant. | Medium | P-01, CR-12, TP-05 |
| B-02 | `billing/invoice-get.md` | `GET /api/v1/patients/{patient_id}/invoices/{invoice_id}` -- Get invoice detail. | Medium | B-01 |
| B-03 | `billing/invoice-list.md` | `GET /api/v1/invoices` -- List invoices across all patients. Filter by status (draft/sent/paid/overdue/cancelled), date range, patient, doctor. | Medium | B-01 |
| B-04 | `billing/invoice-update.md` | `PUT /api/v1/patients/{patient_id}/invoices/{invoice_id}` -- Update draft invoice. Add/remove line items, adjust amounts. Only while in draft status. | Medium | B-01 |
| B-05 | `billing/invoice-send.md` | `POST /api/v1/patients/{patient_id}/invoices/{invoice_id}/send` -- Send invoice to patient via email/WhatsApp. Changes status from draft to sent. | Medium | B-01 |
| B-06 | `billing/invoice-pdf.md` | `GET /api/v1/patients/{patient_id}/invoices/{invoice_id}/pdf` -- Generate invoice PDF with clinic branding, patient info, line items, totals, payment info. | Medium | B-01 |
| B-07 | `billing/payment-record.md` | `POST /api/v1/patients/{patient_id}/invoices/{invoice_id}/payments` -- Record payment. Amount, method (cash, card, transfer, insurance), date, reference number. Partial payments supported. | Medium | B-01 |
| B-08 | `billing/payment-list.md` | `GET /api/v1/patients/{patient_id}/payments` -- List all payments for patient. | Medium | B-07 |
| B-09 | `billing/patient-balance.md` | `GET /api/v1/patients/{patient_id}/balance` -- Get patient account balance. Outstanding invoices, total paid, payment plan status. | Medium | B-01, B-07 |
| B-10 | `billing/payment-plan-create.md` | `POST /api/v1/patients/{patient_id}/payment-plans` -- Create payment plan. Total amount, installment count, frequency (weekly/biweekly/monthly), start date. Auto-generates installment schedule. | Medium | P-01, B-01 |
| B-11 | `billing/payment-plan-get.md` | `GET /api/v1/patients/{patient_id}/payment-plans/{plan_id}` -- Get payment plan with installment schedule and payment status per installment. | Medium | B-10 |
| B-12 | `billing/doctor-commissions.md` | `GET /api/v1/billing/commissions` -- Get commission report by doctor. Filter by date range. Shows procedures performed, revenue generated, commission percentage, amount due. | Medium | CR-12, B-07 |
| B-13 | `billing/billing-summary.md` | `GET /api/v1/billing/summary` -- Billing dashboard. Revenue this month/quarter/year, outstanding balance, top procedures by revenue, payment method breakdown. | Medium | B-01, B-07 |
| B-14 | `billing/service-catalog.md` | `GET /api/v1/billing/services` -- Get service/procedure price catalog for tenant. Procedure code, description, default price. Configurable per clinic. | Medium | CR-11 |
| B-15 | `billing/service-catalog-update.md` | `PUT /api/v1/billing/services/{service_id}` -- Update service price. Clinic_owner only. | Medium | B-14 |
| B-16 | `billing/quotation-create.md` | `POST /api/v1/patients/{patient_id}/quotations` -- Auto-generate quotation from treatment plan. Pulls prices from service catalog. Shows per-item and total cost. Status: draft. | High | TP-01, B-14 |
| B-17 | `billing/quotation-get.md` | `GET /api/v1/patients/{patient_id}/quotations/{quotation_id}` -- Get quotation detail with line items, discounts, total. | High | B-16 |
| B-18 | `billing/quotation-send.md` | `POST /api/v1/patients/{patient_id}/quotations/{quotation_id}/send` -- Send quotation to patient via email/WhatsApp/portal. | High | B-16 |
| B-19 | `billing/quotation-approve.md` | `POST /api/v1/patients/{patient_id}/quotations/{quotation_id}/approve` -- Patient approves quotation. Converts to treatment plan + generates invoice draft. | High | B-16, TP-01 |

## 3.12 Compliance (`compliance/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| CO-01 | `compliance/rips-generate.md` | `POST /api/v1/compliance/rips/generate` -- Generate RIPS files (Colombia). Auto-generates AF, AC, AP, AT, AM, AN, AU files from clinical records, procedures, diagnoses. Period-based (monthly). Validated against MinSalud rules. | Low | CR-01, CR-07, CR-12, P-01 |
| CO-02 | `compliance/rips-get.md` | `GET /api/v1/compliance/rips/{batch_id}` -- Get generated RIPS batch. Download individual files or ZIP. | Low | CO-01 |
| CO-03 | `compliance/rips-list.md` | `GET /api/v1/compliance/rips` -- List RIPS generation history. Status (generated/validated/submitted/rejected). | Low | CO-01 |
| CO-04 | `compliance/rips-validate.md` | `POST /api/v1/compliance/rips/{batch_id}/validate` -- Validate RIPS before submission. Returns error list with specific record references. | Low | CO-01 |
| CO-05 | `compliance/rda-status.md` | `GET /api/v1/compliance/rda/status` -- Check RDA (Registro Dental Automatizado) compliance status. Colombia Resolucion 1888. Validates all required fields are being captured. Returns compliance percentage and gaps. | Low | OD-01, CR-01, P-01 |
| CO-06 | `compliance/electronic-invoice.md` | `POST /api/v1/compliance/e-invoice` -- Generate electronic invoice via country-specific provider (DIAN for Colombia, SAT for Mexico, SII for Chile). Adapter pattern per country. | Low | B-01, I-13 |
| CO-07 | `compliance/electronic-invoice-status.md` | `GET /api/v1/compliance/e-invoice/{invoice_id}/status` -- Check electronic invoice status with tax authority. Polling endpoint. | Low | CO-06 |
| CO-08 | `compliance/country-config.md` | `GET /api/v1/compliance/config` -- Get compliance configuration for tenant's country. Required fields, document types, code systems (CIE-10 version, procedure codes), retention rules. | Low | I-13, T-06 |

## 3.13 Reporting & Analytics (`analytics/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| AN-01 | `analytics/dashboard.md` | `GET /api/v1/analytics/dashboard` -- Clinic dashboard. Metrics: patients (new/total), appointments today/week/month, revenue, no-shows, top procedures, occupancy rate per doctor. Date range support. | Medium | P-01, AP-01, B-01 |
| AN-02 | `analytics/patient-stats.md` | `GET /api/v1/analytics/patients` -- Patient analytics. New patients per period, retention rate, average visits per patient, demographics breakdown, referral sources. | Medium | P-01, AP-01 |
| AN-03 | `analytics/appointment-stats.md` | `GET /api/v1/analytics/appointments` -- Appointment analytics. Utilization rate per doctor, average duration, cancellation rate, no-show rate, peak hours. | Medium | AP-01 |
| AN-04 | `analytics/revenue-stats.md` | `GET /api/v1/analytics/revenue` -- Revenue analytics. Revenue by period, by doctor, by procedure type, by payment method. Accounts receivable aging. | Medium | B-01, B-07 |
| AN-05 | `analytics/clinical-stats.md` | `GET /api/v1/analytics/clinical` -- Clinical analytics. Most common diagnoses, most performed procedures, average treatment plan duration, completion rates. | Medium | CR-07, CR-12, TP-01 |
| AN-06 | `analytics/export.md` | `GET /api/v1/analytics/export` -- Export analytics data to CSV/Excel. Customizable report builder. | Low | AN-01 through AN-05 |
| AN-07 | `analytics/audit-trail.md` | `GET /api/v1/analytics/audit-trail` -- View audit trail. Clinic_owner only. Filter by user, action, resource type, date range. Required for compliance audits. | Low | I-11 |

## 3.14 Patient Portal API (`portal/`)

These endpoints are accessed by patients (not clinic staff).

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| PP-01 | `portal/portal-login.md` | `POST /api/v1/portal/auth/login` -- Patient portal login. Email/phone + password or magic link. | Medium | P-11 |
| PP-02 | `portal/portal-profile.md` | `GET /api/v1/portal/me` -- Get patient's own profile from portal. Limited fields. | Medium | PP-01 |
| PP-03 | `portal/portal-appointments.md` | `GET /api/v1/portal/appointments` -- List patient's own appointments. Upcoming and past. | Medium | PP-01, AP-01 |
| PP-04 | `portal/portal-treatment-plans.md` | `GET /api/v1/portal/treatment-plans` -- View patient's treatment plans. Read-only. Active and completed. | Medium | PP-01, TP-01 |
| PP-05 | `portal/portal-treatment-plan-approve.md` | `POST /api/v1/portal/treatment-plans/{plan_id}/approve` -- Patient approves treatment plan from portal. Digital signature capture. | Medium | PP-04, TP-08 |
| PP-06 | `portal/portal-invoices.md` | `GET /api/v1/portal/invoices` -- View patient's invoices and payment history. | Medium | PP-01, B-01 |
| PP-07 | `portal/portal-documents.md` | `GET /api/v1/portal/documents` -- View patient's documents (X-rays, consent forms, treatment plans as PDF). | Medium | PP-01, P-12 |
| PP-08 | `portal/portal-book-appointment.md` | `POST /api/v1/portal/appointments` -- Book appointment from portal. Similar to public booking but authenticated. | Medium | PP-01, AP-15 |
| PP-09 | `portal/portal-cancel-appointment.md` | `POST /api/v1/portal/appointments/{appointment_id}/cancel` -- Cancel own appointment from portal. Subject to cancellation policy (e.g., 24h minimum). | Medium | PP-03 |
| PP-10 | `portal/portal-messages.md` | `GET /api/v1/portal/messages` -- In-app messaging between patient and clinic. List message threads. | Medium | PP-01 |
| PP-11 | `portal/portal-message-send.md` | `POST /api/v1/portal/messages` -- Send message to clinic from portal. | Medium | PP-10 |
| PP-12 | `portal/portal-consent-sign.md` | `POST /api/v1/portal/consents/{consent_id}/sign` -- Sign consent form from portal. | Medium | PP-01, IC-05 |
| PP-13 | `portal/portal-odontogram.md` | `GET /api/v1/portal/odontogram` -- View own odontogram. Read-only simplified view. | Medium | PP-01, OD-01 |

## 3.15 Voice-to-Odontogram (`voice/`)

AI-powered voice capture and transcription for odontogram and clinical records. Requires AI Voice-to-Chart add-on.

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| V-01 | `voice/voice-capture.md` | `POST /api/v1/patients/{patient_id}/voice/capture` -- Start voice capture session. Returns session_id. Audio streamed from PWA microphone. Records metadata (patient_id, doctor_id, context: odontogram/evolution). | High | P-01, OD-01 |
| V-02 | `voice/voice-transcription.md` | `POST /api/v1/voice/{session_id}/transcribe` -- Send audio chunk for transcription. Uses Whisper Large v3 (Spanish). Returns raw text. Async via queue. | High | V-01 |
| V-03 | `voice/voice-parse.md` | `POST /api/v1/voice/{session_id}/parse` -- LLM parses transcription into structured dental JSON. Extracts: tooth_number, zone, condition, corrections, filters non-clinical speech. Returns proposed changes for confirmation. | High | V-02 |
| V-04 | `voice/voice-apply.md` | `POST /api/v1/voice/{session_id}/apply` -- Apply confirmed voice-parsed changes to odontogram. Bulk update with flag `source: voice`. Audit logged. | High | V-03, OD-11 |
| V-05 | `voice/voice-settings.md` | `GET/PUT /api/v1/settings/voice` -- Voice feature configuration per tenant. Enable/disable, default language, confirmation mode (auto-apply vs review-first), Whisper model preference. | High | T-06 |

## 3.16 Inventory & Sterilization (`inventory/`)

Material inventory management, expiry tracking, sterilization logs, and implant traceability.

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| INV-01 | `inventory/item-create.md` | `POST /api/v1/inventory/items` -- Create inventory item. Fields: name, category (material/instrument/implant/medication), quantity, unit, lot_number, expiry_date, manufacturer, supplier, cost. | Medium | I-01 |
| INV-02 | `inventory/item-list.md` | `GET /api/v1/inventory/items` -- List inventory items. Filters: category, expiry_status (ok/warning/critical/expired), low_stock. Semaphore colors: green (OK), yellow (60d), orange (30d), red (expired). | Medium | INV-01 |
| INV-03 | `inventory/item-update.md` | `PUT /api/v1/inventory/items/{item_id}` -- Update inventory item. Adjust quantity, update lot, mark as consumed. | Medium | INV-01 |
| INV-04 | `inventory/alerts.md` | `GET /api/v1/inventory/alerts` -- Get active inventory alerts. Expiring items, low stock, expired items. Push + email notifications auto-sent. | Medium | INV-01, N-05 |
| INV-05 | `inventory/sterilization-create.md` | `POST /api/v1/inventory/sterilization` -- Record sterilization cycle. Fields: autoclave_id, load_number, date, temperature, duration, biological_indicator, chemical_indicator, instruments[], responsible_user, digital_signature. | Medium | INV-01 |
| INV-06 | `inventory/sterilization-list.md` | `GET /api/v1/inventory/sterilization` -- List sterilization records. Filterable by date, autoclave, load number. Exportable PDF for audits. | Medium | INV-05 |
| INV-07 | `inventory/implant-tracking.md` | `POST /api/v1/inventory/implants/{item_id}/link` -- Link implant (serial, lot, manufacturer) to patient procedure. Creates traceability chain: implant → procedure → patient. | Medium | INV-01, CR-12 |

## 3.17 Admin / Superadmin (`admin/`)

Endpoints for DentalOS platform administration (not clinic-level admin).

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| AD-01 | `admin/superadmin-login.md` | `POST /api/v1/admin/auth/login` -- Superadmin login. Separate auth context. MFA required. | Critical | I-02 |
| AD-02 | `admin/tenant-management.md` | `GET /api/v1/admin/tenants` -- Platform-wide tenant management. Already covered by T-01 through T-05 but with additional metrics: MRR, churn, usage. | High | T-01 |
| AD-03 | `admin/plan-management.md` | `GET/PUT /api/v1/admin/plans` -- Manage subscription plans. Update pricing, features, limits. | High | None |
| AD-04 | `admin/platform-analytics.md` | `GET /api/v1/admin/analytics` -- Platform-level analytics. Total tenants, MRR, MAU, tenants per country, plan distribution, churn rate. | High | T-01 |
| AD-05 | `admin/feature-flags.md` | `GET/PUT /api/v1/admin/feature-flags` -- Feature flag management. Enable/disable features globally or per tenant. Used for gradual rollouts. | High | None |
| AD-06 | `admin/system-health.md` | `GET /api/v1/admin/health` -- System health dashboard. Database connections, queue depth, cache hit rate, error rates per tenant. | High | I-15 |
| AD-07 | `admin/tenant-impersonate.md` | `POST /api/v1/admin/tenants/{tenant_id}/impersonate` -- Impersonate tenant for support. Creates time-limited session with audit trail. | Low | T-01, I-11 |

## 3.18 Messaging (`messages/`)

In-app messaging between clinic staff and patients.

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| MS-01 | `messages/thread-create.md` | `POST /api/v1/messages/threads` -- Create message thread with patient. | Medium | P-01 |
| MS-02 | `messages/thread-list.md` | `GET /api/v1/messages/threads` -- List message threads. Filter by patient, unread. | Medium | MS-01 |
| MS-03 | `messages/message-send.md` | `POST /api/v1/messages/threads/{thread_id}/messages` -- Send message in thread. Text, image, document attachment. | Medium | MS-01 |
| MS-04 | `messages/message-list.md` | `GET /api/v1/messages/threads/{thread_id}/messages` -- List messages in thread. Paginated, ordered by date. | Medium | MS-01 |
| MS-05 | `messages/message-mark-read.md` | `POST /api/v1/messages/threads/{thread_id}/read` -- Mark thread as read. | Medium | MS-01 |

## 3.19 Prescriptions (`prescriptions/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| RX-01 | `prescriptions/prescription-create.md` | `POST /api/v1/patients/{patient_id}/prescriptions` -- Create prescription. Medications with dosage, frequency, duration. Doctor signature. Links to diagnosis. | High | P-01, CR-07 |
| RX-02 | `prescriptions/prescription-get.md` | `GET /api/v1/patients/{patient_id}/prescriptions/{rx_id}` -- Get prescription detail. | High | RX-01 |
| RX-03 | `prescriptions/prescription-list.md` | `GET /api/v1/patients/{patient_id}/prescriptions` -- List prescriptions. | High | RX-01 |
| RX-04 | `prescriptions/prescription-pdf.md` | `GET /api/v1/patients/{patient_id}/prescriptions/{rx_id}/pdf` -- Generate prescription PDF with clinic branding, doctor info, patient info, medications. | High | RX-01 |
| RX-05 | `prescriptions/medication-search.md` | `GET /api/v1/catalog/medications` -- Search medication catalog. Name, active ingredient, presentation. Dental-relevant subset. | High | None |

---

# SECTION 4: INTEGRATION SPECS (`integrations/`)

External service integrations.

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| INT-01 | `integrations/whatsapp-business.md` | **WhatsApp Business API integration.** Template message setup (appointment reminders, treatment plan notifications, payment reminders), message sending service, webhook for incoming messages, session management. Meta Business verification. | Medium | I-06, N-05 |
| INT-02 | `integrations/twilio-sms.md` | **Twilio SMS integration.** SMS sending for appointment reminders (fallback when WhatsApp unavailable), verification codes, notification delivery. | Medium | I-06, N-05 |
| INT-03 | `integrations/email-engine.md` | **Email delivery engine.** Transactional email service (SendGrid/SES), template management, placeholder parsing, delivery tracking, bounce handling. | Critical | I-06 |
| INT-04 | `integrations/dian-electronic-invoice.md` | **DIAN electronic invoicing (Colombia).** Integration with DIAN web services for factura electronica. XML generation (UBL 2.1), digital signature, CUFE generation, submission, status polling. | Low | B-01, CO-06 |
| INT-05 | `integrations/sat-electronic-invoice.md` | **SAT CFDI (Mexico).** Integration with PAC (Proveedor Autorizado de Certificacion) for CFDI generation. XML stamping, UUID assignment. | Low | B-01, CO-06 |
| INT-06 | `integrations/sii-electronic-invoice.md` | **SII electronic invoicing (Chile).** DTE (Documento Tributario Electronico) generation and submission. | Low | B-01, CO-06 |
| INT-07 | `integrations/payment-gateway.md` | **Payment gateway integration.** Online payment collection via patient portal. Mercado Pago (LATAM-wide), PSE (Colombia), card processing. Webhook for payment confirmation. | Low | B-07, PP-06 |
| INT-08 | `integrations/cloud-storage.md` | **S3-compatible storage integration.** Hetzner Object Storage or MinIO. Tenant-isolated prefixes, signed URL generation, file lifecycle policies, CORS configuration. | High | I-17 |
| INT-09 | `integrations/google-calendar-sync.md` | **Google Calendar sync.** Optional bi-directional sync for doctors who use Google Calendar. OAuth2 setup, event mapping, conflict resolution. | Low | AP-01 |
| INT-10 | `integrations/dian-matias.md` | MATIAS API integration for DIAN electronic invoicing. DentalOS as "Casa de Software" technology provider. Each clinic invoices under own NIT. REST API, ~$400K COP/year for multi-client package. | Medium | B-01, CO-06 |

---

# SECTION 4.5: DIGITAL SIGNATURES (`signatures/`)

Legal-grade digital signature infrastructure used across consents, treatment plans, prescriptions, and sterilization records.

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| DS-01 | `signatures/digital-signature.md` | `POST /api/v1/signatures` -- Create legally-valid digital signature. Canvas tactile capture + SHA-256 hash + server timestamp + audit log. Colombia Ley 527/1999. Used by consents, treatment plans, prescriptions. Both doctor and patient sign. | High | I-11 |

---

# SECTION 5: FRONTEND SPECS (`frontend/`)

Organized by application section.

## 5.1 Design System & Shared Components (`frontend/design-system/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| FE-DS-01 | `frontend/design-system/tokens.md` | Design tokens: colors (dental theme, clinical status colors), typography (Inter/system), spacing scale, shadows, border radius. TailwindCSS config. | Critical | I-28 |
| FE-DS-02 | `frontend/design-system/button.md` | Button component. Variants: primary, secondary, outline, ghost, danger. Sizes: sm, md, lg. States: default, hover, active, disabled, loading. | Critical | FE-DS-01 |
| FE-DS-03 | `frontend/design-system/input.md` | Input component. Types: text, email, password, number, phone, date, textarea. Validation states, helper text, error messages. | Critical | FE-DS-01 |
| FE-DS-04 | `frontend/design-system/select.md` | Select/Combobox component. Single/multi select, searchable, async loading (for CIE-10, CUPS autocomplete). | Critical | FE-DS-01 |
| FE-DS-05 | `frontend/design-system/table.md` | Data table component. Sortable columns, pagination, row selection, expandable rows, responsive (horizontal scroll on mobile). | Critical | FE-DS-01 |
| FE-DS-06 | `frontend/design-system/modal.md` | Modal/Dialog component. Sizes: sm, md, lg, full. Confirmation dialogs, form modals, info modals. | Critical | FE-DS-01 |
| FE-DS-07 | `frontend/design-system/toast.md` | Toast/notification component. Types: success, error, warning, info. Auto-dismiss, action buttons, stacking. | Critical | FE-DS-01 |
| FE-DS-08 | `frontend/design-system/sidebar.md` | Navigation sidebar. Collapsible, icon + label, nested groups, active state, role-based visibility. | Critical | FE-DS-01 |
| FE-DS-09 | `frontend/design-system/header.md` | App header. Clinic name/logo, user avatar/menu, notifications bell, search bar, tenant context indicator. | Critical | FE-DS-01 |
| FE-DS-10 | `frontend/design-system/card.md` | Card component. Variants: default, elevated, outlined. Used for patient cards, appointment cards, stats cards. | Critical | FE-DS-01 |
| FE-DS-11 | `frontend/design-system/badge.md` | Badge/pill component. Status badges (appointment status, treatment status, payment status), condition badges for odontogram. | Critical | FE-DS-01 |
| FE-DS-12 | `frontend/design-system/avatar.md` | Avatar component. Image, initials fallback, status indicator (online/offline), size variants. | Critical | FE-DS-01 |
| FE-DS-13 | `frontend/design-system/calendar.md` | Calendar component. Day/week/month views, event rendering, drag-and-drop support, time grid. | Medium | FE-DS-01 |
| FE-DS-14 | `frontend/design-system/signature-pad.md` | Signature capture component. Canvas-based drawing, clear/redo, submit as base64 PNG. Used for consent forms and treatment plan approval. | High | FE-DS-01 |
| FE-DS-15 | `frontend/design-system/file-upload.md` | File upload component. Drag-and-drop zone, preview (images, PDFs), progress bar, allowed types, size limits. | High | FE-DS-01 |
| FE-DS-16 | `frontend/design-system/empty-state.md` | Empty state component. Illustration + message + CTA. Per-context variants (no patients, no appointments, etc.). | Critical | FE-DS-01 |
| FE-DS-17 | `frontend/design-system/skeleton.md` | Skeleton loader component. Variants matching each content type (table skeleton, card skeleton, form skeleton). | Critical | FE-DS-01 |
| FE-DS-18 | `frontend/design-system/tooth-selector.md` | **Dental-specific component.** Interactive tooth selector widget. Click to select tooth by number (FDI). Shows mini-odontogram for selection context. | High | FE-DS-01, OD-09 |
| FE-DS-19 | `frontend/design-system/condition-icon.md` | **Dental-specific component.** Visual icon/badge for each dental condition (caries, restoration, etc.). Color-coded. Used in odontogram and condition lists. | High | FE-DS-01, OD-09 |

## 5.2 Authentication Screens (`frontend/auth/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| FE-A-01 | `frontend/auth/register.md` | Registration page. Multi-step: 1) Email+Password 2) Clinic info (name, country, phone) 3) Plan selection. Responsive. | Critical | A-01, FE-DS-01 |
| FE-A-02 | `frontend/auth/login.md` | Login page. Email + password form. Forgot password link. Logo, tagline. | Critical | A-02, FE-DS-01 |
| FE-A-03 | `frontend/auth/forgot-password.md` | Forgot password page. Email input, success confirmation. | Critical | A-05, FE-DS-01 |
| FE-A-04 | `frontend/auth/reset-password.md` | Reset password page. New password + confirm, token validation. | Critical | A-06, FE-DS-01 |
| FE-A-05 | `frontend/auth/accept-invite.md` | Accept invitation page. Set password, complete profile for invited team member. | Critical | A-10, FE-DS-01 |
| FE-A-06 | `frontend/auth/onboarding-wizard.md` | Post-registration onboarding. 4 steps: clinic details, first doctor, odontogram config, optional patient import. Progress indicator. | Critical | T-10, FE-DS-01 |

## 5.3 Dashboard (`frontend/dashboard/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| FE-D-01 | `frontend/dashboard/main-dashboard.md` | Main dashboard. Widgets: today's appointments, new patients this week, revenue this month, pending treatment plans, upcoming reminders. Role-dependent widgets. | Critical | AN-01, FE-DS-01 |
| FE-D-02 | `frontend/dashboard/doctor-dashboard.md` | Doctor-specific dashboard. My appointments today, my patients, my procedures this week, upcoming appointments. | High | AN-01, FE-DS-01 |

## 5.4 Patient Management Screens (`frontend/patients/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| FE-P-01 | `frontend/patients/patient-list.md` | Patient list page. Table with search, filters, pagination. Quick actions: view, edit, new appointment. Responsive card view on mobile. | Critical | P-03, FE-DS-01 |
| FE-P-02 | `frontend/patients/patient-create.md` | Create patient form. Multi-section: personal info, contact, medical info, insurance. Validate ID document format per country. | Critical | P-01, FE-DS-01 |
| FE-P-03 | `frontend/patients/patient-detail.md` | Patient detail page. Tabbed layout: Overview, Odontogram, Clinical Records, Treatment Plans, Appointments, Billing, Documents. Summary card at top. | Critical | P-02, FE-DS-01 |
| FE-P-04 | `frontend/patients/patient-edit.md` | Edit patient form. Pre-filled from current data. Same sections as create. | Critical | P-04, FE-DS-01 |
| FE-P-05 | `frontend/patients/patient-search.md` | Global patient search. Typeahead in header bar. Shows recent patients, search results with mini-card. | Critical | P-06, FE-DS-01 |
| FE-P-06 | `frontend/patients/patient-import.md` | Patient import page. Upload CSV/Excel, column mapping, validation preview, import progress. | High | P-08, FE-DS-01 |
| FE-P-07 | `frontend/patients/patient-medical-history.md` | Medical history timeline within patient detail. Chronological list of all clinical events. Filter by type. | High | P-07, FE-DS-01 |

## 5.5 Odontogram Screens (`frontend/odontogram/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| FE-OD-01 | `frontend/odontogram/odontogram-classic.md` | **Classic grid odontogram.** Grid layout with all 32 teeth (adult) or 20 (pediatric). Each tooth shows 5 crown zones + root. Click zone to add condition. Color-coded by condition. Free tier. | High | OD-01, FE-DS-01 |
| FE-OD-02 | `frontend/odontogram/odontogram-anatomic.md` | **Anatomic arch odontogram.** SVG-based realistic dental arch. Upper and lower arches. Interactive zoom, click zones. Premium feature (starter+). | High | OD-01, FE-DS-01 |
| FE-OD-03 | `frontend/odontogram/condition-panel.md` | Condition selection panel. Appears when clicking a zone. List of 12 conditions with icons. Quick-select. Notes field. | High | OD-02, FE-DS-19 |
| FE-OD-04 | `frontend/odontogram/odontogram-history-panel.md` | History panel. Sidebar showing timeline of changes for selected tooth or entire chart. Filter by date, condition. | High | OD-04, FE-DS-01 |
| FE-OD-05 | `frontend/odontogram/odontogram-comparison.md` | Comparison view. Side-by-side snapshots. Visual diff highlighting changes. Before/after treatment. | High | OD-08, FE-DS-01 |
| FE-OD-06 | `frontend/odontogram/tooth-detail-panel.md` | Tooth detail panel. Full info for single tooth: all conditions, history, linked treatments, X-rays. Slide-in panel. | High | OD-10, FE-DS-01 |
| FE-OD-07 | `frontend/odontogram/odontogram-toolbar.md` | Odontogram toolbar. Toggle classic/anatomic mode, adult/pediatric, zoom controls, print/export, snapshot button, history toggle. | High | OD-01, FE-DS-01 |

## 5.6 Clinical Records Screens (`frontend/clinical-records/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| FE-CR-01 | `frontend/clinical-records/record-list.md` | Clinical records list within patient detail. Table with type icon, date, doctor, summary. Expandable rows for preview. | High | CR-03, FE-DS-01 |
| FE-CR-02 | `frontend/clinical-records/record-create.md` | Create clinical record form. Dynamic form based on type (anamnesis, examination, diagnosis, evolution note, procedure). Rich text editor for notes. | High | CR-01, FE-DS-01 |
| FE-CR-03 | `frontend/clinical-records/anamnesis-form.md` | Anamnesis questionnaire form. Structured sections: current medications, allergies (with severity), chronic conditions (checkboxes), surgical history, family history, habits. | High | CR-05, FE-DS-01 |
| FE-CR-04 | `frontend/clinical-records/diagnosis-form.md` | Diagnosis creation form. CIE-10 autocomplete search, description, severity selector, link to teeth. | High | CR-07, CR-10, FE-DS-01 |
| FE-CR-05 | `frontend/clinical-records/procedure-form.md` | Procedure recording form. CUPS code autocomplete, tooth selector, zone selector, materials used, duration, notes, link to treatment plan item. | High | CR-12, CR-11, FE-DS-18 |
| FE-CR-06 | `frontend/clinical-records/cie10-search.md` | CIE-10 search component. Autocomplete dropdown, shows code + description, dental-relevant results prioritized. Reusable across forms. | High | CR-10, FE-DS-04 |
| FE-CR-07 | `frontend/clinical-records/cups-search.md` | CUPS search component. Same pattern as CIE-10 but for procedure codes. | High | CR-11, FE-DS-04 |

## 5.7 Treatment Plan Screens (`frontend/treatment-plans/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| FE-TP-01 | `frontend/treatment-plans/plan-list.md` | Treatment plan list within patient detail. Cards showing plan name, status, progress bar, total cost, date. | High | TP-03, FE-DS-01 |
| FE-TP-02 | `frontend/treatment-plans/plan-create.md` | Create treatment plan form. Title, linked diagnoses, add procedure items (CUPS search, tooth, cost), drag to reorder, total calculation. | High | TP-01, TP-05, FE-DS-01 |
| FE-TP-03 | `frontend/treatment-plans/plan-detail.md` | Treatment plan detail page. Item list with status per item, progress bar, cost breakdown, approval status, action buttons (approve, share, PDF). | High | TP-02, FE-DS-01 |
| FE-TP-04 | `frontend/treatment-plans/plan-approval.md` | Treatment plan approval flow. Display plan summary, signature pad, terms acceptance. Mobile-optimized (patients often sign on phone/tablet). | High | TP-08, FE-DS-14 |

## 5.8 Consent Form Screens (`frontend/consents/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| FE-IC-01 | `frontend/consents/consent-list.md` | Consent forms list within patient detail. Status badges (draft, signed), template name, date. | High | IC-07, FE-DS-01 |
| FE-IC-02 | `frontend/consents/consent-create.md` | Create consent form. Select template, preview with patient data, send for signature or sign in-clinic. | High | IC-04, FE-DS-01 |
| FE-IC-03 | `frontend/consents/consent-sign.md` | Consent signing screen. Full consent text display, scroll-to-read, signature pad, submit. Mobile-optimized. | High | IC-05, FE-DS-14 |
| FE-IC-04 | `frontend/consents/consent-template-editor.md` | Custom consent template editor. Rich text editor, placeholder insertion (patient name, date, etc.), preview. Clinic_owner only. | Low | IC-02, FE-DS-01 |

## 5.9 Appointment & Agenda Screens (`frontend/agenda/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| FE-AG-01 | `frontend/agenda/calendar-view.md` | **Main calendar view.** Day/week/month views. Color-coded by appointment type and status. Drag-and-drop to reschedule. Multi-doctor column view (week). Click to create. | Medium | AP-03, FE-DS-13 |
| FE-AG-02 | `frontend/agenda/appointment-create.md` | Create appointment modal/form. Patient search, doctor select, date/time picker, duration, type, notes, link to treatment plan. Availability check in real-time. | Medium | AP-01, FE-DS-01 |
| FE-AG-03 | `frontend/agenda/appointment-detail.md` | Appointment detail modal. Patient info, doctor, time, status, notes, linked clinical records. Action buttons: confirm, complete, cancel, no-show. | Medium | AP-02, FE-DS-01 |
| FE-AG-04 | `frontend/agenda/doctor-schedule-editor.md` | Doctor schedule editor. Weekly template. Day-by-day start/end times, break times, appointment slot duration. Drag to adjust. | Medium | U-08, FE-DS-01 |
| FE-AG-05 | `frontend/agenda/waitlist-panel.md` | Waitlist sidebar panel. List of waiting patients, preferred times, one-click scheduling when slot opens. | Medium | AP-13, FE-DS-01 |
| FE-AG-06 | `frontend/agenda/today-view.md` | Today's appointments quick view. Timeline format, patient status (waiting, in-chair, done), quick actions. | Medium | AP-03, FE-DS-01 |

## 5.10 Billing Screens (`frontend/billing/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| FE-B-01 | `frontend/billing/invoice-list.md` | Invoice list page. Table with filters (status, date, patient). Bulk actions. | Medium | B-03, FE-DS-01 |
| FE-B-02 | `frontend/billing/invoice-create.md` | Create invoice form. Select patient, add line items (from procedures or manual), tax calculation, total. | Medium | B-01, FE-DS-01 |
| FE-B-03 | `frontend/billing/invoice-detail.md` | Invoice detail page. Line items, payments, balance, PDF preview, send actions. | Medium | B-02, FE-DS-01 |
| FE-B-04 | `frontend/billing/payment-record.md` | Record payment modal. Amount, method, reference. Partial payment support. | Medium | B-07, FE-DS-01 |
| FE-B-05 | `frontend/billing/payment-plan.md` | Payment plan creation and management. Installment schedule, payment tracking per installment. | Medium | B-10, B-11, FE-DS-01 |
| FE-B-06 | `frontend/billing/service-catalog.md` | Service/procedure price catalog management. Table with editable prices. Clinic_owner only. | Medium | B-14, FE-DS-01 |
| FE-B-07 | `frontend/billing/commissions-report.md` | Doctor commissions report page. Filter by date, doctor. Table + charts. | Medium | B-12, FE-DS-01 |
| FE-B-08 | `frontend/billing/billing-dashboard.md` | Billing overview dashboard. Revenue charts, outstanding balance, aging report. | Medium | B-13, FE-DS-01 |

## 5.11 Settings Screens (`frontend/settings/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| FE-S-01 | `frontend/settings/clinic-settings.md` | Clinic settings page. Name, address, phone, logo upload, country, timezone, currency. | Critical | T-07, FE-DS-01 |
| FE-S-02 | `frontend/settings/team-management.md` | Team management page. List users, invite new, edit roles, deactivate. | Critical | U-03, A-09, FE-DS-01 |
| FE-S-03 | `frontend/settings/subscription-plan.md` | Subscription plan page. Current plan, usage meters, upgrade/downgrade options, billing history. | High | T-08, FE-DS-01 |
| FE-S-04 | `frontend/settings/odontogram-config.md` | Odontogram configuration. Mode selection (classic/anatomic), default view, condition colors customization. | High | T-07, FE-DS-01 |
| FE-S-05 | `frontend/settings/notification-settings.md` | Notification settings. Reminder timing, channels, templates. Clinic-wide and per-user overrides. | Medium | AP-17, U-09, FE-DS-01 |
| FE-S-06 | `frontend/settings/consent-templates.md` | Consent template management. List, create, edit, preview templates. | High | IC-01, IC-02, FE-DS-01 |
| FE-S-07 | `frontend/settings/compliance-settings.md` | Compliance settings per country. RDA configuration (Colombia), required field enforcement. | Low | CO-05, CO-08, FE-DS-01 |
| FE-S-08 | `frontend/settings/integrations.md` | Integrations page. WhatsApp Business setup, Google Calendar toggle, payment gateway config. | Medium | INT-01, INT-09, FE-DS-01 |
| FE-S-09 | `frontend/settings/audit-log.md` | Audit log viewer. Searchable, filterable log of all clinical data access and modifications. | Low | AN-07, FE-DS-01 |

## 5.12 Patient Portal (separate frontend) (`frontend/portal/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| FE-PP-01 | `frontend/portal/portal-login.md` | Patient portal login. Email/phone + password. Minimal, branded per clinic. | Medium | PP-01, FE-DS-01 |
| FE-PP-02 | `frontend/portal/portal-dashboard.md` | Patient portal dashboard. Next appointment, active treatment plans, unread messages, pending consent forms. | Medium | PP-02, FE-DS-01 |
| FE-PP-03 | `frontend/portal/portal-appointments.md` | Patient's appointment list. Upcoming with confirm/cancel. Past appointments. Book new appointment. | Medium | PP-03, PP-08, FE-DS-01 |
| FE-PP-04 | `frontend/portal/portal-treatment-plans.md` | View treatment plans. Progress visualization. Approve with signature. | Medium | PP-04, PP-05, FE-DS-01 |
| FE-PP-05 | `frontend/portal/portal-documents.md` | Document viewer. X-rays, consent forms, prescriptions as PDF. Download option. | Medium | PP-07, FE-DS-01 |
| FE-PP-06 | `frontend/portal/portal-messages.md` | Chat interface with clinic. Message list, send message, image/file attachment. | Medium | PP-10, PP-11, FE-DS-01 |
| FE-PP-07 | `frontend/portal/portal-invoices.md` | Invoice and payment history. Outstanding balance. Payment link (if online payments enabled). | Medium | PP-06, FE-DS-01 |
| FE-PP-08 | `frontend/portal/portal-consent-sign.md` | Consent form signing from portal. Full document view, signature pad. | Medium | PP-12, FE-DS-14 |
| FE-PP-09 | `frontend/portal/portal-odontogram.md` | Simplified odontogram view for patients. Read-only, color-coded legend. Educational tooltips. | Medium | PP-13, FE-OD-01 |
| FE-PP-10 | `frontend/portal/public-booking.md` | Public appointment booking page. No login required. Clinic-branded. Doctor selection, time slot picker, contact form. | Medium | AP-15, AP-16, FE-DS-01 |

## 5.13 Prescription Screens (`frontend/prescriptions/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| FE-RX-01 | `frontend/prescriptions/prescription-create.md` | Create prescription form. Medication autocomplete, dosage, frequency, duration. Multiple medications per prescription. | High | RX-01, RX-05, FE-DS-01 |
| FE-RX-02 | `frontend/prescriptions/prescription-list.md` | Prescription list within patient detail. Date, medications summary, doctor, PDF download. | High | RX-03, FE-DS-01 |
| FE-RX-03 | `frontend/prescriptions/prescription-preview.md` | Prescription preview/print view. Formatted like a real prescription pad. Print-optimized CSS. | High | RX-04, FE-DS-01 |

## 5.14 Analytics/Reports Screens (`frontend/analytics/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| FE-AN-01 | `frontend/analytics/analytics-dashboard.md` | Analytics main dashboard. Period selector, KPI cards, charts (line, bar, pie). Revenue, patients, appointments metrics. | Medium | AN-01, FE-DS-01 |
| FE-AN-02 | `frontend/analytics/patient-analytics.md` | Patient analytics page. New patients trend, retention, demographics. | Medium | AN-02, FE-DS-01 |
| FE-AN-03 | `frontend/analytics/appointment-analytics.md` | Appointment analytics. Utilization, cancellations, no-shows, peak hours heatmap. | Medium | AN-03, FE-DS-01 |
| FE-AN-04 | `frontend/analytics/revenue-analytics.md` | Revenue analytics. Revenue trends, by doctor, by procedure, payment method breakdown. | Medium | AN-04, FE-DS-01 |

## 5.15 Compliance Screens (`frontend/compliance/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| FE-CO-01 | `frontend/compliance/rips-generator.md` | RIPS generation page (Colombia). Period selection, generate, validate, download. Error listing with links to source records. | Low | CO-01, CO-04, FE-DS-01 |
| FE-CO-02 | `frontend/compliance/rda-dashboard.md` | RDA compliance dashboard (Colombia). Compliance score, missing fields, action items. | Low | CO-05, FE-DS-01 |
| FE-CO-03 | `frontend/compliance/e-invoice-list.md` | Electronic invoice list. Status tracking, resend, download XML/PDF. | Low | CO-06, CO-07, FE-DS-01 |

## 5.16 Voice UI (`frontend/odontogram/` and `frontend/clinical/`)

Voice-to-Odontogram and voice dictation screens. Requires AI Voice-to-Chart add-on.

| # | File Path | Description | Priority |
|---|-----------|-------------|----------|
| FE-V-01 | `frontend/odontogram/voice-input.md` | Voice recording button + real-time transcription display + confirmation UI for odontogram | High |
| FE-V-02 | `frontend/odontogram/voice-review.md` | Review and confirm/reject voice-parsed changes before applying to odontogram | High |
| FE-V-03 | `frontend/clinical/voice-evolution.md` | Voice dictation for clinical evolution notes with template auto-fill | High |

## 5.17 Inventory Screens (`frontend/inventory/`)

| # | File Path | Description | Priority |
|---|-----------|-------------|----------|
| FE-INV-01 | `frontend/inventory/inventory-list.md` | Inventory list with traffic-light semaphore, filters, alerts | Medium |
| FE-INV-02 | `frontend/inventory/sterilization-log.md` | Sterilization cycle registration and history | Medium |
| FE-INV-03 | `frontend/inventory/implant-tracker.md` | Implant traceability linked to patient | Medium |

---

# SECTION 6: EMAIL/NOTIFICATION TEMPLATES (`emails/`)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| E-01 | `emails/welcome-email.md` | Welcome email after clinic registration. Onboarding next steps. | Critical | A-01, INT-03 |
| E-02 | `emails/email-verification.md` | Email verification link. | Critical | A-11, INT-03 |
| E-03 | `emails/password-reset.md` | Password reset link email. | Critical | A-05, INT-03 |
| E-04 | `emails/team-invite.md` | Team member invitation email with accept link. | Critical | A-09, INT-03 |
| E-05 | `emails/appointment-confirmation.md` | Appointment confirmation (email + WhatsApp template). | Medium | AP-01, INT-01, INT-03 |
| E-06 | `emails/appointment-reminder-24h.md` | 24-hour appointment reminder (email + WhatsApp + SMS). | Medium | AP-01, INT-01, INT-02, INT-03 |
| E-07 | `emails/appointment-reminder-2h.md` | 2-hour appointment reminder (WhatsApp + SMS only). | Medium | AP-01, INT-01, INT-02 |
| E-08 | `emails/appointment-cancelled.md` | Appointment cancellation notice to patient. | Medium | AP-05, INT-03 |
| E-09 | `emails/treatment-plan-shared.md` | Treatment plan shared with patient. Link to portal. | Medium | TP-10, INT-03 |
| E-10 | `emails/consent-request.md` | Consent form signature request. Link to portal. | High | IC-04, INT-03 |
| E-11 | `emails/invoice-sent.md` | Invoice sent to patient. PDF attached or link to portal. | Medium | B-05, INT-03 |
| E-12 | `emails/payment-confirmation.md` | Payment received confirmation. | Medium | B-07, INT-03 |
| E-13 | `emails/payment-reminder.md` | Overdue payment reminder (email + WhatsApp). | Medium | B-01, INT-01, INT-03 |
| E-14 | `emails/patient-portal-invite.md` | Patient portal access invitation with registration link. | Medium | P-11, INT-03 |
| E-15 | `emails/new-message-notification.md` | New message notification to patient or clinic. | Medium | MS-03, INT-03 |
| E-16 | `emails/daily-clinic-summary.md` | Daily summary email for clinic owner. Appointments, revenue, new patients. | Low | AN-01, INT-03 |
| E-17 | `emails/plan-upgrade-prompt.md` | Plan limit approaching / upgrade suggestion. | Low | T-09, INT-03 |
| E-18 | `emails/waitlist-slot-available.md` | Waitlist notification: slot opened. | Medium | AP-14, INT-01, INT-03 |

---

# SECTION 7: AI FEATURES (`ai/`)

AI-native features that make DentalOS the most intelligent dental platform in LATAM. Strategy doc: `ai/AI-STRATEGY.md`.

## 7.1 Strategy & Architecture

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| AI-S0 | `ai/AI-STRATEGY.md` | **AI Strategy document.** Competitive analysis (Dentalink, Overjet, Pearl, VELMENI), 12-feature roadmap across 3 tiers, pricing, cost model, architecture, security. | Critical | None |

## 7.2 Tier 1 — Competitive Parity (Sprint 35-36)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| AI-01 | `ai/radiograph-analysis.md` | **AI Radiograph Analysis.** Upload radiograph → Claude Vision identifies findings (caries, bone loss, periapical lesions) → doctor reviews per finding. Async via RabbitMQ. Adapter pattern. FDI mapping, severity scoring, JSONB findings. $20/doc/mo add-on. | Critical | V-01, I-06, INT-03 |
| AI-02 | `ai/clinical-summary.md` | **AI Clinical Summary.** Pre-appointment briefing: active conditions, pending treatments, risk alerts, action suggestions. Aggregates 9 data sources. Claude Haiku, Redis-cached 5min. Pro+ plan. | Critical | P-01, OD-01, CR-01, TP-01, AP-01, B-01 |
| AI-03 | `ai/voice-clinical-notes.md` | **AI Voice Clinical Notes.** Voice dictation → Whisper → Claude SOAP structuring → evolution note. Auto-links FDI teeth, CIE-10 diagnoses, CUPS procedures. Extends voice pipeline. $10/doc/mo (bundled with AI Voice). | Critical | V-01, V-02, V-03, CR-01 |

## 7.3 Tier 2 — Differentiation (Sprint 37-38)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| AI-04 | `ai/smile-simulator.md` | **AI Smile Simulator.** Upload smile photo → Claude Vision analysis → image generation (DALL-E/Flux) → 3 variants (conservative, moderate, ideal). Before/after slider. Portal shareable. Linked to quotations. $20/doc/mo (bundled with Radiograph). | High | AI-01, P-01 |
| AI-05 | `ai/contact-center.md` | **AI Contact Center (Unified).** Single AI agent across WhatsApp + VoIP + web chat. 15+ intents, cross-channel context, proactive outreach (confirmations, recalls, payments). Human escalation. $25/location/mo. | High | VP-12, VP-16, VP-18 |
| AI-06 | `ai/workflow-supervisor.md` | **AI Workflow Supervisor.** 25 built-in rules + custom rules. Compliance scoring, auto-remediation, per-doctor metrics. Scheduled scan (15min) + event-driven. Resolution 1888 aware. Clinica+ plan. | High | GAP-15, I-11 |

## 7.4 Tier 3 — Leapfrog (Sprint 39-40)

| # | File Path | Description | Priority | Dependencies |
|---|-----------|-------------|----------|--------------|
| AI-07 | `ai/voice-perio-charting.md` | **AI Voice Perio Charting.** Dictate probing depths → auto-fill periodontal chart. Real-time voice → number extraction. Bundled with AI Voice. | Medium | AI-03, V-01 |
| AI-08 | `ai/treatment-acceptance-predictor.md` | **AI Treatment Acceptance Predictor.** Logistic regression per clinic. Predicts acceptance probability (0-100) from cost, history, insurance, procedure type. Score badge on quotation. Clinica+ plan. | Medium | TP-01, B-16 |
| AI-09 | `ai/patient-risk-score.md` | **AI Patient Risk Score.** 4 dimensions: caries, periodontal, no-show, payment risk. Rule-based weighted scoring. Event-driven recalculation. Color badges on patient card. Pro+ plan. | Medium | P-01, OD-01, AP-01, B-01 |
| AI-10 | `ai/smart-scheduling.md` | **AI Smart Scheduling.** Slot scoring: learned duration, no-show risk, revenue optimization, buffer time. Advisor panel next to calendar. Clinica+ plan. | Medium | AP-01, AI-09 |
| AI-11 | `ai/revenue-optimizer.md` | **AI Revenue Optimizer.** 6 analysis types: unfinished plans, recall-due, underutilized slots, upsell, pricing. Weekly digest + dashboard widget. Claude for NL insights. Enterprise plan. | Low | AN-01, AI-09 |
| AI-12 | `ai/radiograph-overlay.md` | **AI Radiograph Overlay.** Color-coded Canvas overlays on radiographs. Red=caries, yellow=bone loss, blue=restorations. Toggle per finding type. Client-side rendering. Extends AI-01. Bundled with Radiograph add-on. | Medium | AI-01 |

---

# SUMMARY STATISTICS

## Spec Count by Section

| Section | Count |
|---------|-------|
| Root Documents | 12 |
| Infrastructure (infra/) | 29 |
| Backend: Tenants | 10 |
| Backend: Auth | 11 |
| Backend: Users | 9 |
| Backend: Patients | 16 |
| Backend: Odontogram | 12 |
| Backend: Clinical Records | 17 |
| Backend: Treatment Plans | 10 |
| Backend: Consents | 9 |
| Backend: Appointments | 18 |
| Backend: Notifications | 5 |
| Backend: Billing | 19 |
| Backend: Compliance | 8 |
| Backend: Analytics | 7 |
| Backend: Patient Portal API | 13 |
| Backend: Voice-to-Odontogram | 5 |
| Backend: Inventory & Sterilization | 7 |
| Backend: Admin/Superadmin | 7 |
| Backend: Messaging | 5 |
| Backend: Prescriptions | 5 |
| Digital Signatures | 1 |
| Integrations | 10 |
| Frontend: Design System | 19 |
| Frontend: Auth Screens | 6 |
| Frontend: Dashboard | 2 |
| Frontend: Patients | 7 |
| Frontend: Odontogram | 7 |
| Frontend: Clinical Records | 7 |
| Frontend: Treatment Plans | 4 |
| Frontend: Consents | 4 |
| Frontend: Agenda | 6 |
| Frontend: Billing | 8 |
| Frontend: Settings | 9 |
| Frontend: Patient Portal | 10 |
| Frontend: Prescriptions | 3 |
| Frontend: Analytics | 4 |
| Frontend: Compliance | 3 |
| Frontend: Voice UI | 3 |
| Frontend: Inventory | 3 |
| Email/Notification Templates | 18 |
| AI Features (Strategy + 12 specs) | 13 |
| **TOTAL** | **~394** |

## Spec Count by Priority

| Priority | Sprints | Spec Count | Percentage |
|----------|---------|------------|------------|
| **Critical** | 1-4 (Month 1-2) | ~95 | 25% |
| **High** | 5-8 (Month 3-4) | ~143 | 38% |
| **Medium** | 9-12 (Month 5-6) | ~106 | 28% |
| **Low** | 13-20 (Month 7-10) | ~37 | 10% |

## Backend Endpoint Count (Estimated)

| Domain | Endpoints |
|--------|-----------|
| Tenants/Settings | 10 |
| Auth | 11 |
| Users | 9 |
| Patients | 16 |
| Odontogram | 12 |
| Clinical Records | 17 |
| Treatment Plans | 10 |
| Consents | 9 |
| Appointments | 18 |
| Notifications | 5 |
| Billing | 19 |
| Compliance | 8 |
| Analytics | 7 |
| Patient Portal | 13 |
| Voice-to-Odontogram | 5 |
| Inventory & Sterilization | 7 |
| Digital Signatures | 1 |
| Admin | 7 |
| Messaging | 5 |
| Prescriptions | 5 |
| **TOTAL ENDPOINTS** | **~195** |

---

## Recommended Implementation Order (Sprint Mapping)

### Sprint 1-2 (Month 1): Foundation
**Focus: Multi-tenant arch, auth, team management**
- All infra/core specs (I-01 through I-09)
- All infra/security specs (I-10, I-11)
- All ADRs (I-20 through I-28)
- Design system tokens + core components (FE-DS-01 through FE-DS-12, FE-DS-16, FE-DS-17)
- Root documents (R-01 through R-05, R-10 through R-12)

### Sprint 3-4 (Month 2): Auth + Patients
**Focus: Complete auth flow, patient CRUD, basic UI**
- All auth specs (A-01 through A-11)
- All auth frontend specs (FE-A-01 through FE-A-06)
- User management (U-01 through U-06)
- Patient CRUD (P-01 through P-06)
- Patient frontend (FE-P-01 through FE-P-05)
- Settings basics (T-06 through T-10, FE-S-01, FE-S-02)
- Dashboard (FE-D-01)
- Email templates: welcome, verify, password reset, invite (E-01 through E-04)

### Sprint 5-6 (Month 3): Odontogram + Clinical
**Focus: Core clinical differentiator**
- All odontogram specs (OD-01 through OD-12)
- All odontogram frontend specs (FE-OD-01 through FE-OD-07)
- Dental-specific design system components (FE-DS-18, FE-DS-19)
- Clinical records (CR-01 through CR-09)
- CIE-10/CUPS catalogs (CR-10, CR-11)
- Clinical records frontend (FE-CR-01 through FE-CR-07)
- Anamnesis (CR-05, CR-06, FE-CR-03)

### Sprint 7-8 (Month 4): Treatment Plans + Consents + Prescriptions
**Focus: Complete clinical workflow**
- Procedures (CR-12 through CR-14, FE-CR-05)
- Treatment plans (TP-01 through TP-10)
- Treatment plan frontend (FE-TP-01 through FE-TP-04)
- Consent forms (IC-01 through IC-09)
- Consent frontend (FE-IC-01 through FE-IC-03)
- Prescriptions (RX-01 through RX-05)
- Prescription frontend (FE-RX-01 through FE-RX-03)
- Signature pad component (FE-DS-14)
- File upload + storage (I-17, INT-08, FE-DS-15)
- Patient documents (P-12 through P-14)

### Sprint 9-10 (Month 5): Agenda + Notifications
**Focus: Scheduling, reminders, patient communication**
- All appointment specs (AP-01 through AP-18)
- Calendar component (FE-DS-13)
- Agenda frontend (FE-AG-01 through FE-AG-06)
- WhatsApp integration (INT-01)
- SMS integration (INT-02)
- Notification engine (N-01 through N-05)
- Appointment email/notification templates (E-05 through E-08, E-18)
- Public booking (AP-15, AP-16, FE-PP-10)

### Sprint 11-12 (Month 6): Billing + Patient Portal
**Focus: Revenue and patient experience**
- All billing specs (B-01 through B-15)
- Billing frontend (FE-B-01 through FE-B-08)
- Patient portal API (PP-01 through PP-13)
- Patient portal frontend (FE-PP-01 through FE-PP-09)
- Messaging (MS-01 through MS-05, FE-PP-06)
- Analytics (AN-01 through AN-06)
- Analytics frontend (FE-AN-01 through FE-AN-04)
- Billing email templates (E-11 through E-13)
- Remaining email templates (E-09, E-10, E-14 through E-17)

### Sprint 13-16 (Month 7-8): Compliance + Offline
**Focus: Colombia regulatory compliance, offline**
- All compliance specs (CO-01 through CO-08)
- Compliance frontend (FE-CO-01 through FE-CO-03)
- Electronic invoicing integrations (INT-04 through INT-06)
- Data retention (I-12)
- HIPAA/LATAM compliance (I-13)
- Offline sync (I-18, I-19)
- Audit trail (AN-07, FE-S-09)
- Payment gateway (INT-07)
- Settings: compliance, integrations (FE-S-07, FE-S-08)

### Sprint 17-20 (Month 9-10): Beta + Launch
**Focus: Hardening, testing, Colombia launch**
- Patient merge (P-10)
- Consent template editor (FE-IC-04)
- Google Calendar sync (INT-09)
- Admin/superadmin (AD-01 through AD-07)
- Feature flags (AD-05)
- Remaining infra (I-14 through I-16)
- Deployment, monitoring, backup specs
- Daily summary emails (E-16)
- Plan upgrade prompts (E-17)
- Bug fixes, performance, UAT

---

## Dependency Graph (Critical Path)

```
I-01 (Multi-tenancy)
 |
 +-- I-04 (Database Architecture)
 |    |
 |    +-- T-01 (Tenant Provisioning)
 |         |
 |         +-- A-01 (Register) --> A-02 (Login) --> A-03 (Refresh)
 |         |    |
 |         |    +-- A-09 (Invite) --> A-10 (Accept Invite)
 |         |
 |         +-- T-06 (Settings) --> T-10 (Onboarding)
 |
 +-- I-02 (Auth Rules)
 |    |
 |    +-- U-01 (User Profile) --> U-03 (Team List)
 |
 +-- I-05 (Cache) + I-06 (Queue) + I-07 (Rate Limit)
 |
 +-- P-01 (Patient Create)
      |
      +-- OD-01 (Odontogram Get) --> OD-02 (Update Condition)
      |
      +-- CR-01 (Clinical Record) --> CR-07 (Diagnosis) --> TP-01 (Treatment Plan)
      |
      +-- AP-01 (Appointment Create) --> AP-09 (Availability)
      |
      +-- B-01 (Invoice Create) --> B-07 (Payment Record)
      |
      +-- IC-04 (Consent Create) --> IC-05 (Consent Sign)
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial complete SDD master index |
| 1.1 | 2026-02-24 | Client interview update: Business model table added (Free/Starter/Pro/Clinica/Enterprise + add-ons). New sections: 3.15 Voice-to-Odontogram (V-01 to V-05), 3.16 Inventory & Sterilization (INV-01 to INV-07), 4.5 Digital Signatures (DS-01). New specs: CR-15 to CR-17 (evolution templates), B-16 to B-19 (quotations), P-15 to P-16 (referrals, tooth photos), INT-10 (DIAN MATIAS). Frontend: 5.16 Voice UI (FE-V-01 to FE-V-03), 5.17 Inventory (FE-INV-01 to FE-INV-03). Total: 352 → 381 specs. |

---

*This document was generated as the master plan for DentalOS spec-driven development. Each file listed above should be written following the corresponding template (SPEC_TEMPLATE.md for backend APIs, FRONTEND_SPEC_TEMPLATE.md for screens, infrastructure format for infra specs).*
