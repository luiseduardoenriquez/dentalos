# Database Architecture Spec

---

## Overview

**Feature:** PostgreSQL database architecture for DentalOS. Defines the schema-per-tenant isolation model, the shared `public` schema tables (8 tables including the new `user_tenant_memberships` junction table), the complete tenant schema template with all 44 tables, column definitions, constraints, relationships, indexes, the Alembic multi-tenant migration strategy, connection pooling, and backup considerations.

**Domain:** infra (cross-cutting)

**Priority:** Critical

**Dependencies:** I-01 (multi-tenancy.md)

---

## 1. Schema-Per-Tenant Architecture

### 1.1 Design Rationale

DentalOS uses PostgreSQL **schema-per-tenant** isolation (see `infra/adr/001-schema-per-tenant.md` for the full ADR). Each tenant gets a dedicated PostgreSQL schema with identical table structures. This provides:

- **Strong data isolation**: No risk of cross-tenant data leakage from missing WHERE clauses.
- **Independent backup/restore**: A single tenant's data can be exported or restored without affecting others.
- **Schema-level operations**: Tenant deletion is a simple `DROP SCHEMA CASCADE`.
- **Familiar PostgreSQL tooling**: pg_dump per schema, standard GRANT permissions.

### 1.2 Schema Naming Convention

| Schema | Purpose | Example |
|--------|---------|---------|
| `public` | Shared global data: tenants, plans, superadmin users, catalog tables. | `public.tenants` |
| `tn_{tenant_id_short}` | Tenant-specific data. `tenant_id_short` is the first 12 characters of the tenant UUID (no hyphens). | `tn_a1b2c3d4e5f6.patients` |

**Rules:**
- Tenant schema names are always prefixed with `tn_` to avoid collision with PostgreSQL system schemas.
- The short ID is derived from the tenant UUID at provisioning time and stored in `public.tenants.schema_name`.
- All tenant schemas have identical table structures; they are created from a template during provisioning.

### 1.3 Schema Resolution Flow

```
Request arrives
  -> Extract tenant_id from JWT claims
  -> Look up schema_name from public.tenants (cached in Redis, TTL 5min)
  -> SET search_path TO tn_{schema_name}, public;
  -> Execute query (all unqualified table references resolve to tenant schema first, then public)
```

### 1.4 PostgreSQL Version

PostgreSQL 16+ (Hetzner managed database or self-hosted). Required features: generated columns, JSON path queries, table partitioning, logical replication.

---

## 2. Shared `public` Schema Tables

These tables exist once in the `public` schema and are shared across all tenants.

### 2.1 `tenants`

Stores all tenant (clinic) registrations and their configuration.

```sql
CREATE TABLE public.tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            VARCHAR(63) NOT NULL UNIQUE,
    schema_name     VARCHAR(30) NOT NULL UNIQUE,
    name            VARCHAR(200) NOT NULL,
    country         VARCHAR(2) NOT NULL DEFAULT 'CO',  -- ISO 3166-1 alpha-2
    plan_id         UUID NOT NULL REFERENCES public.plans(id),
    status          VARCHAR(20) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'suspended', 'cancelled', 'provisioning')),
    settings        JSONB NOT NULL DEFAULT '{}',
    owner_email     VARCHAR(320) NOT NULL,
    phone           VARCHAR(20),
    address         TEXT,
    logo_url        TEXT,
    timezone        VARCHAR(50) NOT NULL DEFAULT 'America/Bogota',
    locale          VARCHAR(5) NOT NULL DEFAULT 'es',
    onboarding_step INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tenants_slug ON public.tenants (slug);
CREATE INDEX idx_tenants_status ON public.tenants (status);
CREATE INDEX idx_tenants_country ON public.tenants (country);
CREATE INDEX idx_tenants_plan_id ON public.tenants (plan_id);
```

**`settings` JSONB structure:**

```json
{
  "odontogram_mode": "classic",
  "default_appointment_duration_min": 30,
  "cancellation_policy_hours": 24,
  "reminder_channels": ["whatsapp", "email"],
  "reminder_timing_hours": [24, 2],
  "branding": {
    "primary_color": "#2563EB",
    "clinic_name_display": "Clinica Dental Sonrisa"
  },
  "features_enabled": ["appointments", "billing", "portal"],
  "compliance_config": {
    "rips_enabled": true,
    "electronic_invoice_provider": "dian"
  }
}
```

### 2.2 `plans`

Subscription plans that govern tenant resource limits.

**Pricing tiers (as of 2026-02-25):**
- **Free:** $0 — 50 patients, 1 doctor
- **Starter:** $19/doctor/mo — per-doctor pricing
- **Pro:** $39/doctor/mo — per-doctor pricing
- **Clinica:** $69/location/mo — per-location pricing, includes 3 doctors
- **Enterprise:** Custom pricing

```sql
CREATE TABLE public.plans (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(50) NOT NULL UNIQUE,
    max_patients    INTEGER NOT NULL,
    max_doctors     INTEGER NOT NULL,
    max_storage_mb  INTEGER NOT NULL,
    max_users       INTEGER NOT NULL,
    features        JSONB NOT NULL DEFAULT '{}',
    price_cents     INTEGER NOT NULL,
    currency        VARCHAR(3) NOT NULL DEFAULT 'COP',
    billing_period  VARCHAR(10) NOT NULL DEFAULT 'monthly'
                        CHECK (billing_period IN ('monthly', 'yearly')),
    pricing_model   VARCHAR(20) NOT NULL DEFAULT 'per_doctor'
                        CHECK (pricing_model IN ('per_doctor', 'per_location')),
    included_doctors INT DEFAULT 1,                         -- doctors included in base price
    additional_doctor_price DECIMAL(10,2) DEFAULT 0,       -- cost per additional doctor beyond included_doctors
    is_active       BOOLEAN NOT NULL DEFAULT true,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**`features` JSONB structure:**

```json
{
  "appointments": true,
  "billing": true,
  "patient_portal": false,
  "treatment_plans": true,
  "prescriptions": true,
  "analytics_advanced": false,
  "whatsapp_reminders": false,
  "electronic_invoice": false,
  "custom_consent_templates": false,
  "api_access": false,
  "priority_support": false
}
```

### 2.3 `user_tenant_memberships`

Junction table that enables a single user (doctor or staff member) to belong to multiple clinics (tenants). A user may have memberships across 2–6 clinics simultaneously and can designate one as their primary (default at login).

```sql
CREATE TABLE public.user_tenant_memberships (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,                          -- global user (email is the identity key)
    tenant_id       UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL
                        CHECK (role IN ('clinic_owner', 'doctor', 'assistant', 'receptionist')),
    is_primary      BOOLEAN NOT NULL DEFAULT false,         -- default clinic selected at login
    joined_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    status          VARCHAR(20) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'suspended', 'removed')),
    invited_by      UUID,                                   -- user_id of the person who sent the invite
    UNIQUE (user_id, tenant_id)
);

CREATE INDEX idx_utm_user_id ON public.user_tenant_memberships (user_id);
CREATE INDEX idx_utm_tenant_id ON public.user_tenant_memberships (tenant_id);
CREATE INDEX idx_utm_status ON public.user_tenant_memberships (user_id, status) WHERE status = 'active';
```

**Note:** `user_id` intentionally has no foreign key constraint to `public` because user rows live inside each tenant schema. The application layer is responsible for resolving the correct tenant schema when looking up a user. The unique constraint on `(user_id, tenant_id)` prevents duplicate memberships.

### 2.4 `superadmin_users`

Separate from tenant users. These are DentalOS platform administrators.

```sql
CREATE TABLE public.superadmin_users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(320) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    name            VARCHAR(200) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_superadmin_users_email ON public.superadmin_users (lower(email));
```

### 2.5 `catalog_cie10`

International Classification of Diseases, 10th revision. Dental-relevant subset. Shared across all tenants.

```sql
CREATE TABLE public.catalog_cie10 (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(10) NOT NULL UNIQUE,
    description_es  TEXT NOT NULL,
    description_en  TEXT,
    category        VARCHAR(100) NOT NULL,
    subcategory     VARCHAR(100),
    dental_relevant BOOLEAN NOT NULL DEFAULT false,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_catalog_cie10_code ON public.catalog_cie10 (code);
CREATE INDEX idx_catalog_cie10_dental ON public.catalog_cie10 (dental_relevant) WHERE dental_relevant = true;
CREATE INDEX idx_catalog_cie10_search ON public.catalog_cie10
    USING GIN (to_tsvector('spanish', code || ' ' || description_es));
```

### 2.6 `catalog_cups`

Colombian Unique Procedure Classification (CUPS). Used for procedure coding. Base for other country procedure code systems.

```sql
CREATE TABLE public.catalog_cups (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(20) NOT NULL UNIQUE,
    description_es  TEXT NOT NULL,
    description_en  TEXT,
    category        VARCHAR(100) NOT NULL,
    subcategory     VARCHAR(100),
    dental_relevant BOOLEAN NOT NULL DEFAULT false,
    country         VARCHAR(2) NOT NULL DEFAULT 'CO',
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_catalog_cups_code ON public.catalog_cups (code);
CREATE INDEX idx_catalog_cups_dental ON public.catalog_cups (dental_relevant) WHERE dental_relevant = true;
CREATE INDEX idx_catalog_cups_search ON public.catalog_cups
    USING GIN (to_tsvector('spanish', code || ' ' || description_es));
CREATE INDEX idx_catalog_cups_country ON public.catalog_cups (country);
```

### 2.7 `catalog_medications`

Dental-relevant medications for prescriptions.

```sql
CREATE TABLE public.catalog_medications (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(200) NOT NULL,
    active_ingredient   VARCHAR(200) NOT NULL,
    presentation        VARCHAR(200) NOT NULL,
    concentration       VARCHAR(100),
    route               VARCHAR(50),
    category            VARCHAR(100),
    dental_relevant     BOOLEAN NOT NULL DEFAULT false,
    requires_prescription BOOLEAN NOT NULL DEFAULT true,
    country             VARCHAR(2),
    is_active           BOOLEAN NOT NULL DEFAULT true,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_catalog_medications_name ON public.catalog_medications (name);
CREATE INDEX idx_catalog_medications_dental ON public.catalog_medications (dental_relevant)
    WHERE dental_relevant = true;
CREATE INDEX idx_catalog_medications_search ON public.catalog_medications
    USING GIN (to_tsvector('spanish', name || ' ' || active_ingredient || ' ' || presentation));
```

---

## 3. Tenant Schema Template

When a new tenant is provisioned, a new PostgreSQL schema is created with ALL of the following tables. Every tenant schema is structurally identical.

### 3.1 `users`

Staff members of the dental clinic (doctors, assistants, receptionists, clinic owner).

**Multi-clinic membership:** A user can belong to multiple tenants. Membership across clinics is tracked in `public.user_tenant_memberships` (see Section 2.3). When a doctor works in 2–6 clinics, they have one `users` row per tenant schema plus one `user_tenant_memberships` row per tenant in the public schema. The `is_primary` flag on the membership record controls which clinic is selected by default at login.

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(320) NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    name            VARCHAR(200) NOT NULL,
    phone           VARCHAR(20),
    avatar_url      TEXT,
    role            VARCHAR(20) NOT NULL
                        CHECK (role IN ('clinic_owner', 'doctor', 'assistant', 'receptionist')),
    professional_license VARCHAR(50),
    specialties     TEXT[],
    is_active       BOOLEAN NOT NULL DEFAULT true,
    last_login_at   TIMESTAMPTZ,
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    TIMESTAMPTZ,
    email_verified  BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_users_email ON users (lower(email));
CREATE INDEX idx_users_role ON users (role);
CREATE INDEX idx_users_is_active ON users (is_active);
```

### 3.2 `user_sessions`

Active refresh tokens and session tracking.

```sql
CREATE TABLE user_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL,
    device_info     JSONB,
    ip_address      INET,
    expires_at      TIMESTAMPTZ NOT NULL,
    is_revoked      BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_user_sessions_user_id ON user_sessions (user_id);
CREATE INDEX idx_user_sessions_expires ON user_sessions (expires_at) WHERE is_revoked = false;
```

### 3.3 `user_invites`

Pending invitations for new team members.

```sql
CREATE TABLE user_invites (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(320) NOT NULL,
    role            VARCHAR(20) NOT NULL
                        CHECK (role IN ('doctor', 'assistant', 'receptionist')),
    invited_by      UUID NOT NULL REFERENCES users(id),
    token_hash      VARCHAR(255) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'accepted', 'expired', 'cancelled')),
    expires_at      TIMESTAMPTZ NOT NULL,
    accepted_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_user_invites_email ON user_invites (lower(email));
CREATE INDEX idx_user_invites_status ON user_invites (status);
```

### 3.4 `patients`

Core patient records.

```sql
CREATE TABLE patients (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_type   VARCHAR(20) NOT NULL
                        CHECK (document_type IN ('cedula', 'curp', 'rut', 'passport', 'other')),
    document_number VARCHAR(30) NOT NULL,
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    birthdate       DATE NOT NULL,
    gender          VARCHAR(10) NOT NULL
                        CHECK (gender IN ('male', 'female', 'other')),
    email           VARCHAR(320),
    phone           VARCHAR(20),
    phone_secondary VARCHAR(20),
    address         TEXT,
    city            VARCHAR(100),
    state_province  VARCHAR(100),
    emergency_contact_name  VARCHAR(200),
    emergency_contact_phone VARCHAR(20),
    insurance_provider      VARCHAR(200),
    insurance_policy_number VARCHAR(50),
    blood_type      VARCHAR(5),
    allergies       TEXT[],
    chronic_conditions TEXT[],
    referral_source VARCHAR(50),
    notes           TEXT,
    avatar_url      TEXT,
    portal_user_id  UUID,
    portal_access   BOOLEAN NOT NULL DEFAULT false,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    no_show_count   INTEGER NOT NULL DEFAULT 0,
    last_visit_at   TIMESTAMPTZ,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_patients_document ON patients (document_type, document_number);
CREATE INDEX idx_patients_name ON patients (lower(last_name), lower(first_name));
CREATE INDEX idx_patients_phone ON patients (phone);
CREATE INDEX idx_patients_email ON patients (lower(email)) WHERE email IS NOT NULL;
CREATE INDEX idx_patients_is_active ON patients (is_active);
CREATE INDEX idx_patients_search ON patients
    USING GIN (to_tsvector('spanish',
        coalesce(first_name, '') || ' ' ||
        coalesce(last_name, '') || ' ' ||
        coalesce(document_number, '') || ' ' ||
        coalesce(phone, '')
    ));
CREATE INDEX idx_patients_created_at ON patients (created_at);
```

### 3.5 `patient_documents`

Files attached to patient records (X-rays, lab results, referral letters, etc.).

```sql
CREATE TABLE patient_documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    document_type   VARCHAR(30) NOT NULL
                        CHECK (document_type IN ('xray', 'consent', 'lab_result', 'referral', 'photo', 'other')),
    file_name       VARCHAR(255) NOT NULL,
    file_path       TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    mime_type       VARCHAR(100) NOT NULL,
    description     TEXT,
    tooth_number    INTEGER,
    uploaded_by     UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_patient_documents_patient ON patient_documents (patient_id);
CREATE INDEX idx_patient_documents_type ON patient_documents (patient_id, document_type);
```

### 3.6 `odontogram_states`

Current state of a patient's odontogram. One row per patient representing the active dentition.

```sql
CREATE TABLE odontogram_states (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL UNIQUE REFERENCES patients(id) ON DELETE CASCADE,
    dentition_type  VARCHAR(10) NOT NULL DEFAULT 'adult'
                        CHECK (dentition_type IN ('adult', 'pediatric', 'mixed')),
    last_updated_by UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.7 `odontogram_conditions`

Individual conditions applied to specific tooth zones. This is the core of the odontogram data model.

```sql
CREATE TABLE odontogram_conditions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    odontogram_id   UUID NOT NULL REFERENCES odontogram_states(id) ON DELETE CASCADE,
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    tooth_number    INTEGER NOT NULL,  -- FDI notation (11-48 adult, 51-85 pediatric)
    zone            VARCHAR(15) NOT NULL
                        CHECK (zone IN ('mesial', 'distal', 'vestibular', 'lingual', 'palatino', 'oclusal', 'incisal', 'root', 'full')),
    condition_code  VARCHAR(30) NOT NULL
                        CHECK (condition_code IN (
                            'caries', 'restoration', 'extraction', 'absent',
                            'crown', 'endodontic', 'implant', 'fracture',
                            'sealant', 'fluorosis', 'temporary', 'prosthesis'
                        )),
    severity        VARCHAR(10) DEFAULT 'moderate'
                        CHECK (severity IN ('mild', 'moderate', 'severe')),
    notes           TEXT,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_odontogram_conditions_odontogram ON odontogram_conditions (odontogram_id);
CREATE INDEX idx_odontogram_conditions_patient ON odontogram_conditions (patient_id);
CREATE INDEX idx_odontogram_conditions_tooth ON odontogram_conditions (patient_id, tooth_number);
```

### 3.8 `odontogram_history`

Immutable audit trail of every change made to the odontogram.

```sql
CREATE TABLE odontogram_history (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    tooth_number    INTEGER NOT NULL,
    zone            VARCHAR(15) NOT NULL,
    action          VARCHAR(10) NOT NULL
                        CHECK (action IN ('add', 'update', 'remove')),
    condition_code  VARCHAR(30) NOT NULL,
    previous_data   JSONB,
    new_data        JSONB,
    performed_by    UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_odontogram_history_patient ON odontogram_history (patient_id);
CREATE INDEX idx_odontogram_history_tooth ON odontogram_history (patient_id, tooth_number);
CREATE INDEX idx_odontogram_history_date ON odontogram_history (patient_id, created_at);
```

### 3.9 `odontogram_snapshots`

Point-in-time snapshots of the full odontogram state.

```sql
CREATE TABLE odontogram_snapshots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    snapshot_data   JSONB NOT NULL,
    dentition_type  VARCHAR(10) NOT NULL,
    reason          VARCHAR(100),
    linked_record_id UUID,
    linked_treatment_plan_id UUID,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_odontogram_snapshots_patient ON odontogram_snapshots (patient_id);
CREATE INDEX idx_odontogram_snapshots_date ON odontogram_snapshots (patient_id, created_at);
```

### 3.10 `clinical_records`

General clinical record entries (examinations, evolution notes, procedures).

```sql
CREATE TABLE clinical_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    record_type     VARCHAR(20) NOT NULL
                        CHECK (record_type IN ('anamnesis', 'examination', 'diagnosis', 'evolution_note', 'procedure')),
    appointment_id  UUID REFERENCES appointments(id),
    title           VARCHAR(200),
    content         TEXT NOT NULL,
    attachments     JSONB DEFAULT '[]',
    created_by      UUID NOT NULL REFERENCES users(id),
    is_locked       BOOLEAN NOT NULL DEFAULT false,
    locked_at       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_clinical_records_patient ON clinical_records (patient_id);
CREATE INDEX idx_clinical_records_type ON clinical_records (patient_id, record_type);
CREATE INDEX idx_clinical_records_date ON clinical_records (patient_id, created_at);
CREATE INDEX idx_clinical_records_appointment ON clinical_records (appointment_id) WHERE appointment_id IS NOT NULL;
```

### 3.11 `anamnesis`

Structured medical history questionnaire. One active record per patient.

```sql
CREATE TABLE anamnesis (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    current_medications TEXT[],
    allergies       TEXT[],
    chronic_conditions TEXT[],
    surgical_history TEXT[],
    family_history  TEXT[],
    habits          JSONB DEFAULT '{}',
    pregnancy_status VARCHAR(20) DEFAULT 'not_applicable'
                        CHECK (pregnancy_status IN ('not_applicable', 'not_pregnant', 'pregnant', 'breastfeeding')),
    additional_notes TEXT,
    version         INTEGER NOT NULL DEFAULT 1,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_anamnesis_patient ON anamnesis (patient_id);
```

**`habits` JSONB structure:**

```json
{
  "smoking": { "status": "former", "frequency": "10/day", "years": 5 },
  "alcohol": { "status": "occasional" },
  "bruxism": { "status": "active", "wears_guard": false },
  "oral_hygiene": { "brushing_frequency": "2x_daily", "flossing": "rarely" }
}
```

### 3.12 `diagnoses`

Patient diagnoses linked to CIE-10 codes.

```sql
CREATE TABLE diagnoses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    cie10_code      VARCHAR(10) NOT NULL,
    description     TEXT NOT NULL,
    tooth_number    INTEGER,
    severity        VARCHAR(10) DEFAULT 'moderate'
                        CHECK (severity IN ('mild', 'moderate', 'severe')),
    status          VARCHAR(15) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'resolved', 'chronic')),
    notes           TEXT,
    diagnosed_by    UUID NOT NULL REFERENCES users(id),
    resolved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_diagnoses_patient ON diagnoses (patient_id);
CREATE INDEX idx_diagnoses_status ON diagnoses (patient_id, status);
CREATE INDEX idx_diagnoses_cie10 ON diagnoses (cie10_code);
```

### 3.13 `procedures`

Completed dental procedures.

```sql
CREATE TABLE procedures (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    cups_code       VARCHAR(20) NOT NULL,
    description     TEXT NOT NULL,
    tooth_number    INTEGER,
    zones           TEXT[],
    materials_used  TEXT[],
    doctor_id       UUID NOT NULL REFERENCES users(id),
    appointment_id  UUID REFERENCES appointments(id),
    treatment_plan_item_id UUID REFERENCES treatment_plan_items(id),
    duration_minutes INTEGER,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_procedures_patient ON procedures (patient_id);
CREATE INDEX idx_procedures_doctor ON procedures (doctor_id);
CREATE INDEX idx_procedures_cups ON procedures (cups_code);
CREATE INDEX idx_procedures_date ON procedures (patient_id, created_at);
CREATE INDEX idx_procedures_appointment ON procedures (appointment_id) WHERE appointment_id IS NOT NULL;
```

### 3.14 `treatment_plans`

```sql
CREATE TABLE treatment_plans (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    title           VARCHAR(200) NOT NULL,
    description     TEXT,
    status          VARCHAR(15) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'active', 'completed', 'cancelled')),
    priority        VARCHAR(10) DEFAULT 'normal'
                        CHECK (priority IN ('urgent', 'high', 'normal', 'low')),
    estimated_duration_days INTEGER,
    total_estimated_cost_cents BIGINT DEFAULT 0,
    currency        VARCHAR(3) NOT NULL DEFAULT 'COP',
    approved_at     TIMESTAMPTZ,
    approved_by_patient BOOLEAN NOT NULL DEFAULT false,
    approval_signature_url TEXT,
    approval_ip     INET,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_treatment_plans_patient ON treatment_plans (patient_id);
CREATE INDEX idx_treatment_plans_status ON treatment_plans (patient_id, status);
```

### 3.15 `treatment_plan_items`

Individual procedures within a treatment plan.

```sql
CREATE TABLE treatment_plan_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    treatment_plan_id UUID NOT NULL REFERENCES treatment_plans(id) ON DELETE CASCADE,
    cups_code       VARCHAR(20),
    description     TEXT NOT NULL,
    tooth_number    INTEGER,
    zone            VARCHAR(15),
    status          VARCHAR(15) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'scheduled', 'completed', 'cancelled')),
    estimated_cost_cents BIGINT DEFAULT 0,
    currency        VARCHAR(3) NOT NULL DEFAULT 'COP',
    priority_order  INTEGER NOT NULL DEFAULT 0,
    completed_at    TIMESTAMPTZ,
    procedure_id    UUID REFERENCES procedures(id),
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_treatment_plan_items_plan ON treatment_plan_items (treatment_plan_id);
CREATE INDEX idx_treatment_plan_items_status ON treatment_plan_items (treatment_plan_id, status);
```

### 3.16 `consent_templates`

Consent form templates (built-in and custom per tenant).

```sql
CREATE TABLE consent_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(200) NOT NULL,
    category        VARCHAR(30) NOT NULL
                        CHECK (category IN ('general', 'surgery', 'sedation', 'orthodontics', 'implants', 'endodontics', 'pediatric', 'custom')),
    body_html       TEXT NOT NULL,
    required_fields JSONB DEFAULT '[]',
    is_system       BOOLEAN NOT NULL DEFAULT false,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_consent_templates_category ON consent_templates (category);
CREATE INDEX idx_consent_templates_active ON consent_templates (is_active) WHERE is_active = true;
```

### 3.17 `consents`

Patient consent records with signature tracking.

```sql
CREATE TABLE consents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    template_id     UUID NOT NULL REFERENCES consent_templates(id),
    body_html       TEXT NOT NULL,
    status          VARCHAR(15) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'signed', 'voided')),
    signed_at       TIMESTAMPTZ,
    signature_data  TEXT,
    signer_name     VARCHAR(200),
    signer_ip       INET,
    signer_device   TEXT,
    signed_pdf_path TEXT,
    voided_at       TIMESTAMPTZ,
    voided_by       UUID REFERENCES users(id),
    void_reason     TEXT,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_consents_patient ON consents (patient_id);
CREATE INDEX idx_consents_status ON consents (patient_id, status);
```

### 3.18 `appointments`

```sql
CREATE TABLE appointments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id       UUID NOT NULL REFERENCES users(id),
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ NOT NULL,
    appointment_type VARCHAR(20) NOT NULL DEFAULT 'consultation'
                        CHECK (appointment_type IN ('consultation', 'procedure', 'emergency', 'follow_up', 'cleaning', 'orthodontics')),
    status          VARCHAR(20) NOT NULL DEFAULT 'scheduled'
                        CHECK (status IN ('scheduled', 'confirmed', 'in_progress', 'completed', 'cancelled', 'no_show')),
    notes           TEXT,
    cancellation_reason TEXT,
    cancelled_by    UUID REFERENCES users(id),
    treatment_plan_item_id UUID REFERENCES treatment_plan_items(id),
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_appointment_time CHECK (end_time > start_time)
);

CREATE INDEX idx_appointments_doctor_time ON appointments (doctor_id, start_time, end_time);
CREATE INDEX idx_appointments_patient ON appointments (patient_id);
CREATE INDEX idx_appointments_status ON appointments (status);
CREATE INDEX idx_appointments_date ON appointments (start_time);
CREATE INDEX idx_appointments_doctor_date ON appointments (doctor_id, start_time) WHERE status NOT IN ('cancelled');
```

### 3.19 `appointment_reminders`

```sql
CREATE TABLE appointment_reminders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id  UUID NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
    channel         VARCHAR(15) NOT NULL
                        CHECK (channel IN ('email', 'sms', 'whatsapp', 'in_app')),
    scheduled_at    TIMESTAMPTZ NOT NULL,
    sent_at         TIMESTAMPTZ,
    status          VARCHAR(15) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'sent', 'failed', 'cancelled')),
    failure_reason  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_appointment_reminders_apt ON appointment_reminders (appointment_id);
CREATE INDEX idx_appointment_reminders_pending ON appointment_reminders (scheduled_at)
    WHERE status = 'pending';
```

### 3.20 `doctor_schedules`

Weekly recurring schedule templates for doctors.

```sql
CREATE TABLE doctor_schedules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    day_of_week     INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),  -- 0=Monday
    start_time      TIME NOT NULL,
    end_time        TIME NOT NULL,
    break_start     TIME,
    break_end       TIME,
    default_slot_duration_min INTEGER NOT NULL DEFAULT 30,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_schedule_time CHECK (end_time > start_time),
    CONSTRAINT chk_break_time CHECK (
        (break_start IS NULL AND break_end IS NULL) OR
        (break_start IS NOT NULL AND break_end IS NOT NULL AND break_end > break_start)
    )
);

CREATE UNIQUE INDEX idx_doctor_schedules_unique ON doctor_schedules (doctor_id, day_of_week)
    WHERE is_active = true;
CREATE INDEX idx_doctor_schedules_doctor ON doctor_schedules (doctor_id);
```

### 3.21 `availability_blocks`

One-off blocked times (vacations, personal time, meetings).

```sql
CREATE TABLE availability_blocks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ NOT NULL,
    reason          VARCHAR(200),
    block_type      VARCHAR(15) NOT NULL DEFAULT 'personal'
                        CHECK (block_type IN ('vacation', 'personal', 'meeting', 'training', 'other')),
    is_all_day      BOOLEAN NOT NULL DEFAULT false,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_block_time CHECK (end_time > start_time)
);

CREATE INDEX idx_availability_blocks_doctor ON availability_blocks (doctor_id, start_time, end_time);
```

### 3.22 `waitlist`

```sql
CREATE TABLE waitlist (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    preferred_doctor_id UUID REFERENCES users(id),
    preferred_date_start DATE,
    preferred_date_end DATE,
    preferred_time_start TIME,
    preferred_time_end TIME,
    procedure_type  VARCHAR(20),
    notes           TEXT,
    status          VARCHAR(15) NOT NULL DEFAULT 'waiting'
                        CHECK (status IN ('waiting', 'notified', 'booked', 'cancelled')),
    notified_at     TIMESTAMPTZ,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_waitlist_status ON waitlist (status) WHERE status = 'waiting';
CREATE INDEX idx_waitlist_doctor ON waitlist (preferred_doctor_id) WHERE status = 'waiting';
```

### 3.23 `invoices`

```sql
CREATE TABLE invoices (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    invoice_number  VARCHAR(30) NOT NULL,
    status          VARCHAR(15) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'sent', 'paid', 'partial', 'overdue', 'cancelled', 'voided')),
    subtotal_cents  BIGINT NOT NULL DEFAULT 0,
    tax_cents       BIGINT NOT NULL DEFAULT 0,
    discount_cents  BIGINT NOT NULL DEFAULT 0,
    total_cents     BIGINT NOT NULL DEFAULT 0,
    paid_cents      BIGINT NOT NULL DEFAULT 0,
    currency        VARCHAR(3) NOT NULL DEFAULT 'COP',
    tax_rate        NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    notes           TEXT,
    due_date        DATE,
    sent_at         TIMESTAMPTZ,
    paid_at         TIMESTAMPTZ,
    electronic_invoice_id VARCHAR(100),
    electronic_invoice_status VARCHAR(20),
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_invoices_number ON invoices (invoice_number);
CREATE INDEX idx_invoices_patient ON invoices (patient_id);
CREATE INDEX idx_invoices_status ON invoices (status);
CREATE INDEX idx_invoices_date ON invoices (created_at);
CREATE INDEX idx_invoices_overdue ON invoices (due_date) WHERE status IN ('sent', 'partial');
```

### 3.24 `invoice_items`

```sql
CREATE TABLE invoice_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id      UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    description     TEXT NOT NULL,
    cups_code       VARCHAR(20),
    procedure_id    UUID REFERENCES procedures(id),
    treatment_plan_item_id UUID REFERENCES treatment_plan_items(id),
    quantity        INTEGER NOT NULL DEFAULT 1,
    unit_price_cents BIGINT NOT NULL,
    discount_cents  BIGINT NOT NULL DEFAULT 0,
    total_cents     BIGINT NOT NULL,
    tooth_number    INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_invoice_items_invoice ON invoice_items (invoice_id);
```

### 3.25 `payments`

```sql
CREATE TABLE payments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id      UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    patient_id      UUID NOT NULL REFERENCES patients(id),
    amount_cents    BIGINT NOT NULL,
    currency        VARCHAR(3) NOT NULL DEFAULT 'COP',
    payment_method  VARCHAR(20) NOT NULL
                        CHECK (payment_method IN ('cash', 'card', 'transfer', 'insurance', 'check', 'other')),
    reference_number VARCHAR(100),
    notes           TEXT,
    received_by     UUID NOT NULL REFERENCES users(id),
    payment_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_payments_invoice ON payments (invoice_id);
CREATE INDEX idx_payments_patient ON payments (patient_id);
CREATE INDEX idx_payments_date ON payments (payment_date);
```

### 3.26 `payment_plans`

```sql
CREATE TABLE payment_plans (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    invoice_id      UUID REFERENCES invoices(id),
    total_amount_cents BIGINT NOT NULL,
    currency        VARCHAR(3) NOT NULL DEFAULT 'COP',
    installment_count INTEGER NOT NULL,
    frequency       VARCHAR(15) NOT NULL DEFAULT 'monthly'
                        CHECK (frequency IN ('weekly', 'biweekly', 'monthly')),
    start_date      DATE NOT NULL,
    status          VARCHAR(15) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'completed', 'defaulted', 'cancelled')),
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_payment_plans_patient ON payment_plans (patient_id);
CREATE INDEX idx_payment_plans_status ON payment_plans (status) WHERE status = 'active';
```

### 3.27 `payment_plan_installments`

```sql
CREATE TABLE payment_plan_installments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_plan_id UUID NOT NULL REFERENCES payment_plans(id) ON DELETE CASCADE,
    installment_number INTEGER NOT NULL,
    amount_cents    BIGINT NOT NULL,
    due_date        DATE NOT NULL,
    status          VARCHAR(15) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'paid', 'overdue', 'cancelled')),
    paid_at         TIMESTAMPTZ,
    payment_id      UUID REFERENCES payments(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_installments_plan ON payment_plan_installments (payment_plan_id);
CREATE INDEX idx_installments_due ON payment_plan_installments (due_date) WHERE status = 'pending';
```

### 3.28 `service_catalog`

Tenant-specific procedure pricing.

```sql
CREATE TABLE service_catalog (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cups_code       VARCHAR(20),
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    category        VARCHAR(50),
    default_price_cents BIGINT NOT NULL DEFAULT 0,
    currency        VARCHAR(3) NOT NULL DEFAULT 'COP',
    estimated_duration_min INTEGER,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_service_catalog_cups ON service_catalog (cups_code) WHERE cups_code IS NOT NULL;
CREATE INDEX idx_service_catalog_active ON service_catalog (is_active) WHERE is_active = true;
CREATE INDEX idx_service_catalog_search ON service_catalog
    USING GIN (to_tsvector('spanish', name || ' ' || coalesce(description, '')));
```

### 3.29 `prescriptions`

```sql
CREATE TABLE prescriptions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id       UUID NOT NULL REFERENCES users(id),
    appointment_id  UUID REFERENCES appointments(id),
    diagnosis_id    UUID REFERENCES diagnoses(id),
    notes           TEXT,
    status          VARCHAR(15) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('draft', 'active', 'completed', 'cancelled')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_prescriptions_patient ON prescriptions (patient_id);
CREATE INDEX idx_prescriptions_doctor ON prescriptions (doctor_id);
```

### 3.30 `prescription_items`

```sql
CREATE TABLE prescription_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prescription_id UUID NOT NULL REFERENCES prescriptions(id) ON DELETE CASCADE,
    medication_name VARCHAR(200) NOT NULL,
    active_ingredient VARCHAR(200),
    dosage          VARCHAR(100) NOT NULL,
    frequency       VARCHAR(100) NOT NULL,
    duration        VARCHAR(100) NOT NULL,
    route           VARCHAR(50),
    instructions    TEXT,
    quantity        INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_prescription_items_rx ON prescription_items (prescription_id);
```

### 3.31 `message_threads`

Internal messaging between clinic staff and patients.

```sql
CREATE TABLE message_threads (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID REFERENCES patients(id) ON DELETE CASCADE,
    subject         VARCHAR(200),
    status          VARCHAR(15) NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'closed')),
    last_message_at TIMESTAMPTZ,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_message_threads_patient ON message_threads (patient_id);
CREATE INDEX idx_message_threads_status ON message_threads (status);
```

### 3.32 `messages`

```sql
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id       UUID NOT NULL REFERENCES message_threads(id) ON DELETE CASCADE,
    sender_type     VARCHAR(10) NOT NULL
                        CHECK (sender_type IN ('user', 'patient', 'system')),
    sender_id       UUID,
    body            TEXT NOT NULL,
    attachments     JSONB DEFAULT '[]',
    read_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_messages_thread ON messages (thread_id, created_at);
```

### 3.33 `notifications`

In-app notifications for users.

```sql
CREATE TABLE notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title           VARCHAR(200) NOT NULL,
    body            TEXT,
    notification_type VARCHAR(30) NOT NULL,
    resource_type   VARCHAR(30),
    resource_id     UUID,
    is_read         BOOLEAN NOT NULL DEFAULT false,
    read_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_notifications_user ON notifications (user_id, is_read, created_at);
CREATE INDEX idx_notifications_unread ON notifications (user_id, created_at) WHERE is_read = false;
```

### 3.34 `audit_log`

Immutable audit trail for all clinically significant operations. See `infra/audit-logging.md` for full requirements.

```sql
CREATE TABLE audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    action          VARCHAR(20) NOT NULL
                        CHECK (action IN ('create', 'read', 'update', 'delete', 'login', 'logout', 'export', 'sign')),
    resource_type   VARCHAR(50) NOT NULL,
    resource_id     UUID,
    old_value       JSONB,
    new_value       JSONB,
    ip_address      INET,
    user_agent      TEXT,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_log_user ON audit_log (user_id);
CREATE INDEX idx_audit_log_resource ON audit_log (resource_type, resource_id);
CREATE INDEX idx_audit_log_date ON audit_log (created_at);
CREATE INDEX idx_audit_log_action ON audit_log (action, created_at);
```

**Note:** The `audit_log` table is append-only. No UPDATE or DELETE operations are permitted on this table at the application level. This is enforced via a PostgreSQL trigger and application-level policy.

### 3.35 `tenant_settings`

Key-value settings storage for tenant-specific configuration beyond what fits in the `public.tenants.settings` JSONB.

```sql
CREATE TABLE tenant_settings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key             VARCHAR(100) NOT NULL UNIQUE,
    value           JSONB NOT NULL,
    description     TEXT,
    updated_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_tenant_settings_key ON tenant_settings (key);
```

### Interview-Driven Tables (added 2026-02-25)

The following tables were identified during client interviews and cover clinical workflow automation, voice capture, quoting, inventory, sterilization compliance, implant traceability, digital signatures, and inter-specialist referrals.

### 3.36 `evolution_templates`

Reusable clinical procedure templates that pre-populate evolution/progress notes with structured, variable-driven step text. Supports both system-provided (builtin) templates and custom clinic templates.

```sql
CREATE TABLE evolution_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    name            VARCHAR(200) NOT NULL,                  -- e.g. "Resina Oclusal", "Endodoncia Unirradicular"
    procedure_type  VARCHAR(50) NOT NULL,                   -- resina, endodoncia, exodoncia, limpieza, etc.
    cups_code       VARCHAR(20),                            -- linked CUPS code from public.catalog_cups
    complexity      VARCHAR(20) NOT NULL DEFAULT 'standard'
                        CHECK (complexity IN ('basic', 'standard', 'complex')),
    steps           JSONB NOT NULL,
    -- Ordered array of step objects. Example:
    -- [{"order":1,"text":"Anestesia infiltrativa [tipo] al [porcentaje]%","variables":["tipo","porcentaje"]}, ...]
    variables_schema JSONB,                                 -- JSON Schema for variable validation
    is_builtin      BOOLEAN NOT NULL DEFAULT false,         -- true = system-provided, false = custom per clinic
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_evolution_templates_type ON evolution_templates (tenant_id, procedure_type);
CREATE INDEX idx_evolution_templates_cups ON evolution_templates (tenant_id, cups_code)
    WHERE cups_code IS NOT NULL;
CREATE INDEX idx_evolution_templates_active ON evolution_templates (tenant_id, is_active)
    WHERE is_active = true;
```

### 3.37 `voice_sessions`

Records each voice-to-data capture session. A doctor speaks dental findings (e.g. "diente 36 caries oclusal severa") and the audio is transcribed via Whisper then parsed by an LLM into structured dental data before being applied to the odontogram or evolution note after doctor confirmation.

```sql
CREATE TABLE voice_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id       UUID NOT NULL REFERENCES users(id),
    context         VARCHAR(30) NOT NULL DEFAULT 'odontogram'
                        CHECK (context IN ('odontogram', 'evolution', 'notes')),
    status          VARCHAR(20) NOT NULL DEFAULT 'recording'
                        CHECK (status IN ('recording', 'transcribing', 'parsed', 'applied', 'cancelled')),
    audio_url       TEXT,                                   -- S3 URL to the stored audio file
    audio_duration_seconds INT,
    raw_transcription TEXT,                                 -- raw output from Whisper
    parsed_result   JSONB,
    -- Structured dental data parsed by LLM. Example:
    -- [{"tooth":36,"zone":"oclusal","condition":"caries","confidence":0.95}, ...]
    applied_changes JSONB,                                  -- subset of parsed_result confirmed and applied
    whisper_model   VARCHAR(50) NOT NULL DEFAULT 'whisper-large-v3',
    llm_model       VARCHAR(50) NOT NULL DEFAULT 'claude-haiku',
    processing_cost_usd DECIMAL(8,4),                      -- API cost tracking for billing add-on
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX idx_voice_sessions_patient ON voice_sessions (tenant_id, patient_id);
CREATE INDEX idx_voice_sessions_doctor ON voice_sessions (tenant_id, doctor_id);
CREATE INDEX idx_voice_sessions_status ON voice_sessions (tenant_id, status)
    WHERE status NOT IN ('applied', 'cancelled');
```

### 3.38 `quotations`

Auto-generated price quotations linked to treatment plans. A quotation captures the agreed pricing snapshot at a point in time and can be digitally approved by the patient (via signature).

```sql
CREATE TABLE quotations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    treatment_plan_id UUID REFERENCES treatment_plans(id),
    quotation_number VARCHAR(20) NOT NULL,                  -- sequential per tenant, e.g. "COT-2026-0001"
    status          VARCHAR(20) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'sent', 'approved', 'expired', 'rejected')),
    subtotal        DECIMAL(12,2) NOT NULL,
    discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    discount_percentage DECIMAL(5,2) NOT NULL DEFAULT 0,
    tax_amount      DECIMAL(12,2) NOT NULL DEFAULT 0,
    total           DECIMAL(12,2) NOT NULL,
    currency        VARCHAR(3) NOT NULL DEFAULT 'COP',
    valid_until     DATE,                                   -- expiry date after which status -> expired
    notes           TEXT,
    approved_at     TIMESTAMPTZ,
    approved_signature TEXT,                                -- base64-encoded drawn signature PNG
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, quotation_number)
);

CREATE INDEX idx_quotations_patient ON quotations (tenant_id, patient_id);
CREATE INDEX idx_quotations_status ON quotations (tenant_id, status);
CREATE INDEX idx_quotations_plan ON quotations (treatment_plan_id) WHERE treatment_plan_id IS NOT NULL;
```

### 3.39 `quotation_items`

Line items that make up a quotation. Each row corresponds to one procedure or service with its pricing, linked back to the originating treatment plan item when applicable.

```sql
CREATE TABLE quotation_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quotation_id    UUID NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
    treatment_plan_item_id UUID REFERENCES treatment_plan_items(id),
    procedure_code  VARCHAR(20),                            -- CUPS code
    description     VARCHAR(500) NOT NULL,
    tooth_number    INTEGER,
    zone            VARCHAR(20),
    quantity        INTEGER NOT NULL DEFAULT 1,
    unit_price      DECIMAL(12,2) NOT NULL,
    discount        DECIMAL(12,2) NOT NULL DEFAULT 0,
    total           DECIMAL(12,2) NOT NULL,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_quotation_items_quotation ON quotation_items (quotation_id);
```

### 3.40 `inventory_items`

Tracks dental materials, instruments, implants, medications, and consumables. Includes generated `expiry_status` so low-stock and near-expiry items can be surfaced without computed columns in queries.

```sql
CREATE TABLE inventory_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    name            VARCHAR(200) NOT NULL,
    category        VARCHAR(30) NOT NULL
                        CHECK (category IN ('material', 'instrument', 'implant', 'medication', 'consumable')),
    sku             VARCHAR(50),
    lot_number      VARCHAR(100),
    serial_number   VARCHAR(100),                           -- required for implants
    manufacturer    VARCHAR(200),
    supplier        VARCHAR(200),
    quantity        DECIMAL(10,2) NOT NULL DEFAULT 0,
    unit            VARCHAR(20) NOT NULL DEFAULT 'unit'
                        CHECK (unit IN ('unit', 'ml', 'g', 'pack')),
    min_stock_level DECIMAL(10,2),                          -- alert threshold; NULL means no alert
    cost_per_unit   DECIMAL(12,2),
    expiry_date     DATE,
    expiry_status   VARCHAR(20) GENERATED ALWAYS AS (
                        CASE
                            WHEN expiry_date IS NULL                                 THEN 'no_expiry'
                            WHEN expiry_date < CURRENT_DATE                          THEN 'expired'
                            WHEN expiry_date < CURRENT_DATE + INTERVAL '30 days'    THEN 'critical'
                            WHEN expiry_date < CURRENT_DATE + INTERVAL '60 days'    THEN 'warning'
                            ELSE 'ok'
                        END
                    ) STORED,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_inventory_items_category ON inventory_items (tenant_id, category);
CREATE INDEX idx_inventory_items_expiry ON inventory_items (tenant_id, expiry_date)
    WHERE expiry_date IS NOT NULL;
CREATE INDEX idx_inventory_items_stock ON inventory_items (tenant_id, quantity)
    WHERE quantity <= min_stock_level;
CREATE INDEX idx_inventory_items_active ON inventory_items (tenant_id, is_active)
    WHERE is_active = true;
```

### 3.41 `sterilization_records`

Tracks autoclave sterilization cycles for regulatory compliance (INVIMA / IPS requirements in Colombia). Each cycle records temperature, pressure, duration, and indicator results and is signed by the responsible staff member.

```sql
CREATE TABLE sterilization_records (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL,
    autoclave_identifier VARCHAR(50),                       -- name or number of the autoclave unit
    load_number         VARCHAR(50) NOT NULL,               -- cycle/load identifier
    cycle_date          TIMESTAMPTZ NOT NULL,
    temperature_celsius DECIMAL(5,1),
    duration_minutes    INTEGER,
    pressure_psi        DECIMAL(5,1),
    biological_indicator VARCHAR(20)
                            CHECK (biological_indicator IN ('pass', 'fail', 'pending')),
    chemical_indicator  VARCHAR(20)
                            CHECK (chemical_indicator IN ('pass', 'fail')),
    instruments         JSONB,                              -- array of instrument descriptions or IDs
    responsible_user_id UUID NOT NULL REFERENCES users(id),
    digital_signature   TEXT,                               -- base64-encoded drawn signature PNG
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sterilization_date ON sterilization_records (tenant_id, cycle_date);
CREATE INDEX idx_sterilization_load ON sterilization_records (tenant_id, load_number);
```

### 3.42 `implant_tracking`

Full traceability chain from inventory item to patient and tooth. Required by INVIMA for implant vigilance reporting. Links to the `inventory_items` row that was consumed and to the clinical procedure that placed the implant.

```sql
CREATE TABLE implant_tracking (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL,
    inventory_item_id   UUID NOT NULL REFERENCES inventory_items(id),
    patient_id          UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    procedure_id        UUID REFERENCES procedures(id),     -- clinical procedure that placed the implant
    tooth_number        INTEGER NOT NULL,
    serial_number       VARCHAR(100) NOT NULL,
    lot_number          VARCHAR(100),
    manufacturer        VARCHAR(200) NOT NULL,
    model               VARCHAR(200),
    placed_date         DATE NOT NULL,
    placed_by           UUID NOT NULL REFERENCES users(id),
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_implant_patient ON implant_tracking (tenant_id, patient_id);
CREATE INDEX idx_implant_serial ON implant_tracking (tenant_id, serial_number);
CREATE INDEX idx_implant_inventory ON implant_tracking (inventory_item_id);
```

### 3.43 `digital_signatures`

Centralised, tamper-evident record of every drawn digital signature captured in the system. The `document_hash` records a SHA-256 fingerprint of the document content at the moment of signing so that any later modification can be detected. Signatures can be voided by a `clinic_owner`.

```sql
CREATE TABLE digital_signatures (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    signer_type     VARCHAR(20) NOT NULL
                        CHECK (signer_type IN ('doctor', 'patient')),
    signer_id       UUID NOT NULL,                          -- user_id for doctors, patient_id for patients
    signer_name     VARCHAR(200) NOT NULL,
    signer_document VARCHAR(30),                            -- cedula or national ID number
    signature_image TEXT NOT NULL,                          -- base64-encoded PNG of the drawn signature
    signature_hash  VARCHAR(64) NOT NULL,                   -- SHA-256 hash of the signature_image
    signed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip_address      INET,
    user_agent      TEXT,
    device_info     JSONB,
    -- What was signed
    resource_type   VARCHAR(30) NOT NULL
                        CHECK (resource_type IN ('consent', 'treatment_plan', 'prescription', 'sterilization', 'quotation', 'referral')),
    resource_id     UUID NOT NULL,
    document_hash   VARCHAR(64),                            -- SHA-256 of the document at time of signing
    -- Voiding
    is_valid        BOOLEAN NOT NULL DEFAULT true,
    voided_at       TIMESTAMPTZ,
    voided_by       UUID REFERENCES users(id),
    voided_reason   TEXT
);

CREATE INDEX idx_signatures_resource ON digital_signatures (tenant_id, resource_type, resource_id);
CREATE INDEX idx_signatures_signer ON digital_signatures (tenant_id, signer_type, signer_id);
CREATE INDEX idx_signatures_valid ON digital_signatures (tenant_id, is_valid) WHERE is_valid = true;
```

### 3.44 `patient_referrals`

Tracks inter-specialist referrals within or across clinics on the platform. Both the referring and receiving doctors can digitally sign the referral record. Referrals are linked to `digital_signatures` for non-repudiation.

```sql
CREATE TABLE patient_referrals (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL,
    patient_id              UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    from_doctor_id          UUID NOT NULL REFERENCES users(id),
    to_doctor_id            UUID NOT NULL REFERENCES users(id),
    reason                  TEXT NOT NULL,
    priority                VARCHAR(20) NOT NULL DEFAULT 'normal'
                                CHECK (priority IN ('urgent', 'normal', 'low')),
    specialty               VARCHAR(50),                    -- ortodoncia, endodoncia, periodoncia, etc.
    status                  VARCHAR(20) NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending', 'accepted', 'completed', 'declined')),
    notes                   TEXT,
    from_doctor_signature_id UUID REFERENCES digital_signatures(id),
    to_doctor_signature_id  UUID REFERENCES digital_signatures(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    accepted_at             TIMESTAMPTZ,
    completed_at            TIMESTAMPTZ
);

CREATE INDEX idx_referrals_patient ON patient_referrals (tenant_id, patient_id);
CREATE INDEX idx_referrals_to ON patient_referrals (tenant_id, to_doctor_id, status);
CREATE INDEX idx_referrals_from ON patient_referrals (tenant_id, from_doctor_id);
```

---

## 4. Alembic Migration Strategy for Multi-Tenant

### 4.1 Migration Architecture

DentalOS uses Alembic for database migrations with a dual-track approach:

| Migration Track | Scope | Location | Runs Against |
|----------------|-------|----------|--------------|
| **Public migrations** | Shared tables in `public` schema. | `alembic/public/versions/` | The `public` schema, once. |
| **Tenant migrations** | All tables in tenant schemas. | `alembic/tenant/versions/` | Every tenant schema, in sequence. |

### 4.2 Directory Structure

```
alembic/
  alembic.ini
  env.py                    # Custom env.py that handles multi-schema routing
  public/
    versions/               # Migrations for public schema
      001_initial_public.py
      002_add_catalog_medications.py
  tenant/
    versions/               # Migrations for tenant schemas
      001_initial_tenant.py
      002_add_waitlist.py
```

### 4.3 Migration Runner

```python
# alembic/env.py (simplified)

from alembic import context
from sqlalchemy import create_engine, text

def run_public_migrations():
    """Run migrations against the public schema."""
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=public_metadata,
            version_table="alembic_version_public",
            include_schemas=["public"],
        )
        with context.begin_transaction():
            context.run_migrations()

def run_tenant_migrations():
    """Run migrations against ALL tenant schemas sequentially."""
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        # Get all active tenant schemas
        result = connection.execute(
            text("SELECT schema_name FROM public.tenants WHERE status != 'cancelled'")
        )
        schemas = [row[0] for row in result]

        for schema_name in schemas:
            connection.execute(text(f"SET search_path TO {schema_name}, public"))
            context.configure(
                connection=connection,
                target_metadata=tenant_metadata,
                version_table="alembic_version",
                include_schemas=[schema_name],
            )
            with context.begin_transaction():
                context.run_migrations()
```

### 4.4 Tenant Provisioning Migration

When a new tenant is created, the provisioning process:

1. Creates a new schema: `CREATE SCHEMA tn_{id_short}`.
2. Runs all existing tenant migrations against the new schema from the first to the latest.
3. Seeds default data: system consent templates, default service catalog entries, default doctor schedule template.
4. Records the schema_name in `public.tenants`.

### 4.5 Migration Safety Rules

- All tenant migrations MUST be backward-compatible (no column drops without a deprecation migration first).
- All migrations MUST be idempotent (safe to run multiple times).
- Long-running migrations (adding indexes on large tables) MUST use `CREATE INDEX CONCURRENTLY`.
- Data migrations are separated from schema migrations.
- Every migration includes a `downgrade()` function for rollback.

---

## 5. Connection Pooling

### 5.1 Architecture

```
FastAPI Application
    |
    v
SQLAlchemy AsyncEngine (asyncpg driver)
    |
    v
PgBouncer (connection pooler)
    |
    v
PostgreSQL Server
```

### 5.2 SQLAlchemy Async Configuration

```python
# app/core/database.py

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@pgbouncer-host:6432/dentalos",
    pool_size=20,           # Connections per worker process
    max_overflow=10,        # Extra connections under load
    pool_timeout=30,        # Seconds to wait for a connection
    pool_recycle=1800,      # Recycle connections every 30 minutes
    pool_pre_ping=True,     # Verify connection health before use
    echo=False,             # NEVER True in production
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)
```

### 5.3 Tenant Session Dependency

```python
# app/core/dependencies.py

from sqlalchemy import text

async def get_tenant_session(
    tenant: Tenant = Depends(get_current_tenant),
) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session scoped to the current tenant's schema."""
    async with AsyncSessionLocal() as session:
        # Set the search_path to the tenant schema
        await session.execute(
            text(f"SET search_path TO {tenant.schema_name}, public")
        )
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### 5.4 PgBouncer Configuration

```ini
; pgbouncer.ini

[databases]
dentalos = host=pg-host port=5432 dbname=dentalos

[pgbouncer]
listen_port = 6432
listen_addr = 0.0.0.0
auth_type = md5
pool_mode = transaction         ; MUST be transaction mode for SET search_path
max_client_conn = 400
default_pool_size = 50
min_pool_size = 10
reserve_pool_size = 10
reserve_pool_timeout = 3
server_lifetime = 3600
server_idle_timeout = 600
log_connections = 0
log_disconnections = 0
```

**Critical:** PgBouncer MUST run in `transaction` mode (not `session` mode) because `SET search_path` is issued per transaction via SQLAlchemy. Session mode would leak search_path between tenants.

---

## 6. Backup Strategy Considerations

### 6.1 Backup Tiers

| Tier | Method | Frequency | Retention | RPO |
|------|--------|-----------|-----------|-----|
| **Continuous** | PostgreSQL WAL archiving + streaming replication | Continuous | 7 days of WAL files | ~0 (seconds) |
| **Daily** | pg_dump full database (all schemas) | Daily at 03:00 UTC | 30 days | 24 hours |
| **Weekly** | pg_dump full database + verify restore | Weekly (Sunday) | 90 days | 7 days |
| **Monthly** | Full backup + offsite copy | Monthly (1st) | 1 year | 30 days |

### 6.2 Per-Tenant Export

For individual tenant data export (tenant cancellation, data portability requests):

```bash
pg_dump -n tn_{schema_name} --no-owner --no-privileges dentalos > tenant_export.sql
```

### 6.3 Encryption

- Backups are encrypted at rest using AES-256.
- Backup transfer uses TLS 1.3.
- Encryption keys are managed separately from backup storage.

### 6.4 Restore Testing

- Weekly automated restore test to a staging environment.
- Verify row counts and data integrity checksums post-restore.
- Full disaster recovery drill quarterly.

For complete backup and DR details, see `infra/backup-disaster-recovery.md`.

---

## 7. Additional Database Conventions

### 7.1 Column Naming

- All column names use `snake_case`.
- Primary keys are always `id` (UUID).
- Foreign keys follow the pattern `{referenced_table_singular}_id` (e.g., `patient_id`, `doctor_id`).
- Timestamps are always `TIMESTAMPTZ` (timezone-aware).
- All tables include `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`.
- Mutable tables include `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()` (updated via application code or trigger).
- Monetary amounts are stored as `BIGINT` in cents to avoid floating-point issues.
- Currency is always stored alongside monetary amounts.

### 7.2 Soft Deletes

DentalOS uses `is_active BOOLEAN` for soft deletes on entities that must be retained for audit or clinical compliance (patients, users). Hard deletes are only used for ephemeral data (sessions, reminders, waitlist entries via CASCADE).

### 7.3 UUID Strategy

All primary keys use PostgreSQL `gen_random_uuid()` (v4 UUIDs). UUIDs are used instead of sequential IDs to prevent:
- Enumeration attacks (guessing IDs).
- Cross-tenant ID collision.
- Information leakage about record counts.

### 7.4 Full-Text Search

All text search indexes use the `spanish` text search configuration via `to_tsvector('spanish', ...)` with `GIN` indexes. Search queries use `plainto_tsquery('spanish', ...)` or `websearch_to_tsquery('spanish', ...)`.

---

## 8. Out of Scope

This spec explicitly does NOT cover:

- Read replica configuration and query routing (covered in `infra/deployment-architecture.md`).
- Database monitoring and alerting thresholds (covered in `infra/monitoring-observability.md`).
- Complete disaster recovery procedures and runbooks (covered in `infra/backup-disaster-recovery.md`).
- Data retention and deletion policies by country (covered in `infra/data-retention-policy.md`).
- Row-level security policies (not used; schema isolation provides equivalent guarantees).
- Database encryption at rest configuration (covered in `infra/security-policy.md`).
- Offline sync and conflict resolution schemas (covered in `infra/offline-sync-strategy.md`).

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec. Complete public schema, all 35 tenant tables, Alembic strategy, connection pooling, backup considerations. |
| 1.1 | 2026-02-25 | Interview-driven additions: updated `public.plans` with new pricing model columns and tier documentation (Free/Starter/Pro/Clinica/Enterprise); added `public.user_tenant_memberships` for multi-clinic doctor support; added multi-clinic note to tenant `users` table; added 9 new tenant tables (3.36–3.44): `evolution_templates`, `voice_sessions`, `quotations`, `quotation_items`, `inventory_items`, `sterilization_records`, `implant_tracking`, `digital_signatures`, `patient_referrals`. Total tables: ~52 (8 public + 44 tenant). |
