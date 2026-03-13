# DentalOS -- Implementation Checklist (R-05)

## Overview

This is the **living sprint-by-sprint implementation tracker** for DentalOS, a cloud-native multi-tenant dental SaaS for LATAM.

| Attribute           | Value                                         |
|---------------------|-----------------------------------------------|
| Total Sprints       | 32 (20 pre-launch + 12 post-launch) + backlog |
| Sprint Duration     | 2 weeks each                                  |
| Total Specs Mapped  | ~530 (incl. competitive gap closures)         |
| Launch Target       | Colombia first, then Mexico expansion          |
| Tech Stack          | FastAPI + Next.js + PostgreSQL + Redis + RabbitMQ |
| Hosting             | Hetzner Cloud                                 |

**How to use:** Check off items `[x]` as they are completed. This file is the single source of truth for development progress. Update after every sprint review.

> **North Star (from client interview):** "Si no es más rápido que el papel, fallamos." Every interaction must be measured against its analog equivalent. If the agenda is slower than paper, if the odontogram is slower than dictating to an assistant -- we have failed.

---

## Pricing Model

| Plan | Price | Limits |
|------|-------|--------|
| Free | $0 | 50 patients, 1 doctor |
| Starter | $19/doctor/mo | Unlimited patients |
| Pro | $39/doctor/mo | All features |
| Clinica | $69/location/mo | Includes 3 doctors, +$15/additional doctor |
| Enterprise | Custom | Multi-location, SLA, dedicated support |
| **Add-on:** AI Voice | +$10/doc/mo | Voice-to-Odontogram dictation |
| **Add-on:** AI Radiograph | +$20/doc/mo | Radiograph AI analysis |
| **Add-on:** AI Treatment Advisor | +$5/doc/mo | AI-powered treatment recommendations (VP-13) |
| **Add-on:** Patient Engagement Suite | +$15/loc/mo | Recall/reactivation engine + email campaigns (VP-02, VP-17) |
| **Add-on:** Membership Plans | +$15/loc/mo | Patient subscription/membership management (VP-01) |
| **Add-on:** Reputation Manager | +$10/loc/mo | Review routing + NPS/CSAT surveys (VP-09, VP-21) |
| **Add-on:** Virtual Receptionist | +$10/loc/mo | AI chatbot on WhatsApp + web (VP-16) |
| **Add-on:** Telehealth | +$15/loc/mo | Video consultations (post-MVP roadmap) |

---

## Sprint 1-2: Foundation Infrastructure (Month 1)

**Goal:** Scaffold the entire project, establish multi-tenant architecture, implement authentication, and set up CI/CD.

**Spec count target:** ~42 specs (Infrastructure + Auth + Tenants)

### Project Scaffolding

- [x] FastAPI backend project structure with Poetry/uv dependency management
- [x] Next.js 16 frontend project with TailwindCSS and TypeScript
- [x] Docker Compose for local development (PostgreSQL, Redis, RabbitMQ)
- [-] Monorepo or polyrepo structure decision finalized (see ADR-LOG) — *Deferred — polyrepo structure in use*

### Infrastructure Core (I-01 through I-09)

- [x] **I-01** Multi-tenancy: Schema-per-tenant architecture implemented
  - [x] Tenant schema creation on provisioning
  - [x] Tenant resolution from request (JWT tid claim)
  - [x] Tenant isolation guarantees validated
  - [x] Shared `public` schema for tenants, plans, superadmin tables
- [x] **I-04** Database architecture: PostgreSQL schema-per-tenant
  - [x] Alembic migration runner (per-tenant schema migrations)
  - [x] Connection pool configuration (pool_size, max_overflow in config)
  - [x] Shared schema template for new tenants
- [x] **I-02** Authentication system: JWT RS256
  - [x] Access token generation (15min expiry)
  - [x] Refresh token with rotation (30d expiry, single-use)
  - [x] Replay detection on refresh tokens
  - [x] Revocation on reuse
- [x] **I-02** RBAC middleware with 6 roles
  - [x] clinic_owner role and permissions
  - [x] doctor role and permissions
  - [x] assistant role and permissions
  - [x] receptionist role and permissions
  - [x] patient role and permissions
  - [x] superadmin role and permissions
  - [x] Permission matrix enforcement on all endpoints
- [x] **I-03** Error handling framework
  - [x] HTTP status code mapping
  - [x] Error response schema: `{error, message, details}`
  - [x] Error codes registry
  - [x] Backend exception handling (Python/FastAPI)
  - [x] Logging patterns for structured JSON output
- [x] **I-05** Redis caching layer
  - [x] Cache key namespacing per tenant
  - [x] TTL policies defined and implemented
  - [x] Session cache for active users
  - [x] Plan limits cache for fast enforcement
- [x] **I-06** RabbitMQ setup
  - [x] Queue topology defined (email, SMS, WhatsApp, audit, reports)
  - [x] Worker process scaffolding
  - [x] Retry policies and dead letter queues
  - [x] Priority queue for critical tasks
- [x] **I-07** Rate limiting
  - [x] Per-tenant rate limits
  - [x] Per-user rate limits
  - [x] Per-IP rate limits
  - [x] Endpoint-specific overrides (auth endpoints stricter)
  - [x] Redis-based sliding window implementation
- [x] **I-08** Testing infrastructure
  - [x] pytest configuration with async support
  - [x] Test database provisioning (per-tenant test schemas)
  - [x] Factory patterns: patients, teeth, appointments, users
  - [x] Mock external services (WhatsApp, SMS, email)
  - [x] Coverage target: 80% minimum
- [x] **I-09** Local development environment
  - [x] Docker Compose stack validated and documented
  - [x] Seed data script (demo tenant, demo users, sample patients)
  - [x] Tenant provisioning CLI script
  - [x] Environment variables template (.env.example)

### Security and Compliance Foundation

- [x] **I-10** Security policy: HTTPS, CORS, CSP headers, input sanitization
- [x] **I-11** Audit logging: Immutable audit trail per tenant
- [x] **I-14** Deployment architecture: Hetzner Cloud baseline plan -- docker-compose.prod.yml (7 services), .env.production template, Nginx reverse proxy, setup-server.sh + first-deploy.sh scripts, CD workflow with worker

### Architecture Decision Records (ADRs)

- [x] **I-20** ADR-001: Schema-per-tenant rationale
- [x] **I-21** ADR-002: FastAPI over Django rationale
- [x] **I-22** ADR-003: PostgreSQL over alternatives rationale
- [x] **I-23** ADR-004: Hetzner over AWS/GCP rationale
- [x] **I-27** ADR-008: RabbitMQ over Celery+Redis rationale

### Backend: Authentication Endpoints (A-01 through A-11)

- [x] **A-01** `POST /api/v1/auth/register` -- Register new clinic (creates tenant + first clinic_owner)
- [x] **A-02** `POST /api/v1/auth/login` -- Login with email + password, returns JWT; **must support multi-clinic selector when a doctor belongs to 2-6 clinics (clinic is selected at login time, token encodes clinic context)**
- [x] **A-03** `POST /api/v1/auth/refresh-token` -- Token rotation
- [x] **A-04** `GET /api/v1/auth/me` -- Current user profile with tenant context
- [x] **A-05** `POST /api/v1/auth/forgot-password` -- Send password reset email
- [x] **A-06** `POST /api/v1/auth/reset-password` -- Reset via token
- [x] **A-07** `POST /api/v1/auth/change-password` -- Change password (authenticated)
- [x] **A-08** `POST /api/v1/auth/logout` -- Revoke refresh token
- [x] **A-09** `POST /api/v1/auth/invite` -- Invite team member with role
- [x] **A-10** `POST /api/v1/auth/accept-invite` -- Accept invitation, set password
- [x] **A-11** `POST /api/v1/auth/verify-email` -- Email verification

### Backend: Tenant Management Endpoints (T-01 through T-10)

- [x] **T-01** `POST /api/v1/admin/tenants` -- Create/provision new tenant
- [x] **T-02** `GET /api/v1/admin/tenants/{tenant_id}` -- Get tenant details
- [x] **T-03** `GET /api/v1/admin/tenants` -- List all tenants
- [x] **T-04** `PUT /api/v1/admin/tenants/{tenant_id}` -- Update tenant
- [x] **T-05** `POST /api/v1/admin/tenants/{tenant_id}/suspend` -- Suspend tenant
- [x] **T-06** `GET /api/v1/settings` -- Get current tenant settings
- [x] **T-07** `PUT /api/v1/settings` -- Update tenant settings
- [x] **T-08** `GET /api/v1/settings/usage` -- Plan usage stats
- [x] **T-09** `GET /api/v1/settings/plan-limits` -- Plan limits check
- [x] **T-09b** `GET /api/v1/settings/addons` -- Get tenant add-ons state
- [x] **T-09c** `PUT /api/v1/settings/addons` -- Toggle tenant add-on (voice_dictation, radiograph_ai)
- [x] **T-09d** Alembic migration: add `addons` JSONB column to `public.tenants`
- [x] **T-09e** Merge `tenant.addons` into `TenantContext.features` (addons override plan features)
- [x] **T-10** `POST /api/v1/onboarding` -- Multi-step onboarding wizard
- [x] Integration tests: `tests/integration/test_tenants/` (T-01 through T-10, settings, onboarding)

### CI/CD and DevOps

- [x] GitHub Actions CI pipeline: lint, type-check, test, build
- [x] GitHub Actions CD pipeline: deploy to staging on merge to develop
- [x] Pre-commit hooks: black, ruff, mypy (backend); eslint, prettier (frontend)
- [x] Docker image builds for backend and frontend

### Email Templates (Critical)

- [x] **E-01** Welcome email after clinic registration
- [x] **E-02** Email verification link
- [x] **E-03** Password reset link email
- [x] **E-04** Team member invitation email
- [x] **INT-03** Email delivery engine (SendGrid/SES) baseline integration

---

## Sprint 3-4: Core Entities (Month 2)

**Goal:** Implement user management, patient CRUD, design system, and core frontend screens.

**Spec count target:** ~53 specs (Users + Patients + Design System + Auth/Dashboard/Patient/Settings screens)

### Backend: User Management (U-01 through U-06)

- [x] **U-01** `GET /api/v1/users/me` -- Get own profile
- [x] **U-02** `PUT /api/v1/users/me` -- Update own profile
- [x] **U-03** `GET /api/v1/users` -- List team members (filterable by role, status)
- [x] **U-04** `GET /api/v1/users/{user_id}` -- Get team member profile
- [x] **U-05** `PUT /api/v1/users/{user_id}` -- Update team member (change role, deactivate)
- [x] **U-06** `POST /api/v1/users/{user_id}/deactivate` -- Soft-delete team member

### Backend: Patient CRUD (P-01 through P-06)

- [x] **P-01** `POST /api/v1/patients` -- Create patient (plan limit check included)
- [x] **P-02** `GET /api/v1/patients/{patient_id}` -- Get patient full profile
- [x] **P-03** `GET /api/v1/patients` -- List patients with search, pagination, filters
- [x] **P-04** `PUT /api/v1/patients/{patient_id}` -- Update patient profile
- [x] **P-05** `POST /api/v1/patients/{patient_id}/deactivate` -- Soft-delete patient
- [x] **P-06** `GET /api/v1/patients/search` -- PostgreSQL FTS typeahead search (name, document, phone); **predictive search: 3 letters triggers suggestions, target latency ≤100ms; this is a primary daily workflow**

### Backend: Patient Documents (P-12 through P-14)

- [x] **P-12** `GET /api/v1/patients/{patient_id}/documents` -- List patient documents
- [x] **P-13** `POST /api/v1/patients/{patient_id}/documents` -- Upload document (X-ray, consent, lab result)
- [x] **P-14** `DELETE /api/v1/patients/{patient_id}/documents/{doc_id}` -- Delete document
- [x] **I-17** File storage architecture: S3-compatible with tenant-isolated buckets
- [x] **INT-08** Cloud storage integration (Hetzner Object Storage or MinIO)

### Frontend: Design System (FE-DS-01 through FE-DS-19)

- [x] **I-28** Design system spec: color palette, typography, spacing, TailwindCSS config
- [x] **I-29** Responsive breakpoints: mobile-first, tablet optimization for clinical use
- [x] **FE-DS-01** Design tokens: colors, typography (Inter/system), spacing, shadows
- [x] **FE-DS-02** Button component (primary, secondary, outline, ghost, danger)
- [x] **FE-DS-03** Input component (text, email, password, number, phone, date, textarea)
- [x] **FE-DS-04** Select/Combobox component (searchable, async loading)
- [x] **FE-DS-05** Data table component (sortable, paginated, responsive)
- [x] **FE-DS-06** Modal/Dialog component (sm, md, lg, full)
- [x] **FE-DS-07** Toast/notification component (success, error, warning, info)
- [x] **FE-DS-08** Navigation sidebar (collapsible, role-based visibility)
- [x] **FE-DS-09** App header (clinic name, user menu, notifications, search)
- [x] **FE-DS-10** Card component (default, elevated, outlined)
- [x] **FE-DS-11** Badge/pill component (status badges, condition badges)
- [x] **FE-DS-12** Avatar component (image, initials fallback, status indicator)
- [x] **FE-DS-14** Signature pad component (canvas drawing, base64 export)
- [x] **FE-DS-15** File upload component (drag-and-drop, preview, progress)
- [x] **FE-DS-16** Empty state component (illustration + message + CTA)
- [x] **FE-DS-17** Skeleton loader component

### Frontend: Auth Screens (FE-A-01 through FE-A-06)

- [x] **FE-A-01** Registration page (multi-step: email/password, clinic info, plan selection)
- [x] **FE-A-02** Login page (email + password, forgot password link, **multi-clinic selector shown when user belongs to more than one clinic**)
- [x] **FE-A-03** Forgot password page
- [x] **FE-A-04** Reset password page
- [x] **FE-A-05** Accept invitation page
- [x] **FE-A-06** Post-registration onboarding wizard (4 steps)

### Frontend: Dashboard (FE-D-01, FE-D-02)

- [x] **FE-D-01** Main dashboard (today's appointments, new patients, revenue, pending plans)
- [x] **FE-D-02** Doctor-specific dashboard (my appointments, my patients, my procedures)

### Frontend: Patient Screens (FE-P-01 through FE-P-05)

- [x] **FE-P-01** Patient list page (table + search + filters + responsive card view)
- [x] **FE-P-02** Create patient form (personal info, contact, medical, insurance)
- [x] **FE-P-03** Patient detail page (tabbed: overview, odontogram, records, plans, appointments, billing, docs)
- [x] **FE-P-04** Edit patient form
- [x] **FE-P-05** Global patient search (typeahead in header bar, ≤100ms, predictive after 3 characters)

### Frontend: Settings Screens (FE-S-01, FE-S-02, FE-S-03)

- [x] **FE-S-01** Clinic settings page (name, address, phone, logo, country, timezone)
- [x] **FE-S-02** Team management page (list users, invite, edit roles, deactivate)
- [x] **FE-S-03** Subscription plan page (current plan, usage meters, upgrade options)
- [x] **FE-S-03b** Complementos (add-ons) section in subscription page with toggle cards
- [x] **FE-S-03c** Fix voice upsell links: `/settings/billing` → `/settings/subscription`
- [x] **FE-S-03d** `useAddons()` and `useToggleAddon()` hooks

---

## Sprint 5-6: Clinical Core Part 1 (Month 3)

**Goal:** Implement the odontogram (core differentiator), begin clinical records, load evolution templates, and introduce the service/price catalog needed for quotation flow.

**Spec count target:** ~46 specs (Odontogram + Clinical Records foundation + Anamnesis + Evolution Templates + Service Catalog)

### Backend: Odontogram (OD-01 through OD-12)

- [x] **OD-01** `GET /api/v1/patients/{patient_id}/odontogram` -- Get current state (32 adult / 20 pediatric teeth, 6 zones each)
- [x] **OD-02** `POST /api/v1/patients/{patient_id}/odontogram/conditions` -- Add/update condition on tooth zone
- [x] **OD-03** `DELETE /api/v1/patients/{patient_id}/odontogram/conditions/{condition_id}` -- Remove condition
- [x] **OD-04** `GET /api/v1/patients/{patient_id}/odontogram/history` -- Change history timeline
- [x] **OD-05** `POST /api/v1/patients/{patient_id}/odontogram/snapshots` -- Create point-in-time snapshot
- [x] **OD-06** `GET /api/v1/patients/{patient_id}/odontogram/snapshots/{snapshot_id}` -- Get snapshot
- [x] **OD-07** `GET /api/v1/patients/{patient_id}/odontogram/snapshots` -- List all snapshots
- [x] **OD-08** `GET /api/v1/patients/{patient_id}/odontogram/compare` -- Compare two snapshots (diff)
- [x] **OD-09** `GET /api/v1/catalog/conditions` -- Conditions catalog (12 conditions with codes, colors, SVG data)
- [x] **OD-10** `GET /api/v1/patients/{patient_id}/odontogram/teeth/{tooth_number}` -- Single tooth detail
- [x] **OD-11** `POST /api/v1/patients/{patient_id}/odontogram/bulk` -- Bulk update (initial examination)
- [x] **OD-12** `POST /api/v1/patients/{patient_id}/odontogram/dentition` -- Toggle adult/pediatric

### Frontend: Odontogram (FE-OD-01 through FE-OD-07)

- [x] **I-24** ADR-005: SVG-based odontogram rendering approach
- [x] **FE-OD-01** Classic grid odontogram (32/20 teeth, 5 crown zones + root, color-coded)
- [x] **FE-OD-02** Anatomic arch odontogram (SVG-based, interactive zoom -- premium tier)
- [x] **FE-OD-03** Condition selection panel (12 conditions with icons, quick-select, notes)
- [x] **FE-OD-04** History panel (sidebar timeline of changes, filter by date/condition)
- [-] **FE-OD-05** Comparison view (side-by-side snapshots, visual diff) — *Deferred to Sprint 11+ — backend ready*
- [x] **FE-OD-06** Tooth detail panel (conditions, history, linked treatments, X-rays)
- [x] **FE-OD-07** Odontogram toolbar (mode toggle, adult/pediatric, zoom, print, snapshot)
- [x] **FE-DS-18** Tooth selector widget (interactive, FDI notation)
- [x] **FE-DS-19** Condition icon component (color-coded badges per condition type)

### Backend: Clinical Records Foundation (CR-01 through CR-06)

- [x] **CR-01** `POST /api/v1/patients/{patient_id}/clinical-records` -- Create record (anamnesis, examination, diagnosis, evolution, procedure)
- [x] **CR-02** `GET /api/v1/patients/{patient_id}/clinical-records/{record_id}` -- Get record
- [x] **CR-03** `GET /api/v1/patients/{patient_id}/clinical-records` -- List records (filterable)
- [x] **CR-04** `PUT /api/v1/patients/{patient_id}/clinical-records/{record_id}` -- Update (24h window, audit logged)
- [x] **CR-05** `POST /api/v1/patients/{patient_id}/anamnesis` -- Create/update anamnesis
- [x] **CR-06** `GET /api/v1/patients/{patient_id}/anamnesis` -- Get current anamnesis

### Backend: Catalog Search (CR-10, CR-11)

- [x] **CR-10** `GET /api/v1/catalog/cie10` -- CIE-10 code search (dental subset, Spanish FTS, cached)
- [x] **CR-11** `GET /api/v1/catalog/cups` -- CUPS procedure code search (dental subset, FTS)

### Backend: Evolution Templates (CR-15, CR-16, CR-17)

Evolution templates are MVP Phase 1 -- clinical procedure templates reduce charting time for common procedures.

- [x] **CR-15** `GET /api/v1/evolution-templates` -- List evolution templates (built-in + custom, filterable by procedure type)
- [x] **CR-16** `POST /api/v1/evolution-templates` -- Create custom evolution template (rich text with placeholders)
- [x] **CR-17** `POST /api/v1/patients/{patient_id}/clinical-records/from-template` -- Create record from template (template_id + tooth overrides)
- [x] Seed data: 5-10 built-in procedure templates loaded at tenant creation:
  - [x] Resina compuesta (composite resin)
  - [x] Endodoncia unirradicular / birradicular / trirradicular
  - [x] Exodoncia simple / quirurgica
  - [x] Profilaxis y detartraje
  - [x] Corona ceramica
  - [x] Blanqueamiento dental
  - [x] Consulta de primera vez / urgencia
  - [x] Cirugía de tercer molar incluido
  - [x] Raspaje y alisado radicular
  - [x] Sellante de fotocurado
  - [x] `app/cli/seed_evolution_templates.py` — 10 built-in templates with steps + variables
  - [x] `app/cli/seed_catalogs.py` — 79 CIE-10 + 79 CUPS codes (public schema, idempotent)
  - [x] `app/cli/seed_service_catalog.py` — 74 services with COP cent prices (tenant schema, idempotent)

### Backend: Service/Price Catalog (B-14, B-15)

Moved to Sprint 5-6 because the service catalog is required for the auto-quotation flow in Sprint 7-8.

- [x] **B-14** `GET /api/v1/services` -- Service/procedure price catalog (searchable by name, CUPS code)
- [x] **B-15** `PUT /api/v1/services/{service_id}` -- Update service price (supports per-doctor override)

---

## Sprint 7-8: Clinical Core Part 2 (Month 4)

**Goal:** Complete clinical records, treatment plans, consents, prescriptions, auto-quotation flow, digital signature, and tooth photo attachments.

**Spec count target:** ~57 specs

### Backend: Diagnoses (CR-07 through CR-09)

- [x] **CR-07** `POST /api/v1/patients/{patient_id}/diagnoses` -- Create diagnosis (CIE-10, tooth link)
- [x] **CR-08** `GET /api/v1/patients/{patient_id}/diagnoses` -- List diagnoses (active/resolved)
- [x] **CR-09** `PUT /api/v1/patients/{patient_id}/diagnoses/{diagnosis_id}` -- Update diagnosis

### Backend: Procedures (CR-12 through CR-14)

- [x] **CR-12** `POST /api/v1/patients/{patient_id}/procedures` -- Record procedure (CUPS code, tooth, auto-update odontogram)
- [x] **CR-13** `GET /api/v1/patients/{patient_id}/procedures` -- List procedures
- [x] **CR-14** `GET /api/v1/patients/{patient_id}/procedures/{procedure_id}` -- Get procedure detail

### Backend: Treatment Plans (TP-01 through TP-10)

- [x] **TP-01** `POST /api/v1/patients/{patient_id}/treatment-plans` -- Create plan
- [x] **TP-02** `GET /api/v1/patients/{patient_id}/treatment-plans/{plan_id}` -- Get plan with items and costs
- [x] **TP-03** `GET /api/v1/patients/{patient_id}/treatment-plans` -- List plans (draft/active/completed)
- [x] **TP-04** `PUT /api/v1/patients/{patient_id}/treatment-plans/{plan_id}` -- Update plan metadata/status
- [x] **TP-05** `POST /api/v1/patients/{patient_id}/treatment-plans/{plan_id}/items` -- Add item to plan
- [x] **TP-06** `PUT /api/v1/patients/{patient_id}/treatment-plans/{plan_id}/items/{item_id}` -- Update item
- [x] **TP-07** `POST .../items/{item_id}/complete` -- Mark item completed, link to procedure
- [x] **TP-08** `POST .../treatment-plans/{plan_id}/approve` -- Patient approval with digital signature
- [x] **TP-09** `GET .../treatment-plans/{plan_id}/pdf` -- Generate PDF with clinic branding
- [x] **TP-10** `POST .../treatment-plans/{plan_id}/share` -- Share via email/WhatsApp

### Backend: Auto-Quotation Flow (B-16, B-17, B-18, B-19)

The Odontogram → Treatment Plan → Quotation flow must be seamless. Conditions on the odontogram should auto-suggest procedures from the service catalog with prices already populated.

- [x] **B-16** `POST /api/v1/patients/{patient_id}/quotations` -- Generate quotation from treatment plan items (auto-prices from service catalog)
- [x] **B-17** `GET /api/v1/patients/{patient_id}/quotations/{quotation_id}` -- Get quotation detail with line items and totals
- [x] **B-18** `POST /api/v1/patients/{patient_id}/quotations/{quotation_id}/share` -- Share quotation via email/WhatsApp with payment link
- [x] **B-19** `POST /api/v1/patients/{patient_id}/quotations/{quotation_id}/convert` -- Convert approved quotation into invoice

### Backend: Digital Signature (DS-01)

Required for treatment plan approvals and consent forms. Colombia Ley 527/1999 (e-commerce/digital signature law).

- [x] **DS-01** Digital signature service: capture signature image (canvas), store as PNG, embed in PDF, log timestamp + IP + user-agent for legal validity per Ley 527/1999
  - [x] Signature metadata: signer name, role (patient/doctor/clinic_owner), timestamp (UTC), IP address, user-agent
  - [x] Audit log entry for every signature event
  - [x] PDF embedding: signature image + signature block with metadata

### Backend: Tooth Photo Attachment (P-16)

- [x] **P-16** `POST /api/v1/patients/{patient_id}/odontogram/teeth/{tooth_number}/photos` -- Attach photo to specific tooth (max 2 taps from odontogram view); `GET` and `DELETE` variants
  - [x] S3-compatible upload with tenant isolation
  - [x] Photo linked to tooth number + odontogram state version
  - [x] Thumbnail generation for gallery view

### Backend: Consent Management (IC-01 through IC-09)

- [x] **IC-01** `GET /api/v1/consent-templates` -- List templates (built-in + custom)
- [x] **IC-02** `POST /api/v1/consent-templates` -- Create custom template
- [x] **IC-03** `GET /api/v1/consent-templates/{template_id}` -- Get template detail
- [x] **IC-04** `POST /api/v1/patients/{patient_id}/consents` -- Create consent from template
- [x] **IC-05** `POST .../consents/{consent_id}/sign` -- Sign consent (signature + timestamp + IP)
- [x] **IC-06** `GET .../consents/{consent_id}` -- Get consent detail
- [x] **IC-07** `GET /api/v1/patients/{patient_id}/consents` -- List patient consents
- [x] **IC-08** `GET .../consents/{consent_id}/pdf` -- Download signed PDF
- [x] **IC-09** `POST .../consents/{consent_id}/void` -- Void consent (clinic_owner, audit logged)

### Backend: Prescriptions (RX-01 through RX-05)

- [x] **RX-01** `POST /api/v1/patients/{patient_id}/prescriptions` -- Create prescription
- [x] **RX-02** `GET .../prescriptions/{rx_id}` -- Get prescription
- [x] **RX-03** `GET /api/v1/patients/{patient_id}/prescriptions` -- List prescriptions
- [x] **RX-04** `GET .../prescriptions/{rx_id}/pdf` -- Generate prescription PDF
- [x] **RX-05** `GET /api/v1/catalog/medications` -- Medication catalog search

### Frontend: Clinical Records Screens (FE-CR-01 through FE-CR-07)

- [x] **FE-CR-01** Clinical records list (table with type icon, date, doctor, expandable preview)
- [x] **FE-CR-02** Create clinical record form (dynamic per type, rich text editor, **template selector for evolution notes**)
- [x] **FE-CR-03** Anamnesis questionnaire form (structured sections)
- [x] **FE-CR-04** Diagnosis form (CIE-10 autocomplete, severity, tooth link)
- [x] **FE-CR-05** Procedure recording form (CUPS autocomplete, tooth/zone selector)
- [x] **FE-CR-06** CIE-10 search component (reusable autocomplete)
- [x] **FE-CR-07** CUPS search component (reusable autocomplete)

### Frontend: Treatment Plan Screens (FE-TP-01 through FE-TP-04)

- [x] **FE-TP-01** Treatment plan list (cards with status, progress bar, cost)
- [x] **FE-TP-02** Create treatment plan form (add items, CUPS search, drag reorder, totals, **auto-price from service catalog**)
- [x] **FE-TP-03** Treatment plan detail page (items, progress, cost breakdown, actions, **quotation generation button**)
- [x] **FE-TP-04** Treatment plan approval flow (signature pad, mobile-optimized)

### Frontend: Consent Screens (FE-IC-01 through FE-IC-04)

- [x] **FE-IC-01** Consent forms list (status badges, template name, date)
- [x] **FE-IC-02** Create consent form (select template, preview, send/sign)
- [x] **FE-IC-03** Consent signing screen (scroll-to-read, signature pad, submit)
- [x] **FE-IC-04** Custom consent template editor (rich text, placeholders, preview)

### Frontend: Prescription Screens (FE-RX-01 through FE-RX-03)

- [x] **FE-RX-01** Create prescription form (medication autocomplete, dosage, multiple meds)
- [x] **FE-RX-02** Prescription list (date, medications, doctor, PDF download)
- [x] **FE-RX-03** Prescription preview/print view (formatted like prescription pad)

### Patient Medical History

- [x] **P-07** `GET /api/v1/patients/{patient_id}/medical-history` -- Full timeline
- [x] **FE-P-07** Medical history timeline in patient detail

### Email Templates

- [x] **E-09** Treatment plan shared with patient
- [x] **E-10** Consent form signature request

---

## Sprint 9-10: Agenda and Voice (Month 5)

**Goal:** Implement the full appointment lifecycle, scheduling, calendar views, waitlist, public booking, and Voice-to-Odontogram v1 -- the core differentiator.

> **Agenda North Star:** "If it is not faster than paper, we failed." Max 3 taps to schedule an appointment. Daily view is the DEFAULT (not weekly). Duration is intelligent: auto-calculated based on appointment type (eval = 20 min, endodontics = 1h20, etc.).

**Spec count target:** ~50 specs

### Backend: Appointments (AP-01 through AP-08)

- [x] **AP-01** `POST /api/v1/appointments` -- Create appointment (validates schedule + conflicts); **target: appointment creation completable in ≤3 taps from agenda screen**
- [x] **AP-02** `GET /api/v1/appointments/{appointment_id}` -- Get appointment detail
- [x] **AP-03** `GET /api/v1/appointments` -- List appointments (filters: doctor, patient, date, status)
- [x] **AP-04** `PUT /api/v1/appointments/{appointment_id}` -- Update/reschedule appointment
- [x] **AP-05** `POST .../appointments/{appointment_id}/cancel` -- Cancel with reason
- [x] **AP-06** `POST .../appointments/{appointment_id}/confirm` -- Patient confirmation
- [x] **AP-07** `POST .../appointments/{appointment_id}/complete` -- Complete, link to clinical records
- [x] **AP-08** `POST .../appointments/{appointment_id}/no-show` -- Mark no-show

### Backend: Scheduling and Availability (U-07, U-08, AP-09 through AP-11)

- [x] **U-07** `GET /api/v1/users/{user_id}/schedule` -- Get doctor weekly schedule
- [x] **U-08** `PUT /api/v1/users/{user_id}/schedule` -- Set doctor schedule (days, times, breaks)
- [x] **AP-09** `GET /api/v1/appointments/availability` -- Available slots query; **intelligent duration: auto-calculate default slot length based on appointment type**
- [x] **AP-10** `POST /api/v1/appointments/availability/block` -- Block time (vacation, meeting)
- [x] **AP-11** `PUT .../appointments/{appointment_id}/reschedule` -- Quick drag-and-drop reschedule

### Backend: Waitlist (AP-12 through AP-14)

- [x] **AP-12** `POST /api/v1/appointments/waitlist` -- Add to waitlist
- [x] **AP-13** `GET /api/v1/appointments/waitlist` -- List waitlist entries
- [x] **AP-14** `POST .../waitlist/{entry_id}/notify` -- Notify of available slot

### Backend: Public Booking (AP-15, AP-16)

- [x] **AP-15** `POST /api/v1/public/booking/{tenant_slug}` -- Patient self-booking (public endpoint)
- [x] **AP-16** `GET /api/v1/public/booking/{tenant_slug}/config` -- Booking page configuration

### Backend: Reminders (AP-17, AP-18)

- [x] **AP-17** `GET /api/v1/settings/reminders` -- Reminder configuration
- [x] **AP-18** `PUT /api/v1/settings/reminders` -- Update reminder configuration

### Backend: Voice-to-Odontogram v1 (V-01 through V-05)

Voice dictation is THE core differentiator per the client interview. Moved up from post-MVP. Pipeline: Audio → OpenAI Whisper → LLM (Claude) → Structured JSON → Odontogram API. Requires the AI Voice add-on ($10/mo).

- [x] **V-01** `POST /api/v1/voice/sessions` -- Start voice recording session (returns session_id, presigned S3 upload URL)
- [x] **V-02** `POST /api/v1/voice/sessions/{session_id}/upload` -- Submit audio file, trigger Whisper transcription (async)
- [x] **V-03** `GET /api/v1/voice/sessions/{session_id}` + `POST .../parse` -- Poll for transcription status + trigger LLM parsing; returns structured JSON (tooth numbers, conditions, procedures)
- [x] **V-04** `POST /api/v1/voice/sessions/{session_id}/apply` -- Apply parsed result to odontogram (review-before-apply mode: user confirms before write)
- [x] **V-05** `POST /api/v1/voice/sessions/{session_id}/feedback` -- Submit correction feedback (tooth number errors, condition mismatches) for quality tracking
  - [x] OpenAI Whisper API integration (external dependency, requires API key) -- MVP: stub in voice_worker.py
  - [x] Anthropic Claude API integration for dental NLP parsing (external dependency, requires API key) -- MVP: stub in voice_service._parse_dental_text()
  - [x] LLM prompt: extract tooth numbers (FDI), conditions (caries, fracture, crown, etc. — English codes), procedures from free-form Spanish dental dictation
  - [x] Review-before-apply mode: parsed results shown as diff before commit to odontogram
  - [x] Accuracy tracking: log correction rate per session for quality monitoring
  - [x] Feature gate: AI Voice add-on plan check before allowing voice sessions
  - [x] **V-HARDEN** Voice pipeline hardening: 4 critical bugs (CHECK constraints, failed transcriptions stuck pending, silent NLP failures), 8 high-severity (condition code mismatch, findings validation, input validation, audio size limit, worker null checks, session expiry), 6 medium (zone list, Anthropic guards, config consolidation, dead code). 134 tests passing.

### Frontend: Agenda Screens (FE-AG-01 through FE-AG-06)

- [x] **FE-DS-13** Calendar component (day/week/month views, event rendering, drag-and-drop)
- [x] **FE-AG-01** Main calendar view (color-coded, drag-and-drop, multi-doctor columns, **daily view as DEFAULT**)
- [x] **FE-AG-02** Create appointment modal (patient search, doctor, date/time, availability check, **appointment type auto-sets duration; whole flow completable in ≤3 taps**)
- [x] **FE-AG-03** Appointment detail modal (patient info, status, actions: confirm/complete/cancel)
- [x] **FE-AG-04** Doctor schedule editor (weekly template, drag to adjust times)
- [x] **FE-AG-05** Waitlist sidebar panel (waiting patients, one-click scheduling)
- [x] **FE-AG-06** Today's appointments view (timeline, patient status, quick actions)
- [x] **FE-PP-10** Public booking page (clinic-branded, doctor selection, time picker)

### Frontend: Voice UI (FE-V-01 through FE-V-03)

- [x] **FE-V-01** Voice recording button (floating action in odontogram screen, tap to start/stop, recording indicator with waveform animation)
- [x] **FE-V-02** Transcription review panel (parsed teeth and conditions displayed as a diff over current odontogram, confirm/reject each change, apply button)
- [x] **FE-V-03** Voice session history (list of past sessions, transcription text, applied/rejected status, accuracy feedback)
- [x] **FE-V-04** Voice recording resilience — 7-layer defense against audio loss: IndexedDB chunk persistence, upload retry with exponential backoff, backend idempotency (X-Idempotency-Key), visibilitychange flush (iOS Safari), recovery banner for orphaned recordings, Serwist BackgroundSyncPlugin, navigator.storage.persist()

### Frontend: Settings

- [x] **FE-S-04** Odontogram configuration (mode, default view, condition colors)
- [x] **FE-S-05** Notification settings (reminder timing, channels, templates)
- [x] **FE-AG-SCH** Doctor schedule settings page (`/settings/schedule` — weekly hours, breaks, duration defaults)
- [x] **FE-AG-VOI** Voice settings page (`/settings/voice` — enable toggle, max session duration, max sessions/hour)
- [x] **use-schedule** TanStack Query hooks: `useDoctorSchedule`, `useUpdateSchedule`, `useAvailabilityBlocks`, `useCreateBlock`, `useDeleteBlock`, `useAvailableSlots`
- [x] **use-waitlist** TanStack Query hooks: `useWaitlist`, `useAddToWaitlist`, `useNotifyWaitlistEntry`

### Email Templates

- [x] **E-05** Appointment confirmation (email + WhatsApp)
- [x] **E-06** 24-hour appointment reminder (email + WhatsApp + SMS)
- [x] **E-07** 2-hour appointment reminder (WhatsApp + SMS)
- [x] **E-08** Appointment cancellation notice
- [x] **E-18** Waitlist slot available notification

---

## Sprint 11-12: Operations (Month 6)

**Goal:** Billing, notifications, patient portal, messaging, WhatsApp integration, and inter-specialist patient referral.

**Spec count target:** ~67 specs

### Backend: Billing and Invoicing (B-01 through B-13)

- [x] **B-01** `POST /api/v1/patients/{patient_id}/invoices` -- Create invoice
- [x] **B-02** `GET .../invoices/{invoice_id}` -- Get invoice detail
- [x] **B-03** `GET /api/v1/invoices` -- List invoices (filters: status, date, patient, doctor)
- [x] **B-04** `POST .../invoices/{invoice_id}/cancel` -- Cancel invoice (was: Update draft)
- [x] **B-05** `POST .../invoices/{invoice_id}/send` -- Send invoice to patient
- [x] **B-06** `POST .../invoices/{invoice_id}/payments` -- Record payment (partial supported)
- [x] **B-07** `GET .../invoices/{invoice_id}/payments` -- List invoice payments
- [x] **B-08** `POST .../invoices/{invoice_id}/payment-plan` -- Create payment plan
- [x] **B-09** `GET .../invoices/{invoice_id}/payment-plan` -- Get payment plan with installments
- [x] **B-10** `POST .../invoices/{invoice_id}/payment-plan/{n}/pay` -- Pay installment
- [x] **B-11** `GET /api/v1/billing/summary` -- Billing dashboard summary
- [x] **B-12** `GET /api/v1/billing/aging-report` -- Aging report (overdue by bucket)
- [x] **B-13** `GET /api/v1/billing/revenue` -- Revenue report (month/year)

### Backend: Patient Referral (P-15)

- [x] **P-15** `POST /api/v1/patients/{patient_id}/referrals` -- Create inter-specialist referral within clinic (referring doctor, receiving specialist, reason, urgency, linked odontogram state)
  - [x] `GET /api/v1/patients/{patient_id}/referrals` -- List referrals for patient
  - [x] `PUT .../referrals/{referral_id}` -- Update referral status (pending/accepted/completed)
  - [x] Notification to receiving specialist on referral creation
  - [x] Referral summary appears in receiving doctor's dashboard

### Backend: Notifications (N-01 through N-05)

- [x] **N-01** `GET /api/v1/notifications` -- List in-app notifications
- [x] **N-02** `POST .../notifications/{notification_id}/read` -- Mark as read
- [x] **N-03** `POST /api/v1/notifications/read-all` -- Mark all as read
- [x] **N-04** `GET /api/v1/notifications/preferences` -- Get notification preferences
- [x] **N-05** Notification dispatch engine (routes to in-app, email, WhatsApp, SMS)
- [x] **U-09** `PUT /api/v1/users/me/notifications` -- Update notification preferences

### Backend: Patient Portal (PP-01 through PP-13)

- [x] **P-11** `POST /api/v1/patients/{patient_id}/portal-access` -- Grant/revoke portal access
- [x] **PP-01** `POST /api/v1/portal/auth/login` -- Patient portal login
- [x] **PP-02** `GET /api/v1/portal/me` -- Patient's own profile
- [x] **PP-03** `GET /api/v1/portal/appointments` -- Patient's appointments
- [x] **PP-04** `GET /api/v1/portal/treatment-plans` -- View treatment plans
- [x] **PP-05** `POST .../portal/treatment-plans/{plan_id}/approve` -- Approve plan (digital signature)
- [x] **PP-06** `GET /api/v1/portal/invoices` -- View invoices and payment history
- [x] **PP-07** `GET /api/v1/portal/documents` -- View documents (X-rays, consents)
- [x] **PP-08** `POST /api/v1/portal/appointments` -- Book appointment from portal
- [x] **PP-09** `POST .../portal/appointments/{appointment_id}/cancel` -- Cancel own appointment
- [x] **PP-10** `GET /api/v1/portal/messages` -- Message threads
- [x] **PP-11** `POST /api/v1/portal/messages` -- Send message to clinic
- [x] **PP-12** `POST .../portal/consents/{consent_id}/sign` -- Sign consent from portal
- [x] **PP-13** `GET /api/v1/portal/odontogram` -- View own odontogram (read-only)

### Backend: Messaging (MS-01 through MS-05)

- [x] **MS-01** `POST /api/v1/messages/threads` -- Create message thread
- [x] **MS-02** `GET /api/v1/messages/threads` -- List threads (filter by patient, unread)
- [x] **MS-03** `POST .../threads/{thread_id}/messages` -- Send message
- [x] **MS-04** `GET .../threads/{thread_id}/messages` -- List messages in thread
- [x] **MS-05** `POST .../threads/{thread_id}/read` -- Mark thread as read

### Integration: WhatsApp

- [x] **INT-01** WhatsApp Business API integration (template messages, webhooks, sessions)
- [x] **INT-02** Twilio SMS integration (appointment reminders, verification codes)

### Frontend: Billing Screens (FE-B-01 through FE-B-08)

- [x] **FE-B-01** Invoice list page (patient invoices tab + hooks)
- [x] **FE-B-02** Create invoice form (patient, line items, tax, total)
- [x] **FE-B-03** Invoice detail page (line items, payments, balance, PDF, send)
- [x] **FE-B-04** Record payment modal (amount, method, partial support)
- [x] **FE-B-05** Payment plan creation and management
- [x] **FE-B-06** Service/procedure price catalog management
- [x] **FE-B-07** Doctor commissions report page
- [x] **FE-B-08** Billing overview dashboard (summary cards, sidebar enabled)

### Frontend: Patient Portal (FE-PP-01 through FE-PP-09)

- [x] **FE-PP-01** Patient portal login (clinic-branded)
- [x] **FE-PP-02** Portal dashboard (next appointment, plans, messages, consents)
- [x] **FE-PP-03** Portal appointments list (upcoming, past, book new, confirm/cancel)
- [x] **FE-PP-04** Portal treatment plans (progress, approve with signature)
- [x] **FE-PP-05** Portal document viewer (X-rays, consents, prescriptions)
- [x] **FE-PP-06** Portal chat interface (messages, attachments)
- [x] **FE-PP-07** Portal invoices and payment history
- [x] **FE-PP-08** Portal consent signing (full document, signature pad)
- [x] **FE-PP-09** Portal odontogram (read-only, color-coded, educational tooltips)

### Frontend: Settings

- [x] **FE-S-06** Consent template management (list, create, edit, preview)
- [x] **FE-S-08** Integrations page (WhatsApp, Google Calendar, payment gateway)

### Email Templates

- [x] **E-11** Invoice sent to patient
- [x] **E-12** Payment received confirmation
- [x] **E-13** Overdue payment reminder
- [x] **E-14** Patient portal access invitation
- [x] **E-15** New message notification

### Integration Tests (S11-12)

- [x] Invoice API integration tests (`test_billing/test_invoices_api.py` — 25 tests)
- [x] Payment API integration tests (`test_billing/test_payments_api.py` — 25 tests)
- [x] Billing summary API integration tests (`test_billing/test_billing_summary_api.py` — 14 tests)
- [x] Referral API integration tests (`test_billing/test_referrals_api.py` — 10 tests)
- [x] Portal auth integration tests (`test_portal/test_portal_auth_api.py` — 18 tests)
- [x] Portal data API integration tests (`test_portal/test_portal_data_api.py` — 11 tests)
- [x] Portal actions API integration tests (`test_portal/test_portal_actions_api.py` — 14 tests)
- [x] Notification API integration tests (`test_notifications/test_notifications_api.py` — 22 tests)
- [x] Messaging API integration tests (`test_messaging/test_messages_api.py` — 22 tests)
- [x] Webhook integration tests (`test_webhooks/test_webhooks_api.py` — 7 tests)

---

## Sprint 13-14: Compliance (Month 7)

**Goal:** Implement Colombia-specific compliance (RDA, RIPS, DIAN via MATIAS API), audit verification, and data retention.

**Spec count target:** ~20 specs

### Backend: Compliance (CO-01 through CO-08)

- [x] **I-13** Regulatory compliance engine: country adapter pattern (CO, MX, CL, AR, PE)
- [x] **I-26** ADR-007: Country compliance adapter architecture
- [x] **CO-01** `POST /api/v1/compliance/rips/generate` -- Generate RIPS files (AF, AC, AP, AT, AM, AN, AU)
- [x] **CO-02** `GET /api/v1/compliance/rips/{batch_id}` -- Download RIPS batch
- [x] **CO-03** `GET /api/v1/compliance/rips` -- RIPS generation history
- [x] **CO-04** `POST .../rips/{batch_id}/validate` -- Validate RIPS before submission
- [x] **CO-05** `GET /api/v1/compliance/rda/status` -- RDA compliance status check
- [x] **CO-06** `POST /api/v1/compliance/e-invoice` -- Electronic invoice via MATIAS API (Colombia DIAN); DentalOS operates as "Casa de Software"; any authorized role (clinic_owner, doctor, assistant) can generate invoices -- not restricted to 1 user like Dentalink
- [x] **CO-07** `GET .../e-invoice/{invoice_id}/status` -- E-invoice status with DIAN via MATIAS API
- [x] **CO-07b** `GET /api/v1/compliance/e-invoices` -- List e-invoices with status filters (status badges, paginated)
- [x] **CO-08** `GET /api/v1/compliance/config` -- Country compliance configuration

### Integration: Electronic Invoicing

- [x] **INT-10** MATIAS API integration for DIAN electronic invoicing (UBL 2.1, digital signature, CUFE, submission); replaces generic INT-04
  - [x] DentalOS registered as "Casa de Software" in MATIAS
  - [x] Multi-user invoice generation: RBAC allows clinic_owner, doctor, assistant with `billing:invoice:create` permission
  - [x] CUFE generation and storage per invoice
  - [x] XML and PDF retrieval from MATIAS after DIAN acceptance

### Audit and Data Retention

- [x] **I-11** Audit logging verification: validate all clinical data access is logged
- [x] **I-12** Data retention policies: 15-year clinical record retention (Colombia)
- [x] Audit trail immutability verification
- [x] Right-to-be-forgotten vs clinical retention mandate rules

### Frontend: Compliance Screens (FE-CO-01 through FE-CO-03)

- [x] **FE-CO-01** RIPS generation page (period selection, generate, validate, download)
- [x] **FE-CO-02** RDA compliance dashboard (compliance score, gaps, action items)
- [x] **FE-CO-03** Electronic invoice list (status tracking, resend, download XML/PDF; **accessible to any authorized role, not just clinic_owner**)
- [x] **FE-S-07** Compliance settings per country (RDA configuration, required fields)

---

## Sprint 15-16: Advanced Features and Inventory (Month 8)

**Goal:** Analytics, patient import/export, patient merge, inventory management with semaphore alerts, Mexico compliance, and offline support groundwork.

**Spec count target:** ~37 specs

### Backend: Analytics (AN-01 through AN-07)

- [x] **AN-01** `GET /api/v1/analytics/dashboard` -- Clinic dashboard metrics
- [x] **AN-02** `GET /api/v1/analytics/patients` -- Patient analytics (retention, demographics)
- [x] **AN-03** `GET /api/v1/analytics/appointments` -- Appointment analytics (utilization, no-shows)
- [x] **AN-04** `GET /api/v1/analytics/revenue` -- Revenue analytics (by period, doctor, procedure)
- [x] **AN-05** `GET /api/v1/analytics/clinical` -- Clinical analytics (common diagnoses, procedures)
- [x] **AN-06** `GET /api/v1/analytics/export` -- Export analytics to CSV/Excel
- [x] **AN-07** `GET /api/v1/analytics/audit-trail` -- Audit trail viewer (clinic_owner only)

### Frontend: Analytics Screens (FE-AN-01 through FE-AN-04)

- [x] **FE-AN-01** Analytics main dashboard (KPI cards, charts, period selector)
- [x] **FE-AN-02** Patient analytics page (trends, retention, demographics)
- [x] **FE-AN-03** Appointment analytics (utilization, cancellations, peak hours heatmap)
- [x] **FE-AN-04** Revenue analytics (trends, by doctor, by procedure, payment methods)
- [x] **FE-S-09** Audit log viewer (searchable, filterable)

### Backend: Patient Advanced Operations

- [x] **P-08** `POST /api/v1/patients/import` -- Bulk import from CSV/Excel (async via queue)
- [x] **P-09** `GET /api/v1/patients/export` -- Export patient list to CSV (streaming)
- [x] **P-10** `POST /api/v1/patients/merge` -- Merge duplicate records (clinic_owner only)
- [x] **FE-P-06** Patient import page (upload, column mapping, validation, progress)

### Backend: Inventory Management (INV-01 through INV-07)

Minimal viable inventory: materials tracking, expiry alerts, sterilization cycles, implant traceability. No purchase orders or supplier management in MVP -- keep scope focused.

- [x] **INV-01** `POST /api/v1/inventory` -- Create inventory item (name, category, unit, initial stock, min_stock threshold, expiry_date)
- [x] **INV-02** `GET /api/v1/inventory` -- List inventory items with semaphore status: green (ok), yellow (below min_stock), red (expired or out of stock)
- [x] **INV-03** `PUT /api/v1/inventory/{item_id}` -- Update item (stock adjustment, expiry update — creates QuantityHistory row atomically)
- [x] **INV-04** Quantity history is created inline on update (quantity_change + change_reason fields on PUT endpoint)
- [x] **INV-05** `GET /api/v1/inventory/alerts` -- Active stock alerts (low stock + expiry within 30 days)
- [x] **INV-06** `POST /api/v1/inventory/sterilization` -- Log sterilization cycle (autoclave batch, items included, timestamp, operator, SHA-256 signature)
- [x] **INV-07** `POST /api/v1/inventory/implants/link` -- Register implant with traceability (brand, lot number, patient link, tooth, date placed); atomic quantity decrement
  - [x] `GET /api/v1/inventory/implants/search` -- Search implant placements by lot_number (ILIKE recall) or patient_id

### Frontend: Inventory Screens (FE-INV-01 through FE-INV-03)

- [x] **FE-INV-01** Inventory dashboard (item list with semaphore color indicators, search, filter by category/status)
- [x] **FE-INV-02** Item detail page (stock history, movement log, expiry tracking, sterilization records)
- [x] **FE-INV-03** Alerts panel (red/yellow items, expiry warnings, one-click restock request draft)

### Mexico Compliance Adapter

- [x] **INT-05** SAT CFDI integration (PAC, XML stamping, UUID)
- [x] Mexico compliance adapter: NOM-024 requirements
- [x] Mexico-specific document types (CURP validation, RFC)
- [x] CFDI electronic invoicing flow

### Offline Support (if time allows)

- [x] **I-18** Offline-first architecture design (Service Workers, IndexedDB schema, sync queue) -- ADR-006 defers full implementation to post-MVP
- [x] **I-19** PWA configuration (service worker, manifest.json, cache strategies)
- [x] **I-25** ADR-006: Offline sync approach decision

### Backend: Admin / Superadmin (AD-01 through AD-07)

- [x] **AD-01** `POST /api/v1/admin/auth/login` -- Superadmin login (MFA required)
- [x] **AD-02** `GET /api/v1/admin/tenants` -- Platform-wide tenant management with metrics
- [x] **AD-03** `GET/PUT /api/v1/admin/plans` -- Manage subscription plans
- [x] **AD-04** `GET /api/v1/admin/analytics` -- Platform-level analytics (MRR, MAU, churn)
- [x] **AD-05** `GET/PUT /api/v1/admin/feature-flags` -- Feature flag management
- [x] **AD-06** `GET /api/v1/admin/health` -- System health dashboard
- [x] **AD-07** `POST .../admin/tenants/{tenant_id}/impersonate` -- Tenant impersonation

### Frontend: Admin Panel (FE-AD-01 through FE-AD-07)

- [x] **FE-AD-00** Admin layout, auth guard, sidebar, admin API client, admin auth hooks
- [x] **FE-AD-01** Admin login page (email + password + TOTP, rate limit warning)
- [x] **FE-AD-02** Admin dashboard (platform metrics, system health summary, top tenants)
- [x] **FE-AD-03** Tenants list page (search, filter by plan/status, pagination, metrics per tenant)
- [x] **FE-AD-04** Tenant detail page (overview, users, usage, impersonate modal AD-07)
- [x] **FE-AD-05** Plans management page (plan cards, edit modal with limits/features/pricing)
- [x] **FE-AD-06** Feature flags page (flag list, edit modal with scope/plan/tenant targeting)
- [x] **FE-AD-07** System health page (component cards: DB, Redis, RabbitMQ, Storage, App)
- [x] **FE-AD-08** Platform analytics page (MRR trends, churn, signups, distributions)

### Admin Portal Hardening (Phase 1-7)

- [x] **ADH-01** Real MRR calculation (per-doctor pricing model, additional doctor pricing)
- [x] **ADH-02** Real patient count (cross-schema query with Redis caching)
- [x] **ADH-03** Real churn rate calculation (cancelled in 30d / active at period start)
- [x] **ADH-04** Enhanced analytics response (plan_distribution, top_tenants, country_distribution, new_signups_30d)
- [x] **ADH-05** Real health checks (PostgreSQL version, Redis memory/version, RabbitMQ connectivity, latency per service)
- [x] **ADH-06** Admin audit log migration (admin_audit_logs table + indexes)
- [x] **ADH-07** Admin audit log model (AdminAuditLog)
- [x] **ADH-08** Audit log service methods (log_admin_action, get_admin_audit_logs with pagination/filters)
- [x] **ADH-09** `GET /api/v1/admin/audit-log` endpoint with action/admin/date filters
- [x] **ADH-10** Instrument all mutation endpoints with audit logging (create/update/suspend tenant, update plan, create/update flag, impersonate)
- [x] **ADH-11** Impersonation session tracking table (admin_impersonation_sessions)
- [x] **ADH-12** Impersonation requires reason (min 10 chars) and duration (15-480 min)
- [x] **ADH-13** Concurrent impersonation session limit (max 3)
- [x] **ADH-14** Enhanced tenant filtering (plan_id, country_code, created_after/before, sort_by, sort_order)
- [x] **ADH-15** Feature flag inheritance resolution (tenant → plan → global) with expiry support
- [x] **ADH-16** Feature flag change history table and tracking
- [x] **ADH-17** Feature flag expires_at and reason fields
- [x] **ADH-18** Plan change history table and field-level diff tracking
- [x] **ADH-19** `GET /api/v1/admin/plans/{plan_id}/history` endpoint
- [x] **ADH-20** CSV export endpoints (`GET /admin/export?export_type=tenants|audit`)
- [x] **ADH-21** Superadmin CRUD (`GET/POST /admin/superadmins`, `PUT/DELETE /admin/superadmins/{id}`)
- [x] **ADH-22** FE: Enhanced analytics page (plan distribution bars, top tenants table, country distribution)
- [x] **ADH-23** FE: Real health checks page (latency badges, version info, memory details, expandable details)
- [x] **ADH-24** FE: Tenant list advanced filters (plan, country, sort dropdowns)
- [x] **ADH-25** FE: Impersonation dialog with reason textarea and duration selector
- [x] **ADH-26** FE: Feature flags with scope badges, expiry indicators, reason column, change history modal
- [x] **ADH-27** FE: Plans page with pricing model display and change history modal
- [x] **ADH-28** FE: Audit log page (filterable table, expandable JSON details, CSV export)
- [x] **ADH-29** FE: Sidebar audit log navigation item
- [x] **ADH-30** FE: Admin hooks updated (audit log, plan/flag history, superadmin CRUD, export)
- [x] **ADH-31** Public schema migration 006 (audit logs, impersonation sessions, plan history, flag history, FF columns)
- [x] **ADH-32** FE: Superadmin management page (CRUD table with create/edit/delete dialogs, self-deletion guard)
- [x] **ADH-33** FE: Sidebar superadmins navigation item
- [x] **ADH-34** Admin notifications backend (model, migration, service, API endpoints)
- [x] **ADH-35** Admin notifications frontend (bell icon in header, dropdown, mark read/all-read)
- [x] **ADH-36** Notification instrumentation (suspend_tenant, create_tenant emit notifications)
- [x] **ADH-37** FE: Multi-step tenant onboarding wizard (3 steps: basic info, plan/location, initial config)
- [x] **SA-R02** Trial management: list trials, extend trial endpoint, frontend page with KPI cards
- [x] **SA-O04** Maintenance mode: Redis flag toggle, GET/POST endpoints, frontend page with status card
- [x] **SA-O01** Job monitor: RabbitMQ queue stats endpoint, frontend page with queue cards
- [x] **SA-E01** Announcements: CRUD endpoints, migration 007 (admin_announcements table), model, frontend page with create/edit/delete
- [x] **SA-R01** Revenue dashboard: migration 008 (admin_revenue_snapshots), KPI cards (MRR/ARPA/LTV/NRR), trend chart, plan/country breakdowns
- [x] **SA-R03** Add-on usage tracking: cross-schema aggregation, adoption metrics, upsell candidates, tenant table
- [x] **SA-G03** Onboarding funnel: step funnel visualization, stuck tenants table, onboarding_step labels
- [x] **SA-U01** Cross-tenant user search: cross-schema UNION query, search by email/name, role filter, multi-clinic badge
- [x] **SA-O02** Database metrics: pg_stat queries (connections, index/cache hit ratios, largest tables, slow queries, dead tuples)
- [x] **SA-A03** Bulk operations: suspend/unsuspend/change_plan/extend_trial on multiple tenants, audit logging
- [x] **SA-C01** Compliance dashboard: RIPS/RDA/consent/RETHUS status per Colombian tenant, KPI cards, compliance table
- [x] **SA-C02** Security alerts: failed logins, suspicious IPs, after-hours actions from audit log analysis, severity-sorted alert cards
- [x] **SA-C03** Data retention: retention policies (10yr clinical, 5yr audit), archivable cancelled tenants, HABEAS DATA
- [x] **SA-U02** Tenant usage analytics: per-tenant health scores (active users, patients, appointments, invoices, records), risk levels
- [x] **SA-G01** Cohort analysis: monthly retention matrix, months selector, avg churn month, heatmap visualization
- [x] **SA-G02** Feature adoption: 8-feature adoption bars, per-tenant usage matrix, adoption percentages
- [x] **SA-E02** Broadcast messaging: send filtered broadcasts (plan/country/status), notification worker queue, history log
- [x] **SA-A01** Automated alerts: CRUD alert rules with condition/threshold/channel, toggle active/inactive
- [x] **SA-A02** Scheduled reports: CRUD scheduled reports with type/schedule/recipients, active toggle, run tracking
- [x] **SA-E03** Support chat: thread-per-tenant, admin/clinic_owner messages, unread counts, thread open/close status
- [x] **SA-K01** Catalog administration: tab-switched CIE-10/CUPS management, search, pagination, add/edit codes inline
- [x] **SA-K02** Template management: global consent/evolution templates list, filter by type, edit name/status, version tracking
- [x] **SA-K03** Default prices: CUPS-based pricing per country, upsert, search, country filter, currency formatting
- [x] **SA-U03** Tenant comparison: compare 2-5 tenants side-by-side, metrics rows, plan averages, color-coded cells
- [x] **SA-O03** API usage metrics: 24h request totals, error rate, avg/P95 latency, hourly bar chart, Redis counters
- [x] **SA-G04** Geo intelligence: country breakdown, MRR per country, signup trends, activation rates, flag badges

### Admin Portal Hardening — Execution Engine Fixes

- [x] **AEF-01** ApiMetricsMiddleware: writes Redis counters (hourly buckets, per-endpoint counts/errors/latency, per-tenant counts, latency samples sorted set)
- [x] **AEF-02** MaintenanceMiddleware: checks Redis key, returns 503 for non-admin API routes, auto-clears expired maintenance, exempts health/admin/docs
- [x] **AEF-03** Maintenance mode service: set deletes key when disabled, stores ends_at for auto-expiry
- [x] **AEF-04** Clinic-facing announcements endpoint: GET /api/v1/announcements/active with tenant plan/country filtering
- [x] **AEF-05** Broadcast email delivery: send_broadcast publishes QueueMessage per recipient to notifications queue
- [x] **AEF-06** get_api_usage_metrics reads real Redis counters: endpoint scan, tenant scan, sorted set p95 calculation
- [x] **AEF-07** Maintenance worker: admin.evaluate_alerts handler evaluates active rules against platform metrics, fires email notifications
- [x] **AEF-08** Maintenance worker: admin.generate_report handler generates analytics/revenue/health reports, emails recipients
- [x] **AEF-09** Maintenance worker: admin.revenue_snapshot handler captures monthly MRR/tenant/patient snapshots with upsert

### Patient Portal Hardening (Gap Fixes + Value-Add)

Gap fixes:
- [x] **PH-G1** Postop instructions: replace stub with real `postop_instructions` table, model, migration (018), cursor-paginated endpoint
- [x] **PH-G2** Digital signatures: wire `digital_signature_service.create_signature()` in `approve_treatment_plan` and `sign_consent`
- [x] **PH-G3** Clinic notifications: dispatch all 6 TODO notifications (treatment_plan_approved, appointment_booked_portal, appointment_cancelled_patient, consent_signed, intake_submitted, membership_cancel_requested)
- [x] **PH-G4** Magic link dispatch: publish magic link URL to notifications queue (email/WhatsApp) after Redis storage
- [x] **PH-G5** Public booking: query real doctors from tenant schema, expand appointment types to 4
- [x] **PH-G7** Video page: fix `apiGet` → `portalApiGet` import (was using staff JWT instead of portal JWT)
- [x] **PH-G8** Invoices: add "Pagar ahora" button linking to `/portal/invoices/{id}/pay` for unpaid invoices

Value-add features:
- [x] **PH-V1** Patient profile edit: `PUT /portal/me` endpoint + profile edit page (phone, email, address, emergency contact)
- [x] **PH-V2** Notification preferences: `GET/PUT /portal/notifications/preferences` endpoints + toggle UI page
- [x] **PH-V3** Appointment rescheduling: `POST /portal/appointments/{id}/reschedule` endpoint + reschedule UI with date/time picker
- [x] **PH-V4** Patient document upload: `POST /portal/documents` endpoint with S3 storage + upload UI with type selector
- [x] **PH-V5** Odontogram history timeline: `GET /portal/odontogram/history` endpoint + timeline UI showing snapshots

### Patient Portal Phase 2 — Competitive Parity Features

Wave 1 (Frontend-only — backend exists):
- [x] **PP2-F1** Membership page: plan details, benefits, cancel-request button (`frontend/app/portal/membership/page.tsx`)
- [x] **PP2-F2** Clinic branding fix: populate real `logo_url`, `phone`, `address` from tenant in `/portal/me`
- [x] **PP2-F3** Dashboard enrichment: unread messages badge, confirm attendance button, treatment progress, outstanding balance

Wave 2 (New pages for existing backend services):
- [x] **PP2-F4** Portal intake form: `GET /portal/intake/form` + dynamic form builder page (`frontend/app/portal/intake/page.tsx`)
- [x] **PP2-F5** Chatbot widget: embedded floating chat in portal layout (`ChatbotWidget.tsx`)
- [x] **PP2-F6** Survey history: `GET /portal/surveys` + survey list page (`frontend/app/portal/surveys/page.tsx`)

Wave 3 (New endpoints for existing staff services):
- [x] **PP2-F7** Financing tracker: `GET /portal/financing` + financing list page (`frontend/app/portal/financing/page.tsx`)
- [x] **PP2-F8** Family billing view: `GET /portal/family` + family group page (`frontend/app/portal/family/page.tsx`)
- [x] **PP2-F9** Lab order tracking: `GET /portal/lab-orders` + lab order list page (`frontend/app/portal/lab-orders/page.tsx`)
- [x] **PP2-F10** Tooth photos gallery: `GET /portal/photos` + photo gallery page (`frontend/app/portal/photos/page.tsx`)

Wave 4 (Enhanced features):
- [x] **PP2-F11** Health history update: `GET/PUT /portal/health-history` + editable health form (`frontend/app/portal/health/page.tsx`)
- [x] **PP2-F12** Financing calculator: `POST /portal/financing/simulate` + inline calculator on treatment plans page
- [x] **PP2-F13** Treatment timeline: `GET /portal/treatment-timeline` + vertical timeline page (`frontend/app/portal/timeline/page.tsx`)

### Email Templates

- [x] **E-16** Daily clinic summary email
- [x] **E-17** Plan upgrade prompt (limit approaching)

### Integration Tests (S15-16)

- [x] Analytics API integration tests (`test_analytics/test_analytics_api.py` — 25 tests)
- [x] Inventory API integration tests (`test_inventory/test_inventory_api.py` — 32 tests)
- [x] Admin API integration tests (`test_admin/test_admin_api.py` — 27 tests)
- [x] Patient import/export API integration tests (`test_patients/test_patient_import_export_api.py` — 13 tests)
- [x] Patient merge API integration tests (`test_patients/test_patient_merge_api.py` — 8 tests)
- [x] Service catalog API integration tests (`test_billing/test_service_catalog_api.py` — 11 tests)

### Unit Tests (S15-16)

- [x] Patient import schema validators (`test_schemas_patient_import.py` — 41 tests)
- [x] Mexico compliance validators + CFDI builder (`test_mexico_compliance.py` — 32 tests)

---

## Sprint 17-18: Beta (Month 9)

**Goal:** Stabilize, optimize, test, and prepare for production.

**Spec count target:** Focus on quality, not new features.

### Internal Beta Testing

- [ ] Recruit 3-5 dental clinics in Colombia for beta testing
- [ ] Set up beta environment on Hetzner Cloud
- [ ] Onboard beta clinics with seed data migration
- [ ] Establish feedback collection process (in-app feedback, weekly calls)

### Performance Optimization

- [x] Database query optimization (EXPLAIN ANALYZE on slow queries)
- [x] N+1 query detection and resolution
- [x] Redis cache hit rate optimization (target: >90%)
- [x] Frontend bundle size audit (target: <200KB initial JS)
- [x] Image optimization (X-rays: lazy loading, progressive JPEG)
- [x] API response time audit (target: p95 < 200ms for CRUD, < 500ms for reports)

### Security Audit

- [x] OWASP Top 10 vulnerability scan — test suite in tests/unit/test_security_audit.py
- [x] SQL injection testing (SQLAlchemy parameterization verification) — validate_schema_name() enforced before SET search_path; inline __import__ replaced with proper sqlalchemy.text(); OWASP tests verify rejection of injection payloads
- [x] XSS prevention testing (frontend and API responses) — PHI logging fixed, email XSS sanitized
- [x] JWT token security audit (RS256 key rotation, token revocation) — token_version validation added
- [x] File upload security (virus scanning, MIME type validation) — magic-byte check + ClamAV integration
- [x] PHI (Protected Health Information) access audit — PHI stripped from logs and error responses
- [x] CORS and CSP headers verification — HSTS added to SecurityHeadersMiddleware (HTTPS-only); security headers added to next.config.ts
- [x] Rate limiting effectiveness testing — GlobalRateLimitMiddleware (200 req/min/IP); public booking 5/hr/IP; public config 30/min/IP; login rate limit tightened to 15/15min
- [x] Tenant isolation penetration testing (cross-tenant data access attempts) — schema validation enforced on all SET search_path calls; OWASP test_broken_access_control_schema_pattern verifies rejection of admin/public/pg_catalog/information_schema schemas
- [x] Public router schema validation — validate_schema_name() called before SET search_path in public_router.py
- [x] TrustedHostMiddleware wired in main.py (production only, driven by settings.allowed_hosts_list)

### Load Testing

- [x] Load test: 500 concurrent users target — Locust suite with 5 weighted scenarios (auth/patient/odontogram/appointment/billing) + health monitor; `make load-test` runs 500 VUs for 30min with p95 threshold validation
- [x] Load test: 100 concurrent appointment bookings — ConflictBookingUser with threading.Barrier sync; `make load-test-conflict` verifies 1x 201 + 99x 409 + zero 500s
- [x] Load test: Odontogram bulk updates under load — DoctorUser scenario (25% weight): 80% cached reads, 10% bulk writes (8 conditions), 10% single writes with post-write cache verification
- [x] Load test: Full-text search (patients, CIE-10, CUPS) under load — ClinicalStaffUser scenario (40% weight): 50% search with 30 Colombian name prefixes, p95 threshold 150ms
- [x] Database connection pool stress testing — PoolStressShape (10→25→35→50→10 VUs, 60s each) with zero wait_time; asserts 503 on pool saturation, not 500; `make load-test-pool`
- [x] RabbitMQ queue depth under sustained load — MonitorUser polls RabbitMQ management API every 30s, fires custom Locust events for queue depth reporting, threshold < 500 messages

### Bug Fixes from Beta Feedback

- [x] Triage and prioritize beta feedback items
- [x] Critical bug fixes (P0: data loss, security, crashes) — metrics endpoint auth gating, middleware route gaps, portal booking slot validation, treatment plan signature flow, async boto3 health check
- [x] High-priority bug fixes (P1: workflow blockers) — dashboard link fix, portal error boundary move, portal error handling with retry, anthropic dependency
- [x] UX improvements from clinical staff feedback — portal Link navigation, dark mode global-error, calendar AM/PM Spanish format, useStartAppointment body fix, not-found redirect logic
- [x] Mobile/tablet usability fixes
- [x] E2E receptionist flow bug fixes (flows 18.1–18.34) — 13 FE↔BE mismatches across 7 modules:
  - [x] FE: Intake apiPut→apiPost (405 fix), EPS Claims field+enum renames (unit_cost_cents, English enums), aging display counts not currency
  - [x] FE: Recall 4 field renames (type, channel, schedule, filters) + type enum mapping, removed in_app channel
  - [x] FE: Families field renames (primary_contact_patient_id, billing flat fields), Memberships apiPost+field renames
  - [x] FE: Invoice new page — pass include_tax+tax_rate to API
  - [x] BE: Add GET /recall/campaigns/{id}, POST /intake/submissions/{id}/reject endpoints
  - [x] BE: Add patient-scoped membership endpoints (GET/POST /patients/{id}/membership, POST cancel)
  - [x] BE: Add GET /patients/{id}/family endpoint + family_service.get_by_patient()
  - [x] BE: Portal 500 fix (duplicate PortalCredentials), installment stale reference fix, WhatsApp defensive error handling
  - [x] BE: IVA persistence (include_tax+tax_rate columns, migration 026), rounding fix (floor→round)
- [x] Flow 18.7 bug fixes — Invoice from Treatment Plan (5 fixes):
  - [x] BE: AI treatment cost validation — detect pesos vs cents mismatch, multiply by 100 if below catalog threshold
  - [x] FE: Auto-send invoice via useSearchParams ?send=true on invoice detail page
  - [x] BE: Add treatment_plans:read to receptionist RBAC permissions
  - [x] BE: Wrap S3 signature upload in try/except — graceful fallback when MinIO unavailable
  - [x] BE: Add missing await on treatment_plan_service.generate_pdf() call
- [x] Flow 18.33 Bug#1 — Dashboard KPIs showing 0 for receptionist:
  - [x] BE: Add analytics:read to receptionist RBAC permissions (root cause: 403 silent fail → ?? 0 fallback)

### Additional Infrastructure

- [x] **I-15** Monitoring and observability (structured logging, Sentry, APM) -- Sentry integration DONE (backend + frontend + PHI scrubber); Prometheus/OTel deferred
- [x] **I-16** Backup and disaster recovery (WAL archiving, PITR, cross-region backup)
- [x] **INT-09** Google Calendar sync (optional bi-directional) -- stub created, OAuth flow pending
- [x] **INT-07** Payment gateway integration (Mercado Pago, PSE) -- FULL adapter pattern implemented: ABC base, production service (httpx, HMAC-SHA256), mock service, IPN webhook router (payment + subscription), registered in api_v1_router

---

## Sprint 19-20: Launch (Month 10)

**Goal:** Production deployment, monitoring, documentation, and Colombia launch.

**Spec count target:** Focus on operations, not new features.

### Production Deployment

- [x] Hetzner Cloud production environment provisioning -- Terraform IaC in infra/terraform/ (servers, network, firewall, LB, DB, DNS)
- [x] PostgreSQL managed database setup (production config, backups enabled) -- self-managed CPX31 with 40GB volume in database.tf (Hetzner managed PG incompatible with schema-per-tenant)
- [x] Redis production instance with persistence -- CX21 server in servers.tf with appendonly + maxmemory 256mb
- [x] RabbitMQ cluster setup -- runs on worker server (CPX31) via Docker Compose, defined in servers.tf
- [x] Load balancer configuration with SSL termination -- LB11 in loadbalancer.tf, HTTPS→3000/8000, HTTP→HTTPS redirect, managed Let's Encrypt cert
- [x] DNS and domain setup (dentalos.co or similar) -- dns.tf with Hetzner DNS + Cloudflare templates (A/CNAME records)
- [x] Blue-green deployment pipeline finalized -- CD pipeline in .github/workflows/cd.yml, SHA-tagged images, health check gate
- [x] Rollback strategy tested -- documented in docs/admin-runbook.md Section 3 with docker tag rollback procedure

### Monitoring and Alerting

- [x] Sentry error tracking (backend + frontend)
- [x] Uptime monitoring (health check endpoints)
- [x] Database performance monitoring
- [x] Queue depth alerting (RabbitMQ)
- [x] Disk space and resource utilization alerts
- [x] Custom business metrics dashboard (tenant count, active users, appointments/day)
- [x] On-call rotation and incident response runbook

### Documentation

- [x] User guide for clinic owners (setup, onboarding, daily operations) -- docs/guides/guia-propietario-clinica.md (es-419)
- [x] User guide for doctors (odontogram, clinical records, prescriptions) -- docs/guides/guia-doctor.md (es-419)
- [x] User guide for receptionists (appointments, patient registration) -- docs/guides/guia-recepcionista.md (es-419)
- [x] Patient portal user guide -- docs/guides/guia-portal-paciente.md (es-419)
- [x] API documentation (auto-generated from FastAPI OpenAPI specs) -- api_docs_enabled setting added to config.py; /docs, /redoc, /openapi.json always available
- [x] Admin runbook (tenant provisioning, support procedures) -- docs/admin-runbook.md (1092 lines, 8 sections)

### Marketing Site

- [x] Landing page (value proposition, features, pricing)
- [x] Pricing page with plan comparison
- [x] Self-service registration flow from marketing site
- [x] SEO optimization for "software dental Colombia" keywords
- [x] Blog/content section for dental industry content

### Colombia Launch

- [ ] Final compliance review (RDA, RIPS, data protection law 1581 de 2012)
- [ ] DIAN electronic invoicing certification (MATIAS API, if applicable)
- [ ] Beta-to-production migration for beta clinics
- [ ] Launch announcement to beta participants
- [ ] Outbound sales to dental clinics in Bogota, Medellin, Cali
- [ ] Customer support channels established (WhatsApp, email, in-app)

### Post-Launch Monitoring (first 2 weeks)

- [ ] Daily error rate review
- [ ] Daily performance metrics review
- [ ] User onboarding funnel analysis
- [ ] First-week retention tracking
- [ ] Rapid response to production issues
- [ ] Weekly check-in with early customers

---

## Sprint 21-22: Patient Engagement & Revenue Acceleration (Post-Launch Month 1-2)

**Goal:** Ship critical differentiators that drive clinic revenue and patient engagement. These are P0 features — highest ROI, fastest time-to-value.

### VP-01: Membership Plans (Planes de Membresía Dental)

Patients pay a monthly subscription for preventive care + discounts on treatments. Clinics in US report $100K+/year from memberships. 76% more patient visits. Zero LATAM competitors offer this. Colombia has ~40% out-of-pocket patients — ideal market fit.

- [x] Design `membership_plans` table (tenant schema): plan name, description, monthly_price_cents, annual_price_cents, benefits JSONB, discount_percentage, is_active, created_at, updated_at
- [x] Design `membership_subscriptions` table: patient_id, plan_id, status (active/paused/cancelled/expired), start_date, next_billing_date, cancelled_at, payment_method
- [x] Design `membership_usage_log` table: subscription_id, service_id, discount_applied_cents, used_at
- [x] `POST /api/v1/memberships/plans` — Create membership plan (clinic_owner)
- [x] `GET /api/v1/memberships/plans` — List plans (all staff roles)
- [x] `PUT /api/v1/memberships/plans/{id}` — Update plan (clinic_owner)
- [x] `POST /api/v1/memberships/subscriptions` — Subscribe patient to plan (receptionist+)
- [x] `GET /api/v1/memberships/subscriptions` — List active subscriptions with filters
- [x] `POST /api/v1/memberships/subscriptions/{id}/cancel` — Cancel subscription
- [x] `POST /api/v1/memberships/subscriptions/{id}/pause` — Pause subscription
- [x] Auto-apply membership discount on invoice creation (hook into billing service)
- [x] Mercado Pago recurring payment integration for auto-billing
- [x] Membership renewal notification via existing notification dispatch
- [x] Portal: patient can view their membership plan, benefits used, next billing date
- [x] Portal: patient can request cancellation (triggers staff review)
- [x] FE: Membership plan management page (clinic_owner) — create/edit/archive plans
- [x] FE: Subscribe patient flow from patient profile
- [x] FE: Membership dashboard — active members count, revenue, churn rate

### VP-02: Automated Recall & Reactivation Engine

AI-driven campaigns that identify inactive patients (6+ months) and send WhatsApp/SMS/email sequences to bring them back. Reactivating 50 patients/month = ~10M COP additional revenue per clinic. Leverages existing notification dispatch + WhatsApp + RabbitMQ infrastructure.

- [x] Design `recall_campaigns` table: name, type (recall/reactivation/treatment_followup), filters JSONB, message_template_id, channel (whatsapp/sms/email/multi), schedule JSONB, status (draft/active/paused/completed), created_by
- [x] Design `recall_campaign_recipients` table: campaign_id, patient_id, status (pending/sent/delivered/opened/clicked/booked/failed), sent_at, responded_at, booked_appointment_id
- [x] `POST /api/v1/recall/campaigns` — Create campaign (clinic_owner/receptionist)
- [x] `GET /api/v1/recall/campaigns` — List campaigns with aggregated stats
- [x] `PUT /api/v1/recall/campaigns/{id}` — Update campaign
- [x] `POST /api/v1/recall/campaigns/{id}/activate` — Activate campaign
- [x] `POST /api/v1/recall/campaigns/{id}/pause` — Pause campaign
- [x] Cron job: identify patients with no visit in X months (configurable threshold)
- [x] Cron job: identify patients with incomplete treatment plans
- [x] Cron job: identify patients overdue for hygiene recall (6-month intervals)
- [x] Cron job: identify patients with upcoming birthdays (birthday campaign)
- [x] Multi-step sequence support: day 1 WhatsApp → day 3 SMS → day 7 email
- [x] WhatsApp/SMS/email dispatch via existing notification engine (RabbitMQ `notifications` queue)
- [x] Campaign performance tracking: sent, delivered, opened, booked, revenue attributed
- [x] Unsubscribe/opt-out handling (respect patient communication preferences)
- [x] FE: Campaign builder page — patient segment filters, message template, channel selection, schedule
- [x] FE: Campaign results dashboard — funnel visualization, ROI metrics
- [x] FE: Patient timeline shows recall campaign interactions

### VP-03: Smart Digital Intake Forms

Patient completes medical history, consents, and personal data from their phone before the appointment. Auto-populates the patient record. Reduces front desk time from 15 min to <2 min per patient. Portal + anamnesis + consent infrastructure already exists.

- [x] Design `intake_form_templates` table: name, fields JSONB (field definitions), consent_template_ids, is_default, is_active, tenant_id
- [x] Design `intake_submissions` table: template_id, patient_id (nullable — new patients), appointment_id, data JSONB, status (pending/reviewed/approved/rejected), submitted_at, reviewed_by, reviewed_at
- [x] `POST /api/v1/intake/templates` — Create/customize intake form template (clinic_owner)
- [x] `GET /api/v1/intake/templates` — List templates
- [x] `PUT /api/v1/intake/templates/{id}` — Update template
- [x] `POST /api/v1/public/{slug}/intake` — Patient submits form (public, no auth required for new patients)
- [x] `POST /api/v1/portal/intake` — Patient submits form (portal auth, existing patients)
- [x] `GET /api/v1/intake/submissions` — List submissions for review (staff)
- [x] `POST /api/v1/intake/submissions/{id}/approve` — Approve and auto-populate records
- [x] Auto-populate Patient + Anamnesis + Consent records from approved submission
- [x] Pre-appointment intake link sent via notification dispatch (24h before appointment, configurable)
- [x] Default intake template seeded per tenant (Colombian medical history fields)
- [x] FE: Form template builder for clinic_owner (field types: text, select, date, checkbox, file upload, signature)
- [x] FE: Mobile-optimized patient intake form (public-facing, responsive 320px+)
- [x] FE: Intake submission review queue for staff — approve/edit/reject before saving to patient record
- [x] FE: Intake completion status indicator on today's appointment list

### VP-04: Morning Huddle Dashboard (Resumen del Día)

Daily briefing that aggregates existing data into actionable insights. Dental Intelligence built their entire company on this concept. Clinics report +15-25% production increase. No new data required — pure aggregation of patients, appointments, billing, treatment plans.

- [x] `GET /api/v1/analytics/huddle` — Today's briefing endpoint (aggregates existing data)
- [x] Huddle data: today's appointments with patient name, procedure, status, arrival
- [x] Huddle data: production goal vs actual (daily/weekly/monthly from billing)
- [x] Huddle data: incomplete treatment plans needing follow-up (top 10 by value)
- [x] Huddle data: outstanding patient balances (top 10 by amount)
- [x] Huddle data: patients with birthdays today
- [x] Huddle data: recall-due patients this week (no visit in 6+ months)
- [x] Huddle data: yesterday's collection summary
- [x] Huddle data: no-show count yesterday + today's high-risk no-shows
- [x] Production goal configuration per doctor/clinic (`clinic_settings` JSONB)
- [x] FE: Morning Huddle page in (dashboard) route group
- [x] FE: Auto-refresh every 5 minutes during business hours
- [x] FE: Printable huddle summary (PDF or print-optimized CSS) for team meetings
- [x] FE: Quick-action buttons (call patient, send reminder, view balance)

---

## Sprint 23-24: Colombia-Specific Integrations & Growth (Post-Launch Month 3-4)

**Goal:** Integrate Colombia-specific payment methods and regulatory verifications that no dental SaaS offers. Ship growth loops (referrals) and quick wins (post-op instructions).

### VP-05: Nequi / Daviplata Mobile Wallet Payments

21M+ Nequi users in Colombia — more than credit card holders. Zero dental software integrates mobile wallets. First-mover advantage. Included in all plans as a payment method.

- [x] Nequi Comercios QR Push API integration (sandbox + production)
- [x] Daviplata QR API integration (via Davivienda developer portal)
- [x] Add payment methods `nequi` and `daviplata` to payment recording enum
- [x] QR code generation service (encodes payment amount + reference)
- [x] `POST /api/v1/billing/invoices/{id}/payment-qr` — Generate QR for invoice payment
- [x] Payment webhook endpoint for Nequi confirmation callbacks
- [x] Payment webhook endpoint for Daviplata confirmation callbacks
- [x] Auto-reconcile webhook payment with invoice (mark as paid)
- [x] Patient portal: "Pay with Nequi" and "Pay with Daviplata" buttons on invoice
- [x] FE: QR display component on invoice detail page (staff shows to patient)
- [x] FE: Payment confirmation toast/notification on successful webhook

### VP-06: EPS Insurance Verification (ADRES/BDUA)

One-click verification of patient's EPS affiliation, copay level, and eligible procedures. Clinics currently spend 15-30 min per EPS patient on manual verification. Colombian equivalent of US "instant insurance verification."

- [x] ADRES BDUA API client service (SOAP/REST — document type + number → affiliation status)
- [x] `GET /api/v1/patients/{id}/eps-verification` — Verify EPS status (doctor/receptionist+)
- [x] Design `eps_verifications` table: patient_id, verification_date, eps_name, eps_code, affiliation_status, regime (contributivo/subsidiado), copay_category, raw_response JSONB
- [x] Cache verification result in Redis (TTL 24h, key pattern `...:eps:verification:{patient_id}`)
- [x] Display verification badge on patient profile (verified/unverified/expired)
- [x] Show coverage details: EPS name, regime, copay category, eligible procedure types
- [x] Alert on coverage changes or inactive affiliation
- [x] Auto-verify on patient creation if document_type is CC/TI (background job via RabbitMQ)
- [x] FE: EPS verification badge and expandable detail panel on patient profile
- [x] FE: Manual "Re-verify" button for staff
- [x] FE: EPS status column on patient list (filterable)

### VP-07: RETHUS Professional Registry Verification

Automatic validation of doctor/assistant professional registration against MinSalud registry. Resolución 1888 requires it. High compliance value. No competitor offers automated verification.

- [x] RETHUS verification service (MinSalud RETHUS consulta API or web scraping fallback)
- [x] Add `rethus_number` field to User model (doctor/assistant roles)
- [x] Add `rethus_verification_status` field (pending/verified/failed/expired)
- [x] Add `rethus_verified_at` timestamp field
- [x] `GET /api/v1/users/{id}/rethus-verification` — Check RETHUS status
- [x] `POST /api/v1/users/{id}/rethus-verification` — Trigger manual verification
- [x] Auto-verify on team member invite/onboarding (background job)
- [x] Periodic re-verification via `maintenance` queue (monthly cron)
- [x] Verification status badge on team member profile
- [x] Alert clinic_owner if any doctor's RETHUS verification fails or expires
- [x] FE: RETHUS badge on doctor profile and team management page
- [x] FE: Verification trigger button and status history

### VP-08: Patient Referral Program (Paciente Refiere Paciente)

Word-of-mouth is the #1 patient acquisition channel for dental clinics in Colombia. Unique referral codes with discounts for both referrer and referred patient. +20-35% new patient acquisition. Public booking already accepts new patients.

- [x] Design `referral_codes` table: patient_id, code (unique, 8-char alphanumeric), is_active, uses_count, max_uses (nullable), created_at
- [x] Design `referral_rewards` table: referrer_patient_id, referred_patient_id, referral_code_id, reward_type (discount/credit/points), reward_amount_cents, status (pending/applied/expired), applied_to_invoice_id
- [x] Design `referral_program_config` in tenant settings JSONB: enabled, referrer_reward_type, referrer_reward_amount, referred_discount_percentage, max_referrals_per_patient
- [x] Auto-generate unique referral code per patient on first portal login
- [x] `GET /api/v1/portal/referral` — Patient views their referral code and stats
- [x] `GET /api/v1/portal/referral/rewards` — Patient views earned rewards
- [x] Accept `referral_code` parameter in public booking endpoint
- [x] Auto-create referral_reward record when referred patient completes first appointment
- [x] Auto-apply referrer discount on their next invoice
- [x] Welcome discount for referred patient on first invoice
- [x] Notification to referrer when their referral books + completes appointment
- [x] `GET /api/v1/referrals/stats` — Referral program analytics (clinic_owner)
- [x] FE: Referral program settings page (clinic_owner — configure reward rules)
- [x] FE: Portal referral sharing page (shareable link, WhatsApp share button, QR code)
- [x] FE: Referral tracking dashboard (clinic_owner — top referrers, conversion rate)

### VP-20: Post-Operative Instructions Automation (Quick Win)

After a procedure, automatically send care instructions via WhatsApp/email/portal. Reduces post-op phone calls by 40-60%. Reuses evolution templates + notification dispatch infrastructure.

- [x] Design `postop_templates` table: procedure_type (maps to evolution template type), title, instruction_content (rich text), channel_preference (whatsapp/email/portal/all), is_active
- [x] Seed 10 built-in post-op templates for common procedures: resina, endodoncia, exodoncia, profilaxis, cirugía periodontal, blanqueamiento, corona, implante, ortodoncia ajuste, urgencia
- [x] `GET /api/v1/postop/templates` — List templates (staff)
- [x] `POST /api/v1/postop/templates` — Create custom template (clinic_owner)
- [x] `PUT /api/v1/postop/templates/{id}` — Update template
- [x] Event listener: on procedure completion (evolution record saved), auto-dispatch matching post-op instructions
- [x] Send via patient's preferred channel (WhatsApp → email → portal fallback)
- [x] Portal: patient can view past post-op instructions
- [x] `POST /api/v1/postop/send/{patient_id}` — Manual send for any procedure (staff)
- [x] FE: Post-op template management page (clinic_owner)
- [x] FE: "Send post-op instructions" button on procedure completion screen

### GAP-02: Control de Caja (Cash Register / Daily Cash Flow)

~40% of Colombian patients pay cash. Clinic owners need daily cash control with opening balance, cash/card/transfer breakdown, and end-of-day reconciliation. Dentalink has it — this is a daily operational tool.

- [x] Design `cash_registers` table: name, location, status (open/closed), opened_by, opened_at, opening_balance_cents, closing_balance_cents, closed_by, closed_at
- [x] Design `cash_movements` table: register_id, type (income/expense/adjustment), amount_cents, payment_method (cash/card/transfer/nequi/daviplata), reference_id (invoice/expense), description, recorded_by, created_at
- [x] `POST /api/v1/cash-registers/open` — Open register with initial balance (receptionist/clinic_owner)
- [x] `POST /api/v1/cash-registers/close` — Close register with reconciliation
- [x] `GET /api/v1/cash-registers/current` — Current register status and balance
- [x] `GET /api/v1/cash-registers/history` — Daily cash register history
- [x] Auto-record cash movements on invoice payment (hook into B-06)
- [x] FE: Cash register panel (open/close, current balance, today's movements)
- [x] FE: Daily cash report (printable)

### GAP-03: Control de Gastos (Expense Tracking)

Clinic owners need to see profit, not just revenue. Without expense tracking, they use a separate spreadsheet. Pairs naturally with Control de Caja for a complete financial picture.

- [x] Design `expense_categories` table: name, is_default, is_active (seed: rent, supplies, lab, salaries, utilities, marketing, equipment, other)
- [x] Design `expenses` table: category_id, amount_cents, description, date, receipt_url, recorded_by, created_at
- [x] `POST /api/v1/expenses` — Record expense (clinic_owner/receptionist)
- [x] `GET /api/v1/expenses` — List expenses with filters (date range, category)
- [x] `GET /api/v1/analytics/profit-loss` — Monthly P&L report (revenue from billing - expenses)
- [x] FE: Expense recording form (amount, category, date, receipt upload)
- [x] FE: Expense list page with filters
- [x] FE: P&L dashboard card on analytics page

### GAP-05: Tareas de Morosidad (Automated Delinquency Follow-up)

DentalOS has B-12 aging report but no actionable task workflow. Auto-generate follow-up tasks when patients have overdue balances. Cash collection is a top pain point for clinics.

- [x] Event listener: when invoice ages past 30/60/90 days, auto-create follow-up task (`staff_task_service.check_delinquency`, dispatched via `tasks.check_delinquency` queue job)
- [x] Task assignment to receptionist with patient context + overdue amount (auto-assigns to first active receptionist)
- [x] Configurable thresholds in tenant settings (days before task creation, reads `billing.delinquency_thresholds_days` with [30,60,90] default)
- [x] FE: Delinquency task queue on billing dashboard

### GAP-06: Tareas de Captación (Treatment Acceptance Follow-up)

Treatment plan acceptance is directly tied to revenue. Clinics report 40-60% of quotations never convert. Auto-create follow-up tasks when quotations aren't accepted within configurable days.

- [x] Event listener: when quotation not accepted within X days (configurable, default 7), auto-create follow-up task (`staff_task_service.check_acceptance`, dispatched via `tasks.check_acceptance` queue job)
- [x] `GET /api/v1/analytics/acceptance-rate` — Quotation acceptance rate metrics
- [x] FE: Quotation follow-up queue with one-click call/WhatsApp actions

---

## Sprint 25-26: Reputation, Intelligence & Multi-Currency (Post-Launch Month 5-6)

**Goal:** Build reputation management loop, schedule intelligence, and support for dental tourism / multi-currency billing.

### VP-09: Review & Reputation Management

Post-appointment auto-survey that routes satisfied patients to Google Reviews and unsatisfied patients to private feedback. 77% of patients check reviews before choosing a dentist. Google Maps reviews are critical for discovery in LATAM.

- [x] Design `satisfaction_surveys` table: patient_id, appointment_id, score (1-5), feedback_text, channel_sent, sent_at, responded_at, routed_to (google_review/private_feedback) (`backend/app/models/tenant/satisfaction_survey.py`, `012_sprint25_reputation_intelligence.py`)
- [x] Design `reputation_config` in tenant settings JSONB: enabled, min_score_for_review_routing (default 4), google_review_url, survey_delay_hours (default 2), channels (`backend/app/services/reputation_service.py`)
- [x] `POST /api/v1/reputation/surveys/send` — Manually trigger survey for appointment (`backend/app/api/v1/reputation/router.py`)
- [x] Event listener: auto-send survey X hours after appointment completion (`backend/app/workers/maintenance_worker.py` — `survey.auto_send`)
- [x] Survey response handler: score >= threshold → redirect to Google Reviews link; score < threshold → save as private feedback (`backend/app/services/reputation_service.py`)
- [x] `GET /api/v1/reputation/dashboard` — Reputation analytics (avg score, response rate, review count, NPS) (`backend/app/api/v1/reputation/router.py`)
- [x] `GET /api/v1/reputation/feedback` — List private feedback (clinic_owner) (`backend/app/api/v1/reputation/router.py`)
- [x] WhatsApp/SMS/email survey delivery via notification engine (`backend/app/services/reputation_service.py` — enqueues via publish_message)
- [x] FE: Reputation dashboard — score trends, review volume, feedback queue (`frontend/app/(dashboard)/reputation/page.tsx`)
- [x] FE: Reputation settings page (Google Review URL, threshold, channels) (`frontend/app/(dashboard)/settings/reputation/page.tsx`)
- [x] FE: Patient-facing survey form (mobile-optimized, 1-tap star rating) (`frontend/app/(public)/survey/[token]/page.tsx`)

### VP-10: Intelligent Schedule Optimization

AI analyzes appointment patterns to suggest fill strategies, predict no-shows, and recommend optimal scheduling. +10-15% chair utilization. All data already exists in appointments module.

- [x] `GET /api/v1/analytics/schedule-intelligence` — Schedule optimization insights (`backend/app/api/v1/analytics/schedule_intelligence_router.py`)
- [x] No-show prediction model: based on patient history, day of week, time, procedure type, weather (future) (`backend/app/services/schedule_intelligence_service.py`)
- [x] Gap analysis: identify unfilled slots and suggest patients from waitlist or recall list (`backend/app/services/schedule_intelligence_service.py`)
- [x] Overbooking recommendations: for high no-show slots, suggest double-booking threshold (`backend/app/services/schedule_intelligence_service.py`)
- [x] Optimal scheduling patterns: analyze which procedure sequences maximize production (`backend/app/services/schedule_intelligence_service.py`)
- [x] Chair utilization metrics: actual vs potential production per chair/doctor (`backend/app/services/schedule_intelligence_service.py`)
- [x] `GET /api/v1/appointments/suggested-fills` — AI-suggested patients for empty slots (`backend/app/api/v1/analytics/schedule_intelligence_router.py`)
- [x] Alert: same-day unfilled slot notification to receptionist with suggested patients (`backend/app/workers/maintenance_worker.py` — `schedule.unfilled_alert`)
- [x] FE: Schedule intelligence panel on agenda sidebar (`frontend/components/schedule-intelligence-panel.tsx`)
- [x] FE: No-show risk indicator on appointment cards (low/medium/high) (`frontend/components/no-show-risk-badge.tsx`)
- [x] FE: Suggested fill actions (one-click send invite to suggested patient) (`frontend/components/suggested-fill-card.tsx`)

### VP-14: Multi-Currency Billing

Invoice in COP/USD/EUR with automatic conversion. Growing dental tourism in Medellín/Cartagena. Border clinics (Cúcuta) serve Venezuelan patients. Plan-gated to Clínica+ tier.

- [x] Add `currency` field to invoice model (default COP, options: COP/USD/EUR/MXN) (`backend/app/models/tenant/invoice.py`, `012_sprint25_reputation_intelligence.py`)
- [x] Add `exchange_rate` and `exchange_rate_date` fields to invoice (`backend/app/models/tenant/invoice.py`)
- [x] Exchange rate service: daily rates from Banco de la República API (COP) or fallback to open exchange rates (`backend/app/integrations/exchange_rates/banco_republica.py`)
- [x] Cache exchange rates in Redis (TTL 1h) (`backend/app/services/exchange_rate_service.py`)
- [x] Multi-currency service catalog: prices can be defined in multiple currencies (`backend/app/models/tenant/service_catalog.py` — `prices_multi_currency` JSONB)
- [x] Invoice PDF renders with correct currency symbol and formatting (`backend/app/services/invoice_service.py` — `format_currency_amount()` helper + `*_formatted` fields in invoice dict)
- [x] Payment recording supports multi-currency (amount_paid_cents + currency) (`backend/app/schemas/payment.py` — `currency` field; `backend/app/models/tenant/payment.py` — `currency` column; `backend/app/services/payment_service.py` + `backend/app/api/v1/payments/router.py` wired through)
- [x] `GET /api/v1/billing/exchange-rates` — Current exchange rates (`backend/app/api/v1/billing/exchange_rate_router.py`)
- [x] FE: Currency selector on invoice creation (`frontend/components/currency-selector.tsx`)
- [x] FE: Exchange rate display on invoice detail (`frontend/components/exchange-rate-display.tsx`)
- [x] FE: Multi-currency financial reports (normalize to COP for clinic reporting) (`frontend/components/analytics/multi-currency-report.tsx`)

### VP-15: Patient Loyalty / Points Program

Points for completed appointments, on-time payments, referrals. Redeemable for discounts. +15-20% retention. Multiplies effect of memberships (VP-01) and referrals (VP-08).

- [x] Design `loyalty_config` in tenant settings JSONB: enabled, points_per_appointment, points_per_referral, points_per_ontime_payment, points_to_currency_ratio (`backend/app/services/loyalty_service.py`)
- [x] Design `loyalty_points` table: patient_id, points_balance, lifetime_points_earned, lifetime_points_redeemed (`backend/app/models/tenant/loyalty.py`, `012_sprint25_reputation_intelligence.py`)
- [x] Design `loyalty_transactions` table: patient_id, type (earned/redeemed/expired/adjusted), points, reason, reference_id, created_at (`backend/app/models/tenant/loyalty.py`)
- [x] Award points on: appointment completion, on-time payment, referral completion, membership renewal (`backend/app/workers/maintenance_worker.py` — loyalty handlers)
- [x] `GET /api/v1/portal/loyalty` — Patient views points balance and history (`backend/app/api/v1/portal/loyalty_router.py`)
- [x] `POST /api/v1/loyalty/redeem` — Redeem points for discount on next invoice (staff action) (`backend/app/api/v1/loyalty/router.py`)
- [x] Points expiration: configurable TTL (default 12 months of inactivity) (`backend/app/services/loyalty_service.py`, `maintenance_worker.py`)
- [x] `GET /api/v1/loyalty/leaderboard` — Top patients by points (gamification) (`backend/app/api/v1/loyalty/router.py`)
- [x] FE: Portal loyalty page — balance, history, available rewards (`frontend/app/(portal)/loyalty/page.tsx`)
- [x] FE: Points redemption flow at checkout (staff applies patient points) (`frontend/components/loyalty-redemption-dialog.tsx`)
- [x] FE: Loyalty program settings page (clinic_owner) (`frontend/app/(dashboard)/settings/loyalty/page.tsx`)

### GAP-01: Periodontograma (Periodontal Charting)

~30% of adult patients need perio treatment. Clinics doing perio work CANNOT use DentalOS without this. Interactive periodontal charting with pocket depths, bleeding, recession, mobility, and furcation per tooth. Table stakes for any complete dental SaaS.

- [x] Design `periodontal_records` table: patient_id, recorded_by, recorded_at, dentition_type, notes (`backend/app/models/tenant/periodontal.py`, `012_sprint25_reputation_intelligence.py`)
- [x] Design `periodontal_measurements` table: record_id, tooth_number (FDI), site (mesial_buccal, buccal, distal_buccal, mesial_lingual, lingual, distal_lingual), pocket_depth, recession, clinical_attachment_level, bleeding_on_probing (bool), plaque_index, mobility (0-3), furcation (0-3) (`backend/app/models/tenant/periodontal.py`)
- [x] `POST /api/v1/patients/{patient_id}/periodontal-records` — Create record with measurements (doctor/assistant) (`backend/app/api/v1/periodontal/router.py`)
- [x] `GET /api/v1/patients/{patient_id}/periodontal-records` — List records (`backend/app/api/v1/periodontal/router.py`)
- [x] `GET /api/v1/patients/{patient_id}/periodontal-records/{id}` — Get with all measurements (`backend/app/api/v1/periodontal/router.py`)
- [x] `GET /api/v1/patients/{patient_id}/periodontal-records/compare` — Compare two records (improvement tracking) (`backend/app/api/v1/periodontal/router.py`)
- [x] Voice-to-periodontogram: extend V-01 pipeline to parse "18 mesial 4, bleeding" → structured perio data (`backend/app/services/perio_voice_parser.py`)
- [x] FE: Periodontal charting view (6-site measurement grid per tooth, color-coded depths) (`frontend/app/(dashboard)/patients/[id]/periodontal/page.tsx`, `frontend/components/perio-measurement-grid.tsx`)
- [x] FE: Perio comparison view (before/after with color diff) (`frontend/components/perio-comparison-view.tsx`)
- [x] FE: Voice recording button on perio charting screen (`frontend/components/perio-voice-recorder.tsx`)

### GAP-04: Gestión de Convenios (Corporate Agreements / Discount Plans)

Many clinics in Colombia have agreements with empresas, universidades, fondos de empleados. Auto-apply discounts when patient is linked to a convenio — eliminates manual calculation errors.

- [x] Design `convenios` table: company_name, contact_info JSONB, discount_rules JSONB, valid_from, valid_until, is_active (`backend/app/models/tenant/convenio.py`, `backend/alembic_tenant/versions/012_sprint25_reputation_intelligence.py`)
- [x] Design `convenio_patients` table: convenio_id, patient_id, employee_id (company internal) (`backend/app/models/tenant/convenio.py`, `backend/alembic_tenant/versions/012_sprint25_reputation_intelligence.py`)
- [x] `POST /api/v1/convenios` — Create convenio (clinic_owner) (`backend/app/api/v1/convenios/router.py`)
- [x] `GET /api/v1/convenios` — List convenios (`backend/app/api/v1/convenios/router.py`)
- [x] `PUT /api/v1/convenios/{id}` — Update convenio (`backend/app/api/v1/convenios/router.py`)
- [x] `POST /api/v1/patients/{id}/convenio` — Link patient to convenio (`backend/app/api/v1/convenios/router.py`)
- [x] Auto-apply convenio discount on invoice creation (hook into billing service) (`backend/app/services/invoice_service.py` step 2b, `backend/app/services/convenio_service.py`)
- [x] FE: Convenio management page (clinic_owner) (`frontend/app/(dashboard)/convenios/page.tsx`)
- [x] FE: Patient convenio badge and discount display on invoice (`frontend/components/convenio-patient-badge.tsx`)

### GAP-08: Gestión de Tareas (Internal Task Management)

Clinics currently use WhatsApp groups for task coordination — messy and untracked. Assign, track, and prioritize tasks among staff. Feeds into GAP-05 and GAP-06 automated tasks.

- [x] Design `staff_tasks` table: title, description, assigned_to, priority, status, due_date, patient_id, reference_id/type, metadata JSONB (`backend/app/models/tenant/staff_task.py`)
- [x] `POST /api/v1/tasks` — Create task (any staff role) (`backend/app/api/v1/tasks/router.py`)
- [x] `GET /api/v1/tasks` — List tasks (filterable by assignee, status, type) (`backend/app/api/v1/tasks/router.py`)
- [x] `PUT /api/v1/tasks/{id}` — Update task with validated status transitions (`backend/app/api/v1/tasks/router.py`)
- [x] Notification on task assignment (`backend/app/services/staff_task_service.py` — dispatches `notification.dispatch` with `type='task_assigned'`)
- [x] FE: Task list/board view with filters
- [x] FE: Quick-add task from patient profile, invoice, appointment (`frontend/components/quick-add-task-button.tsx`)

### GAP-10: Super Familias (Family Grouping)

Families are the natural unit in dental — parent brings kids, pays for all. Link patients into family groups for consolidated billing, family discounts, and unified communication.

- [x] Design `family_groups` table: name, primary_contact_patient_id (`backend/app/models/tenant/family.py`, `backend/alembic_tenant/versions/012_sprint25_reputation_intelligence.py`)
- [x] Design `family_members` table: family_group_id, patient_id, relationship (parent/child/spouse/sibling) (`backend/app/models/tenant/family.py`, `backend/alembic_tenant/versions/012_sprint25_reputation_intelligence.py`)
- [x] `POST /api/v1/families` — Create family group (`backend/app/api/v1/families/router.py`)
- [x] `GET /api/v1/families/{id}` — Get family with members (`backend/app/api/v1/families/router.py`)
- [x] `POST /api/v1/families/{id}/members` — Add member (`backend/app/api/v1/families/router.py`)
- [x] Consolidated family billing view (all invoices for family members) (`backend/app/services/family_service.py`, `backend/app/api/v1/families/router.py`)
- [x] FE: Family group management on patient profile (`frontend/app/(dashboard)/patients/[id]/family/page.tsx`)
- [x] FE: Family billing summary view (`frontend/components/family-billing-summary.tsx`)

---

## Sprint 27-28: AI Advisor, WhatsApp Chat & Email Marketing (Post-Launch Month 7-8)

**Goal:** Ship AI-powered treatment recommendations, bidirectional WhatsApp, and email marketing campaigns to complete the patient engagement suite.

### VP-12: Bidirectional WhatsApp Chat

Unified inbox in dashboard for WhatsApp conversations with patients. Currently only sends template messages. Clinics need to answer questions, send post-op instructions, coordinate appointments.

- [x] WhatsApp Business API webhook for incoming messages
- [x] Design `whatsapp_conversations` table: patient_id, phone_number, status (active/archived), last_message_at, assigned_to (staff user_id)
- [x] Design `whatsapp_messages` table: conversation_id, direction (inbound/outbound), content, media_url, status (sent/delivered/read/failed), timestamp
- [x] Inbound message processing: match phone number to patient record
- [x] `GET /api/v1/messaging/conversations` — List active conversations (staff)
- [x] `GET /api/v1/messaging/conversations/{id}/messages` — Message history
- [x] `POST /api/v1/messaging/conversations/{id}/send` — Send message (staff)
- [x] Real-time updates via WebSocket or SSE for new incoming messages
- [x] Conversation assignment: receptionist assigns conversations to staff members
- [x] Quick-reply templates for common responses (appointment confirmation, directions, hours)
- [x] FE: WhatsApp inbox page — conversation list + message thread
- [x] FE: Unread message badge in navigation
- [x] FE: Quick-reply template selector
- [x] FE: Patient profile link from conversation

### VP-13: AI Treatment Recommendation

Based on odontogram conditions + patient history, AI suggests a treatment plan with procedures from the clinic's service catalog and prices. Reduces plan creation from 10-15 min to <2 min. Reuses Claude API from voice pipeline.

- [x] AI treatment advisor service: input = odontogram state + patient age/history + catalog → output = suggested procedures with rationale
- [x] `POST /api/v1/treatment-plans/ai-suggest` — Generate AI treatment suggestion (doctor)
- [x] Claude API integration: structured prompt with patient context + dental knowledge
- [x] Map AI suggestions to clinic's service catalog (procedure codes + prices)
- [x] Confidence score per suggestion (high/medium/low)
- [x] Doctor review flow: accept, modify, or reject each suggestion before creating plan
- [x] Usage metering: track AI suggestions per doctor for add-on billing
- [x] Add-on gating: check AI Treatment Advisor add-on is active for tenant
- [x] FE: "AI Suggest" button on treatment plan creation screen
- [x] FE: AI suggestion review panel — accept/modify/reject per procedure
- [x] FE: AI confidence indicators and reasoning display

### VP-17: Email Marketing Campaigns

Patient segmentation + dental-specific email templates in Spanish + open/click tracking. Extends recall engine (VP-02). Pre-built Spanish templates are a competitive advantage over US-centric tools.

- [x] Design `email_campaigns` table: name, subject, template_id, segment_filters JSONB, status (draft/scheduled/sending/sent), scheduled_at, sent_count, open_count, click_count
- [x] Design `email_campaign_recipients` table: campaign_id, patient_id, email, status (pending/sent/opened/clicked/bounced/unsubscribed)
- [x] Patient segmentation engine: filter by last visit date, procedures received, age range, insurance type, membership status, balance
- [x] `POST /api/v1/marketing/campaigns` — Create campaign (clinic_owner)
- [x] `GET /api/v1/marketing/campaigns` — List campaigns with stats
- [x] `POST /api/v1/marketing/campaigns/{id}/send` — Send campaign
- [x] `POST /api/v1/marketing/campaigns/{id}/schedule` — Schedule campaign
- [x] Open/click tracking via tracking pixel and redirect links
- [x] Seed 10 dental email templates in Spanish: recall, birthday, new service, holiday, referral promo, membership promo, treatment followup, post-op care, feedback request, welcome
- [x] Unsubscribe handling (CAN-SPAM / Colombia Ley 1581 compliance)
- [x] Bundled with Patient Engagement Suite add-on (VP-02 recall + VP-17 campaigns)
- [x] FE: Campaign builder — template selection, segment filters, preview, schedule
- [x] FE: Campaign analytics dashboard — open rate, click rate, unsubscribe rate, revenue attributed
- [x] FE: Email template editor (basic rich text, variable interpolation: {patient_name}, {clinic_name}, etc.)

### GAP-14: Informes IA (Natural Language Reports)

"How much revenue did Dr. Garcia generate last month?" → AI answers with charts. Low effort since Claude API is already integrated from voice pipeline. High wow factor for demos.

- [x] `POST /api/v1/analytics/ai-query` — Natural language query endpoint (doctor/clinic_owner)
- [x] Claude API integration: convert natural language → SQL-safe analytics query
- [x] Predefined safe query templates (revenue by period, appointments by doctor, top procedures, patient demographics, etc.)
- [x] Guardrails: only SELECT on analytics views, no raw table access, no PHI in responses
- [x] FE: "Ask AI" search bar on analytics dashboard
- [x] FE: AI response display with charts/tables

---

## Sprint 29-30: Patient Financing, Chatbot & Surveys (Post-Launch Month 9-10)

**Goal:** Ship patient financing integration, AI virtual receptionist, and satisfaction surveys.

### VP-11: Patient Financing (Cuotas vía Fintech)

Interest-free installments for expensive treatments via fintech partners (Addi, Sistecrédito). Treatment acceptance increases 30-60% with financing options. Revenue share model (1-2%).

- [x] Addi API integration (payment plan creation, status callbacks) — `integrations/financing/addi_service.py` + mock
- [x] Sistecrédito API integration (as alternative/complementary) — `integrations/financing/sistecredito_service.py` + mock
- [x] Add `financing` payment method to billing module — `models/tenant/financing.py` (FinancingApplication, FinancingPayment)
- [x] `POST /api/v1/billing/invoices/{id}/financing-request` — Request financing for invoice — `api/v1/financing/router.py`
- [x] Financing status tracking: requested → approved → disbursed → repaying → completed — model + webhook handler
- [x] Financing eligibility check: patient credit pre-qualification — `GET /billing/invoices/{id}/financing-eligibility`
- [x] Auto-record payment on financing disbursement (clinic receives full amount) — webhook router + service `handle_webhook_update`
- [x] Revenue share tracking for DentalOS (1-2% per financed transaction)
- [x] FE: "Finance this treatment" button on invoice/quotation — `frontend/components/billing/finance-treatment-button.tsx`
- [x] FE: Financing status on invoice detail — `frontend/components/billing/financing-status-badge.tsx`
- [x] FE: Financing report for clinic_owner (financed amounts, approval rate) — `GET /financing/report` + `frontend/app/(dashboard)/financing/page.tsx`

### VP-16: AI Virtual Receptionist / Chatbot

24/7 bot on web and WhatsApp that schedules appointments, answers FAQs, and processes payments. In LATAM the value is 24/7 availability — clinics close at 6pm but patients search at night.

- [x] Chatbot engine: intent classification (schedule, reschedule, cancel, FAQ, payment, hours, location, emergency) — `app/services/chatbot_engine.py`
- [x] Claude API integration for natural language understanding (Spanish dental context) — uses `ai_claude_client.call_claude()` with haiku
- [x] WhatsApp chatbot: integrate with VP-12 bidirectional WhatsApp — `chatbot_service.handle_message(channel="whatsapp")`
- [x] Web widget chatbot: embeddable JavaScript widget for clinic website — `api/v1/chatbot/widget_router.py`
- [x] Appointment scheduling flow: available slots → patient selects → confirmation — `chatbot_engine._build_scheduling_response()` multi-turn state machine
- [x] FAQ knowledge base: configurable per clinic (hours, services, prices, location, insurance accepted) — `chatbot_engine._build_faq_response()` + `chatbot_config JSONB`
- [x] Payment collection: send payment link via chat — intent=payment generates payment link response
- [x] Human handoff: escalate to staff when bot can't resolve — `chatbot_service.escalate_conversation()`
- [x] `GET /api/v1/chatbot/conversations` — Bot conversation history (staff oversight) — `api/v1/chatbot/router.py`
- [x] `PUT /api/v1/chatbot/config` — Configure bot responses, FAQ, business hours (clinic_owner) — `api/v1/chatbot/router.py`
- [x] Usage metering for add-on billing (conversations per month) — conversation count tracked per tenant
- [x] FE: Chatbot configuration page (clinic_owner — FAQs, tone, hours) — `frontend/app/(dashboard)/chatbot/config/page.tsx`
- [x] FE: Bot conversation monitoring dashboard (staff) — `frontend/app/(dashboard)/chatbot/page.tsx`
- [x] FE: Web widget customization (colors, position, greeting message) — `frontend/components/chatbot/widget-customizer.tsx`
- [x] FE: Conversation viewer with message bubbles, escalate/resolve actions — `frontend/components/chatbot/conversation-viewer.tsx`

### VP-21: Patient Satisfaction Surveys (NPS/CSAT)

Automated post-appointment surveys with NPS and CSAT tracking per doctor. Feeds into reputation management (VP-09). Actionable data for clinic_owner.

- [x] Design `nps_survey_responses` table: patient_id, appointment_id, doctor_id, nps_score (0-10), csat_score (1-5), comments, submitted_at — `app/models/tenant/nps_survey.py`
- [x] NPS calculation service: promoters (9-10), passives (7-8), detractors (0-6) — `app/services/nps_survey_service.py`
- [x] Auto-send survey after appointment (idempotent, deduplicates by appointment_id) — `nps_survey_service.auto_send_after_appointment`
- [x] Multi-channel delivery: WhatsApp default (channel stored per survey record)
- [x] `GET /api/v1/analytics/nps` — NPS dashboard data with monthly trend — `app/api/v1/surveys/router.py`
- [x] `GET /api/v1/analytics/nps/by-doctor` — NPS breakdown per doctor — `app/api/v1/surveys/router.py`
- [x] NPS trend over time (monthly, configurable date range)
- [x] Alert clinic_owner on detractor response — `_handle_detractor` (logs structured event; full notification deferred to Sprint 31+)
- [x] Public endpoints: `GET/POST /public/{slug}/nps-survey/{token}` — `app/api/v1/surveys/public_router.py`
- [x] FE: NPS/CSAT dashboard with trends, per-doctor breakdown — `frontend/app/(dashboard)/analytics/nps/page.tsx` + `frontend/components/analytics/nps-chart.tsx`
- [x] FE: Patient-facing survey form (mobile-optimized, WhatsApp-embedded or web link) — `frontend/app/(public)/survey/nps/[token]/page.tsx`
- [x] FE: Detractor alert inbox for clinic_owner — `frontend/components/analytics/detractor-inbox.tsx`

### GAP-09: Telemedicina (Video Consultations)

Post-COVID, teleodontología is growing. Built-in video consultation capability linked to appointment and clinical record. Listed in pricing as Telehealth add-on ($15/loc/mo) but no spec exists yet.

- [x] Integrate video provider (Daily.co or Twilio Video) — `integrations/telemedicine/daily_service.py` + mock
- [x] Design `video_sessions` table: appointment_id, provider_session_id, status (created/active/ended), started_at, ended_at, duration_seconds, recording_url — migration 014 + `models/tenant/video_session.py`
- [x] `POST /api/v1/appointments/{id}/video-session` — Create video session for appointment (doctor) — `api/v1/telemedicine/router.py`
- [x] `GET /api/v1/appointments/{id}/video-session` — Get session URL/token — `api/v1/telemedicine/router.py`
- [x] Patient joins via portal or unique link (no app install required) — `GET /portal/video-sessions/{id}/join`
- [x] Auto-link video session to clinical record — `telemedicine_service.link_to_clinical_record()`
- [x] FE: "Start Video Call" button on appointment detail (doctor) — `frontend/components/appointments/video-call-button.tsx`
- [x] FE: Patient video call page (portal) — `frontend/app/portal/video/[sessionId]/page.tsx`
- [x] FE: Telemedicine management page (dashboard) — `frontend/app/(dashboard)/telemedicine/page.tsx`
- [x] Feature gate: Telehealth add-on check

---

## Sprint 31-32: Advanced Operations & Lab Management (Post-Launch Month 11-12)

**Goal:** Ship remaining value propositions — VoIP integration, EPS claims management, and dental lab order tracking.

### VP-18: VoIP with Screen Pop

When receiving a phone call, the patient's profile automatically appears on screen. Weave built a billion-dollar company on this. Lower impact in LATAM (WhatsApp > phone calls) but valuable for clinics with high call volume.

- [x] VoIP provider integration (Twilio Voice or local provider)
- [x] Caller ID → patient phone number matching service
- [x] `GET /api/v1/calls/screen-pop/{phone}` — Lookup patient by phone number
- [x] WebSocket push: incoming call notification with patient data to receptionist's browser
- [x] Call logging: design `call_log` table — patient_id, phone_number, direction, duration, staff_id, notes
- [x] `GET /api/v1/calls/log` — Call history with patient links
- [x] FE: Screen pop notification component (appears on incoming call)
- [x] FE: Call log page with patient links and note-taking
- [x] FE: Click-to-call from patient profile

### VP-19: EPS Claims Management (Gestión de Recobros)

Generate and track electronic claims to EPS insurers. High complexity — each EPS has different portals. Only for clinics with high EPS patient volume.

- [x] Design `eps_claims` table: patient_id, eps_code, claim_type, procedures JSONB, total_amount_cents, status (draft/submitted/acknowledged/paid/rejected/appealed), submitted_at, response_at
- [x] Claim generation service: compile patient + procedures + diagnoses into standardized claim format
- [x] `POST /api/v1/billing/eps-claims` — Create EPS claim (clinic_owner/billing staff)
- [x] `GET /api/v1/billing/eps-claims` — List claims with status filters
- [x] `PUT /api/v1/billing/eps-claims/{id}` — Update claim status
- [x] Claim status tracking workflow: draft → submitted → acknowledged → paid/rejected
- [x] Rejection handling: reason codes, resubmission flow
- [x] Aging report: claims by age bucket (30/60/90+ days)
- [x] FE: EPS claims management page — create, submit, track
- [x] FE: Claims aging dashboard
- [x] FE: Claim detail page with status history and documents

### VP-22: Dental Lab Order Management

Track orders to external dental laboratories with patient-order traceability. Lab coordination (5-15 day turnaround) is a common pain point currently managed via WhatsApp.

- [x] Design `lab_orders` table: patient_id, treatment_plan_id, lab_id, order_type (corona, puente, protesis, ferula, modelo, etc.), specifications JSONB, status (draft/sent/in_progress/ready/delivered/rejected), due_date, sent_at, completed_at
- [x] Design `dental_labs` table (tenant): name, contact_info JSONB, phone, email, address, is_active
- [x] `POST /api/v1/lab-orders` — Create lab order (doctor)
- [x] `GET /api/v1/lab-orders` — List orders with status filters
- [x] `PUT /api/v1/lab-orders/{id}` — Update order status
- [x] `POST /api/v1/lab-orders/{id}/send` — Send order to lab (generates PDF or email)
- [x] Status update notifications: alert doctor when lab marks order as ready
- [x] Overdue order alerts: notify when order passes due_date
- [x] Link lab order to patient's treatment plan and appointment (schedule delivery appointment)
- [x] FE: Lab order management page — create, track, filter by status/lab/patient
- [x] FE: Lab directory management (clinic_owner)
- [x] FE: Lab order detail with specifications and status timeline
- [x] FE: Overdue orders alert on dashboard

---

## Post-S32 Backlog (Competitive Analysis Gaps — Future)

Items identified from competitive analysis (Dentalink, Dentrix, Open Dental, Curve Dental) that are lower priority or high effort. To be scheduled based on customer demand and market signals.

### BACKLOG: GAP-07 — Módulo de Ortodoncia
Specialized orthodontics tracking: bracket bonding chart, archwire changes, appointment sequence, payment tracking per visit, material tracking. ~25-30% of clinic revenue. Consider a "lite" version first.
- [x] Design orthodontic case model and visit tracking
- [x] Bracket bonding chart UI
- [x] Ortho-specific payment plan (per-visit tracking over 12-36 months)
- [x] Material tracking per case

### BACKLOG: GAP-11 — Videos Educativos 3D
Curate or embed open-source dental education videos. Low dev effort if embedded from external library.
- [ ] Video library integration (embed or curate open-source dental education content)

### BACKLOG: GAP-12 — Módulo de Estética Facial
Facial aesthetics with body/face diagram for clinics doing botox/fillers. Niche feature.
- [x] Facial aesthetics module (body/face diagram, injection points tracking)

### BACKLOG: GAP-13 — Simulador de Sonrisa IA
AI-generated smile simulation for patient consultations. Could integrate 3rd party.
- [ ] AI smile simulation integration (3rd party or custom)

### BACKLOG: GAP-15 — Controlador IA (Workflow Compliance Monitor)
AI that monitors if clinical and administrative workflows are being completed on time.
- [x] AI workflow compliance monitor (alerts on incomplete workflows)

### BACKLOG: GAP-16 — Marketplace de API Abierta
Open API marketplace for third-party integrations. Valuable long-term for ecosystem.
- [ ] Public API marketplace with developer portal and OAuth2 for third-party apps

### BACKLOG: GAP-17 — Panel de Impacto Ecológico
"Paper saved" dashboard. Pure marketing feature, very low effort.
- [ ] Eco-impact dashboard (paper saved, digital vs analog metrics)

### BACKLOG: GAP-18 — Gestión Predictiva de Inventario
AI predicts inventory needs from scheduled procedures. Enhances INV module.
- [ ] AI-powered inventory prediction based on scheduled procedures

### BACKLOG: GAP-19 — Centro de Capacitación del Personal
In-app training LMS for staff onboarding and compliance training.
- [ ] In-app training/LMS module for staff

### BACKLOG: GAP-20 — App Gamificada Salud Pediátrica
Gamified kids brushing app. Very niche, low priority.
- [ ] Gamified pediatric oral health app

---

## Acceptance Criteria per Sprint

Each sprint must meet these criteria before sign-off:

### Sprint 1-2: Foundation Infrastructure
| Criteria | Target |
|----------|--------|
| Specs implemented | ~42 |
| Test coverage | 80% backend |
| API response time | p95 < 200ms for auth endpoints |
| Security | JWT RS256 validated, RBAC tested for all 6 roles |
| Infrastructure | Docker Compose up in < 2 min, seed data loads cleanly |
| Multi-clinic login | Doctor with multiple clinics sees clinic selector at login; token encodes selected clinic context |

### Sprint 3-4: Core Entities
| Criteria | Target |
|----------|--------|
| Specs implemented | ~53 |
| Test coverage | 80% backend, 70% frontend components |
| API response time | p95 < 200ms for patient CRUD |
| Search | Patient FTS returns results in ≤100ms after 3 characters typed |
| UI | All design system components pass accessibility audit (WCAG 2.1 AA) |

### Sprint 5-6: Clinical Core Part 1
| Criteria | Target |
|----------|--------|
| Specs implemented | ~46 |
| Test coverage | 85% odontogram module |
| Odontogram | All 12 conditions render correctly in classic mode |
| Performance | Odontogram state loads in < 300ms |
| Data | CIE-10 and CUPS catalogs loaded with dental subsets |
| Templates | Evolution templates for 5 common procedures loaded (resina, endodoncia, exodoncia, profilaxis, urgencia) |
| Service catalog | Service/price catalog accessible and editable before Sprint 7-8 quotation work |

### Sprint 7-8: Clinical Core Part 2
| Criteria | Target |
|----------|--------|
| Specs implemented | ~57 |
| Test coverage | 80% clinical records, treatment plans, consents |
| Audit | All clinical data writes generate audit log entries |
| PDF | Treatment plan and consent PDFs generate correctly |
| Signatures | Digital signature capture and storage validated; Ley 527/1999 metadata logged |
| Quotation | Odontogram conditions can auto-suggest procedures; treatment plan auto-prices from catalog; quotation PDF generated |
| Tooth photos | Photo attachable to specific tooth in ≤2 taps from odontogram screen |

### Sprint 9-10: Agenda and Voice
| Criteria | Target |
|----------|--------|
| Specs implemented | ~50 |
| Test coverage | 80% appointment module, 70% voice pipeline |
| Calendar | Daily view is default; day/week/month views render correctly |
| Scheduling | No double-booking possible; appointment creation completable in ≤3 taps |
| Intelligent duration | Appointment type auto-fills slot length (eval 20min, endo 1h20, etc.) |
| Reminders | Email reminders send at configured times |
| Voice | Voice capture records and parses dental dictation with >90% accuracy for tooth numbers in test set |
| Voice UX | Review-before-apply mode: user confirms changes before odontogram is written |

### Sprint 11-12: Operations
| Criteria | Target |
|----------|--------|
| Specs implemented | ~67 |
| Test coverage | 75% billing, portal, messaging |
| Billing | Invoice creation, payment recording, balance calculation accurate |
| Portal | Patient can log in, view appointments, sign consents |
| WhatsApp | Template messages send successfully |
| Referral | Doctor can create inter-specialist referral; receiving doctor notified |

### Sprint 13-14: Compliance
| Criteria | Target |
|----------|--------|
| Specs implemented | ~20 |
| RIPS | Generates valid AF, AC, AP, AT, AM, AN, AU files |
| RDA | Compliance check returns accurate score |
| Audit | 100% of clinical data access logged |
| Retention | 15-year retention policy enforced at DB level |
| E-invoice | MATIAS API integration generates CUFE; XML retrievable; multiple roles can invoice |

### Sprint 15-16: Advanced Features and Inventory
| Criteria | Target |
|----------|--------|
| Specs implemented | ~37 |
| Analytics | Dashboard loads in < 1s for clinics with 10K patients |
| Import | CSV import handles 5K patients in < 60s |
| Export | Patient export streams without memory issues |
| Admin | Superadmin can manage tenants, plans, feature flags |
| Inventory | Semaphore alerts (green/yellow/red) visible in inventory dashboard; sterilization cycle log functional |
| Implants | Implant registered to patient + tooth; traceability report available |

### Sprint 17-18: Beta
| Criteria | Target |
|----------|--------|
| Beta clinics | 3-5 active beta testers |
| Load test | 500 concurrent users sustained for 30 min |
| Security | Zero critical/high vulnerabilities from audit |
| Performance | p95 API < 200ms, p99 < 500ms |
| Uptime | 99.9% during beta period |

### Sprint 19-20: Launch
| Criteria | Target |
|----------|--------|
| Production | All infrastructure provisioned and validated |
| Monitoring | Alerts configured for all critical paths |
| Documentation | User guides for all 4 roles complete |
| Compliance | Colombia legal review passed |
| Launch | First paying customers onboarded |

### Sprint 21-22: Patient Engagement & Revenue Acceleration
| Criteria | Target |
|----------|--------|
| Membership Plans | Patient can subscribe, discount auto-applies on invoice, portal shows membership |
| Recall Engine | Campaigns identify inactive patients, send multi-channel sequences, track conversions |
| Digital Intake | Patient completes intake on phone pre-appointment, data auto-populates record in <2 min |
| Morning Huddle | Dashboard loads in <1s, shows all 8 data sections, printable summary works |
| Test coverage | 80% for all new modules |

### Sprint 23-24: Colombia Integrations & Growth
| Criteria | Target |
|----------|--------|
| Nequi/Daviplata | QR payment flow works end-to-end in sandbox, webhook confirms payment |
| EPS Verification | ADRES lookup returns affiliation status, cached in Redis, badge displays on patient |
| RETHUS | Doctor registration verified against MinSalud, monthly re-check via cron |
| Referral Program | Patient shares code, referred patient books, referrer earns reward automatically |
| Post-Op Instructions | Auto-dispatched on procedure completion, 10 templates seeded |
| Cash Register (GAP-02) | Open/close register, auto-record invoice payments, printable daily report |
| Expenses (GAP-03) | Record/list expenses by category, P&L report shows revenue minus expenses |
| Delinquency Tasks (GAP-05) | Auto-create follow-up tasks at 30/60/90 day overdue thresholds |
| Acceptance Tasks (GAP-06) | Auto-create tasks for unaccepted quotations after configurable days |

### Sprint 25-26: Reputation, Intelligence & Multi-Currency
| Criteria | Target |
|----------|--------|
| Reputation | Post-appointment survey sends, routes high scores to Google Reviews |
| Schedule AI | No-show prediction and fill suggestions based on historical data |
| Multi-Currency | Invoice in COP/USD/EUR with exchange rates from Banco de la República |
| Loyalty | Points awarded, redeemable for discounts, portal shows balance |
| Periodontogram (GAP-01) | 6-site measurement per tooth, color-coded depths, comparison between records, voice input |
| Convenios (GAP-04) | Create convenio with discount rules, link patients, auto-apply on invoice |
| Task Management (GAP-08) | Create/assign/track tasks, notifications on assignment, quick-add from context |
| Family Groups (GAP-10) | Create family, link patients, consolidated billing view |

### Sprint 27-28: AI Advisor, WhatsApp Chat & Email Marketing
| Criteria | Target |
|----------|--------|
| WhatsApp Chat | Bidirectional messaging with real-time updates, conversation assignment |
| AI Treatment | Claude suggests treatment plan from odontogram, doctor reviews before applying |
| Email Marketing | Segment patients, send campaigns, track opens/clicks, 10 Spanish templates |
| AI Reports (GAP-14) | Natural language query returns analytics data, guardrails prevent PHI leakage |

### Sprint 29-30: Patient Financing, Chatbot & Surveys
| Criteria | Target |
|----------|--------|
| Financing | Addi integration works, financing request flow, payment auto-recorded |
| Chatbot | 24/7 bot schedules appointments, answers FAQs on WhatsApp + web |
| NPS/CSAT | Auto-survey after appointment, NPS dashboard with per-doctor breakdown |
| Telemedicine (GAP-09) | Video session linked to appointment, patient joins via portal link, no install |

### Sprint 31-32: Advanced Operations & Lab Management
| Criteria | Target |
|----------|--------|
| VoIP | Incoming call triggers screen pop with patient profile |
| EPS Claims | Claim generation, submission tracking, aging report |
| Lab Orders | Order tracking with patient-lab traceability, overdue alerts |

---

## Progress Tracking

| Sprint | Month | Specs | Backend | Frontend | Tests | Status |
|--------|-------|-------|---------|----------|-------|--------|
| 1-2 | 1 | ~42 | Auth + Tenants + Infra | -- | Infrastructure tests | Complete |
| 3-4 | 2 | ~53 | Users + Patients | Design system + Auth + Dashboard + Patients + Settings | Component + API tests | Complete |
| 5-6 | 3 | ~46 | Odontogram + Clinical Records (base) + Evolution Templates + Service Catalog | Odontogram + Clinical (base) | Odontogram tests | Complete |
| 7-8 | 4 | ~57 | Diagnoses + Procedures + Treatment + Consents + Rx + Quotation + Digital Sig + Tooth Photos | Clinical + Treatment + Consent + Rx screens | Clinical workflow tests | Complete |
| 9-10 | 5 | ~50 | Appointments + Scheduling + Waitlist + Public booking + Voice Pipeline | Calendar + Agenda screens + Voice UI | Scheduling + Voice tests | Complete |
| 11-12 | 6 | ~67 | Billing + Notifications + Portal + Messaging + WhatsApp + Referral | Billing + Portal screens | Integration tests | Complete |
| 13-14 | 7 | ~20 | Colombia compliance (RIPS, RDA, MATIAS/DIAN) | Compliance screens | Compliance validation tests | Complete |
| 15-16 | 8 | ~37 | Analytics + Import/Export + Merge + Inventory + Mexico + Admin | Analytics + Import + Inventory screens | Analytics + Load tests | Complete (59/59) |
| 17-18 | 9 | -- | Bug fixes + Optimizations | Bug fixes + UX polish | Security audit + Load tests | In Progress (32/36) |
| 19-20 | 10 | -- | Production deploy + Monitoring | Marketing site | Final validation | In Progress (26/38) |
| 21-22 | 11 | ~52 | Memberships + Recall + Intake + Huddle | Membership + Campaign + Intake + Huddle pages | Module tests | Complete (48/52) |
| 23-24 | 12 | ~44 | Nequi/Daviplata + EPS + RETHUS + Referrals + Post-Op + **Cash Register + Expenses + Delinquency/Acceptance Tasks** | Payment QR + EPS badge + Referral portal + Cash register + Expense mgmt | Integration tests | Complete (78/84) |
| 25-26 | 13 | ~47 | Reputation + Schedule AI + Multi-Currency + Loyalty + **Periodontogram + Convenios + Tasks + Families** | Reviews + Intelligence + Loyalty + Perio chart + Convenios + Task board + Family groups | Analytics + perio tests | Complete (71/73) |
| 27-28 | 14 | ~20 | WhatsApp Chat + AI Treatment + Email Marketing + **AI Reports** | Inbox + AI panel + Campaign builder + AI query bar | AI + messaging tests | Not Started |
| 29-30 | 15 | ~21 | Financing + Chatbot + NPS/CSAT + **Telemedicine** | Financing flow + Bot config + NPS dashboard + Video calls | Chatbot + survey + video tests | Not Started |
| 31-32 | 16 | ~10 | VoIP + EPS Claims + Lab Orders | Screen pop + Claims mgmt + Lab tracking | VoIP + claims tests | Complete |
| **Total** | **16** | **~530** | | | | |

---

## Dependencies Graph

The critical path determines what must be built before what. Parallel work is possible where dependencies allow.

```
CRITICAL PATH (sequential):

Infrastructure (I-01, I-04)
    |
    v
Authentication (I-02, A-01 through A-11)
    |
    v
Tenant Management (T-01 through T-10)
    |
    v
User Management (U-01 through U-06)
    |
    v
Patient CRUD (P-01 through P-06)
    |
    +---> Odontogram (OD-01 through OD-12)
    |         |
    |         +---> Voice-to-Odontogram (V-01 through V-05) [Sprint 9-10]
    |         |
    |         +---> Evolution Templates (CR-15 through CR-17)
    |         |
    |         v
    +---> Clinical Records (CR-01 through CR-14)
    |         |
    |         v
    +---> Treatment Plans (TP-01 through TP-10)
    |         |
    |         +---> Auto-Quotation (B-16 through B-19)
    |         |
    |         v
    +---> Consents (IC-01 through IC-09)
    |
    v
Appointments (AP-01 through AP-18)
    |
    v
Billing (B-01 through B-13)
    |
    v
Compliance (CO-01 through CO-08)
    |
    v
Analytics (AN-01 through AN-07)
```

### Parallel Tracks (can be developed alongside critical path)

```
Track A: Design System (Sprint 3-4)
    FE-DS-01 through FE-DS-19
    Independent of backend, enables all frontend work.

Track B: Infrastructure (ongoing)
    I-10 Security policy
    I-11 Audit logging
    I-14 Deployment architecture
    I-15 Monitoring
    I-16 Backup/DR
    I-17 File storage

Track C: Email Templates (as needed)
    E-01 through E-18
    Each built alongside its triggering feature.

Track D: Integrations (Sprint 11+)
    INT-01 WhatsApp
    INT-02 Twilio SMS
    INT-03 Email engine (Sprint 1 -- critical)
    INT-10 MATIAS API / DIAN electronic invoicing (Sprint 13+)
    INT-05 through INT-06 Mexico SAT/CFDI (Sprint 15+)
    INT-07 Payment gateway (Sprint 17+)
    INT-08 Cloud storage (Sprint 3 -- with patient documents)
    INT-09 Google Calendar (Sprint 17+)

Track E: Voice Pipeline (Sprint 9-10)
    V-01 through V-05
    Requires: Whisper API key, Claude API key
    External dependency: OpenAI Whisper API, Anthropic Claude API
    Feature gated: AI Voice add-on ($10/mo) plan check at V-01

Track F: Post-Launch Value Propositions (Sprint 21+)
    VP-01 Memberships: Requires billing (B-01+), portal, patient (P-01+)
    VP-02 Recall Engine: Requires notifications (N-01+), patients, appointments
    VP-03 Digital Intake: Requires patients (P-01+), anamnesis, consents (IC-01+), portal
    VP-04 Morning Huddle: Requires appointments, billing, patients (pure aggregation)
    VP-05 Nequi/Daviplata: Requires billing (B-01+), portal
    VP-06 EPS Verification: Requires patients (P-01+)
    VP-07 RETHUS: Requires users (U-01+)
    VP-08 Referrals: Requires portal, public booking (AP-15), billing
    VP-09 Reputation: Requires appointments, notifications
    VP-10 Schedule AI: Requires appointments (AP-01+), analytics
    VP-11 Financing: Requires billing (B-01+)
    VP-12 WhatsApp Chat: Requires WhatsApp integration (INT-01)
    VP-13 AI Treatment: Requires odontogram (OD-01+), catalog (CR-11), Claude API
    VP-14 Multi-Currency: Requires billing (B-01+)
    VP-15 Loyalty: Requires patients, billing, VP-01, VP-08
    VP-16 Chatbot: Requires VP-12, appointments (AP-01+), Claude API
    VP-17 Email Marketing: Requires VP-02, email engine (INT-03)
    VP-18 VoIP: Requires patients, Twilio Voice
    VP-19 EPS Claims: Requires billing, VP-06, compliance (CO-01+)
    VP-20 Post-Op: Requires evolution templates (CR-15+), notifications
    VP-21 NPS/CSAT: Requires appointments, notifications, VP-09
    VP-22 Lab Orders: Requires treatment plans (TP-01+), patients

Track G: Competitive Gap Closures (Sprint 23+)
    GAP-02 Cash Register: Requires billing (B-01+). Sprint 23-24
    GAP-03 Expenses: Requires tenant settings. Sprint 23-24
    GAP-05 Delinquency Tasks: Requires billing aging (B-12), GAP-08 Tasks. Sprint 23-24
    GAP-06 Acceptance Tasks: Requires quotations (B-16+), GAP-08 Tasks. Sprint 23-24
    GAP-01 Periodontogram: Requires patients (P-01+), odontogram (OD-01+), voice (V-01+). Sprint 25-26
    GAP-04 Convenios: Requires patients (P-01+), billing (B-01+). Sprint 25-26
    GAP-08 Task Management: Requires users (U-01+), notifications (N-01+). Sprint 25-26
    GAP-10 Family Groups: Requires patients (P-01+), billing (B-01+). Sprint 25-26
    GAP-14 AI Reports: Requires analytics (AN-01+), Claude API. Sprint 27-28
    GAP-09 Telemedicine: Requires appointments (AP-01+), portal, video provider API. Sprint 29-30
```

### Blocking Dependencies (must resolve before proceeding)

| Blocked Feature | Blocked By | Sprint |
|-----------------|-----------|--------|
| All backend endpoints | I-01 Multi-tenancy, I-02 Auth | Sprint 1 |
| Patient CRUD | T-09 Plan limits check | Sprint 2 |
| Odontogram | P-01 Patient create, T-06 Tenant settings | Sprint 5 |
| Clinical Records | P-01 Patient, I-11 Audit logging | Sprint 5 |
| Evolution Templates | CR-01 Clinical Records, OD-01 Odontogram | Sprint 5 |
| Auto-Quotation | B-14 Service Catalog, TP-05 Plan items | Sprint 7 |
| Digital Signature | IC-05 Consent sign, TP-08 Plan approve | Sprint 7 |
| Treatment Plans | CR-07 Diagnoses, CR-11 CUPS catalog | Sprint 7 |
| Voice Pipeline | OD-01 Odontogram (apply target), OpenAI + Anthropic API keys | Sprint 9 |
| Appointments | P-01 Patient, U-07 Doctor schedule | Sprint 9 |
| Billing | P-01 Patient, CR-12 Procedures, TP-05 Plan items | Sprint 11 |
| Patient Referral | U-03 Users, P-01 Patient, N-05 Notifications | Sprint 11 |
| RIPS generation | CR-01, CR-07, CR-12, P-01 (all clinical data) | Sprint 13 |
| Electronic invoicing | B-01 Invoices, I-13 Compliance engine, INT-10 MATIAS API | Sprint 13 |
| Inventory | P-01 Patient (for implant linking), I-11 Audit logging | Sprint 15 |
| Analytics | Requires data from patients, appointments, billing | Sprint 15 |
| Patient Portal | Requires auth, patients, appointments, billing, consents | Sprint 11 |
| VP-01 Membership Plans | Requires billing (B-01+), portal, patient management | Sprint 21 |
| VP-02 Recall Engine | Requires notifications (N-01+), patients, appointments data | Sprint 21 |
| VP-03 Digital Intake | Requires patients, anamnesis, consents, portal | Sprint 21 |
| VP-05 Nequi/Daviplata | Requires billing module, Nequi/Daviplata API credentials | Sprint 23 |
| VP-06 EPS Verification | Requires patient management, ADRES API access | Sprint 23 |
| VP-08 Referral Program | Requires portal, public booking (AP-15), billing | Sprint 23 |
| VP-12 WhatsApp Chat | Requires WhatsApp integration (INT-01) | Sprint 27 |
| VP-13 AI Treatment | Requires odontogram, service catalog, Claude API key | Sprint 27 |
| VP-16 AI Chatbot | Requires VP-12 WhatsApp Chat, appointments, Claude API | Sprint 29 |
| VP-19 EPS Claims | Requires billing, VP-06 EPS Verification, compliance engine | Sprint 31 |
| VP-21 NPS/CSAT | Requires VP-09 Reputation Management, appointments | Sprint 29 |
| GAP-02 Cash Register | Requires billing module (B-01+) | Sprint 23 |
| GAP-05 Delinquency Tasks | Requires billing aging (B-12), GAP-08 Task Management | Sprint 23 |
| GAP-06 Acceptance Tasks | Requires quotations (B-16+), GAP-08 Task Management | Sprint 23 |
| GAP-01 Periodontogram | Requires patients (P-01+), odontogram (OD-01+), voice pipeline (V-01+) | Sprint 25 |
| GAP-04 Convenios | Requires patients (P-01+), billing (B-01+) | Sprint 25 |
| GAP-08 Task Management | Requires users (U-01+), notifications (N-01+) | Sprint 25 |
| GAP-14 AI Reports | Requires analytics (AN-01+), Claude API key | Sprint 27 |
| GAP-09 Telemedicine | Requires appointments (AP-01+), portal, video provider API credentials | Sprint 29 |

---

## Risk Register

| Risk | Impact | Mitigation | Sprint |
|------|--------|------------|--------|
| Schema-per-tenant performance at scale (100+ tenants) | High | Load test early, connection pool tuning, read replicas | 1-2 |
| Odontogram SVG complexity | Medium | Start with classic grid, defer anatomic to later sprint | 5-6 |
| RIPS compliance complexity | High | Engage Colombian dental compliance consultant | 13-14 |
| WhatsApp Business API approval delays | Medium | Build with email fallback first, add WhatsApp async | 11-12 |
| Beta clinic recruitment | Medium | Start outreach in Sprint 13, use personal network | 17-18 |
| Offline sync complexity | Low | Defer to post-launch if needed, focus on online-first | 15-16 |
| Voice transcription accuracy | Medium | Use LLM post-processing to compensate Whisper errors. Review-before-apply mode prevents bad data from reaching odontogram | 9-10 |
| Inventory scope creep | Low | Keep inventory minimal: no purchase orders, no supplier management in MVP. Semaphore + sterilization + implant traceability only | 15-16 |
| Nequi/Daviplata API stability | Medium | Build with graceful fallback to manual payment recording. Test extensively in sandbox | 23-24 |
| ADRES/BDUA API availability | Medium | Cache aggressively (24h TTL). Manual verification fallback if API is down | 23-24 |
| RETHUS API access | Low | Web scraping fallback if no official API. Manual entry always available | 23-24 |
| Fintech partner integration delays (Addi/Sistecrédito) | Medium | Start partnership conversations early. Build generic financing interface | 29-30 |
| WhatsApp Business API message limits | Medium | Rate limiting + queue management. Start with template messages for campaigns | 27-28 |
| AI treatment recommendation accuracy | Medium | Doctor always reviews before applying. Track acceptance rate. Iterate on prompts | 27-28 |
| Post-launch feature scope creep | High | Strict tier prioritization (P0→P1→P2→P3). Ship P0 first, validate with metrics before P1 | 21+ |
| GAP-01 Perio voice accuracy | Medium | Reuse V-01 pipeline patterns. Start with manual entry, voice as enhancement. Review-before-apply | 25-26 |
| GAP-02 Cash register edge cases | Low | Keep simple: open/close/movements. No multi-register reconciliation in v1 | 23-24 |
| GAP-09 Video provider reliability | Medium | Use Daily.co (simpler) or Twilio Video. Fallback to shareable meeting link | 29-30 |
| GAP-14 AI report safety | Medium | Strict guardrails: read-only analytics views, no PHI, no raw SQL. Predefined query templates | 27-28 |

---

*Last updated: 2026-03-01*
*Document version: 1.3*
*v1.3: Added 10 competitive gap closures (GAP-01 through GAP-10, GAP-14) + post-S32 backlog (GAP-07, GAP-11 through GAP-20) from Dentalink/Dentrix/Open Dental/Curve analysis*
*v1.2: Added 22 post-launch value propositions (VP-01 through VP-22) across Sprints 21-32*
*v1.1: Revised based on client interview findings (2026-02-25)*
*Next review: End of Sprint 2*
