# DentalOS -- Navigation Map & User Flows (R-04)

> Complete navigation map, route definitions, user flow diagrams, state machines,
> and role-based access for DentalOS. This is the primary reference for the
> frontend team building the Next.js App Router application.

**Version:** 1.0
**Date:** 2026-02-24
**Tech Stack:** Next.js 14 App Router + TailwindCSS | Spanish (es-419) default | Tablet-first
**Dependencies:** I-02 (authentication-rules.md), I-01 (multi-tenancy.md)
**Referenced by:** All frontend specs, all screen specs, QA test plans

---

## Roles Overview

| Role | Code | Scope | Primary Actions |
|------|------|-------|-----------------|
| Clinic Owner | `clinic_owner` | Full clinic access | Settings, billing, team, analytics, all clinical |
| Doctor | `doctor` | Clinical work | Odontogram, records, diagnoses, treatment plans, prescriptions |
| Assistant | `assistant` | Clinical support | Patient prep, record entry, appointment management |
| Receptionist | `receptionist` | Front desk | Patient registration, appointments, billing, messages |
| Patient | `patient` | Own data only | View records, sign consents, view invoices, messages |
| Superadmin | `superadmin` | Platform-wide | Tenant management, platform analytics, plan management |

---

# 1. Route Map

All routes use Next.js App Router route groups: `(public)`, `(dashboard)`, `(portal)`, `(admin)`.
Layout inheritance follows the group hierarchy. Each group has its own root layout.

## 1.1 Public Routes -- `(public)`

No authentication required. Redirects to `/dashboard` if already authenticated.

| Route | Screen Name | Description |
|-------|-------------|-------------|
| `/login` | Iniciar Sesion | Email + password login form. Tenant resolved from subdomain. |
| `/register` | Registrar Clinica | Clinic owner registration. Creates tenant + first user. |
| `/forgot-password` | Recuperar Contrasena | Email input to request password reset link. |
| `/reset-password` | Nueva Contrasena | Password reset form. Requires valid token from email. |
| `/verify-email` | Verificar Correo | Email verification landing. Auto-verifies on token match. |
| `/invite/accept` | Aceptar Invitacion | Team invite acceptance. Sets name + password for new user. |

**Layout:** Minimal centered card layout. Logo + language selector. No sidebar.

## 1.2 Dashboard Routes -- `(dashboard)`

Authenticated clinic staff only. Requires valid JWT with `aud: "dentalos-api"`.
Tenant context resolved from subdomain. Sidebar navigation visible.

### Core Pages

| Route | Screen Name | Allowed Roles | Description |
|-------|-------------|---------------|-------------|
| `/dashboard` | Panel Principal | ALL staff | Role-specific dashboard with widgets (see Section 4) |
| `/notifications` | Notificaciones | ALL staff | Notification center. Real-time via WebSocket. |

### Patient Management

| Route | Screen Name | Allowed Roles | Description |
|-------|-------------|---------------|-------------|
| `/patients` | Lista de Pacientes | ALL staff | Searchable, filterable patient list. Pagination. |
| `/patients/new` | Nuevo Paciente | clinic_owner, receptionist, assistant | Patient registration form. Auto-creates odontogram_state. |
| `/patients/[id]` | Detalle de Paciente | ALL staff | Patient detail with tabbed interface (see below) |
| `/patients/[id]/odontogram` | Odontograma | clinic_owner, doctor, assistant | Full-screen odontogram view and edit. SVG interactive. |
| `/patients/[id]/records` | Registros Clinicos | clinic_owner, doctor, assistant | Clinical records list for this patient. |
| `/patients/[id]/records/new` | Nuevo Registro | clinic_owner, doctor, assistant | New clinical record form. CIE-10/CUPS selectors. |
| `/patients/[id]/treatment-plans` | Planes de Tratamiento | clinic_owner, doctor | Treatment plans list. Status filters. |
| `/patients/[id]/treatment-plans/new` | Nuevo Plan | clinic_owner, doctor | Treatment plan builder. Add procedures, costs, sequence. |
| `/patients/[id]/consents` | Consentimientos | ALL staff | Consent documents list. Signed/pending status. |
| `/patients/[id]/consents/new` | Nuevo Consentimiento | clinic_owner, doctor | Create consent from template. Assign to patient. |
| `/patients/[id]/prescriptions` | Recetas | clinic_owner, doctor | Prescriptions list for this patient. |
| `/patients/[id]/prescriptions/new` | Nueva Receta | clinic_owner, doctor | Prescription form. Drug search, dosage, duration. |

**Patient Detail Tabs** (`/patients/[id]`):

| Tab | Label | Roles | Content |
|-----|-------|-------|---------|
| info | Informacion | ALL staff | Demographics, contact, insurance, emergency contact |
| odontogram | Odontograma | ALL staff (edit: doctor, assistant) | Embedded odontogram preview. Link to full view. |
| records | Registros | ALL staff | Recent clinical records. Link to full list. |
| treatments | Tratamientos | ALL staff | Active treatment plans. Progress bars. |
| appointments | Citas | ALL staff | Appointment history and upcoming. |
| billing | Facturacion | clinic_owner, receptionist | Invoice history for this patient. |
| documents | Documentos | ALL staff | Consents, prescriptions, uploaded files. |

### Agenda (Appointments)

| Route | Screen Name | Allowed Roles | Description |
|-------|-------------|---------------|-------------|
| `/agenda` | Agenda | ALL staff | Calendar view: day, week, month. Filter by doctor. |
| `/agenda/new` | Nueva Cita | clinic_owner, receptionist, assistant | New appointment form/modal. Doctor + slot selection. |

### Billing

| Route | Screen Name | Allowed Roles | Description |
|-------|-------------|---------------|-------------|
| `/billing` | Facturacion | clinic_owner, receptionist | Invoice list. Status filters. Date range. |
| `/billing/new` | Nueva Factura | clinic_owner, receptionist | Invoice creation. Link procedures, add line items. |
| `/billing/[id]` | Detalle Factura | clinic_owner, receptionist | Invoice detail. Payment recording. PDF generation. |

### Messages

| Route | Screen Name | Allowed Roles | Description |
|-------|-------------|---------------|-------------|
| `/messages` | Mensajes | ALL staff | Message thread list. Unread indicators. |
| `/messages/[id]` | Conversacion | ALL staff | Thread detail. Real-time messaging. |

### Settings (clinic_owner only)

| Route | Screen Name | Allowed Roles | Description |
|-------|-------------|---------------|-------------|
| `/settings` | Configuracion | clinic_owner | Clinic profile: name, logo, address, phone, tax ID. |
| `/settings/team` | Equipo | clinic_owner | Team members list. Invite new. Change roles. Deactivate. |
| `/settings/services` | Servicios | clinic_owner | Service/procedure catalog. Prices, CIE-10/CUPS codes. |
| `/settings/schedules` | Horarios | clinic_owner | Doctor availability schedules. Working hours, breaks. |
| `/settings/billing` | Suscripcion | clinic_owner | Plan details, payment method, invoice history. |
| `/settings/templates` | Plantillas | clinic_owner | Consent document templates. Create, edit, preview. |

### Analytics

| Route | Screen Name | Allowed Roles | Description |
|-------|-------------|---------------|-------------|
| `/analytics` | Analiticas | clinic_owner, doctor | Revenue, appointments, patient stats, procedure stats. |

## 1.3 Patient Portal Routes -- `(portal)`

Patient-only access. Requires JWT with `aud: "dentalos-portal"`.
Separate layout. Top nav instead of sidebar. Mobile-first responsive.

| Route | Screen Name | Description |
|-------|-------------|-------------|
| `/portal/dashboard` | Mi Panel | Welcome screen. Upcoming appointments, unread messages, pending consents. |
| `/portal/appointments` | Mis Citas | Appointment list. Upcoming and past. Cancel/reschedule buttons. |
| `/portal/records` | Mis Registros | Clinical records (read-only). Expandable cards. |
| `/portal/prescriptions` | Mis Recetas | Prescription list. Active and past. PDF download. |
| `/portal/invoices` | Mis Facturas | Invoice list. Payment status. PDF download. |
| `/portal/consents` | Consentimientos | Pending consents to review and sign. Signed history. |
| `/portal/messages` | Mensajes | Message threads with the clinic. Send new message. |
| `/portal/profile` | Mi Perfil | Personal info, password change, notification preferences. |

## 1.4 Superadmin Routes -- `(admin)`

Superadmin only. Separate subdomain: `admin.dentalos.app`.
JWT with `role: "superadmin"`, no `tid` claim.

| Route | Screen Name | Description |
|-------|-------------|-------------|
| `/admin/dashboard` | Panel Admin | Platform metrics: total tenants, MRR, active users, system health. |
| `/admin/tenants` | Clinicas | All tenants list. Search, filter by plan, status. |
| `/admin/tenants/[id]` | Detalle Clinica | Tenant detail: users, usage, plan, billing, logs. Impersonate option. |
| `/admin/users` | Usuarios | Global user search across all tenants. |
| `/admin/analytics` | Analiticas | Platform-wide analytics: growth, churn, feature usage. |
| `/admin/plans` | Planes | Subscription plan CRUD. Feature flags, limits, pricing. |

---

# 2. User Flow Diagrams

## 2.1 Authentication Flow

```
 UNAUTHENTICATED USER
        |
        v
  +------------------+
  |   /login          |
  |  Email + Password |
  +--------+---------+
           |
     +-----+------+------------------+
     |            |                   |
     v            v                   v
  [Valid]    [Invalid]         [No Account]
     |            |                   |
     v            v                   v
  Resolve      Show error        /register
  tenant       "Credenciales     Clinic name +
  from sub-    invalidas"        Owner email +
  domain           |             Password
     |             v                  |
     v          [3 fails]             v
  Issue        -> Show             Create tenant
  JWT pair     CAPTCHA             Create schema
     |                              Create user
     v                                |
  Redirect                            v
  /dashboard                     Send verification
  (role-based                    email
   widgets)                          |
                                     v
                                /verify-email
                                     |
                                     v
                                  /login


 FORGOT PASSWORD FLOW:

  /forgot-password           /reset-password
  +----------------+        +------------------+
  | Enter email    |------->| Token from email |
  | Send reset     |  email | New password x2  |
  +----------------+        | Submit           |
                             +--------+---------+
                                      |
                                      v
                                   /login
                                   (show success)


 TEAM INVITE FLOW:

  clinic_owner                  Invited User
  /settings/team                /invite/accept
  +---------------+            +-----------------+
  | Enter email   |---email--->| Set name        |
  | Select role   |            | Set password    |
  | Send invite   |            | Accept terms    |
  +---------------+            +--------+--------+
                                        |
                                        v
                                     /dashboard
                                     (new team member)
```

## 2.2 Patient Registration Flow

```
  RECEPTIONIST / ASSISTANT
        |
        v
  /patients/new
  +----------------------------------+
  | Step 1: Basic Info               |
  |   Nombre completo                |
  |   Tipo documento (CC/CE/TI/PP)   |
  |   Numero documento               |
  |   Fecha nacimiento               |
  |   Genero                         |
  |   Telefono, Email                |
  +----------------------------------+
        |
        v
  +----------------------------------+
  | Step 2: Contact & Insurance      |
  |   Direccion                      |
  |   Contacto emergencia            |
  |   EPS / Aseguradora              |
  |   Numero poliza                  |
  +----------------------------------+
        |
        v
  +----------------------------------+
  | Step 3: Medical History          |
  |   Alergias                       |
  |   Medicamentos actuales          |
  |   Condiciones medicas            |
  |   Antecedentes relevantes        |
  +----------------------------------+
        |
        v
  POST /api/v1/patients
        |
        +---> Patient record created
        +---> odontogram_state auto-created (32 teeth, clean state)
        +---> Audit log entry written
        +---> Portal invite email queued (optional)
        |
        v
  Redirect: /patients/[new_id]
  (Patient detail, info tab)
```

## 2.3 Clinical Visit Flow

```
  PATIENT ARRIVES
        |
        v
  Receptionist: /agenda
  +----------------------+
  | Find appointment     |
  | Click "Registrar     |
  |  Llegada"            |
  +----------+-----------+
             |
             v
  Appointment -> confirmed -> in_progress
             |
             v
  Assistant: /patients/[id]
  +----------------------+
  | Prep patient tab     |
  | Verify medical hx    |
  | Update vitals        |
  +----------+-----------+
             |
             v
  Doctor: /patients/[id]/odontogram
  +----------------------------------+
  | Review current odontogram        |
  | Mark findings on teeth           |
  |   - Caries (surfaces)            |
  |   - Fractures                    |
  |   - Missing teeth                |
  |   - Existing restorations        |
  | Save odontogram changes          |
  +----------------------------------+
             |
             v
  Doctor: /patients/[id]/records/new
  +----------------------------------+
  | Select record type               |
  | Chief complaint (motivo)         |
  | Diagnosis (CIE-10 codes)        |
  | Procedures performed (CUPS)      |
  | Notes / findings                 |
  | Attach images (optional)         |
  | Save record                      |
  +----------------------------------+
             |
             +---> Record created (locked after 24h)
             +---> Odontogram updated with procedures
             +---> Audit log written
             |
             v
  Doctor or Assistant: Treatment plan update
  +----------------------------------+
  | Mark completed procedures        |
  | Schedule next procedures         |
  | Update plan progress             |
  +----------------------------------+
             |
             v
  Receptionist: /billing/new
  +----------------------------------+
  | Auto-populate from procedures    |
  | Verify amounts                   |
  | Apply discounts (if any)         |
  | Generate invoice                 |
  | Process payment                  |
  +----------------------------------+
             |
             v
  Appointment -> completed
  Patient receives receipt (email/WhatsApp)
```

## 2.4 Appointment Booking Flow

```
  RECEPTIONIST / ASSISTANT
        |
        v
  /agenda/new (or modal from /agenda)
  +----------------------------------+
  | Step 1: Select Patient           |
  |   Search by name or document     |
  |   Or create new patient inline   |
  +----------------------------------+
        |
        v
  +----------------------------------+
  | Step 2: Select Doctor            |
  |   List available doctors         |
  |   Show specialties               |
  +----------------------------------+
        |
        v
  GET /api/v1/appointments/available-slots
  ?doctor_id=...&date_from=...&date_to=...
        |
        v
  +----------------------------------+
  | Step 3: Select Time Slot         |
  |   Show available slots           |
  |   30/60 min increments           |
  |   Grayed-out = unavailable       |
  +----------------------------------+
        |
        v
  +----------------------------------+
  | Step 4: Select Service           |
  |   Procedure type                 |
  |   Estimated duration             |
  |   Notes for doctor               |
  +----------------------------------+
        |
        v
  POST /api/v1/appointments
        |
        +---> Appointment created (status: scheduled)
        +---> Confirmation email/WhatsApp sent to patient
        +---> Reminder scheduled: 24h before, 2h before
        +---> Calendar slot blocked for doctor
        |
        v
  Redirect: /agenda (day view, new appointment highlighted)


  REMINDER TIMELINE:
  +---------+----------+-----------+----------+-------+
  | Created | 24h      | 2h        | Appt     | +24h  |
  |         | Reminder | Reminder  | Time     | No-   |
  |         | (WA/SMS) | (WA/SMS)  |          | show? |
  +---------+----------+-----------+----------+-------+
```

## 2.5 Treatment Plan Flow

```
  DOCTOR
    |
    v
  /patients/[id]/treatment-plans/new
  +----------------------------------+
  | Plan Name / Description          |
  | Diagnosis reference (CIE-10)     |
  +----------------------------------+
    |
    v
  +----------------------------------+
  | Add Treatment Items:             |
  |  +---+----------+------+------+  |
  |  | # | Procedure| Tooth| Cost |  |
  |  +---+----------+------+------+  |
  |  | 1 | Resina   | 36   | $80K |  |
  |  | 2 | Endodon. | 36   | $350K|  |
  |  | 3 | Corona   | 36   | $500K|  |
  |  +---+----------+------+------+  |
  | Total: $930,000 COP             |
  +----------------------------------+
    |
    v
  POST /api/v1/patients/{id}/treatment-plans
  (status: draft)
    |
    v
  +----------------------------------+
  | Review with Patient              |
  | Explain procedures               |
  | Discuss payment options          |
  +----------------------------------+
    |
    +-------+--------+
    |                |
    v                v
  [Patient       [Patient
   Approves]      Declines]
    |                |
    v                v
  Generate        Plan stays
  consent         as draft
  document        (can modify)
    |
    v
  /patients/[id]/consents/new
  (auto-linked to plan)
    |
    v
  Patient signs consent
  (portal or in-clinic tablet)
    |
    v
  Plan status -> active
    |
    v
  Schedule individual procedures
  (each item: pending -> scheduled -> completed)
    |
    v
  Track progress until all items completed
    |
    v
  Plan status -> completed
```

## 2.6 Billing Flow

```
  RECEPTIONIST
    |
    v
  /billing/new
  +----------------------------------+
  | Select Patient                   |
  | Auto-load completed procedures   |
  |   not yet invoiced               |
  +----------------------------------+
    |
    v
  +----------------------------------+
  | Invoice Line Items:              |
  |  +---+-----------+--------+      |
  |  | # | Service   | Amount |      |
  |  +---+-----------+--------+      |
  |  | 1 | Resina 36 | $80K   |      |
  |  | 2 | Limpieza  | $60K   |      |
  |  +---+-----------+--------+      |
  |  Subtotal:         $140,000      |
  |  Descuento:        -$10,000      |
  |  Total:            $130,000      |
  +----------------------------------+
    |
    v
  POST /api/v1/invoices (status: draft)
    |
    +------+---------+
    |                |
    v                v
  [Send to        [Record
   Patient]        Payment
    |              Immediately]
    v                |
  Invoice ->         v
  sent            Invoice ->
    |              paid
    v                |
  Patient             v
  receives           Generate
  email/WA           receipt
  with PDF             |
    |                  v
    v              Email/WA
  Patient          receipt
  pays               to
  (transfer/        patient
   cash/card)
    |
    v
  Record payment
  (full or partial)
    |
    +------+--------+
    |               |
    v               v
  [Full]         [Partial]
    |               |
    v               v
  Invoice ->     Invoice ->
  paid           partial
    |               |
    v               v
  Receipt        Track
  generated      remaining
                 balance


  OVERDUE LOGIC (background job):
  +----------------------------------+
  | Daily check at 06:00 UTC-5       |
  | If invoice.status == 'sent'      |
  |   AND due_date < today           |
  | Then: status -> overdue          |
  |   Send overdue notification      |
  +----------------------------------+
```

## 2.7 Patient Portal Flow

```
  PATIENT
    |
    v
  /login (portal subdomain)
  +----------------------------------+
  | Email + Password                 |
  | OR: Magic link via email/WA      |
  +----------------------------------+
    |
    v
  /portal/dashboard
  +----------------------------------+
  | Proximas Citas (next 3)          |
  | Mensajes sin leer (count)        |
  | Consentimientos pendientes       |
  | Facturas pendientes              |
  +----------------------------------+
    |
    +-------+-------+-------+-------+-------+
    |       |       |       |       |       |
    v       v       v       v       v       v
  Citas  Regis-  Recetas  Fact.  Consen. Mensajes
    |    tros      |       |      |       |
    v       v       v       v       v       v
  View   View    View    View   Review  Send/
  past/  clinical prescr. invoic. consent receive
  upcoming records (PDF)  (PDF)  doc     messages
  appts  (read              |      |
    |    only)               v      v
    v                     Pay?   Sign
  Cancel/                (link   (digital
  Reschedule             to pay  signature)
  request                portal)
    |
    v
  Sends notification
  to clinic for
  confirmation
```

---

# 3. State Machines

## 3.1 Appointment State Machine

```
States: scheduled, confirmed, in_progress, completed, cancelled, no_show

                          +-------------+
                   +----->| cancelled   |
                   |      +-------------+
                   |
  +----------+     |      +-------------+
  | scheduled |----+----->| confirmed   |
  +----------+     |      +------+------+
       |           |             |
       |    [patient cancels     |
       |     or staff cancels]   v
       |                  +-------------+
       |                  | in_progress |
       |                  +------+------+
       |                         |
       |               +---------+---------+
       |               |                   |
       |               v                   v
       |        +-------------+     +-------------+
       |        | completed   |     | no_show     |
       |        +-------------+     +-------------+
       |
       +----> (if patient does not confirm 2h before -> no_show eligible)
```

**Transition Rules:**

| From | To | Triggered By | Conditions |
|------|----|-------------|------------|
| `scheduled` | `confirmed` | patient (portal), receptionist, system (auto after booking) | Patient confirms via link or receptionist confirms by phone |
| `scheduled` | `cancelled` | patient, receptionist, clinic_owner | Cancellation reason required. >=24h before: free. <24h: late cancel flag |
| `confirmed` | `in_progress` | receptionist, assistant | Patient has physically arrived. Check-in action. |
| `confirmed` | `cancelled` | patient, receptionist, clinic_owner | Same rules as scheduled -> cancelled |
| `in_progress` | `completed` | doctor, assistant | Clinical visit finished. At least one record or note. |
| `in_progress` | `no_show` | receptionist, system | Patient left without completing. Rare manual override. |
| `scheduled` | `no_show` | system (background job) | 30 min past appointment time with no check-in. Auto-mark. |
| `confirmed` | `no_show` | system (background job) | 30 min past appointment time with no check-in. Auto-mark. |

## 3.2 Treatment Plan State Machine

```
  +-------+       +--------+       +-----------+
  | draft |------>| active |------>| completed |
  +-------+       +--------+       +-----------+
      |               |
      v               v
  +-----------+   +-----------+
  | cancelled |   | cancelled |
  +-----------+   +-----------+
```

| From | To | Triggered By | Conditions |
|------|----|-------------|------------|
| `draft` | `active` | doctor, clinic_owner | Patient consent signed. At least one treatment item. |
| `draft` | `cancelled` | doctor, clinic_owner | Reason required. Patient informed. |
| `active` | `completed` | system (auto) | All treatment items are `completed` or `cancelled`. |
| `active` | `cancelled` | doctor, clinic_owner | Reason required. Patient consent. Remaining items cancelled. |

## 3.3 Treatment Plan Item State Machine

```
  +---------+       +-----------+       +-----------+
  | pending |------>| scheduled |------>| completed |
  +---------+       +-----------+       +-----------+
      |                  |
      v                  v
  +-----------+     +-----------+
  | cancelled |     | cancelled |
  +-----------+     +-----------+
```

| From | To | Triggered By | Conditions |
|------|----|-------------|------------|
| `pending` | `scheduled` | doctor, assistant, receptionist | Appointment created and linked to this item. |
| `pending` | `cancelled` | doctor, clinic_owner | Part of plan cancellation or individual item removal. |
| `scheduled` | `completed` | doctor | Procedure performed. Clinical record created. |
| `scheduled` | `cancelled` | doctor, clinic_owner | Appointment cancelled or procedure no longer needed. |

## 3.4 Invoice State Machine

```
  +-------+     +------+     +------+     +---------+
  | draft |---->| sent |---->| paid |     | overdue |
  +-------+     +------+     +------+     +---------+
     |             |  |          ^             ^
     |             |  +----------+-------------+
     v             |  |          |
  +--------+      |  v          |
  | voided |      | +---------+ |
  +--------+      | | partial |-+
                  | +---------+
                  v
              +-----------+
              | cancelled |
              +-----------+
```

| From | To | Triggered By | Conditions |
|------|----|-------------|------------|
| `draft` | `sent` | receptionist, clinic_owner | Invoice validated. Patient notified. |
| `draft` | `voided` | receptionist, clinic_owner | Invoice discarded before sending. |
| `sent` | `paid` | receptionist, clinic_owner | Full payment recorded. Payment method logged. |
| `sent` | `partial` | receptionist, clinic_owner | Partial payment recorded. Remaining balance tracked. |
| `sent` | `overdue` | system (daily job) | `due_date < current_date` and status is `sent`. |
| `sent` | `cancelled` | clinic_owner | Cancellation reason required. Credit note generated if needed. |
| `partial` | `paid` | receptionist, clinic_owner | Remaining balance paid in full. |
| `partial` | `overdue` | system (daily job) | `due_date < current_date` and status is `partial`. |
| `overdue` | `paid` | receptionist, clinic_owner | Full remaining balance paid. |
| `overdue` | `partial` | receptionist, clinic_owner | Partial payment on overdue invoice. Stays overdue. |
| `overdue` | `cancelled` | clinic_owner | Write-off. Reason required. |

## 3.5 Consent State Machine

```
  +-------+       +--------+
  | draft |------>| signed |
  +-------+       +--------+
      |
      v
  +--------+
  | voided |
  +--------+
```

| From | To | Triggered By | Conditions |
|------|----|-------------|------------|
| `draft` | `signed` | patient (portal or in-clinic) | Digital signature captured. Timestamp recorded. IP logged. |
| `draft` | `voided` | doctor, clinic_owner | Consent no longer needed. Reason required. |

**Note:** Signed consents are immutable. They cannot be voided or modified after signing.
A new consent must be created if changes are needed.

## 3.6 Prescription State Machine

```
  +-------+       +--------+       +-----------+
  | draft |------>| active |------>| completed |
  +-------+       +--------+       +-----------+
      |               |
      v               v
  +-----------+   +-----------+
  | cancelled |   | cancelled |
  +-----------+   +-----------+
```

| From | To | Triggered By | Conditions |
|------|----|-------------|------------|
| `draft` | `active` | doctor | Prescription finalized and shared with patient. |
| `draft` | `cancelled` | doctor | Prescription discarded before activation. |
| `active` | `completed` | system (auto), doctor | End date reached or manually marked complete. |
| `active` | `cancelled` | doctor | Medication discontinued. Reason required. Patient notified. |

## 3.7 Clinical Record Lifecycle

```
  +----------+    +24 hours     +--------+
  | created  |----------------->| locked |
  | (editable|                  | (immut-|
  |  by      |                  |  able) |
  |  author) |                  |        |
  +----------+                  +--------+
```

| State | Rules |
|-------|-------|
| `created` | Editable only by the original author (doctor) for 24 hours after creation. |
| `locked` | System auto-locks after 24 hours. No edits allowed. Addendums can be appended as new linked records. |

**Immutability rules:**
- Records cannot be deleted, only appended to.
- Corrections require a new "addendum" record type linked to the original.
- All edits within the 24h window are tracked in the audit log.
- Required for Colombian RDA (Resolucion 3100 de 2019) compliance.

## 3.8 User Invite State Machine

```
  +---------+       +----------+
  | pending |------>| accepted |
  +---------+       +----------+
      |
      +------+
      |      |
      v      v
  +---------+ +-----------+
  | expired | | cancelled |
  +---------+ +-----------+
```

| From | To | Triggered By | Conditions |
|------|----|-------------|------------|
| `pending` | `accepted` | invited user | User clicks invite link, sets password, accepts. |
| `pending` | `expired` | system (background job) | 7 days elapsed since invite sent. |
| `pending` | `cancelled` | clinic_owner | Owner revokes invite before acceptance. |

---

# 4. Dashboard Widgets per Role

## 4.1 clinic_owner -- `/dashboard`

| Widget | Description | Data Source |
|--------|-------------|-------------|
| Citas de Hoy | Total appointments today with status breakdown | `GET /api/v1/appointments?date=today` |
| Ingresos del Mes | Revenue this month vs previous month | `GET /api/v1/analytics/revenue?period=month` |
| Nuevos Pacientes | New patient registrations this week | `GET /api/v1/analytics/patients?period=week` |
| Actividad del Equipo | Recent actions by team members (last 10) | `GET /api/v1/analytics/team-activity` |
| Estado de Suscripcion | Current plan, usage limits, renewal date | `GET /api/v1/tenants/me/subscription` |
| Facturas Pendientes | Count and total amount of unpaid invoices | `GET /api/v1/invoices?status=sent,overdue` |

## 4.2 doctor -- `/dashboard`

| Widget | Description | Data Source |
|--------|-------------|-------------|
| Mis Citas Hoy | My appointments for today, ordered by time | `GET /api/v1/appointments?doctor_id=me&date=today` |
| Planes Pendientes | Treatment plans in draft needing review | `GET /api/v1/treatment-plans?status=draft&doctor_id=me` |
| Pacientes en Espera | Patients checked-in, waiting for consultation | `GET /api/v1/appointments?status=in_progress&doctor_id=me` |
| Registros Recientes | Last 5 clinical records created by me | `GET /api/v1/clinical-records?author_id=me&limit=5` |
| Proxima Cita | Next upcoming appointment with patient info | `GET /api/v1/appointments?doctor_id=me&status=confirmed&limit=1` |

## 4.3 assistant -- `/dashboard`

| Widget | Description | Data Source |
|--------|-------------|-------------|
| Agenda de Hoy | Full schedule for today, all doctors | `GET /api/v1/appointments?date=today` |
| Pacientes por Preparar | Confirmed appointments arriving soon | `GET /api/v1/appointments?status=confirmed&date=today` |
| Registros Pendientes | Records started but not yet completed | `GET /api/v1/clinical-records?status=draft` |
| Tareas Rapidas | Quick action buttons: check-in patient, new record | N/A (navigation shortcuts) |

## 4.4 receptionist -- `/dashboard`

| Widget | Description | Data Source |
|--------|-------------|-------------|
| Citas de Hoy | Today's appointments with check-in status | `GET /api/v1/appointments?date=today` |
| Cola de Llegadas | Patients who arrived, pending check-in | `GET /api/v1/appointments?status=scheduled,confirmed&date=today` |
| Facturas Pendientes | Invoices awaiting payment | `GET /api/v1/invoices?status=sent,overdue` |
| Mensajes sin Leer | Unread message count with latest preview | `GET /api/v1/messages?unread=true` |
| Proximas Citas | Next 3 upcoming appointments | `GET /api/v1/appointments?status=scheduled&limit=3` |

---

# 5. Navigation Structure

## 5.1 Sidebar Navigation -- `(dashboard)`

Items are rendered conditionally based on the user's `role` claim in the JWT.

### clinic_owner

```
  +----------------------------------+
  | [Logo] DentalOS                  |
  |----------------------------------|
  |  Panel Principal      /dashboard |
  |  Pacientes            /patients  |
  |  Agenda               /agenda    |
  |  Facturacion          /billing   |
  |  Mensajes             /messages  |
  |  Analiticas           /analytics |
  |  Notificaciones    /notifications|
  |----------------------------------|
  |  CONFIGURACION                   |
  |  Clinica              /settings  |
  |  Equipo        /settings/team    |
  |  Servicios  /settings/services   |
  |  Horarios  /settings/schedules   |
  |  Suscripcion /settings/billing   |
  |  Plantillas /settings/templates  |
  |----------------------------------|
  |  [Avatar] Dr. Garcia    Salir    |
  +----------------------------------+
```

### doctor

```
  +----------------------------------+
  | [Logo] DentalOS                  |
  |----------------------------------|
  |  Panel Principal      /dashboard |
  |  Pacientes            /patients  |
  |  Agenda               /agenda    |
  |  Mensajes             /messages  |
  |  Notificaciones    /notifications|
  |----------------------------------|
  |  [Avatar] Dra. Lopez    Salir    |
  +----------------------------------+
```

### assistant

```
  +----------------------------------+
  | [Logo] DentalOS                  |
  |----------------------------------|
  |  Panel Principal      /dashboard |
  |  Pacientes            /patients  |
  |  Agenda               /agenda    |
  |  Mensajes             /messages  |
  |  Notificaciones    /notifications|
  |----------------------------------|
  |  [Avatar] Ana M.        Salir    |
  +----------------------------------+
```

### receptionist

```
  +----------------------------------+
  | [Logo] DentalOS                  |
  |----------------------------------|
  |  Panel Principal      /dashboard |
  |  Pacientes            /patients  |
  |  Agenda               /agenda    |
  |  Facturacion          /billing   |
  |  Mensajes             /messages  |
  |  Notificaciones    /notifications|
  |----------------------------------|
  |  [Avatar] Carlos R.     Salir    |
  +----------------------------------+
```

## 5.2 Portal Navigation -- `(portal)`

Horizontal top navigation bar. Mobile: hamburger menu.

```
  +------------------------------------------------------------------------+
  | [Logo] DentalOS  |  Panel | Citas | Registros | Recetas | Facturas    |
  |                  |        |       |           |         |             |
  |                  | Consentimientos | Mensajes  | Mi Perfil  | Salir  |
  +------------------------------------------------------------------------+
```

| Item | Route | Icon |
|------|-------|------|
| Panel | `/portal/dashboard` | home |
| Citas | `/portal/appointments` | calendar |
| Registros | `/portal/records` | file-text |
| Recetas | `/portal/prescriptions` | pill |
| Facturas | `/portal/invoices` | receipt |
| Consentimientos | `/portal/consents` | shield-check |
| Mensajes | `/portal/messages` | message-circle |
| Mi Perfil | `/portal/profile` | user |

## 5.3 Admin Navigation -- `(admin)`

Sidebar navigation, distinct branding (dark theme).

```
  +----------------------------------+
  | [Logo] DentalOS Admin            |
  |----------------------------------|
  |  Dashboard        /admin/dashboard|
  |  Clinicas         /admin/tenants  |
  |  Usuarios         /admin/users    |
  |  Analiticas     /admin/analytics  |
  |  Planes           /admin/plans    |
  |----------------------------------|
  |  [Avatar] Admin         Salir    |
  +----------------------------------+
```

---

# 6. API Endpoints per Flow

All endpoints prefixed with `/api/v1/`. Methods follow REST conventions.
Tenant context resolved from `X-Tenant-ID` header or subdomain.

## 6.1 Authentication Flow

| Action | Method | Endpoint | Request Body | Response |
|--------|--------|----------|-------------|----------|
| Login | POST | `/auth/login` | `{email, password}` | `{access_token, user}` + Set-Cookie refresh |
| Register clinic | POST | `/auth/register` | `{clinic_name, email, password, owner_name}` | `{tenant, user}` |
| Forgot password | POST | `/auth/forgot-password` | `{email}` | `{message}` |
| Reset password | POST | `/auth/reset-password` | `{token, password}` | `{message}` |
| Verify email | POST | `/auth/verify-email` | `{token}` | `{message}` |
| Refresh token | POST | `/auth/refresh` | Cookie only | `{access_token}` + Set-Cookie refresh |
| Logout | POST | `/auth/logout` | None | Clears cookie, revokes refresh token |
| Accept invite | POST | `/auth/invite/accept` | `{token, name, password}` | `{access_token, user}` |

## 6.2 Patient Management

| Action | Method | Endpoint | Roles |
|--------|--------|----------|-------|
| List patients | GET | `/patients` | ALL staff |
| Search patients | GET | `/patients?q={query}` | ALL staff |
| Create patient | POST | `/patients` | clinic_owner, receptionist, assistant |
| Get patient detail | GET | `/patients/{patient_id}` | ALL staff |
| Update patient | PUT | `/patients/{patient_id}` | clinic_owner, receptionist, assistant |
| Delete patient (soft) | DELETE | `/patients/{patient_id}` | clinic_owner |

## 6.3 Odontogram

| Action | Method | Endpoint | Roles |
|--------|--------|----------|-------|
| Get odontogram | GET | `/patients/{patient_id}/odontogram` | ALL staff |
| Update tooth state | PATCH | `/patients/{patient_id}/odontogram/teeth/{tooth_number}` | doctor, assistant |
| Get odontogram history | GET | `/patients/{patient_id}/odontogram/history` | doctor, clinic_owner |

## 6.4 Clinical Records

| Action | Method | Endpoint | Roles |
|--------|--------|----------|-------|
| List records | GET | `/patients/{patient_id}/clinical-records` | ALL staff |
| Create record | POST | `/patients/{patient_id}/clinical-records` | doctor, clinic_owner |
| Get record detail | GET | `/patients/{patient_id}/clinical-records/{record_id}` | ALL staff |
| Update record (within 24h) | PUT | `/patients/{patient_id}/clinical-records/{record_id}` | author only |
| Create addendum | POST | `/patients/{patient_id}/clinical-records/{record_id}/addendum` | doctor |

## 6.5 Treatment Plans

| Action | Method | Endpoint | Roles |
|--------|--------|----------|-------|
| List plans | GET | `/patients/{patient_id}/treatment-plans` | ALL staff |
| Create plan | POST | `/patients/{patient_id}/treatment-plans` | doctor, clinic_owner |
| Get plan detail | GET | `/patients/{patient_id}/treatment-plans/{plan_id}` | ALL staff |
| Update plan | PUT | `/patients/{patient_id}/treatment-plans/{plan_id}` | doctor, clinic_owner |
| Add plan item | POST | `/patients/{patient_id}/treatment-plans/{plan_id}/items` | doctor, clinic_owner |
| Update plan item | PUT | `/patients/{patient_id}/treatment-plans/{plan_id}/items/{item_id}` | doctor, clinic_owner |
| Activate plan | POST | `/patients/{patient_id}/treatment-plans/{plan_id}/activate` | doctor, clinic_owner |
| Cancel plan | POST | `/patients/{patient_id}/treatment-plans/{plan_id}/cancel` | doctor, clinic_owner |

## 6.6 Appointments

| Action | Method | Endpoint | Roles |
|--------|--------|----------|-------|
| List appointments | GET | `/appointments` | ALL staff |
| Get available slots | GET | `/appointments/available-slots` | ALL staff |
| Create appointment | POST | `/appointments` | clinic_owner, receptionist, assistant |
| Get appointment | GET | `/appointments/{appointment_id}` | ALL staff |
| Update appointment | PUT | `/appointments/{appointment_id}` | clinic_owner, receptionist, assistant |
| Check-in (arrive) | POST | `/appointments/{appointment_id}/check-in` | receptionist, assistant |
| Complete | POST | `/appointments/{appointment_id}/complete` | doctor, assistant |
| Cancel | POST | `/appointments/{appointment_id}/cancel` | ALL staff, patient (portal) |
| Mark no-show | POST | `/appointments/{appointment_id}/no-show` | receptionist, system |

## 6.7 Billing / Invoices

| Action | Method | Endpoint | Roles |
|--------|--------|----------|-------|
| List invoices | GET | `/invoices` | clinic_owner, receptionist |
| Create invoice | POST | `/invoices` | clinic_owner, receptionist |
| Get invoice | GET | `/invoices/{invoice_id}` | clinic_owner, receptionist |
| Send invoice | POST | `/invoices/{invoice_id}/send` | clinic_owner, receptionist |
| Record payment | POST | `/invoices/{invoice_id}/payments` | clinic_owner, receptionist |
| Void invoice | POST | `/invoices/{invoice_id}/void` | clinic_owner |
| Cancel invoice | POST | `/invoices/{invoice_id}/cancel` | clinic_owner |
| Download PDF | GET | `/invoices/{invoice_id}/pdf` | clinic_owner, receptionist, patient |

## 6.8 Consents

| Action | Method | Endpoint | Roles |
|--------|--------|----------|-------|
| List consents | GET | `/patients/{patient_id}/consents` | ALL staff |
| Create consent | POST | `/patients/{patient_id}/consents` | doctor, clinic_owner |
| Get consent | GET | `/patients/{patient_id}/consents/{consent_id}` | ALL staff, patient |
| Sign consent | POST | `/patients/{patient_id}/consents/{consent_id}/sign` | patient |
| Void consent | POST | `/patients/{patient_id}/consents/{consent_id}/void` | doctor, clinic_owner |

## 6.9 Prescriptions

| Action | Method | Endpoint | Roles |
|--------|--------|----------|-------|
| List prescriptions | GET | `/patients/{patient_id}/prescriptions` | ALL staff |
| Create prescription | POST | `/patients/{patient_id}/prescriptions` | doctor, clinic_owner |
| Get prescription | GET | `/patients/{patient_id}/prescriptions/{prescription_id}` | ALL staff, patient |
| Activate prescription | POST | `/patients/{patient_id}/prescriptions/{prescription_id}/activate` | doctor |
| Cancel prescription | POST | `/patients/{patient_id}/prescriptions/{prescription_id}/cancel` | doctor |
| Download PDF | GET | `/patients/{patient_id}/prescriptions/{prescription_id}/pdf` | ALL staff, patient |

## 6.10 Messages

| Action | Method | Endpoint | Roles |
|--------|--------|----------|-------|
| List threads | GET | `/messages` | ALL staff |
| Create thread | POST | `/messages` | ALL staff |
| Get thread | GET | `/messages/{thread_id}` | ALL staff |
| Send message | POST | `/messages/{thread_id}/messages` | ALL staff, patient |
| Mark read | POST | `/messages/{thread_id}/read` | ALL staff, patient |

## 6.11 Settings (clinic_owner)

| Action | Method | Endpoint | Roles |
|--------|--------|----------|-------|
| Get clinic settings | GET | `/settings/clinic` | clinic_owner |
| Update clinic settings | PUT | `/settings/clinic` | clinic_owner |
| List team members | GET | `/settings/team` | clinic_owner |
| Invite team member | POST | `/settings/team/invite` | clinic_owner |
| Update member role | PUT | `/settings/team/{user_id}` | clinic_owner |
| Deactivate member | DELETE | `/settings/team/{user_id}` | clinic_owner |
| List services | GET | `/settings/services` | clinic_owner |
| Create service | POST | `/settings/services` | clinic_owner |
| Update service | PUT | `/settings/services/{service_id}` | clinic_owner |
| Delete service | DELETE | `/settings/services/{service_id}` | clinic_owner |
| Get schedules | GET | `/settings/schedules` | clinic_owner |
| Update schedule | PUT | `/settings/schedules/{doctor_id}` | clinic_owner |
| List templates | GET | `/settings/templates` | clinic_owner |
| Create template | POST | `/settings/templates` | clinic_owner |
| Update template | PUT | `/settings/templates/{template_id}` | clinic_owner |
| Delete template | DELETE | `/settings/templates/{template_id}` | clinic_owner |
| Get subscription | GET | `/settings/subscription` | clinic_owner |

## 6.12 Analytics

| Action | Method | Endpoint | Roles |
|--------|--------|----------|-------|
| Revenue stats | GET | `/analytics/revenue` | clinic_owner |
| Appointment stats | GET | `/analytics/appointments` | clinic_owner, doctor |
| Patient stats | GET | `/analytics/patients` | clinic_owner |
| Procedure stats | GET | `/analytics/procedures` | clinic_owner, doctor |
| Team activity | GET | `/analytics/team-activity` | clinic_owner |

## 6.13 Patient Portal Endpoints

| Action | Method | Endpoint | Roles |
|--------|--------|----------|-------|
| My dashboard data | GET | `/portal/dashboard` | patient |
| My appointments | GET | `/portal/appointments` | patient |
| Cancel my appointment | POST | `/portal/appointments/{id}/cancel` | patient |
| My records | GET | `/portal/records` | patient |
| My prescriptions | GET | `/portal/prescriptions` | patient |
| My invoices | GET | `/portal/invoices` | patient |
| My pending consents | GET | `/portal/consents` | patient |
| Sign consent | POST | `/portal/consents/{id}/sign` | patient |
| My messages | GET | `/portal/messages` | patient |
| Send message | POST | `/portal/messages/{thread_id}/reply` | patient |
| My profile | GET | `/portal/profile` | patient |
| Update profile | PUT | `/portal/profile` | patient |

## 6.14 Superadmin Endpoints

| Action | Method | Endpoint | Roles |
|--------|--------|----------|-------|
| Platform metrics | GET | `/admin/metrics` | superadmin |
| List tenants | GET | `/admin/tenants` | superadmin |
| Get tenant detail | GET | `/admin/tenants/{tenant_id}` | superadmin |
| Update tenant | PUT | `/admin/tenants/{tenant_id}` | superadmin |
| Suspend tenant | POST | `/admin/tenants/{tenant_id}/suspend` | superadmin |
| Global user search | GET | `/admin/users` | superadmin |
| Platform analytics | GET | `/admin/analytics` | superadmin |
| List plans | GET | `/admin/plans` | superadmin |
| Create plan | POST | `/admin/plans` | superadmin |
| Update plan | PUT | `/admin/plans/{plan_id}` | superadmin |
| Impersonate tenant | POST | `/admin/tenants/{tenant_id}/impersonate` | superadmin |

---

# 7. Middleware & Guards

## 7.1 Route Protection

| Route Group | Guard | Redirect on Failure |
|-------------|-------|---------------------|
| `(public)` | `isUnauthenticated` -- redirect away if logged in | `/dashboard` (staff) or `/portal/dashboard` (patient) |
| `(dashboard)` | `isAuthenticated` + `isStaffRole` | `/login` |
| `(portal)` | `isAuthenticated` + `isPatientRole` | `/login` |
| `(admin)` | `isAuthenticated` + `isSuperadmin` | `/login` |

## 7.2 Role-Based Page Guards

```
middleware.ts (Next.js)
  |
  +-- Check JWT in cookie/header
  |     |
  |     +-- No token -> redirect /login
  |     +-- Expired -> attempt refresh -> fail -> redirect /login
  |     +-- Valid -> extract role, tid
  |
  +-- Route group check
  |     |
  |     +-- (dashboard) + role=patient -> redirect /portal/dashboard
  |     +-- (portal) + role!=patient -> redirect /dashboard
  |     +-- (admin) + role!=superadmin -> redirect /dashboard
  |
  +-- Per-route role check
        |
        +-- /settings/* + role!=clinic_owner -> redirect /dashboard (403 toast)
        +-- /billing/* + role not in [clinic_owner, receptionist] -> redirect /dashboard
        +-- /analytics + role not in [clinic_owner, doctor] -> redirect /dashboard
```

## 7.3 Tenant Resolution

```
Request arrives
  |
  v
Extract subdomain: {tenant_slug}.dentalos.app
  |
  v
Lookup tenant by slug in public.tenants table
  |
  +-- Not found -> 404 "Clinica no encontrada"
  +-- Found but suspended -> 403 "Clinica suspendida"
  +-- Found and active -> Set tenant context
        |
        v
      SET search_path TO tenant_{tenant_id}, public;
      Continue request processing
```

---

# Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-24 | DentalOS Team | Initial navigation map: routes, flows, state machines, widgets, API mapping |

---

*This document is the authoritative reference for all frontend navigation, routing, and user flow implementation. All screen specs in `specs/frontend/` must reference routes defined here. Any new route must be added to this document first.*
