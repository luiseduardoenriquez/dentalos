# Crear Consentimiento Informado — Frontend Spec

## Overview

**Screen:** Three-step consent creation flow. Step 1: select a consent template (built-in or custom). Step 2: preview the filled consent with patient data auto-substituted into placeholders. Step 3: choose delivery method — sign in-clinic now (opens FE-IC-03) or send to patient portal for remote signing.

**Route:** `/patients/{id}/consentimientos/nuevo`

**Priority:** High

**Backend Specs:**
- `specs/consents/IC-01` — Create consent instance from template
- `specs/consents/IC-04` — Send consent to patient portal
- `specs/consents/consent-template-list.md` — List available templates

**Dependencies:**
- `specs/frontend/consents/consent-list.md` (FE-IC-01) — returns here after creation
- `specs/frontend/consents/consent-sign.md` (FE-IC-03) — in-clinic signing target
- `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Click "Nuevo Consentimiento" in FE-IC-01 consent list
- Quick-action from patient detail (before procedure)

**Exit Points:**
- Step 3 → "Firmar ahora" → navigate to FE-IC-03 signing screen
- Step 3 → "Enviar al portal" → POST creates consent + sends portal link → return to FE-IC-01 with toast
- Cancel at any step → confirmation dialog "¿Descartar el consentimiento?" → return to FE-IC-01
- Step 3 → "Guardar borrador" → POST creates draft → return to FE-IC-01

**User Story:**
> As a doctor or assistant, I want to create a consent form by picking a template and previewing it pre-filled with patient data so that the process is fast, accurate, and legally compliant.

**Roles with access:** clinic_owner, doctor, assistant (receptionist cannot create)

---

## Layout Structure

```
+----------------------------------------------------------+
|  [← Consentimientos]  Nuevo Consentimiento Informado    |
+----------------------------------------------------------+
|                                                          |
|  [Step indicator: ●──○──○]  Paso 1 de 3                |
|                                                          |
|  Paso 1: Seleccionar Plantilla                          |
|  ┌────────────────────────────────────────┐             |
|  │ [Search: "Buscar plantilla..."]        │             |
|  │                                        │             |
|  │ Plantillas del Sistema                 │             |
|  │ ┌──────────┐ ┌──────────┐ ┌──────────┐│             |
|  │ │Extracción│ │Blanquea- │ │Ortodoncia││             |
|  │ │ Dental   │ │ miento   │ │          ││             |
|  │ └──────────┘ └──────────┘ └──────────┘│             |
|  │                                        │             |
|  │ Plantillas de la Clínica               │             |
|  │ ┌──────────┐                           │             |
|  │ │Implante  │                           │             |
|  │ │ Dental   │                           │             |
|  │ └──────────┘                           │             |
|  └────────────────────────────────────────┘             |
|                                                          |
|  [Cancelar]                    [Siguiente →]            |
+----------------------------------------------------------+
```

**Sections:**
1. Page header — back link, title
2. Step progress indicator — 3-step visual stepper
3. Step content area — changes per step
4. Footer navigation — back/cancel + next/confirm

---

## UI Components

### Component 1: StepProgressIndicator

**Type:** Visual stepper

**Content:** 3 steps with labels: "Plantilla" → "Vista previa" → "Entrega"
**States:**
- Completed step: filled circle with checkmark `bg-primary-600 text-white`
- Current step: filled circle with number `bg-primary-600 text-white` + label `font-semibold`
- Pending step: outlined circle `border-2 border-gray-300 text-gray-400` + label `text-gray-400`
- Connector line: `bg-primary-600` for completed, `bg-gray-200` for pending

### Component 2: TemplateGrid (Step 1)

**Type:** Card grid selector

**Layout:** 3 columns (tablet), 4 columns (desktop), 2 columns (mobile)

**Template Card:**
- Icon: category icon (Tooth, Syringe, Scissors, etc.) `w-8 h-8 text-primary-600`
- Title: template name `text-sm font-semibold text-gray-900`
- Category tag: `text-xs text-gray-500` (e.g., "Cirugía", "Estética", "Periodoncia")
- Source badge: "Sistema" (`bg-blue-50 text-blue-600`) or "Clínica" (`bg-teal-50 text-teal-600`)
- Click: selects template, card gets `ring-2 ring-primary-500 bg-primary-50`

**Grouping:**
- "Plantillas del Sistema" — DentalOS built-in templates (cannot be edited here)
- "Plantillas de la Clínica" — custom templates created via FE-IC-04

**Search:**
- Input filters cards client-side by name, 300ms debounce
- "Sin resultados": shows `FileSearch` icon + "No se encontraron plantillas" + "Crear nueva plantilla →" link

### Component 3: ConsentPreview (Step 2)

**Type:** Read-only rich text display with variable highlights

**Content:**
- Full consent text with patient variables substituted:
  - `{{patient_name}}` → actual patient name (bold highlight: `bg-yellow-100 px-1 rounded`)
  - `{{patient_document}}` → actual document number
  - `{{date}}` → today's date formatted
  - `{{procedure}}` → procedure name (from template or user input)
  - `{{doctor_name}}` → selected doctor
- Scroll container: `max-h-[60vh] overflow-y-auto border border-gray-200 rounded-xl p-6 bg-white`
- Language: template text in Spanish, pre-written by DentalOS legal team

**Override fields (below preview):**
- If template has optional fields: small form appears for user-supplied variables
- Example: "Nombre del procedimiento" if not auto-detected from treatment plan

**Action:** "Editar contenido" link only if this is a clinic custom template (opens inline editor — not full FE-IC-04)

### Component 4: DeliverySelector (Step 3)

**Type:** Radio card selector (large touch-friendly)

**Options:**

**Option A: "Firmar en clínica ahora"**
- Icon: `PenTool` `w-8 h-8 text-primary-600`
- Title: "Firma presencial"
- Description: "El paciente firma en este dispositivo ahora mismo."
- Badge: `bg-green-50 text-green-700` "Recomendado — más seguro"
- Select → navigates to FE-IC-03

**Option B: "Enviar al portal del paciente"**
- Icon: `Send` `w-8 h-8 text-blue-600`
- Title: "Firma remota"
- Description: "El paciente recibe un enlace por email/SMS para firmar desde su dispositivo."
- Sub-field (visible when selected): email + phone pre-filled from patient profile, editable
- Confirmation toggle: "Notificar por WhatsApp también" (if tenant has WhatsApp integration)

**Option C: "Guardar como borrador"**
- Icon: `Save` `w-8 h-8 text-gray-500`
- Title: "Guardar borrador"
- Description: "Guarda sin enviar. Puedes completarlo más tarde."

**Card style:**
- Unselected: `bg-white border-2 border-gray-200 rounded-xl`
- Selected: `bg-primary-50 border-2 border-primary-500 rounded-xl`
- Min height: 80px (56px icon area + text)

---

## Form Fields

### Step 1 — Template selection

| Field | Type | Required | Validation | Error Message |
|-------|------|----------|------------|---------------|
| template_id | card-select | Yes | Must select template | "Selecciona una plantilla para continuar" |

### Step 2 — Override variables (if template requires)

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| procedure_override | text | If template uses it | Max 200 chars | "Ingresa el nombre del procedimiento" | "Nombre del procedimiento" |
| doctor_id | select | Yes | Active doctor | "Selecciona el doctor responsable" | — |

### Step 3 — Delivery

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| delivery_method | radio | Yes | One of: in_clinic, portal, draft | "Selecciona método de entrega" | — |
| patient_email | email | If portal selected | Valid email | "Email inválido" | Patient email pre-filled |
| patient_phone | phone | No | Valid Colombian phone | — | Patient phone pre-filled |

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Load templates | `/api/v1/consent-templates?limit=100` | GET | `specs/consents/consent-template-list.md` | 10min |
| Create consent (in-clinic) | `/api/v1/consents` | POST | `specs/consents/IC-01` | none |
| Create + send to portal | `/api/v1/consents` + `/api/v1/consents/{id}/send` | POST | `specs/consents/IC-01`, `IC-04` | none |
| Save draft | `/api/v1/consents?status=draft` | POST | `specs/consents/IC-01` | none |

### State Management

**Local State (useState):**
- `currentStep: 1 | 2 | 3`
- `selectedTemplate: ConsentTemplate | null`
- `overrideVars: Record<string, string>`
- `deliveryMethod: 'in_clinic' | 'portal' | 'draft'`
- `isSubmitting: boolean`

**Global State (Zustand):**
- `authStore.user` — for doctor_id default
- `patientStore.patient` — patient data for preview substitution

**Server State (TanStack Query):**
- Query key: `['consent-templates', tenantId]` — staleTime 10min
- Mutation: `useCreateConsent()` — POST, on success navigates to FE-IC-03 (in-clinic) or FE-IC-01 (portal/draft)

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Select template card | Click | Card highlights, "Siguiente" enables | Ring animation |
| Search templates | Input | Client-side filter | Instant |
| Click "Siguiente" (Step 1) | Button click | Advance to Step 2 | Step indicator updates |
| Click "Siguiente" (Step 2) | Button click | Advance to Step 3 | Step indicator updates |
| Click "Firmar ahora" | Radio select | Delivery option selected | Card highlights |
| Click "Confirmar y Firmar" | Button click | POST create → navigate FE-IC-03 | Spinner → navigate |
| Click "Confirmar y Enviar" | Button click | POST create + send | Spinner → success toast → FE-IC-01 |
| Click "Guardar borrador" | Button click | POST draft | Spinner → toast → FE-IC-01 |
| Click "Volver" | Button click | Return to previous step | Step indicator updates |
| Click "Cancelar" | Button click | Discard confirmation dialog | Dialog |

### Animations/Transitions

- Step advance: content slides left and fades (200ms) as next step content slides in from right
- Step indicator: connector line fills with primary color, circle fills, checkmark appears
- Template card select: `ring-2 ring-primary-500` scale-up (scale(1.02), 100ms)

---

## Loading & Error States

### Loading State
- Template grid: 8 skeleton cards `animate-pulse rounded-xl h-28`
- Step 2 preview: skeleton text lines filling content area

### Error State
- Templates load failure: "Error al cargar las plantillas. Intenta de nuevo." with Reintentar
- Create failure 500: toast "Error al crear el consentimiento. Intenta de nuevo."
- Send failure (portal): toast "El consentimiento se creó pero el envío falló. Ve a la lista para reenviar."

### Empty State
- No templates at all: "Sin plantillas disponibles. Crea tu primera plantilla." with CTA → FE-IC-04
- Template category search no results: "Sin plantillas para '{query}'. Prueba otro término."

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Template grid 2 columns. Preview scrollable full-height. Delivery options stacked vertically. Step labels hidden (dots only). Footer buttons full-width stacked. |
| Tablet (640-1024px) | Template grid 3 columns. Preview in scrollable container. Delivery options as large radio cards side by side. Primary device. All 44px touch targets. |
| Desktop (> 1024px) | Template grid 4 columns. Two-panel layout on step 2: template selector left + preview right. Full delivery card labels. |

**Tablet priority:** High — consent creation happens in the clinic, at the chair, before procedures.

---

## Accessibility

- **Focus order:** Step indicator → search → template cards → Next button → (step 2) preview → override fields → Next → (step 3) delivery options → confirm/send
- **Screen reader:** Step indicator `aria-label="Paso {n} de 3: {label}"`. Template cards `role="radio"` `aria-checked="true/false"` `aria-label="{template name} — {category}"`. Preview container `aria-label="Vista previa del consentimiento informado"`. Delivery options `role="radiogroup"` with `aria-labelledby`.
- **Keyboard navigation:** Arrow keys to navigate template grid. Space/Enter to select. Tab through delivery options. Enter to confirm.
- **Color contrast:** WCAG AA. Variable highlights (yellow background) maintain adequate text contrast.
- **Language:** All labels, descriptions, button text in es-419.

---

## Design Tokens

**Colors:**
- Step connector completed: `bg-primary-600`
- Step connector pending: `bg-gray-200`
- Template card selected: `ring-2 ring-primary-500 bg-primary-50`
- Template source "Sistema": `bg-blue-50 text-blue-600`
- Template source "Clínica": `bg-teal-50 text-teal-600`
- Variable highlight: `bg-yellow-100 text-yellow-900 rounded px-1`
- Delivery card selected: `bg-primary-50 border-primary-500`

**Typography:**
- Page title: `text-xl font-bold text-gray-900`
- Step label: `text-sm font-medium` (current: `text-primary-700`, pending: `text-gray-400`)
- Template name: `text-sm font-semibold text-gray-900`
- Category: `text-xs text-gray-500`
- Preview text: `text-sm text-gray-800 leading-relaxed`
- Delivery option title: `text-base font-semibold text-gray-900`
- Delivery option description: `text-sm text-gray-500`

**Spacing:**
- Template grid gap: `gap-3`
- Template card padding: `p-4`
- Preview padding: `p-6`
- Step content padding: `py-6`
- Footer padding: `pt-4 border-t border-gray-200`

**Border Radius:**
- Template cards: `rounded-xl`
- Delivery option cards: `rounded-xl`
- Preview container: `rounded-xl`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `zod` — form validation (Step 2 + Step 3 fields)
- `@tanstack/react-query` — templates query + create mutation
- `lucide-react` — PenTool, Send, Save, Search, FileSearch, ChevronRight, ChevronLeft, Check
- `framer-motion` — step transition animations
- `date-fns` — date formatting for preview

**File Location:**
- Page: `src/app/(dashboard)/patients/[id]/consentimientos/nuevo/page.tsx`
- Components: `src/components/consents/ConsentCreateWizard.tsx`, `src/components/consents/TemplateGrid.tsx`, `src/components/consents/ConsentPreview.tsx`, `src/components/consents/DeliverySelector.tsx`
- Hook: `src/hooks/useCreateConsent.ts`

**Hooks Used:**
- `useAuth()` — user as default doctor
- `usePatient(id)` — patient data for variable substitution
- `useQuery(['consent-templates'])` — template list
- `useCreateConsent()` — POST mutation

**Variable substitution utility:**
```typescript
function substituteVars(template: string, vars: Record<string, string>): string {
  return template.replace(/\{\{(\w+)\}\}/g, (_, key) => vars[key] ?? `{{${key}}}`);
}
```

---

## Test Cases

### Happy Path
1. Doctor creates in-clinic consent in 3 steps
   - **Given:** Patient has profile, templates loaded
   - **When:** Select "CI Extracción Dental" → Next → preview looks correct → "Firmar ahora" → Confirm
   - **Then:** POST creates consent with status `pending_signature`, navigate to FE-IC-03

2. Send consent to portal
   - **Given:** Delivery method "portal" selected, patient email pre-filled
   - **When:** Click "Confirmar y Enviar"
   - **Then:** POST create + POST send, return to consent list, toast "Consentimiento enviado al paciente"

### Edge Cases
1. Template has unfilled variable
   - **Given:** Template contains `{{procedure}}` not mapped
   - **When:** Step 2 renders preview
   - **Then:** `{{procedure}}` highlighted in amber with tooltip "Campo pendiente" — input field appears below

2. Patient has no email for portal delivery
   - **Given:** Patient profile has no email
   - **When:** "Enviar al portal" selected
   - **Then:** Email field highlighted "El paciente no tiene email registrado" with input to add

### Error Cases
1. Create fails mid-flow
   - **Given:** POST /consents returns 500
   - **When:** "Confirmar y Firmar" clicked
   - **Then:** Toast error, stay on step 3, button re-enabled

---

## Acceptance Criteria

- [ ] Three-step stepper with visual progress indicator
- [ ] Step 1: template grid with system + clinic templates grouped
- [ ] Template search (client-side)
- [ ] Step 2: preview with all patient variables substituted
- [ ] Variable highlights in preview
- [ ] Step 2: optional override fields for user-supplied variables
- [ ] Step 3: three delivery options as radio cards (in-clinic, portal, draft)
- [ ] Portal option shows patient email/phone pre-filled (editable)
- [ ] Step transitions with slide animation
- [ ] "Guardar borrador" saves without sending
- [ ] Loading skeletons for template grid
- [ ] Error handling for template load and create failures
- [ ] Empty state when no templates exist
- [ ] Discard confirmation dialog on Cancel
- [ ] Responsive: 3 steps on all breakpoints
- [ ] Touch targets min 44px (template cards, delivery option cards, buttons)
- [ ] ARIA: radiogroup, step labels, card descriptions
- [ ] All labels in es-419

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
