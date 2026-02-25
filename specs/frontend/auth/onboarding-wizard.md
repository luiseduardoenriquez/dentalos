# Asistente de Configuracion Inicial (Onboarding Wizard) — Frontend Spec

## Overview

**Screen:** Post-registration 4-step onboarding wizard for new clinic owners. Guides through clinic setup, first doctor profile, odontogram preferences, and optional patient import. Each step can be skipped. Progress is persisted so the wizard can be resumed.

**Route:** `/onboarding`

**Priority:** High

**Backend Specs:** `specs/tenants/tenant-onboarding.md` (T-10), `specs/auth/register.md` (A-01)

**Dependencies:** `specs/frontend/auth/register.md`, `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Automatic redirect after successful registration at `/register`
- Manual access via notification banner in dashboard if onboarding incomplete
- Resume via `/onboarding?step={1|2|3|4}` if partially completed

**Exit Points:**
- Complete all steps → redirect to `/dashboard` with success toast
- Skip any step → advance to next step (step is marked skipped in DB)
- Skip entire wizard (link at bottom) → redirect to `/dashboard`
- Navigate away mid-wizard → progress saved, resume banner shown in dashboard

**User Story:**
> As a clinic_owner completing registration, I want a guided setup so that my clinic is fully configured and ready to use in under 10 minutes.

**Roles with access:** `clinic_owner` only. Redirect non-owners to `/dashboard`.

---

## Layout Structure

```
+--------------------------------------------------+
|  DentalOS Logo (left) | "Omitir configuracion" link (right) |
+--------------------------------------------------+
|                                                  |
|    [Progress indicator: Step X of 4]             |
|    [Step title + subtitle]                       |
|                                                  |
|   +------------------------------------------+  |
|   |                                          |  |
|   |           Step Content Area              |  |
|   |                                          |  |
|   +------------------------------------------+  |
|                                                  |
|   [Atras btn (hidden step 1)] [Omitir] [Siguiente / Finalizar btn] |
|                                                  |
+--------------------------------------------------+
```

**Sections:**
1. Top bar — logo, "Omitir configuracion" link
2. Progress indicator — step number, horizontal step dots, current step title
3. Step content area — varies per step (see below)
4. Navigation row — back, skip step, continue/finish buttons

---

## UI Components

### Component 1: StepProgressIndicator

**Type:** Progress tracker

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.10

**Visual:** 4 numbered circles connected by lines.
- Completed: `bg-teal-600 text-white` with checkmark icon
- Current: `bg-teal-600 text-white` with step number, pulsing ring `ring-2 ring-teal-300`
- Upcoming: `bg-gray-200 text-gray-500`
- Connecting lines: `h-0.5 flex-1` — `bg-teal-600` for completed segments, `bg-gray-200` for upcoming

**Step labels (below circles):**

| Step | Label |
|------|-------|
| 1 | Tu Clinica |
| 2 | Tu Perfil |
| 3 | Odontograma |
| 4 | Pacientes |

### Component 2: StepContentCard

**Type:** Card container per step

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.4

**Animation:** Slide-in from right for forward navigation, from left for back: `motion.div initial={{ x: direction * 40, opacity: 0 }} animate={{ x: 0, opacity: 1 }}` 250ms ease-out.

### Component 3: NavigationRow

**Type:** Button group

**Buttons:**
- "Atras" — `variant="outline"` `text-gray-600 border-gray-300`, hidden on step 1
- "Omitir este paso" — `variant="ghost" text-sm text-gray-500`, always visible
- "Siguiente" / "Finalizar" — `variant="primary" bg-teal-600`, right-aligned

---

## Step Specifications

### Step 1: Datos de la Clinica

**Form Fields:**

| Field | Type | Required | Validation | Error Message (es-419) | Placeholder |
|-------|------|----------|------------|------------------------|-------------|
| nombre_clinica | text | Yes | Min 3, max 100 chars | "El nombre de la clinica es obligatorio" | "Ej: Clinica Dental Sonrisa" |
| nit | text | Yes (if Colombia) | Format: `{9 digits}-{1 check digit}` | "NIT invalido. Formato: 900123456-7" | "900123456-7" |
| direccion | text | No | Max 200 chars | — | "Calle 80 # 12-34, Bogota" |
| telefono | tel | Yes | E.164 format | "Ingresa un numero de telefono valido" | "+57 1 234 5678" |
| logo | file | No | JPEG/PNG/WebP, max 2MB, min 100x100px | "Imagen invalida. Maximo 2MB, formato JPG o PNG" | — |

**Logo Upload Component:**
- Drag-and-drop zone: `border-2 border-dashed border-gray-300 rounded-xl p-8 text-center`
- Hover: `border-teal-400 bg-teal-50`
- Preview: circular crop `w-24 h-24 rounded-full object-cover` shown after selection
- Remove button: `XCircle` icon overlay on preview
- Accepts: `image/jpeg, image/png, image/webp`

**Zod Schema:**
```typescript
const step1Schema = z.object({
  nombre_clinica: z.string().min(3).max(100),
  nit: z.string().regex(/^\d{9}-\d$/, "NIT invalido. Formato: 900123456-7").optional(),
  direccion: z.string().max(200).optional(),
  telefono: z.string().regex(/^\+?[1-9]\d{6,19}$/),
  logo: z.instanceof(File).optional(),
});
```

---

### Step 2: Perfil del Primer Doctor

**Context note:** This creates the clinic_owner's doctor profile (or a first additional doctor if owner is admin-only).

**Form Fields:**

| Field | Type | Required | Validation | Error Message (es-419) | Placeholder |
|-------|------|----------|------------|------------------------|-------------|
| nombre_doctor | text | Yes | Min 3, max 100 chars | "El nombre es obligatorio" | "Dr. Juan Garcia" |
| especialidad | select | Yes | From predefined list | "Selecciona una especialidad" | "Seleccionar especialidad" |
| numero_registro | text | Yes | Alphanumeric, max 30 chars | "Numero de registro obligatorio" | "RETHUS: 12345678" |
| firma_digital | file | No | PNG with transparency, max 1MB | "Imagen de firma invalida" | — |

**Especialidad options:**
- Odontologia General
- Ortodoncia
- Endodoncia
- Periodoncia
- Cirugia Oral y Maxilofacial
- Odontopediatria
- Rehabilitacion Oral
- Radiologia Oral

**Firma Digital Upload:** Same drag-and-drop pattern as logo. Shows white-background preview with `border border-gray-200 rounded-lg p-2`.

---

### Step 3: Configuracion del Odontograma

**Visual preference selector, not a standard form:**

**Odontogram Mode Selection:**

| Option | Preview | Description |
|--------|---------|-------------|
| Clasico | Grid of labeled squares (FDI numbers) | "Vista de cuadricula con numeracion FDI. Rapido y familiar." |
| Anatomico | Tooth shape SVG thumbnails | "Representacion anatomica de cada diente. Mas visual." |

**UI Pattern:** Two large selectable cards side by side.
- Selected card: `border-2 border-teal-600 bg-teal-50 ring-2 ring-teal-200`
- Unselected: `border-2 border-gray-200 bg-white hover:border-teal-300`
- Each card: preview image/SVG thumbnail (120px) + mode name + description

**Condition Colors (Palette Customization):**
- Displays 6 key condition types: Caries, Extraccion, Endodoncia, Corona, Ausente, Tratamiento
- Each has a color swatch (circle, 32px) that opens a color picker on click
- Default colors pre-filled from design system tokens
- "Usar colores predeterminados" reset link

**Color picker:** Native `<input type="color">` wrapped in custom UI, `h-8 w-8 rounded-full cursor-pointer border-2 border-white shadow`

---

### Step 4: Importar Pacientes

**Import options — two cards:**

**Option A: Importar desde CSV/Excel**
- File drop zone (same pattern as logo upload)
- Accepts: `.csv`, `.xlsx`, `.xls`
- Max size: 10MB
- After selection: shows filename + row count preview "Archivo listo: {name} ({n} filas detectadas)"
- "Mapear columnas" button → triggers column mapping modal (simplified inline version)
- Column mapping table: detected columns on left, DentalOS fields on right (dropdown per row)
- Required fields highlighted: Nombre, Documento

**Option B: Omitir por ahora**
- Large outlined card with `PlusCircle` icon + "Agrega pacientes manualmente cuando lo necesites"
- Click selects this option as the chosen action

**State machine:**
- `idle` — two option cards displayed
- `file_selected` — Option A card highlighted, file name shown, mapping button visible
- `mapping` — column mapping inline table visible
- `ready` — validation summary: "X pacientes listos para importar"

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Save step 1 (clinic) | `/api/v1/tenants/onboarding/clinic` | POST | `specs/tenants/tenant-onboarding.md` | None |
| Save step 2 (doctor) | `/api/v1/tenants/onboarding/doctor` | POST | `specs/tenants/tenant-onboarding.md` | None |
| Save step 3 (odontogram config) | `/api/v1/tenants/onboarding/config` | POST | `specs/tenants/tenant-onboarding.md` | None |
| Import patients | `/api/v1/patients/import` | POST (multipart) | `specs/patients/patient-import.md` | None |
| Get onboarding status | `/api/v1/tenants/onboarding/status` | GET | `specs/tenants/tenant-onboarding.md` | 1min |

### State Management

**Local State (useState):**
- `currentStep: 1 | 2 | 3 | 4`
- `direction: 1 | -1` — for animation direction
- `stepData: Record<1|2|3|4, object>` — accumulated form data
- `isSubmitting: boolean`
- `serverError: string | null`

**Global State (Zustand):**
- `onboardingStore.completedSteps: Set<number>` — persisted to localStorage
- `onboardingStore.skippedSteps: Set<number>`

**Server State (TanStack Query):**
- Query: `useQuery(['onboarding-status'])` on mount to resume progress
- Mutations per step: `useMutation` for each step save

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click "Siguiente" | Button | Validate current step → save → advance | Spinner on button, then slide to next step |
| Click "Atras" | Button | Navigate to previous step | Slide animation left |
| Click "Omitir este paso" | Button | Mark step skipped → advance | Step circle shows dashed outline |
| Click "Omitir configuracion" | Top link | Confirm dialog → redirect to dashboard | Modal: "¿Seguro? Puedes completarlo despues." |
| Drop file in zone | Drag-drop or click | File selected, preview shown | Filename + check icon |
| Click odontogram mode | Card | Mode selected | Card highlighted with teal border |
| Click "Finalizar" (step 4) | Button | Submit all pending data → redirect | Full-page success animation |

### Skip Confirmation Dialog

When user clicks "Omitir configuracion" (full wizard skip):
- Modal with: "¿Salir de la configuracion?"
- Body: "Tu progreso hasta aqui se ha guardado. Puedes completar la configuracion desde el panel principal."
- Buttons: "Cancelar" (secondary) | "Salir de todas formas" (primary, teal)

### Animations/Transitions

- Step transition forward: `x: 40 → 0, opacity: 0 → 1` 250ms
- Step transition back: `x: -40 → 0, opacity: 0 → 1` 250ms
- Progress circles: completed step animates checkmark icon scale `0 → 1` 200ms
- Finish: confetti-like particle animation (CSS `@keyframes`) + large checkmark for 1.5s, then redirect

---

## Loading & Error States

### Loading State
- On "Siguiente" click: button shows "Guardando..." + spinner, form disabled
- Resuming wizard (onboarding status query): skeleton for step content area `h-64 animate-pulse bg-gray-100 rounded-xl`

### Error State
- Per-step API error: banner `bg-red-50 border-red-200` above navigation row
- Field validation: inline `text-xs text-red-600` below each field
- File upload error (size/format): inline error below drop zone

### Empty State
- Step 4 with no file selected: two option cards displayed, neither selected — "Siguiente" is labeled "Finalizar sin importar" if user hasn't selected Option A

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Progress circles show only numbers, labels hidden. Odontogram mode cards stack vertically. Navigation buttons full-width stacked. |
| Tablet (640-1024px) | `max-w-2xl` centered card. Odontogram cards side by side. All fields full-width. |
| Desktop (> 1024px) | `max-w-3xl` centered. Two-column layout for some step fields (name + phone side by side). |

**Tablet priority:** High — clinic owners frequently set up on iPad. Touch targets min 44px. Logo upload touch target min 80x80px.

---

## Accessibility

- **Focus order:** Follows visual top-to-bottom, left-to-right within each step form. Navigation buttons at bottom: Atras → Omitir → Siguiente/Finalizar.
- **Screen reader:** `aria-current="step"` on current progress circle. `role="group"` + `aria-label="Paso X de 4: {titulo}"` wrapping each step form. `aria-live="polite"` for step transitions. Odontogram mode cards use `role="radio"` + `aria-checked`.
- **Keyboard navigation:** Tab within step. Arrow keys for odontogram mode selection. Enter submits / advances step.
- **Color contrast:** WCAG AA for all text. Progress circles meet 4.5:1 on teal background.
- **Language:** All labels, step titles, descriptions, and error messages in es-419.

---

## Design Tokens

**Colors:**
- Progress — complete: `bg-teal-600`; current ring: `ring-teal-300`; upcoming: `bg-gray-200`
- Primary button: `bg-teal-600 hover:bg-teal-700 text-white`
- Secondary button: `border border-gray-300 text-gray-600 bg-white hover:bg-gray-50`
- Ghost: `text-gray-500 hover:text-gray-700`
- Drop zone default: `border-gray-300`; hover: `border-teal-400 bg-teal-50`
- Card selected: `border-teal-600 bg-teal-50`

**Typography:**
- Step title: `text-2xl font-bold font-inter text-gray-900`
- Step subtitle: `text-sm text-gray-500`
- Labels: `text-sm font-medium text-gray-700`
- Helper text: `text-xs text-gray-400`

**Spacing:**
- Page container: `max-w-2xl lg:max-w-3xl mx-auto px-4 py-8`
- Step card padding: `p-6 md:p-8`
- Field gap: `space-y-5`
- Navigation row margin: `mt-8 pt-6 border-t border-gray-100`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `@hookform/resolvers` + `zod`
- `framer-motion` — step slide animations, finish confetti
- `lucide-react` — CheckCircle2, ChevronLeft, ChevronRight, Upload, X, Loader2
- `react-dropzone` — file drag-and-drop zones

**File Location:**
- Page: `src/app/(public)/onboarding/page.tsx`
- Components: `src/components/onboarding/OnboardingWizard.tsx`, `src/components/onboarding/StepProgress.tsx`, `src/components/onboarding/steps/Step1Clinic.tsx`, `src/components/onboarding/steps/Step2Doctor.tsx`, `src/components/onboarding/steps/Step3Odontogram.tsx`, `src/components/onboarding/steps/Step4Patients.tsx`
- Store: `src/stores/onboardingStore.ts`

**Hooks Used:**
- `useForm()` per step with separate Zod schemas
- `useMutation()` per step for API save
- `useQuery(['onboarding-status'])` on mount
- `useRouter()` — redirect on finish
- `useOnboardingStore()` — Zustand store for step progress

**Resume Logic:**
- On mount, fetch `/api/v1/tenants/onboarding/status`
- Response includes `{ completed_steps: number[], skipped_steps: number[], current_step: number }`
- Set `currentStep` to `response.current_step`
- Pre-fill form values from any previously saved step data

---

## Test Cases

### Happy Path
1. Complete all 4 steps
   - **Given:** New clinic_owner just registered
   - **When:** Completes each step and clicks "Siguiente" / "Finalizar"
   - **Then:** Clinic configured, doctor created, odontogram set, redirect to `/dashboard`

### Edge Cases
1. Resume interrupted wizard
   - **Given:** Owner completed steps 1-2 and closed browser
   - **When:** Navigates back to `/onboarding`
   - **Then:** Wizard opens at step 3, steps 1-2 show checkmarks

2. Skip all steps
   - **Given:** Owner clicks "Omitir este paso" on all 4 steps
   - **When:** Reaches end
   - **Then:** Redirect to `/dashboard`, banner "Completa la configuracion de tu clinica" shown

3. Invalid NIT format
   - **Given:** Owner enters "900123456" (missing check digit)
   - **When:** Field blurs or Siguiente clicked
   - **Then:** Inline error "NIT invalido. Formato: 900123456-7"

### Error Cases
1. Logo file too large
   - **Given:** Owner drops a 5MB PNG in Step 1
   - **When:** File is dropped
   - **Then:** Inline error "Imagen invalida. Maximo 2MB, formato JPG o PNG" — file rejected

2. API error on step save
   - **Given:** Network error on "Siguiente" in step 2
   - **When:** Mutation fails
   - **Then:** Error banner "No se pudo guardar. Intenta de nuevo.", button re-enabled

---

## Acceptance Criteria

- [ ] 4-step wizard with progress indicator
- [ ] Step 1: clinic name, NIT, address, phone, logo upload with preview
- [ ] Step 2: doctor name, specialty dropdown, license number, signature upload
- [ ] Step 3: odontogram mode selection (classic/anatomic) + condition color customization
- [ ] Step 4: CSV/Excel import option or skip-for-now option
- [ ] Each step has independent Zod validation
- [ ] "Omitir este paso" advances without validation
- [ ] "Omitir configuracion" shows confirmation dialog then redirects to dashboard
- [ ] Progress saved between steps and resumable
- [ ] Slide animations between steps
- [ ] Responsive on mobile, tablet, desktop
- [ ] Accessibility: ARIA step labels, keyboard navigation, focus management between steps
- [ ] Spanish (es-419) labels throughout
- [ ] Touch targets minimum 44px

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
