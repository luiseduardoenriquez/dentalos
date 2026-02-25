# Mi Plan de Tratamiento — Portal del Paciente (Portal Treatment Plans) — Frontend Spec

## Overview

**Screen:** Patient-facing treatment plan viewer in portal. Shows plan cards with progress bars. Click to expand procedure list with cost breakdown. "Approve" button for pending plans triggers a signature flow (canvas pad for legal consent).

**Route:** `/portal/[clinicSlug]/treatment-plans`

**Priority:** High

**Backend Specs:** `specs/portal/PP-04.md`, `specs/portal/PP-05.md`

**Dependencies:** `specs/frontend/portal/portal-dashboard.md`, `specs/frontend/portal/portal-consent-sign.md`

---

## User Flow

**Entry Points:**
- "Ver plan" from portal dashboard treatment plan card
- "Mi plan de tratamiento" in portal navigation

**Exit Points:**
- "Approve" plan → signature flow → `/portal/[clinicSlug]/treatment-plans/{id}/approve`
- Signature submitted → back to treatment plans list
- "← Inicio" → portal dashboard

**User Story:**
> As a patient, I want to see what procedures my doctor planned for me and how much each one costs so that I can understand my treatment and approve it before work begins.

**Roles with access:** patient (portal session)

---

## Layout Structure

```
+------------------------------------------+
|  [Navbar]                                 |
+------------------------------------------+
|  ← Inicio     Mi Plan de Tratamiento     |
|                                           |
|  +--------------------------------------+ |
|  | Ortodoncia Completa          Activo  | |
|  | Dr. Carlos López                    | |
|  | ████████░░░░░░░░ 3 de 8 pasos       | |
|  | Costo total: $4.800.000             | |
|  | [Ver detalle ▼]                     | |
|  |                                     | |
|  |  (expanded):                        | |
|  |  ✓ Examen inicial          $200.000 | |
|  |  ✓ Radiografías            $150.000 | |
|  |  ✓ Limpieza preortodoncia  $120.000 | |
|  |  ○ Colocación de brackets  $800.000 | |
|  |  ○ Control 1               $200.000 | |
|  |    ...                              | |
|  +--------------------------------------+ |
|                                           |
|  +--------------------------------------+ |
|  | Restauraciones Pendientes  Pendiente | |
|  | Dra. María Ruiz                     | |
|  | ○ 0 de 4 pasos                      | |
|  | Costo estimado: $1.200.000          | |
|  | Estado: Pendiente de aprobación      | |
|  | [Aprobar plan]                      | |
|  +--------------------------------------+ |
+------------------------------------------+
```

**Sections:**
1. Page header — back link, title
2. Treatment plan cards — one per plan; expandable; with progress bar
3. Expanded view — procedures list with status icons and costs
4. Approval CTA (if plan status = pending approval)

---

## UI Components

### Component 1: TreatmentPlanCard

**Type:** Expandable card (accordion)

**States:**
- Collapsed: plan name, status badge, doctor, progress bar, total cost, "Ver detalle" toggle
- Expanded: all collapsed info + procedure list

**Progress bar:**
- Fill: `bg-primary-500`
- Track: `bg-gray-200`
- Width calculated: `(completed / total) * 100%`
- Label: "N de M pasos completados" (plain language, not "procedimientos")

**Status badges:**

| Status | Label | Color |
|--------|-------|-------|
| active | Activo | green |
| pending_approval | Pendiente de aprobación | orange |
| completed | Completado | blue |
| on_hold | En pausa | gray |

**"Ver detalle" toggle:** Chevron icon rotates 180° on expand.

### Component 2: ProcedureList

**Type:** Ordered list (inside expanded card)

**Per item:**
- Status icon: ✓ (green, completed), ○ (gray, pending), ● (primary, in progress)
- Procedure name (patient-friendly language, max 40 chars)
- Cost (right-aligned): "$200.000"

**Cost subtotal:** Sum of completed procedures / total cost at bottom.

**Patient language mapping:**
- "Extracción" → "Extracción de diente"
- "Endodoncia" → "Tratamiento del nervio"
- "Corona" → "Colocación de corona"
(Mapping from backend `patient_label` field; fallback to `name`)

### Component 3: ApprovePlanSection

**Type:** Highlighted call-to-action section (inside card, visible when status=pending_approval)

**Content:**
- Info box: "Tu doctor preparó este plan de tratamiento para ti. Para comenzar, necesitas aprobarlo."
- Cost summary: total estimated cost
- "Aprobar y firmar plan" button (primary)

**Approval flow:** Clicking "Aprobar y firmar" navigates to `portal-consent-sign.md` flow adapted for treatment plan approval signature.

---

## Form Fields

No form fields on list page. Signature form is in the consent-sign screen.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| List treatment plans | `/api/v1/portal/treatment-plans` | GET | `specs/portal/PP-04.md` | 2min |
| Get plan detail | `/api/v1/portal/treatment-plans/{id}` | GET | `specs/portal/PP-04.md` | 2min |
| Initiate approval | `/api/v1/portal/treatment-plans/{id}/approve/initiate` | POST | `specs/portal/PP-05.md` | — |

### State Management

**Local State (useState):**
- `expandedPlanId: string | null` — which plan is expanded

**Global State (Zustand):**
- `portalStore.patient`

**Server State (TanStack Query):**
- Query key: `['portal-treatment-plans', patientId]` — stale 2min
- Detail fetched on expand: `['portal-treatment-plan', planId]`

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click "Ver detalle" | Tap card | Expands/collapses procedure list | Chevron rotates, list animates in |
| Click "Aprobar y firmar plan" | Tap button | Navigate to approval/signature flow | Standard navigation |
| Only one plan | — | Plan auto-expanded on page load | — |

### Animations/Transitions

- Card expand: height animate from 0 to full (200ms, framer-motion AnimatePresence)
- Progress bar: fills from left on first render (600ms, CSS transition)
- Status icon for completed: green tick with slight scale-in (150ms)

---

## Loading & Error States

### Loading State
- 2 skeleton plan cards (collapsed height)

### Error State
- "Error al cargar tu plan de tratamiento. Intenta de nuevo."

### Empty State
- No treatment plans: illustration + "Tu doctor aún no ha creado un plan de tratamiento para ti." + "Si tienes preguntas, escríbenos" link → messages

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Full-width cards. Procedure list text slightly smaller. Cost amounts right-aligned. "Aprobar y firmar" full-width button. |
| Tablet+ | Cards max-width 600px, centered. Same layout. |

---

## Accessibility

- **Focus order:** Plan cards in order (collapsed). On expand: procedure items, approve button.
- **Screen reader:** `aria-expanded` on card toggle button. Progress bar: `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-label="Progreso: 3 de 8 pasos completados"`. Procedure status icons: `aria-label="Completado"` or `aria-label="Pendiente"`.
- **Keyboard navigation:** Enter to expand/collapse card. Tab through procedure items and approve button.
- **Language:** Patient-friendly procedure names. es-419.

---

## Design Tokens

**Colors:**
- Plan card border active: `border-primary-200`
- Progress bar: `bg-primary-500`
- Completed step icon: `text-green-500`
- Pending step icon: `text-gray-300`
- In-progress step icon: `text-primary-500`
- Pending approval banner: `bg-orange-50 border-orange-200`

**Spacing:**
- Between plan cards: `space-y-4`
- Procedure list item: `py-2`
- Card padding: `p-4`

---

## Implementation Notes

**File Location:**
- Page: `src/app/(portal)/[clinicSlug]/treatment-plans/page.tsx`
- Components: `src/components/portal/TreatmentPlanCard.tsx`, `src/components/portal/ProcedureList.tsx`, `src/components/portal/ApprovePlanSection.tsx`
- Hooks: `src/hooks/usePortalTreatmentPlans.ts`

---

## Test Cases

### Happy Path
1. View active plan
   - **Given:** Patient has active "Ortodoncia Completa" plan with 3/8 completed
   - **When:** Navigates to treatment plans
   - **Then:** Card shows progress bar at 37.5%, "3 de 8 pasos completados", cost

2. Approve pending plan
   - **Given:** "Restauraciones" plan has status pending_approval
   - **When:** Patient taps "Aprobar y firmar plan"
   - **Then:** Navigates to signature/approval screen

### Edge Cases
1. Plan with no cost (free consultation)
   - **Given:** Plan has $0 total
   - **When:** Card renders
   - **Then:** Cost row shows "Costo a confirmar con tu doctor" instead of $0

### Error Cases
1. Plan load failure
   - **Given:** Backend error
   - **When:** Page loads
   - **Then:** Error card with retry button

---

## Acceptance Criteria

- [ ] Treatment plan cards with plan name, status badge, doctor, progress bar, cost
- [ ] Progress bar: animated fill, "N de M pasos completados" label (patient language)
- [ ] Expandable procedure list per card with status icons and costs
- [ ] Patient-friendly procedure labels (from backend `patient_label` field)
- [ ] Pending approval card: info box + "Aprobar y firmar plan" button
- [ ] Single plan auto-expanded on load
- [ ] Loading skeletons
- [ ] Empty state with messages link
- [ ] Error state with retry
- [ ] Responsive: mobile-first, max-width centered
- [ ] Accessibility: aria-expanded, progress bar ARIA, keyboard
- [ ] Non-clinical language, es-419

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
