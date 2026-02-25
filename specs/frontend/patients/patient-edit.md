# Editar Paciente (Patient Edit) — Frontend Spec

## Overview

**Screen:** Edit patient form. Same four-section accordion layout as patient creation, but pre-filled with existing data. The document number field is immutable (read-only). Changed fields are visually highlighted with a yellow left border. Each section has its own "Guardar cambios" button to enable partial saves without requiring the user to save all sections at once.

**Route:** `/patients/{id}/edit`

**Priority:** High

**Backend Specs:** `specs/patients/patient-update.md` (P-04)

**Dependencies:** `specs/frontend/patients/patient-detail.md`, `specs/frontend/patients/patient-create.md`

---

## User Flow

**Entry Points:**
- "Editar" button on patient detail page (`/patients/{id}`)
- Direct URL navigation

**Exit Points:**
- "Volver al perfil" button → `/patients/{id}` (patient detail)
- Breadcrumb "Pacientes > {Nombre}" → patient detail
- After any section save → stay on edit page, success inline indicator per section

**User Story:**
> As a receptionist | doctor | assistant, I want to update a patient's information so that their profile stays current without losing any existing data.

**Roles with access:** `clinic_owner`, `doctor`, `assistant`, `receptionist`

---

## Layout Structure

```
+--------------------------------------------------+
|  Sidebar | Breadcrumb: Pacientes > {Nombre} > Editar |
|          +---------------------------------------+
|          |  "Editando: {Nombre Paciente}"        |
|          |  [Volver al perfil btn]               |
|          +---------------------------------------+
|          |                                       |
|          |  [Accordion 1: Informacion Personal]  |
|          |  [Save section 1 button]              |
|          |                                       |
|          |  [Accordion 2: Contacto]              |
|          |  [Save section 2 button]              |
|          |                                       |
|          |  [Accordion 3: Antecedentes Medicos]  |
|          |  [Save section 3 button]              |
|          |                                       |
|          |  [Accordion 4: Seguro / Convenio]     |
|          |  [Save section 4 button]              |
|          |                                       |
+------------------------------------------+-------+
```

**Sections:**
1. Page header — breadcrumb, patient name subtitle, back button
2. Four accordion sections, each with individual save button at bottom
3. Changed field highlighting — yellow left border on modified inputs

---

## UI Components

### Component 1: DirtyFieldHighlight

**Type:** Visual diff indicator

**Behavior:**
- When a field's current value differs from the originally loaded value, apply: `border-l-4 border-l-amber-400 bg-amber-50/30 rounded-r-md` on the field wrapper
- Yellow left border appears immediately on keystroke — not on blur
- Cleared when: field value returns to original value OR section is saved
- Section accordion header shows a yellow dot badge when any field in section is dirty: `w-2 h-2 rounded-full bg-amber-400`

### Component 2: SectionSaveButton

**Type:** Button (per section)

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| isDirty | boolean | false | Shows save button only when section has changes |
| isSaving | boolean | false | Loading state for this specific section |
| isSuccess | boolean | false | Brief success state after save |

**Behavior:**
- Button hidden (`invisible` to preserve layout) when section has no dirty fields
- Button visible when `isDirty === true`: `text-sm text-teal-600 border border-teal-300 hover:bg-teal-50 rounded-lg px-4 py-2`
- On click: validates section schema → PATCH → success state
- Success state: button briefly shows `CheckCircle2` icon + "Guardado" for 2 seconds, then reverts to hidden
- Saving state: "Guardando..." + `Loader2 animate-spin` icon

### Component 3: ImmutableDocumentField

**Type:** Read-only input with explanation

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.3

**Visual:** `bg-gray-50 text-gray-500 border-gray-200 cursor-not-allowed` with `LockKeyhole` icon at right
**Tooltip on hover/focus:** "El numero de documento no puede modificarse una vez creado el paciente. Contacta soporte si hay un error."
**aria-readonly:** `"true"`, `aria-describedby` pointing to tooltip text

---

## Form Fields

### Section 1: Informacion Personal

Identical fields to `patient-create.md` Section 1, except:
- `numero_documento` — read-only (immutable), `LockKeyhole` icon
- `tipo_documento` — read-only (immutable)
- `foto_paciente` — shows current photo thumbnail; "Cambiar foto" link opens replace flow; "Eliminar foto" red link

**Photo management:**
- Current photo: `w-20 h-20 rounded-full object-cover` thumbnail
- "Cambiar foto" → opens drop zone overlay to replace photo
- "Eliminar foto" → confirmation: "¿Eliminar la foto del paciente?" → DELETE `/api/v1/patients/{id}/photo`

### Section 2: Informacion de Contacto

Same as create. All fields editable and pre-filled.

### Section 3: Antecedentes Medicos

Same as create. Tag inputs pre-populated with existing tags.
- Existing tags rendered as chips on mount
- User can add new tags or click X to remove existing ones
- Removed tags tracked as `removedTags` in local state for PATCH payload

### Section 4: Seguro / Convenio

Same as create. All fields editable and pre-filled.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Load patient | `/api/v1/patients/{id}` | GET | `specs/patients/patient-get.md` | 5min |
| Save section (partial update) | `/api/v1/patients/{id}` | PATCH | `specs/patients/patient-update.md` | None |
| Replace photo | `/api/v1/patients/{id}/photo` | POST (multipart) | `specs/patients/patient-photo.md` | None |
| Delete photo | `/api/v1/patients/{id}/photo` | DELETE | `specs/patients/patient-photo.md` | None |

### PATCH Payload Strategy

Each section save sends only the changed fields (not the full patient object):

```typescript
// Section 1 PATCH example
{
  primer_nombre: "Carlos",
  telefono_principal: "+57 300 000 1234"
  // only fields that changed from original
}
```

**Changed field detection:** On mount, store original values in `originalData` ref. On section save, compute diff: `const patch = Object.fromEntries(Object.entries(currentValues).filter(([k, v]) => v !== originalData[k]))`

### State Management

**Local State (useState):**
- `originalData: PatientData | null` — snapshot on mount for diff comparison
- `sectionDirty: Record<1|2|3|4, boolean>` — dirty state per section
- `sectionSaving: Record<1|2|3|4, boolean>` — saving state per section
- `sectionError: Record<1|2|3|4, string | null>` — per-section error

**Global State (Zustand):**
- Invalidate `['patient', id]` in query cache after any section save

**Server State (TanStack Query):**
- Query: `useQuery({ queryKey: ['patient', id] })` to load initial data
- Mutation: one `useMutation` per section (or a single mutation with section context)

### Error Code Mapping

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `validation_error` | 422 | "Verifica los campos marcados en esta seccion." |
| `patient_not_found` | 404 | "El paciente no fue encontrado." |
| `document_immutable` | 400 | "El documento no puede modificarse." |
| `photo_too_large` | 413 | "La foto no puede superar 5MB." |

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Modify any field | Keystroke / select | Yellow highlight on field, dirty indicator on section header, section save button appears | Immediate visual diff |
| Return field to original value | Keystroke | Yellow highlight removed, section save button hides if no other dirty fields | Real-time |
| Click section "Guardar cambios" | Click | Validate section → PATCH with changed fields only | Section save button shows "Guardando..." → "Guardado" |
| Multiple sections dirty simultaneously | — | Each section save button visible independently | User can save in any order |
| Click "Volver al perfil" | Click | If any section dirty: confirm dialog; else navigate | Modal or direct navigation |
| Click "Cambiar foto" | Click | Drop zone overlay appears | Overlay animation |
| Click "Eliminar foto" | Click | Confirmation dialog | Modal |

### Unsaved Changes on Navigation

If any section is dirty when user clicks "Volver al perfil":
- Dialog: "Tienes cambios sin guardar en {section names}. ¿Salir de todas formas?"
- "Cancelar" — stay on edit page
- "Salir sin guardar" — navigate to patient detail

### Animations/Transitions

- Dirty field highlight: `transition-all duration-150` on border-left color
- Section save button appearance: `motion.div` fade in `opacity-0 → opacity-100` 200ms
- Success state on section save button: scale check icon `0 → 1` with `text-green-600`
- Accordion collapse/expand: same 250ms height animation as create page

---

## Loading & Error States

### Loading State
- Initial load: skeleton for all form fields (same dimensions as real inputs) with `animate-pulse`
- Section save: per-section save button shows spinner, that section's inputs `opacity-70`
- Other sections remain fully interactive during any section save

### Error State
- Per-section error: `bg-red-50 border-red-200` banner at bottom of accordion content, above save button
- Field errors: `text-xs text-red-600` below field + red left border replacing yellow
- Photo upload error: inline below drop zone

### Empty State
- Not applicable — form always has data from existing patient

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Accordions start collapsed (user expands to edit). Section save button full-width at accordion bottom. Photo management below photo thumbnail. |
| Tablet (640-1024px) | All accordions open. Two-column for name pairs. Section save button right-aligned. |
| Desktop (> 1024px) | Two-column layout for multiple field groups. Max width `max-w-3xl`. |

**Tablet priority:** High. Touch targets min 44px. Tag chip X remove buttons min 36px with expanded touch area.

---

## Accessibility

- **Focus order:** Same as create page per section. After section save, focus returns to section save button area with announcement "Seccion guardada exitosamente" via `aria-live="polite"`.
- **Screen reader:** `aria-label="Campo modificado"` on dirty field wrappers. Immutable document field announces "No editable" in aria-label. Section dirty badge announced as "Seccion con cambios sin guardar".
- **Keyboard navigation:** Tab navigates fields. Enter on section save button triggers save. Escape dismisses confirmation dialog.
- **Color contrast:** Yellow highlight `bg-amber-50` with `border-l-amber-400` meets contrast with input text. Error red meets WCAG AA.
- **Language:** All labels and messages in es-419.

---

## Design Tokens

**Colors:**
- Dirty field border: `border-l-4 border-l-amber-400`
- Dirty field background: `bg-amber-50/30`
- Section dirty indicator: `bg-amber-400` dot
- Section save button: `border-teal-300 text-teal-600 hover:bg-teal-50`
- Section save success: `text-green-600`
- Immutable field: `bg-gray-50 text-gray-500 border-gray-200`
- Primary back button: `text-gray-600 border border-gray-300 hover:bg-gray-50`

**Typography:**
- Page subtitle: `text-lg font-semibold text-gray-700` "Editando: {Nombre}"
- Labels: `text-sm font-medium text-gray-700`
- Immutable note: `text-xs text-gray-400`

**Spacing:**
- Page container: `max-w-3xl mx-auto px-4 py-6`
- Section save button margin: `mt-4 flex justify-end`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `@hookform/resolvers` + `zod`
- `framer-motion` — section save button animations
- `lucide-react` — LockKeyhole, CheckCircle2, Loader2, X

**File Location:**
- Page: `src/app/(dashboard)/patients/[id]/edit/page.tsx`
- Components: `src/components/patients/PatientEditForm.tsx`, `src/components/patients/SectionSaveButton.tsx`, `src/components/patients/DirtyFieldWrapper.tsx`
- Schema: `src/lib/schemas/patient.ts` (same as create, minus immutable fields)

**Hooks Used:**
- `useForm()` per section with `defaultValues` from patient query result
- `useWatch()` — detect dirty fields by comparing to original values snapshot
- `useMutation()` — one per section or single with section context
- `useQuery(['patient', id])` — load initial values

**Diff Logic:**
```typescript
const useSectionDiff = (current: object, original: object) => {
  return useMemo(
    () => Object.fromEntries(
      Object.entries(current).filter(([k, v]) => v !== original[k as keyof typeof original])
    ),
    [current, original]
  );
};
```

---

## Test Cases

### Happy Path
1. Edit phone number and save section
   - **Given:** Patient edit page loaded with existing patient data
   - **When:** Receptionist changes phone number in Section 2, clicks "Guardar cambios"
   - **Then:** PATCH sent with only `telefono_principal`, success indicator shown, query cache invalidated

### Edge Cases
1. Revert field to original value
   - **Given:** Doctor changes patient first name, sees yellow highlight
   - **When:** Doctor types back the original name exactly
   - **Then:** Yellow highlight removed, section save button disappears

2. Two sections dirty simultaneously
   - **Given:** Sections 1 and 3 both have dirty fields
   - **When:** User saves Section 1 first
   - **Then:** Section 1 saved successfully, Section 3 save button remains visible

3. Attempt to modify document number via DevTools
   - **Given:** Input is read-only disabled
   - **When:** PATCH sent with `numero_documento` field
   - **Then:** Backend returns 400 `document_immutable`, UI shows error

### Error Cases
1. Section save validation fails
   - **Given:** Phone changed to invalid format
   - **When:** "Guardar cambios" clicked for contact section
   - **Then:** Inline field error, no API call, section error banner

2. Network error during section save
   - **Given:** Connection lost during PATCH
   - **When:** Section save button clicked
   - **Then:** Per-section error banner "Error al guardar. Intenta de nuevo.", button re-enabled

---

## Acceptance Criteria

- [ ] Form pre-filled with existing patient data on load
- [ ] Document number is read-only with lock icon and tooltip
- [ ] Changed fields show yellow left border highlight immediately
- [ ] Section accordion headers show dirty indicator dot when fields modified
- [ ] Each section has independent "Guardar cambios" button, visible only when dirty
- [ ] Section save button shows loading → success states
- [ ] PATCH sends only changed fields (not full object)
- [ ] Photo: view current, replace, or delete with confirmation
- [ ] Unsaved changes dialog when navigating away with dirty sections
- [ ] Per-section error states without affecting other sections
- [ ] Responsive on mobile, tablet, desktop
- [ ] Accessibility: ARIA on dirty fields, focus management after save
- [ ] Spanish (es-419) throughout

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
