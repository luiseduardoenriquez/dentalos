# Mis Citas — Portal del Paciente (Portal Appointments) — Frontend Spec

## Overview

**Screen:** Patient appointments view in portal. Upcoming appointments as actionable cards (confirm/cancel). Past appointments as a simple chronological list. "Agendar nueva cita" CTA visible at top.

**Route:** `/portal/[clinicSlug]/appointments`

**Priority:** High

**Backend Specs:** `specs/portal/PP-03.md`, `specs/portal/PP-08.md`, `specs/portal/PP-09.md`

**Dependencies:** `specs/frontend/portal/portal-dashboard.md`, `specs/frontend/portal/public-booking.md`

---

## User Flow

**Entry Points:**
- "Ver cita" from portal dashboard next appointment card
- "Mis citas" in portal navigation
- Appointment reminder SMS/email link

**Exit Points:**
- "Agendar nueva cita" → `/portal/[clinicSlug]/book`
- Cancel appointment → confirmation modal → stays on page
- "Volver" → portal dashboard

**User Story:**
> As a patient, I want to see my upcoming and past appointments so that I can confirm, cancel, or book new ones from my phone.

**Roles with access:** patient (portal session)

---

## Layout Structure

```
+------------------------------------------+
|  [Navbar]                                 |
+------------------------------------------+
|  ← Inicio     Mis Citas                  |
|                                           |
|  [Agendar nueva cita]                     |
|                                           |
|  PRÓXIMAS CITAS                           |
|  +--------------------------------------+ |
|  | Martes 3 de marzo • 10:00 AM        | |
|  | Dr. Carlos López                    | |
|  | Revisión General • Consultorio 2    | |
|  | ● Confirmada                        | |
|  | [Confirmar]  [Cancelar cita]        | |
|  +--------------------------------------+ |
|                                           |
|  +--------------------------------------+ |
|  | Viernes 15 de marzo • 3:00 PM       | |
|  | Dra. María Ruiz                     | |
|  | Limpieza dental                     | |
|  | ○ Pendiente de confirmar            | |
|  | [Confirmar asistencia]  [Cancelar]  | |
|  +--------------------------------------+ |
|                                           |
|  CITAS PASADAS                            |
|  • 10 Feb 2026 — Extracción — Dr. López  |
|  • 15 Ene 2026 — Revisión — Dra. Ruiz   |
|                                           |
+------------------------------------------+
```

**Sections:**
1. Page header — back link, title "Mis Citas"
2. Book new appointment CTA button
3. Upcoming appointments section — cards with actions
4. Past appointments section — simple list

---

## UI Components

### Component 1: UpcomingAppointmentCard

**Type:** Card with action buttons

**Content:**
- Date + time (formatted: "Martes 3 de marzo de 2026 • 10:00 AM")
- Doctor name (plain — "Dr. Carlos López")
- Appointment type (non-clinical: "Revisión general", "Limpieza", "Consulta de dolor")
- Location: office/room if multi-room clinic
- Confirmation status indicator:
  - Confirmed: green dot + "Confirmada"
  - Pending: orange dot + "Pendiente de confirmar"
  - Today: pulsing red dot + "¡Tu cita es HOY!"

**Action buttons:**
- "Confirmar asistencia" (primary, shown when not confirmed)
- "✓ Confirmada" (green, disabled, shown when already confirmed)
- "Cancelar cita" (ghost/destructive, shown when appointment is ≥ 24h away)
- No cancel button if < 24h to appointment (policy)

### Component 2: CancelAppointmentModal

**Type:** Dialog modal (bottom sheet on mobile)

**Trigger:** "Cancelar cita" button

**Content:**
- Warning: "¿Seguro que quieres cancelar tu cita?"
- Appointment summary: date, time, doctor
- Cancellation policy note: "Recuerda que puedes cancelar hasta 24 horas antes sin problema."
- Reason for cancellation (optional): select dropdown (me siento mejor, conflicto de agenda, costo, otra razón)
- "Sí, cancelar cita" (destructive) + "No, mantener cita" (secondary) buttons

### Component 3: PastAppointmentsList

**Type:** Simple timeline list

**Item content:**
- Date (dd MMM yyyy)
- Appointment type
- Doctor name
- Status: "Atendida" or "Cancelada" badge

**No pagination (load more on scroll):** Virtual scroll or "Cargar más" button after 10 items.

---

## Form Fields

No form fields — action buttons only. Cancel modal has optional reason dropdown.

| Field | Type | Required | Options |
|-------|------|----------|---------|
| cancel_reason | Select | No | me_siento_mejor, conflicto_agenda, costo, otra_razon |

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| List upcoming | `/api/v1/portal/appointments?status=upcoming` | GET | `specs/portal/PP-03.md` | 2min |
| List past | `/api/v1/portal/appointments?status=past` | GET | `specs/portal/PP-03.md` | 5min |
| Confirm appointment | `/api/v1/portal/appointments/{id}/confirm` | PATCH | `specs/portal/PP-08.md` | — |
| Cancel appointment | `/api/v1/portal/appointments/{id}/cancel` | POST | `specs/portal/PP-09.md` | — |

### State Management

**Local State (useState):**
- `cancelModalAppointmentId: string | null`
- `confirmingId: string | null`

**Global State (Zustand):**
- `portalStore.patient`

**Server State (TanStack Query):**
- Query key: `['portal-appointments-upcoming', patientId]` — stale 2min
- Query key: `['portal-appointments-past', patientId]` — stale 5min
- Mutation: `confirmAppointment` — optimistic update: immediately change button state
- Mutation: `cancelAppointment` — on success: remove card from upcoming list (animated), add to past

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Confirm attendance | Button click | PATCH confirm; optimistic update | Button → "✓ Confirmada" immediately |
| Cancel appointment | Button click | Open cancel modal | Bottom sheet slides up |
| Select cancel reason | Dropdown | Reason stored in form state | Dropdown updates |
| Confirm cancellation | "Sí, cancelar" | POST cancel; remove card | Card fades out (300ms) → success toast "Cita cancelada" |
| Dismiss cancel modal | "No, mantener" or backdrop | Modal closes | No change |
| Tap "Agendar nueva cita" | Button | Navigate to public booking | Standard navigation |
| Load more past | Button or scroll | Fetch next page of past appointments | Loading spinner below list |

### Animations/Transitions

- Upcoming cards: stagger fade in on load (100ms, 50ms delay each)
- Cancelled card removal: fade out + height collapse (300ms)
- Confirmation button state change: color transition (200ms)
- Cancel modal: slide up from bottom on mobile (250ms)

---

## Loading & Error States

### Loading State
- Upcoming appointments: 2 skeleton cards (card height ~110px)
- Past appointments list: 5 skeleton list items

### Error State
- Load failure: error card in each section with "Error al cargar tus citas. Reintentar."
- Confirm failure: toast "No se pudo confirmar tu cita. Intenta de nuevo." Button reverts.
- Cancel failure: toast "No se pudo cancelar. Intenta de nuevo." Modal closes.

### Empty State
- No upcoming appointments: card with calendar icon + "No tienes citas próximas" + "Agendar cita" button
- No past appointments: "Aún no tienes historial de citas." (no CTA needed)

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Full-width cards, single column. Cancel modal = bottom sheet (full width, rounded top). "Agendar" CTA full width. Past appointments list compact (date + type only, doctor on second line). |
| Tablet (640-1024px) | Cards max-width 560px, centered. Modal centered dialog. Past list shows all columns. |
| Desktop (> 1024px) | Portal stays centered/narrow. Same as tablet. |

---

## Accessibility

- **Focus order:** "Agendar nueva cita" → upcoming cards (confirm button, cancel button per card) → past list items
- **Screen reader:** Each upcoming card: `aria-label="Cita el {date} a las {time} con {doctor}. Estado: {status}"`. Confirm button: `aria-busy` during confirm. Cancel modal: `role="alertdialog"`.
- **Keyboard navigation:** Tab through cards. Enter on buttons. Escape to close modal.
- **Color contrast:** Today indicator (red pulse) uses both color and text "HOY". Confirmed green dot has text label.
- **Language:** Non-clinical appointment type names. es-419 throughout.

---

## Design Tokens

**Colors:**
- Confirmed status: `text-green-600` + green dot
- Pending status: `text-orange-500` + orange dot
- Today status: `text-red-600` + pulsing red dot
- Cancel button: `text-red-600 border-red-200 hover:bg-red-50`
- Past appointment item: `text-gray-600`
- Section heading: `text-xs font-semibold text-gray-400 uppercase tracking-wider`

**Typography:**
- Appointment date: `text-base font-bold text-gray-900`
- Doctor name: `text-sm font-medium text-gray-700`
- Appointment type: `text-sm text-gray-500`
- Past item: `text-sm text-gray-600`

**Spacing:**
- Between upcoming cards: `gap-4`
- Card padding: `p-4`
- Section header margin: `mt-6 mb-3`

---

## Implementation Notes

**Dependencies (npm):**
- `@tanstack/react-query` — data fetching
- `@radix-ui/react-dialog` — cancel modal
- `lucide-react` — Calendar, CheckCircle, Clock, X, Plus
- `date-fns` — `format`, `isSameDay`, `differenceInHours` with es locale
- `framer-motion` — card animations

**File Location:**
- Page: `src/app/(portal)/[clinicSlug]/appointments/page.tsx`
- Components: `src/components/portal/UpcomingAppointmentCard.tsx`, `src/components/portal/CancelAppointmentModal.tsx`, `src/components/portal/PastAppointmentsList.tsx`
- Hooks: `src/hooks/usePortalAppointments.ts`

**Cancel eligibility check:**
```typescript
function canCancel(appointment: Appointment): boolean {
  const hoursUntil = differenceInHours(new Date(appointment.datetime), new Date());
  return hoursUntil >= 24;
}
```

---

## Test Cases

### Happy Path
1. Confirm upcoming appointment
   - **Given:** Upcoming appointment with status "pending"
   - **When:** Patient taps "Confirmar asistencia"
   - **Then:** Button immediately changes to "✓ Confirmada" (optimistic), PATCH sent in background

2. Cancel appointment
   - **Given:** Appointment is 3 days away
   - **When:** Patient taps "Cancelar cita" → selects reason → "Sí, cancelar"
   - **Then:** Card fades out, toast "Cita cancelada". Appointment appears in past list as "Cancelada".

### Edge Cases
1. Appointment in < 24 hours
   - **Given:** Appointment is tomorrow morning (18 hours away)
   - **When:** Appointments page loads
   - **Then:** "Cancelar cita" button not shown. Card shows "¡Tu cita es MAÑANA!" style urgency.

### Error Cases
1. Confirm while offline
   - **Given:** Patient has no network
   - **When:** Taps confirm
   - **Then:** Toast "Sin conexión. Confirma cuando tengas internet." Button reverts to original state.

---

## Acceptance Criteria

- [ ] Upcoming appointments: cards with date/time, doctor, type, confirmation status
- [ ] Confirm button: PATCH confirm with optimistic update
- [ ] Today indicator: pulsing red dot + "HOY" text
- [ ] Cancel button visible only when ≥ 24h to appointment
- [ ] Cancel modal: reason dropdown (optional), confirmation dialog
- [ ] Successful cancel: card removed (animated), added to past list
- [ ] Past appointments: simple list with date, type, doctor, status
- [ ] Empty state for no upcoming appointments with "Agendar cita" CTA
- [ ] "Agendar nueva cita" button at top
- [ ] Loading skeletons
- [ ] Error states with retry
- [ ] Responsive: bottom sheet mobile, centered modal tablet/desktop
- [ ] Non-clinical appointment type names
- [ ] Accessibility: aria-labels, focus order, keyboard navigation
- [ ] Spanish (es-419) labels

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
