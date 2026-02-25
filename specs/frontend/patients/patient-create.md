# Crear Paciente (Patient Create) — Frontend Spec

## Overview

**Screen:** Multi-section accordion form for registering a new patient. Organized into four collapsible sections: información personal, contacto, antecedentes médicos, y seguro/convenio. Document number format validation adapts to the selected document type (cédula de ciudadanía, cédula extranjería, pasaporte, tarjeta de identidad).

**Route:** `/patients/new`

**Priority:** Critical

**Backend Specs:** `specs/patients/patient-create.md` (P-01)

**Dependencies:** `specs/frontend/patients/patient-list.md`, `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- "Nuevo paciente" button in patient list (`/patients`)
- "Nuevo paciente" quick action button in header
- "Nuevo paciente" from appointment creation modal (shortcut)

**Exit Points:**
- Success → redirect to `/patients/{id}` (patient detail) with toast "Paciente creado exitosamente"
- "Cancelar" button → back to `/patients`
- Browser back → confirm dialog if form has unsaved changes

**User Story:**
> As a receptionist | doctor | assistant, I want to register a new patient so that I can create appointments and clinical records for them.

**Roles with access:** `clinic_owner`, `doctor`, `assistant`, `receptionist`

---

## Layout Structure

```
+--------------------------------------------------+
|  Sidebar |  Breadcrumb: Pacientes > Nuevo        |
|          +---------------------------------------+
|          |  Page title: "Nuevo Paciente"         |
|          |  [Cancelar btn]  [Guardar Paciente btn]|
|          +---------------------------------------+
|          |                                       |
|          |  [Accordion 1: Informacion Personal]  |
|          |  [Accordion 2: Informacion de Contacto]|
|          |  [Accordion 3: Antecedentes Medicos]  |
|          |  [Accordion 4: Seguro / Convenio]     |
|          |                                       |
|          |  [Cancelar btn]  [Guardar Paciente btn]|
|          +---------------------------------------+
```

**Sections:**
1. Page header — breadcrumb, title, top action buttons
2. Accordion form sections — 4 collapsible panels, all open by default on create
3. Bottom action row — duplicate of top buttons for convenience on long pages

---

## UI Components

### Component 1: AccordionSection

**Type:** Collapsible section container

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.11

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| title | string | — | Section heading |
| isOpen | boolean | true | Expanded state on create |
| hasErrors | boolean | false | Red indicator dot on header when section has errors |
| isComplete | boolean | false | Green check icon on header when all required fields valid |

**Header:** `flex items-center justify-between p-4 cursor-pointer select-none`
- Left: section number badge (`bg-teal-100 text-teal-700 text-xs font-bold w-6 h-6 rounded-full`) + title `text-base font-semibold text-gray-800`
- Right: error dot or check icon + `ChevronUp/Down` toggle icon
- Animated: `motion.div` height transition 250ms ease-in-out

### Component 2: DocumentTypeSelect + DocumentInput

**Type:** Linked select + input pair

**Behavior:**
- Document type `<select>` on left `w-1/3`
- Document number `<input type="text">` on right `flex-1`
- When type changes, input clears and validation rule swaps
- Regex by type:
  - `cedula_ciudadania`: `/^\d{6,10}$/`
  - `cedula_extranjeria`: `/^[A-Z0-9]{4,12}$/i`
  - `tarjeta_identidad`: `/^\d{10,11}$/`
  - `pasaporte`: `/^[A-Z0-9]{5,15}$/i`
  - `nit`: `/^\d{9}-\d$/`

### Component 3: QuickTagInput (Medical Info)

**Type:** Tag/chip multi-input

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.12

**Behavior:**
- Text input with typeahead suggestions for common values
- Press Enter or comma to add a tag
- Tags shown as chips: `bg-gray-100 text-gray-700 text-sm rounded-full px-3 py-1` with X remove button
- Max 20 tags per field
- Suggestions for allergias: "Penicilina", "Latex", "Ibuprofeno", "Amoxicilina", "Aspirina", "Anestesia local"
- Suggestions for condiciones: "Diabetes", "Hipertension", "Asma", "Cardiopatia", "HIV/SIDA", "Embarazo", "Trastorno de coagulacion"
- Suggestions for medicamentos: "Warfarina", "Aspirina", "Metformina", "Insulina", "Antihipertensivos"

---

## Form Fields

### Section 1: Informacion Personal

| Field | Type | Required | Validation | Error Message (es-419) | Placeholder |
|-------|------|----------|------------|------------------------|-------------|
| primer_nombre | text | Yes | Min 2, max 50 chars, letters + spaces | "El nombre es obligatorio" | "Primer nombre" |
| segundo_nombre | text | No | Max 50 chars | — | "Segundo nombre" |
| primer_apellido | text | Yes | Min 2, max 50 chars | "El apellido es obligatorio" | "Primer apellido" |
| segundo_apellido | text | No | Max 50 chars | — | "Segundo apellido" |
| tipo_documento | select | Yes | From enum list | "Selecciona el tipo de documento" | "Tipo de documento" |
| numero_documento | text | Yes | Regex by tipo_documento | "Numero de documento invalido" | "Numero de documento" |
| fecha_nacimiento | date | Yes | Past date, min age 0, max 120 years | "Fecha de nacimiento invalida" | "DD/MM/AAAA" |
| genero | select | Yes | M / F / Otro / Prefiero_no_decir | "Selecciona el genero" | "Genero" |
| foto_paciente | file | No | JPEG/PNG, max 5MB | "Imagen invalida. Max 5MB, JPG o PNG" | — |

**Genero options:** Masculino / Femenino / Otro / Prefiero no decir

**Tipo de documento options:** Cedula de ciudadania / Cedula de extranjeria / Tarjeta de identidad / Pasaporte / NIT (empresas)

**Age display:** After fecha_nacimiento is valid, show computed age inline: `"({n} años)"` in `text-sm text-gray-500` next to the date field.

### Section 2: Informacion de Contacto

| Field | Type | Required | Validation | Error Message (es-419) | Placeholder |
|-------|------|----------|------------|------------------------|-------------|
| telefono_principal | tel | Yes | E.164, min 7 digits | "Telefono obligatorio" | "+57 300 000 0000" |
| telefono_alternativo | tel | No | E.164 format | "Telefono invalido" | "+57 300 000 0001" |
| correo | email | No | Valid email format | "Correo invalido" | "correo@ejemplo.com" |
| direccion | text | No | Max 200 chars | — | "Calle 80 # 12-34, Bogota" |
| ciudad | text | No | Max 100 chars | — | "Bogota" |
| departamento | select | No | Colombia departments list | — | "Departamento" |
| contacto_emergencia_nombre | text | No | Max 100 chars | — | "Nombre del contacto" |
| contacto_emergencia_telefono | tel | No | E.164 format | "Telefono invalido" | "+57 300 000 0002" |
| contacto_emergencia_relacion | text | No | Max 50 chars | — | "Ej: Esposa, Madre, Hijo" |

### Section 3: Antecedentes Medicos

| Field | Type | Required | Validation | Error Message (es-419) |
|-------|------|----------|------------|------------------------|
| alergias | tags | No | Max 20 tags, max 100 chars each | "Maximo 20 alergias" |
| condiciones_medicas | tags | No | Max 20 tags | "Maximo 20 condiciones" |
| medicamentos_actuales | tags | No | Max 20 tags | "Maximo 20 medicamentos" |
| notas_medicas | textarea | No | Max 1000 chars | — |
| grupo_sanguineo | select | No | A+/A-/B+/B-/AB+/AB-/O+/O- / No sabe | — |

**Character counter** on `notas_medicas`: `{n}/1000` in `text-xs text-gray-400` bottom-right corner.

### Section 4: Seguro / Convenio

| Field | Type | Required | Validation | Error Message (es-419) | Placeholder |
|-------|------|----------|------------|------------------------|-------------|
| aseguradora | text | No | Max 100 chars | — | "Ej: Sura, Colsanitas, EPS Sanitas" |
| numero_poliza | text | No | Max 50 chars | — | "Numero de poliza o afiliacion" |
| fecha_vencimiento_poliza | date | No | Future date | "La fecha debe ser futura" | "DD/MM/AAAA" |
| tipo_afiliacion | select | No | Contributivo / Subsidiado / Particular / Convenio | — | "Tipo de afiliacion" |

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Create patient | `/api/v1/patients` | POST | `specs/patients/patient-create.md` | None |
| Check duplicate document | `/api/v1/patients/check-duplicate` | GET | `specs/patients/patient-create.md` | None |
| Upload patient photo | `/api/v1/patients/{id}/photo` | POST (multipart) | `specs/patients/patient-photo.md` | None |

### Duplicate Check

Triggered on blur of `numero_documento` field (debounced 500ms):
- If duplicate found: warning banner `bg-amber-50 border-amber-200` "Ya existe un paciente con este documento. [Ver paciente →]" (link to existing patient)
- Warning does not block form submission — receptionist may intentionally add family member with same document type (different tenant scenario)

### State Management

**Local State (useState):**
- `isDirty: boolean` — true after any field changes (for unsaved-changes dialog)
- `serverError: string | null`
- `duplicatePatient: { id, name } | null`

**Global State (Zustand):**
- `patientStore` — invalidate `['patients']` query after successful create

**Server State (TanStack Query):**
- Mutation: `useMutation({ mutationFn: createPatient, onSuccess: () => queryClient.invalidateQueries(['patients']) })`

### Error Code Mapping

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `document_duplicate` | 409 | "Ya existe un paciente con este numero de documento en la clinica." |
| `validation_error` | 422 | "Revisa los campos marcados en rojo." |
| `quota_exceeded` | 403 | "Has alcanzado el limite de pacientes de tu plan. Actualiza tu plan para continuar." |

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click accordion header | Click | Toggle section expand/collapse | ChevronUp/Down animation |
| Select document type | Change select | Clear + re-validate document number | Document input placeholder updates |
| Blur document number | Focus leave | Check duplicate (debounced 500ms) | Duplicate warning if found |
| Add allergy tag | Enter/comma in tag input | Tag added as chip | New chip appears with remove X |
| Remove tag | Click X on chip | Tag removed | Chip disappears |
| Click "Guardar Paciente" | Click / Enter | Validate all sections → POST | All accordions show section-level errors |
| Click "Cancelar" | Click | If dirty: confirm dialog; else navigate back | Modal or direct navigation |

### Unsaved Changes Dialog

When navigating away from a dirty form:
- "¿Salir sin guardar?" / "Los cambios no guardados se perderan." / "Cancelar" + "Salir sin guardar"

### Animations/Transitions

- Accordion expand/collapse: `motion.div` height animation 250ms
- Tag chips: scale in `0.8 → 1` on add, scale out `1 → 0` on remove with `opacity-0`
- Duplicate warning: slide in from top 200ms
- Error state on submit: all sections with errors auto-expand and scroll to first error field

---

## Loading & Error States

### Loading State
- On submit: "Guardando paciente..." button with spinner, all fields `pointer-events-none opacity-70`
- Photo upload progress: inline progress bar below drop zone

### Error State
- Per-section error indicator: red dot on accordion header
- Field errors: `text-xs text-red-600` below each field, `border-red-400` on input
- On failed submit: toast `"Error al guardar. Revisa los campos marcados."` + auto-scroll to first invalid section

### Empty State
- Not applicable (create form always renders)

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Single column. All fields full-width. Action buttons stacked (Guardar on top). Accordions start collapsed on mobile (except Section 1). |
| Tablet (640-1024px) | Two-column layout for name fields (primer/segundo nombre side-by-side). Full-width otherwise. All accordions open. |
| Desktop (> 1024px) | Two-column layout for name pairs and contact fields. Max-width container `max-w-3xl`. |

**Tablet priority:** High — receptionists register patients on clinic tablets. Touch targets min 44px. Tag chips min 36px height with min 44px touch area around X button.

---

## Accessibility

- **Focus order:** Section 1 fields top-to-bottom → accordion 1 close → Section 2 fields → ... → Submit button → Cancel
- **Screen reader:** `aria-expanded` on accordion headers. `role="list"` + `role="listitem"` on tag chips. `aria-label="Eliminar alergia: {tag}"` on chip X buttons. `role="alert"` on duplicate warning and server errors.
- **Keyboard navigation:** Enter opens/closes accordions. Backspace removes last tag in tag input. Escape cancels unsaved-changes dialog.
- **Color contrast:** WCAG AA for all field labels, error text, and tag chips.
- **Language:** All labels, placeholders, options, and errors in es-419.

---

## Design Tokens

**Colors:**
- Primary button: `bg-teal-600 hover:bg-teal-700 text-white`
- Accordion header: `bg-gray-50 hover:bg-gray-100`
- Section badge: `bg-teal-100 text-teal-700`
- Complete indicator: `text-green-500` CheckCircle2
- Error indicator: `text-red-500` dot
- Tag chips: `bg-gray-100 text-gray-700`
- Duplicate warning: `bg-amber-50 border-amber-200 text-amber-800`

**Typography:**
- Page title: `text-2xl font-bold font-inter text-gray-900`
- Accordion title: `text-base font-semibold text-gray-800`
- Labels: `text-sm font-medium text-gray-700`
- Error: `text-xs text-red-600`
- Helper/counter: `text-xs text-gray-400`

**Spacing:**
- Page container: `max-w-3xl mx-auto px-4 py-6`
- Accordion content padding: `p-6`
- Field gap: `space-y-4`
- Section gap: `space-y-3`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `@hookform/resolvers` + `zod`
- `framer-motion` — accordion, tag animations
- `lucide-react` — ChevronUp, ChevronDown, CheckCircle2, XCircle, X, Loader2
- `react-dropzone` — patient photo upload

**File Location:**
- Page: `src/app/(dashboard)/patients/new/page.tsx`
- Components: `src/components/patients/PatientForm.tsx`, `src/components/patients/sections/PersonalInfoSection.tsx`, `src/components/patients/sections/ContactSection.tsx`, `src/components/patients/sections/MedicalHistorySection.tsx`, `src/components/patients/sections/InsuranceSection.tsx`
- Shared: `src/components/ui/QuickTagInput.tsx`, `src/components/ui/AccordionSection.tsx`
- Schema: `src/lib/schemas/patient.ts`

**Hooks Used:**
- `useForm()` — React Hook Form, `mode: "onBlur"`
- `useMutation()` — create patient
- `useQuery()` — duplicate check (enabled on document blur)
- `useBeforeUnload()` — dirty state warning on tab close

---

## Test Cases

### Happy Path
1. Register complete patient
   - **Given:** Receptionist opens create form
   - **When:** Fills all required fields across all sections and clicks "Guardar Paciente"
   - **Then:** Patient created, redirect to patient detail page with success toast

### Edge Cases
1. Duplicate document number
   - **Given:** Patient with cedula 12345678 already exists
   - **When:** Receptionist enters same document number
   - **Then:** Amber warning "Ya existe un paciente..." but form still submittable

2. Change document type resets document number
   - **Given:** "Cedula" selected, number entered
   - **When:** Type changed to "Pasaporte"
   - **Then:** Number field clears, validation regex updates

### Error Cases
1. Submit with required fields missing
   - **Given:** Only Section 1 partial filled
   - **When:** "Guardar Paciente" clicked
   - **Then:** All accordions expand, error indicators on headers, first error field receives focus

2. Plan quota exceeded
   - **Given:** Free plan with 50-patient limit reached
   - **When:** Submit
   - **Then:** Error banner "Has alcanzado el limite de pacientes de tu plan."

---

## Acceptance Criteria

- [ ] 4-section accordion form, all sections open by default
- [ ] Section headers show completion/error indicators
- [ ] Document type/number pair with per-type regex validation
- [ ] Age auto-calculated from birthdate
- [ ] Duplicate document check on blur (non-blocking warning)
- [ ] QuickTag input for allergies, conditions, medications with typeahead
- [ ] Photo upload with drag-and-drop and preview
- [ ] Unsaved changes confirmation dialog on navigation
- [ ] Success → redirect to patient detail with toast
- [ ] All required errors surfaced on submit attempt
- [ ] Responsive on mobile, tablet, desktop
- [ ] Accessibility: ARIA on accordions, tags, alerts; keyboard navigation
- [ ] Spanish (es-419) throughout

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
