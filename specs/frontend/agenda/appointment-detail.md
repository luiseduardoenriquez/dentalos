# Detalle de Cita (Panel Deslizante) — Frontend Spec

## Overview

**Screen:** Appointment detail slide-in panel (side drawer on tablet/desktop, bottom sheet on mobile). Shows full appointment information: patient summary card, doctor, datetime, status badge, notes, linked clinical records, linked treatment plan items. Action buttons drive status transitions: confirm, start (in_progress), complete, cancel, no-show. Actions shown contextually based on current status and user role.

**Route:** Slide-in panel overlaying `/agenda` (no dedicated route). Also accessible at `/agenda/citas/{id}` for direct link sharing.

**Priority:** Critical

**Backend Specs:**
- `specs/appointments/AP-02` — Get appointment detail
- `specs/appointments/AP-04` — Update appointment status
- `specs/appointments/AP-05` — Cancel appointment
- `specs/appointments/AP-06` — Record no-show

**Dependencies:**
- `specs/frontend/agenda/calendar-view.md` (FE-AG-01) — parent calendar triggers this panel
- `specs/frontend/agenda/appointment-create.md` (FE-AG-02) — "Editar" opens create modal pre-filled
- `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Click appointment block in calendar view (FE-AG-01)
- Click appointment row in today-view panel (FE-AG-06)
- Click appointment row in doctor dashboard widget (FE-D-02)
- Direct URL `/agenda/citas/{id}`

**Exit Points:**
- Close panel (X button or ESC or click outside) → return to calendar
- "Ver paciente" → `/patients/{id}`
- "Editar" → open FE-AG-02 modal with appointment pre-filled
- "Abrir registro clínico" → `/patients/{id}/clinical-records/{record_id}`
- "Ver plan de tratamiento" → `/patients/{id}/treatment-plans/{plan_id}`
- Status transition actions (confirm, start, complete) → panel updates in place

**User Story:**
> As a doctor or receptionist, I want to see all appointment details at a glance and take actions (confirm, start, complete) without leaving the calendar so that I can manage patient flow efficiently.

**Roles with access:**
- clinic_owner: view + all actions
- doctor: view own appointments + confirm/start/complete/no-show
- assistant: view all + confirm/start/complete/no-show
- receptionist: view all + confirm/cancel/no-show (cannot start/complete — clinical actions)

---

## Layout Structure

```
+----------------------------------------+
|  [X]          Detalle de Cita          |
+----------------------------------------+
|  [Status Badge]  [Type Badge]          |
|                                        |
|  +---------------------------------+   |
|  | [Avatar] Nombre Paciente        |   |
|  |          Cédula | Edad | Tel    |   |
|  | [Ver perfil paciente →]         |   |
|  +---------------------------------+   |
|                                        |
|  Doctor:  [Avatar] Dr. García          |
|  Fecha:   Lun 25 Feb 2026             |
|  Hora:    09:00 – 09:30 (30 min)      |
|  Sala:    Consultorio 1               |
|                                        |
|  Notas:                               |
|  [notes text block]                   |
|                                        |
|  Registros Clínicos Vinculados:       |
|  [record chip] [record chip]          |
|                                        |
|  Plan de Tratamiento:                 |
|  [plan item chip]                     |
|                                        |
+----------------------------------------+
|  [Primary Action Button]              |
|  [Secondary actions row]             |
+----------------------------------------+
```

**Sections:**
1. Panel header — title, close button
2. Status + type badges — prominent at top
3. Patient summary card — avatar, name, document, age, phone, "Ver perfil" link
4. Appointment details — doctor, date, time, duration, room/location
5. Notes block — read-only display (editable inline on click)
6. Linked clinical records — chips with record type + date
7. Linked treatment plan item — chip with procedure name
8. Action footer — contextual primary action + secondary actions

---

## UI Components

### Component 1: AppointmentDetailPanel

**Type:** Side drawer (slide-in from right on tablet/desktop, bottom sheet on mobile)

**Animation:** Slides in from right (desktop), slides up from bottom (mobile), 250ms spring

### Component 2: StatusBadge

**Type:** Colored pill badge

**Status mapping:**

| Status | Label | Color |
|--------|-------|-------|
| `scheduled` | Programada | `bg-blue-100 text-blue-700` |
| `confirmed` | Confirmada | `bg-green-100 text-green-700` |
| `in_progress` | En consulta | `bg-teal-100 text-teal-700` |
| `completed` | Completada | `bg-gray-100 text-gray-600` |
| `cancelled` | Cancelada | `bg-red-100 text-red-600` |
| `no_show` | No asistió | `bg-amber-100 text-amber-700` |

### Component 3: AppointmentTypeBadge

**Type:** Outlined pill badge

| Type | Label | Icon |
|------|-------|------|
| `consulta` | Consulta | `Stethoscope` |
| `procedimiento` | Procedimiento | `Wrench` |
| `emergencia` | Emergencia | `AlertTriangle` (red) |
| `seguimiento` | Seguimiento | `RefreshCcw` |
| `primera_vez` | Primera vez | `UserPlus` |

### Component 4: PatientSummaryCard

**Type:** Compact card with avatar

**Content:**
- Avatar: initials-based colored circle, 48px
- Full name: `text-base font-semibold text-gray-900`
- Document number: `text-sm text-gray-500`
- Age: calculated from `birth_date`, `text-sm text-gray-500`
- Phone: with `tel:` link for one-tap calling on mobile
- "Ver perfil completo →" link in `text-primary-600 text-sm`

### Component 5: AppointmentMetaBlock

**Type:** Data display list

**Rows:** Doctor (avatar + name), Fecha (formatted `EEEE d MMM yyyy`), Hora (HH:mm – HH:mm + duration), Sala/Consultorio.
Each row: `text-sm text-gray-500 label` + `text-sm font-medium text-gray-900 value`.

### Component 6: NotesBlock

**Type:** Inline-editable text block

**Behavior:**
- Displays notes text or "Sin notas" placeholder in gray italic
- Click to edit: inline textarea with save/cancel mini-buttons
- `PATCH /api/v1/appointments/{id}` on save
- Only editable by doctor assigned + clinic_owner + assistant

### Component 7: LinkedRecordsChips

**Type:** Chip list

**Content:** Each chip shows record type icon + date. Click → navigate to record detail.
**Empty:** "Sin registros clínicos vinculados" in gray italic.

### Component 8: ActionFooter

**Type:** Sticky bottom section in panel

**Primary action (contextual by status + role):**

| Current Status | Primary Action | Button Variant | Roles |
|----------------|----------------|----------------|-------|
| `scheduled` | Confirmar cita | `success` | all |
| `confirmed` | Iniciar consulta | `primary` | doctor, assistant, clinic_owner |
| `in_progress` | Completar consulta | `success` | doctor, assistant, clinic_owner |
| `completed` | (none) | — | — |
| `cancelled` | (none) | — | — |
| `no_show` | (none) | — | — |

**Secondary actions (icon buttons row):**
- "Editar" (`Pencil` icon): opens FE-AG-02 modal — hidden if `completed`, `cancelled`, `no_show`
- "Cancelar cita" (`XCircle` icon, red): opens cancel confirmation dialog — visible if not terminal status
- "Registrar inasistencia" (`UserX` icon): only if `scheduled` or `confirmed`, not past appointment
- "Imprimir / Compartir" (`Share2` icon): generates printable appointment summary

---

## Form Fields

### Cancel Confirmation Dialog

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| cancellation_reason | select | Yes | One of predefined reasons | "Selecciona motivo" | "Motivo de cancelación" |
| notes | textarea | No | Max 300 chars | — | "Notas adicionales (opcional)" |
| notify_patient | boolean | No | — | — | — |

**Cancellation reasons (es-419):**
- `paciente_canceló` — Paciente canceló
- `doctor_canceló` — Doctor no disponible
- `emergencia` — Emergencia médica
- `reprogramación` — Reprogramada para otra fecha
- `otro` — Otro motivo

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Load appointment | `/api/v1/appointments/{id}` | GET | `specs/appointments/AP-02` | 1min |
| Confirm appointment | `/api/v1/appointments/{id}/confirm` | POST | `specs/appointments/AP-04` | none |
| Start appointment | `/api/v1/appointments/{id}/start` | POST | `specs/appointments/AP-04` | none |
| Complete appointment | `/api/v1/appointments/{id}/complete` | POST | `specs/appointments/AP-04` | none |
| Cancel appointment | `/api/v1/appointments/{id}/cancel` | POST | `specs/appointments/AP-05` | none |
| Record no-show | `/api/v1/appointments/{id}/no-show` | POST | `specs/appointments/AP-06` | none |
| Update notes | `/api/v1/appointments/{id}` | PATCH | `specs/appointments/AP-02` | none |

### State Management

**Local State (useState):**
- `isEditing: boolean` — notes inline edit mode
- `isCancelDialogOpen: boolean`
- `isActionLoading: boolean` — action button loading state

**Global State (Zustand):**
- `agendaStore.selectedAppointmentId: string | null`
- `agendaStore.panelOpen: boolean`

**Server State (TanStack Query):**
- Query key: `['appointment', appointmentId, tenantId]`
- Stale time: 1min
- On action mutation success: invalidate `['appointments', ...]` and `['appointment', appointmentId, ...]`

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Open panel | Calendar block click | Panel slides in, data loads | Skeleton while loading |
| Close panel | X button or ESC | Panel slides out | None |
| Click "Ver perfil" | Link click | Navigate to `/patients/{id}` | Navigation |
| Click "Confirmar cita" | Button click | POST /confirm, status updates | Button spinner → badge updates |
| Click "Iniciar consulta" | Button click | POST /start, status updates | Button spinner → badge turns teal |
| Click "Completar consulta" | Button click | POST /complete, status updates | Button spinner → badge turns gray |
| Click "Cancelar cita" | Icon button click | Cancel dialog opens | Dialog modal |
| Confirm cancellation | Dialog confirm | POST /cancel, panel updates | Toast "Cita cancelada" |
| Click "Registrar inasistencia" | Icon button click | Confirm dialog → POST /no-show | Toast "Inasistencia registrada" |
| Edit notes | Click notes block | Inline textarea activates | Focus on textarea |
| Save notes | Click save button | PATCH notes, re-render | "Notas guardadas" toast |

### Animations/Transitions

- Panel: slide-in from right 250ms spring (desktop), slide-up 300ms (mobile)
- Status badge: crossfade on status change (200ms)
- Primary action button: loading spinner during action submission
- Cancel dialog: fade+scale 150ms

---

## Loading & Error States

### Loading State
- Patient card: skeleton with avatar circle + 3 lines
- Meta block: 4 skeleton rows
- Notes: 2-line skeleton
- Linked records: 2 skeleton chips
- Action buttons: skeleton rectangle `h-11 w-full rounded-lg animate-pulse`

### Error State
- Load failure: "No se pudo cargar la cita. Intenta de nuevo." centered with Reintentar button
- Action failure (confirm/start/complete): toast `variant="error"` with action name + "Intenta de nuevo"
- Notes save failure: toast "Error al guardar notas" — textarea stays in edit mode

### Empty State
- No notes: italic `text-gray-400 text-sm` "Sin notas registradas. Haz clic para agregar."
- No linked records: `text-gray-400 text-sm` "Sin registros vinculados"
- No treatment plan: `text-gray-400 text-sm` "Sin plan de tratamiento vinculado"

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Bottom sheet, full width, max-height 90vh, scrollable content. Action buttons full width stacked. |
| Tablet (640-1024px) | Right side drawer, width 400px. Overlay darkens calendar. Primary device — all 44px touch targets. |
| Desktop (> 1024px) | Right side drawer, width 480px. No overlay — calendar shifts left to accommodate if pinned. |

**Tablet priority:** High — doctors read appointment details and trigger status transitions on tablets during patient visits.

---

## Accessibility

- **Focus order:** Close button → status badge → patient name → doctor → action buttons → secondary actions
- **Screen reader:** Panel has `role="dialog"` `aria-modal="true"` `aria-label="Detalle de cita"`. Status badge `aria-label="Estado: Confirmada"`. Action buttons have descriptive `aria-label` including patient name.
- **Keyboard navigation:** ESC closes panel. Tab through interactive elements. Enter activates focused action. Action confirmation dialogs trap focus.
- **Color contrast:** WCAG AA. Status badges use both color + text label. Type badges use icon + label (not color alone).
- **Language:** All labels, aria-labels, toasts in es-419.

---

## Design Tokens

**Colors:**
- Panel background: `bg-white dark:bg-gray-900`
- Panel shadow: `shadow-2xl`
- Header border: `border-b border-gray-200`
- Patient card background: `bg-gray-50 rounded-xl`
- Meta label: `text-gray-500`
- Meta value: `text-gray-900 font-medium`
- Action footer border: `border-t border-gray-200`
- Cancel button: `text-red-600 hover:bg-red-50`

**Typography:**
- Panel title: `text-lg font-bold text-gray-900`
- Patient name: `text-base font-semibold text-gray-900`
- Section headers: `text-xs font-semibold text-gray-500 uppercase tracking-wide`
- Notes text: `text-sm text-gray-700 leading-relaxed`

**Spacing:**
- Panel padding: `p-5`
- Section gap: `gap-5`
- Meta row gap: `gap-2`
- Action footer padding: `pt-4`

**Border Radius:**
- Panel: `rounded-2xl` (mobile bottom sheet), `rounded-none` (desktop drawer)
- Patient card: `rounded-xl`
- Action buttons: `rounded-lg h-11`
- Chips: `rounded-full`

---

## Implementation Notes

**Dependencies (npm):**
- `framer-motion` — panel slide animation
- `lucide-react` — X, Check, Play, CheckCircle, XCircle, UserX, Pencil, Share2, Stethoscope
- `date-fns` — date formatting
- `@tanstack/react-query` — data fetching + mutations

**File Location:**
- Component: `src/components/agenda/AppointmentDetailPanel.tsx`
- Sub-components: `src/components/agenda/PatientSummaryCard.tsx`, `src/components/agenda/AppointmentActionFooter.tsx`, `src/components/agenda/CancelAppointmentDialog.tsx`
- Hook: `src/hooks/useAppointmentActions.ts`

**Hooks Used:**
- `useAuth()` — role for conditional action rendering
- `useQuery(['appointment', id])` — detail data
- `useAppointmentActions(id)` — all status transition mutations
- `useAgendaStore()` — open/close panel state

**Permission helper:**
```typescript
function canPerformAction(action: AppointmentAction, role: UserRole, appointment: Appointment): boolean {
  const clinicalRoles = ['doctor', 'assistant', 'clinic_owner'];
  if (action === 'start' || action === 'complete') return clinicalRoles.includes(role);
  if (action === 'confirm') return true;
  if (action === 'cancel') return appointment.status !== 'completed';
  return false;
}
```

---

## Test Cases

### Happy Path
1. Doctor starts and completes appointment
   - **Given:** Appointment is `confirmed`, logged in as doctor
   - **When:** Click "Iniciar consulta" → click "Completar consulta"
   - **Then:** Status badge changes: `confirmed` → `in_progress` → `completed`. Primary action button disappears. Toast "Consulta completada."

2. Receptionist cancels appointment
   - **Given:** Appointment is `scheduled`, logged in as receptionist
   - **When:** Click cancel icon → select reason → confirm
   - **Then:** Panel updates to `cancelled` status. Toast "Cita cancelada."

### Edge Cases
1. Appointment already in terminal state
   - **Given:** Appointment is `completed`
   - **When:** Panel opens
   - **Then:** No action buttons shown. Notes still viewable. Read-only display.

2. Receptionist tries to start appointment
   - **Given:** Appointment `confirmed`, logged in as receptionist
   - **When:** Panel loads
   - **Then:** "Iniciar consulta" button not rendered for receptionist role.

### Error Cases
1. Confirm action fails with 409
   - **Given:** Appointment modified concurrently by another user
   - **When:** Click "Confirmar"
   - **Then:** Toast "La cita fue modificada por otro usuario. Recargando..." — query invalidated, panel refreshes.

---

## Acceptance Criteria

- [ ] Panel slides in from right on tablet/desktop, up from bottom on mobile
- [ ] Patient summary card with avatar, name, document, age, phone, "Ver perfil" link
- [ ] Status badge with correct color per status
- [ ] Type badge with icon and label
- [ ] Appointment meta: doctor, date, time range, duration, room
- [ ] Notes inline editing with save/cancel
- [ ] Linked clinical records chips (clickable)
- [ ] Linked treatment plan item chip (clickable)
- [ ] Contextual primary action button by status + role
- [ ] Secondary actions: edit, cancel, no-show, print
- [ ] Cancel dialog with reason select and notify toggle
- [ ] Loading skeletons for all sections
- [ ] Toast feedback for all status transitions
- [ ] Empty states for notes, records, treatment plan
- [ ] Responsive: bottom sheet mobile, drawer tablet/desktop
- [ ] Touch targets min 44px for all buttons
- [ ] Keyboard: ESC closes, Tab navigation, focus trapping in cancel dialog
- [ ] ARIA: dialog role, labels on all actions
- [ ] All labels in es-419

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
