# DentalOS -- Implementation Checklist (R-05)

## Overview

This is the **living sprint-by-sprint implementation tracker** for DentalOS, a cloud-native multi-tenant dental SaaS for LATAM.

| Attribute           | Value                                         |
|---------------------|-----------------------------------------------|
| Total Sprints       | 20 (across 10 months)                         |
| Sprint Duration     | 2 weeks each                                  |
| Total Specs Mapped  | ~381                                          |
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
| **Add-on:** AI Voice | +$10/mo | Voice-to-Odontogram dictation |
| **Add-on:** AI Radiograph | +$20/mo | Radiograph AI analysis |

---

## Sprint 1-2: Foundation Infrastructure (Month 1)

**Goal:** Scaffold the entire project, establish multi-tenant architecture, implement authentication, and set up CI/CD.

**Spec count target:** ~42 specs (Infrastructure + Auth + Tenants)

### Project Scaffolding

- [x] FastAPI backend project structure with Poetry/uv dependency management
- [x] Next.js 16 frontend project with TailwindCSS and TypeScript
- [x] Docker Compose for local development (PostgreSQL, Redis, RabbitMQ)
- [ ] Monorepo or polyrepo structure decision finalized (see ADR-LOG)

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
- [ ] **I-14** Deployment architecture: Hetzner Cloud baseline plan

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
- [x] **T-10** `POST /api/v1/onboarding` -- Multi-step onboarding wizard
- [x] Integration tests: `tests/integration/test_tenants/` (T-01 through T-10, settings, onboarding)

### CI/CD and DevOps

- [ ] GitHub Actions CI pipeline: lint, type-check, test, build
- [ ] GitHub Actions CD pipeline: deploy to staging on merge to develop
- [ ] Pre-commit hooks: black, ruff, mypy (backend); eslint, prettier (frontend)
- [ ] Docker image builds for backend and frontend

### Email Templates (Critical)

- [ ] **E-01** Welcome email after clinic registration
- [ ] **E-02** Email verification link
- [ ] **E-03** Password reset link email
- [ ] **E-04** Team member invitation email
- [ ] **INT-03** Email delivery engine (SendGrid/SES) baseline integration

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

- [ ] **P-12** `GET /api/v1/patients/{patient_id}/documents` -- List patient documents
- [ ] **P-13** `POST /api/v1/patients/{patient_id}/documents` -- Upload document (X-ray, consent, lab result)
- [ ] **P-14** `DELETE /api/v1/patients/{patient_id}/documents/{doc_id}` -- Delete document
- [ ] **I-17** File storage architecture: S3-compatible with tenant-isolated buckets
- [ ] **INT-08** Cloud storage integration (Hetzner Object Storage or MinIO)

### Frontend: Design System (FE-DS-01 through FE-DS-19)

- [ ] **I-28** Design system spec: color palette, typography, spacing, TailwindCSS config
- [ ] **I-29** Responsive breakpoints: mobile-first, tablet optimization for clinical use
- [ ] **FE-DS-01** Design tokens: colors, typography (Inter/system), spacing, shadows
- [x] **FE-DS-02** Button component (primary, secondary, outline, ghost, danger)
- [x] **FE-DS-03** Input component (text, email, password, number, phone, date, textarea)
- [x] **FE-DS-04** Select/Combobox component (searchable, async loading)
- [x] **FE-DS-05** Data table component (sortable, paginated, responsive)
- [x] **FE-DS-06** Modal/Dialog component (sm, md, lg, full)
- [ ] **FE-DS-07** Toast/notification component (success, error, warning, info)
- [x] **FE-DS-08** Navigation sidebar (collapsible, role-based visibility)
- [x] **FE-DS-09** App header (clinic name, user menu, notifications, search)
- [x] **FE-DS-10** Card component (default, elevated, outlined)
- [x] **FE-DS-11** Badge/pill component (status badges, condition badges)
- [x] **FE-DS-12** Avatar component (image, initials fallback, status indicator)
- [ ] **FE-DS-14** Signature pad component (canvas drawing, base64 export)
- [ ] **FE-DS-15** File upload component (drag-and-drop, preview, progress)
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
- [ ] **FE-D-02** Doctor-specific dashboard (my appointments, my patients, my procedures)

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

- [ ] **I-24** ADR-005: SVG-based odontogram rendering approach
- [x] **FE-OD-01** Classic grid odontogram (32/20 teeth, 5 crown zones + root, color-coded)
- [ ] **FE-OD-02** Anatomic arch odontogram (SVG-based, interactive zoom -- premium tier)
- [x] **FE-OD-03** Condition selection panel (12 conditions with icons, quick-select, notes)
- [x] **FE-OD-04** History panel (sidebar timeline of changes, filter by date/condition)
- [ ] **FE-OD-05** Comparison view (side-by-side snapshots, visual diff)
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
- [ ] **B-18** `POST /api/v1/patients/{patient_id}/quotations/{quotation_id}/share` -- Share quotation via email/WhatsApp with payment link
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
- [ ] **RX-05** `GET /api/v1/catalog/medications` -- Medication catalog search

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

- [ ] **E-09** Treatment plan shared with patient
- [ ] **E-10** Consent form signature request

---

## Sprint 9-10: Agenda and Voice (Month 5)

**Goal:** Implement the full appointment lifecycle, scheduling, calendar views, waitlist, public booking, and Voice-to-Odontogram v1 -- the core differentiator.

> **Agenda North Star:** "If it is not faster than paper, we failed." Max 3 taps to schedule an appointment. Daily view is the DEFAULT (not weekly). Duration is intelligent: auto-calculated based on appointment type (eval = 20 min, endodontics = 1h20, etc.).

**Spec count target:** ~50 specs

### Backend: Appointments (AP-01 through AP-08)

- [ ] **AP-01** `POST /api/v1/appointments` -- Create appointment (validates schedule + conflicts); **target: appointment creation completable in ≤3 taps from agenda screen**
- [ ] **AP-02** `GET /api/v1/appointments/{appointment_id}` -- Get appointment detail
- [ ] **AP-03** `GET /api/v1/appointments` -- List appointments (filters: doctor, patient, date, status)
- [ ] **AP-04** `PUT /api/v1/appointments/{appointment_id}` -- Update/reschedule appointment
- [ ] **AP-05** `POST .../appointments/{appointment_id}/cancel` -- Cancel with reason
- [ ] **AP-06** `POST .../appointments/{appointment_id}/confirm` -- Patient confirmation
- [ ] **AP-07** `POST .../appointments/{appointment_id}/complete` -- Complete, link to clinical records
- [ ] **AP-08** `POST .../appointments/{appointment_id}/no-show` -- Mark no-show

### Backend: Scheduling and Availability (U-07, U-08, AP-09 through AP-11)

- [ ] **U-07** `GET /api/v1/users/{user_id}/schedule` -- Get doctor weekly schedule
- [ ] **U-08** `PUT /api/v1/users/{user_id}/schedule` -- Set doctor schedule (days, times, breaks)
- [ ] **AP-09** `GET /api/v1/appointments/availability` -- Available slots query; **intelligent duration: auto-calculate default slot length based on appointment type**
- [ ] **AP-10** `POST /api/v1/appointments/availability/block` -- Block time (vacation, meeting)
- [ ] **AP-11** `PUT .../appointments/{appointment_id}/reschedule` -- Quick drag-and-drop reschedule

### Backend: Waitlist (AP-12 through AP-14)

- [ ] **AP-12** `POST /api/v1/appointments/waitlist` -- Add to waitlist
- [ ] **AP-13** `GET /api/v1/appointments/waitlist` -- List waitlist entries
- [ ] **AP-14** `POST .../waitlist/{entry_id}/notify` -- Notify of available slot

### Backend: Public Booking (AP-15, AP-16)

- [ ] **AP-15** `POST /api/v1/public/booking/{tenant_slug}` -- Patient self-booking (public endpoint)
- [ ] **AP-16** `GET /api/v1/public/booking/{tenant_slug}/config` -- Booking page configuration

### Backend: Reminders (AP-17, AP-18)

- [ ] **AP-17** `GET /api/v1/settings/reminders` -- Reminder configuration
- [ ] **AP-18** `PUT /api/v1/settings/reminders` -- Update reminder configuration

### Backend: Voice-to-Odontogram v1 (V-01 through V-05)

Voice dictation is THE core differentiator per the client interview. Moved up from post-MVP. Pipeline: Audio → OpenAI Whisper → LLM (Claude) → Structured JSON → Odontogram API. Requires the AI Voice add-on ($10/mo).

- [x] **V-01** `POST /api/v1/voice/sessions` -- Start voice recording session (returns session_id, presigned S3 upload URL)
- [x] **V-02** `POST /api/v1/voice/sessions/{session_id}/upload` -- Submit audio file, trigger Whisper transcription (async)
- [x] **V-03** `GET /api/v1/voice/sessions/{session_id}` + `POST .../parse` -- Poll for transcription status + trigger LLM parsing; returns structured JSON (tooth numbers, conditions, procedures)
- [x] **V-04** `POST /api/v1/voice/sessions/{session_id}/apply` -- Apply parsed result to odontogram (review-before-apply mode: user confirms before write)
- [ ] **V-05** `POST /api/v1/voice/sessions/{session_id}/feedback` -- Submit correction feedback (tooth number errors, condition mismatches) for quality tracking
  - [ ] OpenAI Whisper API integration (external dependency, requires API key) -- MVP: stub in voice_worker.py
  - [ ] Anthropic Claude API integration for dental NLP parsing (external dependency, requires API key) -- MVP: stub in voice_service._parse_dental_text()
  - [ ] LLM prompt: extract tooth numbers (FDI), conditions (caries, fractura, corona, etc.), procedures from free-form Spanish dental dictation
  - [x] Review-before-apply mode: parsed results shown as diff before commit to odontogram
  - [ ] Accuracy tracking: log correction rate per session for quality monitoring
  - [x] Feature gate: AI Voice add-on plan check before allowing voice sessions

### Frontend: Agenda Screens (FE-AG-01 through FE-AG-06)

- [ ] **FE-DS-13** Calendar component (day/week/month views, event rendering, drag-and-drop)
- [ ] **FE-AG-01** Main calendar view (color-coded, drag-and-drop, multi-doctor columns, **daily view as DEFAULT**)
- [ ] **FE-AG-02** Create appointment modal (patient search, doctor, date/time, availability check, **appointment type auto-sets duration; whole flow completable in ≤3 taps**)
- [ ] **FE-AG-03** Appointment detail modal (patient info, status, actions: confirm/complete/cancel)
- [x] **FE-AG-04** Doctor schedule editor (weekly template, drag to adjust times)
- [x] **FE-AG-05** Waitlist sidebar panel (waiting patients, one-click scheduling)
- [ ] **FE-AG-06** Today's appointments view (timeline, patient status, quick actions)
- [ ] **FE-PP-10** Public booking page (clinic-branded, doctor selection, time picker)

### Frontend: Voice UI (FE-V-01 through FE-V-03)

- [x] **FE-V-01** Voice recording button (floating action in odontogram screen, tap to start/stop, recording indicator with waveform animation)
- [x] **FE-V-02** Transcription review panel (parsed teeth and conditions displayed as a diff over current odontogram, confirm/reject each change, apply button)
- [x] **FE-V-03** Voice session history (list of past sessions, transcription text, applied/rejected status, accuracy feedback)

### Frontend: Settings

- [ ] **FE-S-04** Odontogram configuration (mode, default view, condition colors)
- [ ] **FE-S-05** Notification settings (reminder timing, channels, templates)
- [x] **FE-AG-SCH** Doctor schedule settings page (`/settings/schedule` — weekly hours, breaks, duration defaults)
- [x] **FE-AG-VOI** Voice settings page (`/settings/voice` — enable toggle, max session duration, max sessions/hour)
- [x] **use-schedule** TanStack Query hooks: `useDoctorSchedule`, `useUpdateSchedule`, `useAvailabilityBlocks`, `useCreateBlock`, `useDeleteBlock`, `useAvailableSlots`
- [x] **use-waitlist** TanStack Query hooks: `useWaitlist`, `useAddToWaitlist`, `useNotifyWaitlistEntry`

### Email Templates

- [ ] **E-05** Appointment confirmation (email + WhatsApp)
- [ ] **E-06** 24-hour appointment reminder (email + WhatsApp + SMS)
- [ ] **E-07** 2-hour appointment reminder (WhatsApp + SMS)
- [ ] **E-08** Appointment cancellation notice
- [ ] **E-18** Waitlist slot available notification

---

## Sprint 11-12: Operations (Month 6)

**Goal:** Billing, notifications, patient portal, messaging, WhatsApp integration, and inter-specialist patient referral.

**Spec count target:** ~67 specs

### Backend: Billing and Invoicing (B-01 through B-13)

- [ ] **B-01** `POST /api/v1/patients/{patient_id}/invoices` -- Create invoice
- [ ] **B-02** `GET .../invoices/{invoice_id}` -- Get invoice detail
- [ ] **B-03** `GET /api/v1/invoices` -- List invoices (filters: status, date, patient, doctor)
- [ ] **B-04** `PUT .../invoices/{invoice_id}` -- Update draft invoice
- [ ] **B-05** `POST .../invoices/{invoice_id}/send` -- Send invoice to patient
- [ ] **B-06** `GET .../invoices/{invoice_id}/pdf` -- Generate invoice PDF
- [ ] **B-07** `POST .../invoices/{invoice_id}/payments` -- Record payment (partial supported)
- [ ] **B-08** `GET /api/v1/patients/{patient_id}/payments` -- List patient payments
- [ ] **B-09** `GET /api/v1/patients/{patient_id}/balance` -- Patient account balance
- [ ] **B-10** `POST /api/v1/patients/{patient_id}/payment-plans` -- Create payment plan
- [ ] **B-11** `GET .../payment-plans/{plan_id}` -- Get payment plan with installment schedule
- [ ] **B-12** `GET /api/v1/billing/commissions` -- Doctor commissions report
- [ ] **B-13** `GET /api/v1/billing/summary` -- Billing dashboard data

### Backend: Patient Referral (P-15)

- [ ] **P-15** `POST /api/v1/patients/{patient_id}/referrals` -- Create inter-specialist referral within clinic (referring doctor, receiving specialist, reason, urgency, linked odontogram state)
  - [ ] `GET /api/v1/patients/{patient_id}/referrals` -- List referrals for patient
  - [ ] `PUT .../referrals/{referral_id}` -- Update referral status (pending/accepted/completed)
  - [ ] Notification to receiving specialist on referral creation
  - [ ] Referral summary appears in receiving doctor's dashboard

### Backend: Notifications (N-01 through N-05)

- [ ] **N-01** `GET /api/v1/notifications` -- List in-app notifications
- [ ] **N-02** `POST .../notifications/{notification_id}/read` -- Mark as read
- [ ] **N-03** `POST /api/v1/notifications/read-all` -- Mark all as read
- [ ] **N-04** `GET /api/v1/notifications/preferences` -- Get notification preferences
- [ ] **N-05** Notification dispatch engine (routes to in-app, email, WhatsApp, SMS)
- [ ] **U-09** `PUT /api/v1/users/me/notifications` -- Update notification preferences

### Backend: Patient Portal (PP-01 through PP-13)

- [ ] **P-11** `POST /api/v1/patients/{patient_id}/portal-access` -- Grant/revoke portal access
- [ ] **PP-01** `POST /api/v1/portal/auth/login` -- Patient portal login
- [ ] **PP-02** `GET /api/v1/portal/me` -- Patient's own profile
- [ ] **PP-03** `GET /api/v1/portal/appointments` -- Patient's appointments
- [ ] **PP-04** `GET /api/v1/portal/treatment-plans` -- View treatment plans
- [ ] **PP-05** `POST .../portal/treatment-plans/{plan_id}/approve` -- Approve plan (digital signature)
- [ ] **PP-06** `GET /api/v1/portal/invoices` -- View invoices and payment history
- [ ] **PP-07** `GET /api/v1/portal/documents` -- View documents (X-rays, consents)
- [ ] **PP-08** `POST /api/v1/portal/appointments` -- Book appointment from portal
- [ ] **PP-09** `POST .../portal/appointments/{appointment_id}/cancel` -- Cancel own appointment
- [ ] **PP-10** `GET /api/v1/portal/messages` -- Message threads
- [ ] **PP-11** `POST /api/v1/portal/messages` -- Send message to clinic
- [ ] **PP-12** `POST .../portal/consents/{consent_id}/sign` -- Sign consent from portal
- [ ] **PP-13** `GET /api/v1/portal/odontogram` -- View own odontogram (read-only)

### Backend: Messaging (MS-01 through MS-05)

- [ ] **MS-01** `POST /api/v1/messages/threads` -- Create message thread
- [ ] **MS-02** `GET /api/v1/messages/threads` -- List threads (filter by patient, unread)
- [ ] **MS-03** `POST .../threads/{thread_id}/messages` -- Send message
- [ ] **MS-04** `GET .../threads/{thread_id}/messages` -- List messages in thread
- [ ] **MS-05** `POST .../threads/{thread_id}/read` -- Mark thread as read

### Integration: WhatsApp

- [ ] **INT-01** WhatsApp Business API integration (template messages, webhooks, sessions)
- [ ] **INT-02** Twilio SMS integration (appointment reminders, verification codes)

### Frontend: Billing Screens (FE-B-01 through FE-B-08)

- [ ] **FE-B-01** Invoice list page (table, filters, bulk actions)
- [ ] **FE-B-02** Create invoice form (patient, line items, tax, total)
- [ ] **FE-B-03** Invoice detail page (line items, payments, balance, PDF, send)
- [ ] **FE-B-04** Record payment modal (amount, method, partial support)
- [ ] **FE-B-05** Payment plan creation and management
- [ ] **FE-B-06** Service/procedure price catalog management
- [ ] **FE-B-07** Doctor commissions report page
- [ ] **FE-B-08** Billing overview dashboard (revenue charts, aging report)

### Frontend: Patient Portal (FE-PP-01 through FE-PP-09)

- [ ] **FE-PP-01** Patient portal login (clinic-branded)
- [ ] **FE-PP-02** Portal dashboard (next appointment, plans, messages, consents)
- [ ] **FE-PP-03** Portal appointments list (upcoming, past, book new, confirm/cancel)
- [ ] **FE-PP-04** Portal treatment plans (progress, approve with signature)
- [ ] **FE-PP-05** Portal document viewer (X-rays, consents, prescriptions)
- [ ] **FE-PP-06** Portal chat interface (messages, attachments)
- [ ] **FE-PP-07** Portal invoices and payment history
- [ ] **FE-PP-08** Portal consent signing (full document, signature pad)
- [ ] **FE-PP-09** Portal odontogram (read-only, color-coded, educational tooltips)

### Frontend: Settings

- [ ] **FE-S-06** Consent template management (list, create, edit, preview)
- [ ] **FE-S-08** Integrations page (WhatsApp, Google Calendar, payment gateway)

### Email Templates

- [ ] **E-11** Invoice sent to patient
- [ ] **E-12** Payment received confirmation
- [ ] **E-13** Overdue payment reminder
- [ ] **E-14** Patient portal access invitation
- [ ] **E-15** New message notification

---

## Sprint 13-14: Compliance (Month 7)

**Goal:** Implement Colombia-specific compliance (RDA, RIPS, DIAN via MATIAS API), audit verification, and data retention.

**Spec count target:** ~20 specs

### Backend: Compliance (CO-01 through CO-08)

- [ ] **I-13** Regulatory compliance engine: country adapter pattern (CO, MX, CL, AR, PE)
- [ ] **I-26** ADR-007: Country compliance adapter architecture
- [ ] **CO-01** `POST /api/v1/compliance/rips/generate` -- Generate RIPS files (AF, AC, AP, AT, AM, AN, AU)
- [ ] **CO-02** `GET /api/v1/compliance/rips/{batch_id}` -- Download RIPS batch
- [ ] **CO-03** `GET /api/v1/compliance/rips` -- RIPS generation history
- [ ] **CO-04** `POST .../rips/{batch_id}/validate` -- Validate RIPS before submission
- [ ] **CO-05** `GET /api/v1/compliance/rda/status` -- RDA compliance status check
- [ ] **CO-06** `POST /api/v1/compliance/e-invoice` -- Electronic invoice via MATIAS API (Colombia DIAN); DentalOS operates as "Casa de Software"; any authorized role (clinic_owner, doctor, assistant) can generate invoices -- not restricted to 1 user like Dentalink
- [ ] **CO-07** `GET .../e-invoice/{invoice_id}/status` -- E-invoice status with DIAN via MATIAS API
- [ ] **CO-08** `GET /api/v1/compliance/config` -- Country compliance configuration

### Integration: Electronic Invoicing

- [ ] **INT-10** MATIAS API integration for DIAN electronic invoicing (UBL 2.1, digital signature, CUFE, submission); replaces generic INT-04
  - [ ] DentalOS registered as "Casa de Software" in MATIAS
  - [ ] Multi-user invoice generation: RBAC allows clinic_owner, doctor, assistant with `billing:invoice:create` permission
  - [ ] CUFE generation and storage per invoice
  - [ ] XML and PDF retrieval from MATIAS after DIAN acceptance

### Audit and Data Retention

- [ ] **I-11** Audit logging verification: validate all clinical data access is logged
- [ ] **I-12** Data retention policies: 15-year clinical record retention (Colombia)
- [ ] Audit trail immutability verification
- [ ] Right-to-be-forgotten vs clinical retention mandate rules

### Frontend: Compliance Screens (FE-CO-01 through FE-CO-03)

- [ ] **FE-CO-01** RIPS generation page (period selection, generate, validate, download)
- [ ] **FE-CO-02** RDA compliance dashboard (compliance score, gaps, action items)
- [ ] **FE-CO-03** Electronic invoice list (status tracking, resend, download XML/PDF; **accessible to any authorized role, not just clinic_owner**)
- [ ] **FE-S-07** Compliance settings per country (RDA configuration, required fields)

---

## Sprint 15-16: Advanced Features and Inventory (Month 8)

**Goal:** Analytics, patient import/export, patient merge, inventory management with semaphore alerts, Mexico compliance, and offline support groundwork.

**Spec count target:** ~37 specs

### Backend: Analytics (AN-01 through AN-07)

- [ ] **AN-01** `GET /api/v1/analytics/dashboard` -- Clinic dashboard metrics
- [ ] **AN-02** `GET /api/v1/analytics/patients` -- Patient analytics (retention, demographics)
- [ ] **AN-03** `GET /api/v1/analytics/appointments` -- Appointment analytics (utilization, no-shows)
- [ ] **AN-04** `GET /api/v1/analytics/revenue` -- Revenue analytics (by period, doctor, procedure)
- [ ] **AN-05** `GET /api/v1/analytics/clinical` -- Clinical analytics (common diagnoses, procedures)
- [ ] **AN-06** `GET /api/v1/analytics/export` -- Export analytics to CSV/Excel
- [ ] **AN-07** `GET /api/v1/analytics/audit-trail` -- Audit trail viewer (clinic_owner only)

### Frontend: Analytics Screens (FE-AN-01 through FE-AN-04)

- [ ] **FE-AN-01** Analytics main dashboard (KPI cards, charts, period selector)
- [ ] **FE-AN-02** Patient analytics page (trends, retention, demographics)
- [ ] **FE-AN-03** Appointment analytics (utilization, cancellations, peak hours heatmap)
- [ ] **FE-AN-04** Revenue analytics (trends, by doctor, by procedure, payment methods)
- [ ] **FE-S-09** Audit log viewer (searchable, filterable)

### Backend: Patient Advanced Operations

- [ ] **P-08** `POST /api/v1/patients/import` -- Bulk import from CSV/Excel (async via queue)
- [ ] **P-09** `GET /api/v1/patients/export` -- Export patient list to CSV (streaming)
- [ ] **P-10** `POST /api/v1/patients/merge` -- Merge duplicate records (clinic_owner only)
- [ ] **FE-P-06** Patient import page (upload, column mapping, validation, progress)

### Backend: Inventory Management (INV-01 through INV-07)

Minimal viable inventory: materials tracking, expiry alerts, sterilization cycles, implant traceability. No purchase orders or supplier management in MVP -- keep scope focused.

- [ ] **INV-01** `POST /api/v1/inventory/items` -- Create inventory item (name, category, unit, initial stock, min_stock threshold, expiry_date)
- [ ] **INV-02** `GET /api/v1/inventory/items` -- List inventory items with semaphore status: green (ok), yellow (below min_stock), red (expired or out of stock)
- [ ] **INV-03** `PUT /api/v1/inventory/items/{item_id}` -- Update item (stock adjustment, expiry update)
- [ ] **INV-04** `POST /api/v1/inventory/items/{item_id}/movements` -- Record stock movement (consumption, restock, waste)
- [ ] **INV-05** `GET /api/v1/inventory/alerts` -- Active stock alerts (low stock + expiry within 30 days)
- [ ] **INV-06** `POST /api/v1/inventory/sterilization-cycles` -- Log sterilization cycle (autoclave batch, items included, timestamp, operator)
- [ ] **INV-07** `POST /api/v1/inventory/implants` -- Register implant with traceability (brand, lot number, patient link, tooth, date placed)
  - [ ] `GET /api/v1/patients/{patient_id}/implants` -- List implants for patient (traceability report)

### Frontend: Inventory Screens (FE-INV-01 through FE-INV-03)

- [ ] **FE-INV-01** Inventory dashboard (item list with semaphore color indicators, search, filter by category/status)
- [ ] **FE-INV-02** Item detail page (stock history, movement log, expiry tracking, sterilization records)
- [ ] **FE-INV-03** Alerts panel (red/yellow items, expiry warnings, one-click restock request draft)

### Mexico Compliance Adapter

- [ ] **INT-05** SAT CFDI integration (PAC, XML stamping, UUID)
- [ ] Mexico compliance adapter: NOM-024 requirements
- [ ] Mexico-specific document types (CURP validation, RFC)
- [ ] CFDI electronic invoicing flow

### Offline Support (if time allows)

- [ ] **I-18** Offline-first architecture design (Service Workers, IndexedDB schema, sync queue)
- [ ] **I-19** PWA configuration (service worker, manifest.json, cache strategies)
- [ ] **I-25** ADR-006: Offline sync approach decision

### Backend: Admin / Superadmin (AD-01 through AD-07)

- [ ] **AD-01** `POST /api/v1/admin/auth/login` -- Superadmin login (MFA required)
- [ ] **AD-02** `GET /api/v1/admin/tenants` -- Platform-wide tenant management with metrics
- [ ] **AD-03** `GET/PUT /api/v1/admin/plans` -- Manage subscription plans
- [ ] **AD-04** `GET /api/v1/admin/analytics` -- Platform-level analytics (MRR, MAU, churn)
- [ ] **AD-05** `GET/PUT /api/v1/admin/feature-flags` -- Feature flag management
- [ ] **AD-06** `GET /api/v1/admin/health` -- System health dashboard
- [ ] **AD-07** `POST .../admin/tenants/{tenant_id}/impersonate` -- Tenant impersonation

### Email Templates

- [ ] **E-16** Daily clinic summary email
- [ ] **E-17** Plan upgrade prompt (limit approaching)

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

- [ ] Database query optimization (EXPLAIN ANALYZE on slow queries)
- [ ] N+1 query detection and resolution
- [ ] Redis cache hit rate optimization (target: >90%)
- [ ] Frontend bundle size audit (target: <200KB initial JS)
- [ ] Image optimization (X-rays: lazy loading, progressive JPEG)
- [ ] API response time audit (target: p95 < 200ms for CRUD, < 500ms for reports)

### Security Audit

- [ ] OWASP Top 10 vulnerability scan
- [ ] SQL injection testing (SQLAlchemy parameterization verification)
- [ ] XSS prevention testing (frontend and API responses)
- [ ] JWT token security audit (RS256 key rotation, token revocation)
- [ ] File upload security (virus scanning, MIME type validation)
- [ ] PHI (Protected Health Information) access audit
- [ ] CORS and CSP headers verification
- [ ] Rate limiting effectiveness testing
- [ ] Tenant isolation penetration testing (cross-tenant data access attempts)

### Load Testing

- [ ] Load test: 500 concurrent users target
- [ ] Load test: 100 concurrent appointment bookings
- [ ] Load test: Odontogram bulk updates under load
- [ ] Load test: Full-text search (patients, CIE-10, CUPS) under load
- [ ] Database connection pool stress testing
- [ ] RabbitMQ queue depth under sustained load

### Bug Fixes from Beta Feedback

- [ ] Triage and prioritize beta feedback items
- [ ] Critical bug fixes (P0: data loss, security, crashes)
- [ ] High-priority bug fixes (P1: workflow blockers)
- [ ] UX improvements from clinical staff feedback
- [ ] Mobile/tablet usability fixes

### Additional Infrastructure

- [ ] **I-15** Monitoring and observability (structured logging, Sentry, APM)
- [ ] **I-16** Backup and disaster recovery (WAL archiving, PITR, cross-region backup)
- [ ] **INT-09** Google Calendar sync (optional bi-directional)
- [ ] **INT-07** Payment gateway integration (Mercado Pago, PSE)

---

## Sprint 19-20: Launch (Month 10)

**Goal:** Production deployment, monitoring, documentation, and Colombia launch.

**Spec count target:** Focus on operations, not new features.

### Production Deployment

- [ ] Hetzner Cloud production environment provisioning
- [ ] PostgreSQL managed database setup (production config, backups enabled)
- [ ] Redis production instance with persistence
- [ ] RabbitMQ cluster setup
- [ ] Load balancer configuration with SSL termination
- [ ] DNS and domain setup (dentalos.co or similar)
- [ ] Blue-green deployment pipeline finalized
- [ ] Rollback strategy tested

### Monitoring and Alerting

- [ ] Sentry error tracking (backend + frontend)
- [ ] Uptime monitoring (health check endpoints)
- [ ] Database performance monitoring
- [ ] Queue depth alerting (RabbitMQ)
- [ ] Disk space and resource utilization alerts
- [ ] Custom business metrics dashboard (tenant count, active users, appointments/day)
- [ ] On-call rotation and incident response runbook

### Documentation

- [ ] User guide for clinic owners (setup, onboarding, daily operations)
- [ ] User guide for doctors (odontogram, clinical records, prescriptions)
- [ ] User guide for receptionists (appointments, patient registration)
- [ ] Patient portal user guide
- [ ] API documentation (auto-generated from FastAPI OpenAPI specs)
- [ ] Admin runbook (tenant provisioning, support procedures)

### Marketing Site

- [ ] Landing page (value proposition, features, pricing)
- [ ] Pricing page with plan comparison
- [ ] Self-service registration flow from marketing site
- [ ] SEO optimization for "software dental Colombia" keywords
- [ ] Blog/content section for dental industry content

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

---

## Progress Tracking

| Sprint | Month | Specs | Backend | Frontend | Tests | Status |
|--------|-------|-------|---------|----------|-------|--------|
| 1-2 | 1 | ~42 | Auth + Tenants + Infra | -- | Infrastructure tests | In Progress |
| 3-4 | 2 | ~53 | Users + Patients | Design system + Auth + Dashboard + Patients + Settings | Component + API tests | Not Started |
| 5-6 | 3 | ~46 | Odontogram + Clinical Records (base) + Evolution Templates + Service Catalog | Odontogram + Clinical (base) | Odontogram tests | Complete |
| 7-8 | 4 | ~57 | Diagnoses + Procedures + Treatment + Consents + Rx + Quotation + Digital Sig + Tooth Photos | Clinical + Treatment + Consent + Rx screens | Clinical workflow tests | Not Started |
| 9-10 | 5 | ~50 | Appointments + Scheduling + Waitlist + Public booking + Voice Pipeline | Calendar + Agenda screens + Voice UI | Scheduling + Voice tests | Not Started |
| 11-12 | 6 | ~67 | Billing + Notifications + Portal + Messaging + WhatsApp + Referral | Billing + Portal screens | Integration tests | Not Started |
| 13-14 | 7 | ~20 | Colombia compliance (RIPS, RDA, MATIAS/DIAN) | Compliance screens | Compliance validation tests | Not Started |
| 15-16 | 8 | ~37 | Analytics + Import/Export + Merge + Inventory + Mexico + Admin | Analytics + Import + Inventory screens | Analytics + Load tests | Not Started |
| 17-18 | 9 | -- | Bug fixes + Optimizations | Bug fixes + UX polish | Security audit + Load tests | Not Started |
| 19-20 | 10 | -- | Production deploy + Monitoring | Marketing site | Final validation | Not Started |
| **Total** | **10** | **~381** | | | | |

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

---

*Last updated: 2026-02-25*
*Document version: 1.1*
*Revised based on client interview findings (2026-02-25)*
*Next review: End of Sprint 2*
