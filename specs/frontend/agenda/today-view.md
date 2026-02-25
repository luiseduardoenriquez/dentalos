# Vista de Hoy — Frontend Spec

## Overview

**Screen:** Today's appointments quick-view panel. Vertical timeline format showing all appointments for the current day. Displays patient name, time, appointment type icon, and status pill. Real-time status tracking: waiting, in-chair, completed. Quick actions available per row: start, complete, no-show. Functions both as a sidebar widget within the calendar view and as a standalone full-page view accessible from the dashboard.

**Route:** Widget panel on `/agenda` | Standalone: `/agenda/hoy`

**Priority:** High

**Backend Specs:**
- `specs/appointments/AP-03` — List appointments (filtered to today, ordered by time)
- `specs/appointments/AP-04` — Update appointment status (start, complete)
- `specs/appointments/AP-06` — Record no-show

**Dependencies:**
- `specs/frontend/agenda/calendar-view.md` (FE-AG-01) — embeds today-view as panel mode
- `specs/frontend/agenda/appointment-detail.md` (FE-AG-03) — click appointment row opens detail
- `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Automatic: calendar loads in day view → today-view panel shows as collapsed sidebar
- Dashboard "Citas de Hoy" widget "Ver todas" → `/agenda/hoy` standalone
- Doctor dashboard next-appointment countdown "Ver agenda completa" link
- Sidebar nav "Hoy" shortcut (if configured in nav)

**Exit Points:**
- Click appointment row → opens FE-AG-03 detail slide-in
- Click patient name → `/patients/{id}`
- Toggle to full calendar → `/agenda` with today's date
- Print → generates printable daily schedule

**User Story:**
> As a doctor or assistant, I want to see today's full appointment list at a glance with real-time patient status so that I can manage patient flow efficiently during the day without clicking around.

**Roles with access:**
- clinic_owner: all doctors' appointments today
- doctor: own appointments only (default), can toggle to see clinic view
- assistant: all appointments
- receptionist: all appointments + check-in actions

---

## Layout Structure

```
--- Sidebar / Widget mode ---
+--------------------------------------------+
|  Hoy — Lunes 25 Feb   [Imprimir] [Expand] |
|--------------------------------------------|
|  [Current time indicator: 10:23 AM]        |
|                                            |
|  08:00  [●] J. Ramírez    [Consulta]  done |
|  08:30  [●] M. Torres     [Proced.]   done |
|  09:00  ─── AHORA ─────────────────────── |
|  09:30  [○] L. Castillo   [Seguim.]   prog |
|  10:00  [○] P. Mendoza    [1ra vez]   conf |
|  10:30  [·] R. Gómez      [Consulta]  wait |
|  11:00  [·] E. Flores     [Proced.]   sch  |
|  ...                                       |
|  18:00  [·] C. Vargas     [Consulta]  sch  |
|                                            |
|  [12 de 18 citas completadas]              |
+--------------------------------------------+
```

```
--- Standalone full-page mode ---
+--------+--------------------------------------------------+
|        |  Hoy: Lunes 25 de Febrero 2026                  |
|        |  [Doctor filter]  [Imprimir]  [← Calendario]    |
|        |--------------------------------------------------|
| Side-  |  MAÑANA        |  TARDE         |  NOCHE        |
|  bar   |  08:00–12:00   |  12:00–17:00   |  17:00–21:00  |
|        |  [8 citas]     |  [6 citas]     |  [4 citas]    |
|        |  [Timeline]    |  [Timeline]    |  [Timeline]   |
+--------+--------------------------------------------------+
```

**Sections (widget mode):**
1. Panel header — today's date, print shortcut, expand link
2. Current time indicator — red line at current position in timeline
3. Appointment timeline — scrolled to current time on load
4. Completion counter — "N de M citas completadas" at bottom

**Sections (full-page mode):**
1. Page header — date, doctor filter, print, back link
2. Three-column time-of-day groups: Mañana / Tarde / Noche
3. Per-column appointment timeline

---

## UI Components

### Component 1: TodayViewPanel

**Type:** Scrollable timeline list

**Behavior:**
- Auto-scrolls to current time on mount: `element.scrollIntoView({ behavior: 'smooth', block: 'center' })`
- Refetches every 60 seconds (`refetchInterval: 60000`)
- Each appointment row is clickable → FE-AG-03 detail panel

### Component 2: TimelineRow (per appointment)

**Type:** Interactive list row

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| appointment | Appointment | — | Appointment data |
| isNext | boolean | false | Highlights "next up" appointment |
| isPast | boolean | false | Dims completed/past appointments |

**Content:**
- Time: `text-sm font-mono text-gray-500 w-14 shrink-0` (e.g., "09:30")
- Status dot: colored circle `w-3 h-3 rounded-full` — see status colors below
- Patient name: `text-sm font-medium text-gray-900 truncate flex-1`
- Type icon: `w-4 h-4` with tooltip
- Status pill: compact badge `text-xs rounded-full px-2 py-0.5`
- Quick-action buttons (visible on hover/tap): appear at row right edge

**Status dot + pill colors:**

| Status | Dot | Pill |
|--------|-----|------|
| `scheduled` | `bg-gray-300` | `bg-gray-100 text-gray-600` "Prog." |
| `confirmed` | `bg-blue-400` | `bg-blue-100 text-blue-700` "Conf." |
| `in_progress` | `bg-teal-400 animate-pulse` | `bg-teal-100 text-teal-700` "En consulta" |
| `completed` | `bg-green-500` | `bg-green-100 text-green-700` "Listo" |
| `no_show` | `bg-amber-400` | `bg-amber-100 text-amber-700` "No asistió" |
| `cancelled` | `bg-red-300` | `bg-red-100 text-red-600` "Cancelada" |

**"Next up" highlight:**
- Applied to first non-completed, non-past appointment
- Row background: `bg-primary-50 border-l-4 border-primary-500`
- Label: small `text-xs text-primary-600 font-medium` "Próxima" badge

### Component 3: CurrentTimeIndicator

**Type:** Absolute-positioned red line within scrollable list

**Content:** Red horizontal line `h-0.5 bg-red-500` with small label "Ahora 09:23"
**Behavior:** Updates position every minute. Positioned between the row above and below current time.

### Component 4: QuickActionButtons

**Type:** Action button group (visible on hover/focus for each row)

**Actions (contextual by status + role):**

| Status | Available actions | Roles |
|--------|-----------------|-------|
| `scheduled` / `confirmed` | Iniciar (▶), No asistió (✗) | doctor, assistant, clinic_owner |
| `confirmed` | Check-in (✓) | receptionist, assistant |
| `in_progress` | Completar (✓) | doctor, assistant, clinic_owner |
| `completed` / `cancelled` / `no_show` | Ver detalle | all |

**Button style:** `h-8 w-8 rounded-full` icon buttons, `bg-white border border-gray-200 hover:bg-gray-50`
**Tap target:** Entire row triggers detail panel; action buttons are distinct targets with 44px spacing

### Component 5: CompletionCounter

**Type:** Progress bar + label

**Content:**
- Label: "8 de 18 citas completadas"
- Thin progress bar: `bg-green-500` fill proportional to completion ratio
- Sub-label: "3 en consulta | 7 pendientes" in `text-xs text-gray-500`

### Component 6: DoctorFilterChips (standalone mode only)

**Type:** Horizontal chip group (same pattern as FE-AG-01)

**Behavior:** Filters timeline to show only selected doctor. "Todos" chip default.

---

## Form Fields

Not applicable — today-view is a read/action screen. Status transition actions use direct API calls (no form).

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Load today's appointments | `/api/v1/appointments?date={today}&doctor_id={if doctor}&order=scheduled_at:asc` | GET | `specs/appointments/AP-03` | 1min |
| Start appointment | `/api/v1/appointments/{id}/start` | POST | `specs/appointments/AP-04` | none |
| Complete appointment | `/api/v1/appointments/{id}/complete` | POST | `specs/appointments/AP-04` | none |
| No-show | `/api/v1/appointments/{id}/no-show` | POST | `specs/appointments/AP-06` | none |

### State Management

**Local State (useState):**
- `activeDoctorId: string | null` — filter (full-page mode only)
- `actionLoadingId: string | null` — which row is processing an action

**Global State (Zustand):**
- `authStore.user.role` — determines visible actions and default filter
- `authStore.user.id` — for doctor's own filter default

**Server State (TanStack Query):**
- Query key: `['appointments', 'today', tenantId, doctorId]`
- Stale time: 1min
- Refetch interval: 60000ms (1 minute) for real-time status updates
- Mutation: `useStartAppointment(id)`, `useCompleteAppointment(id)`, `useNoShowAppointment(id)` — each invalidates the today query on success

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click appointment row | Click | Opens FE-AG-03 detail panel | Row highlights, panel slides in |
| Click patient name | Click (name link) | Navigate to `/patients/{id}` | Navigation |
| Click "Iniciar" quick-action | Button click | POST /start, status updates | Button spinner → dot turns teal+pulse |
| Click "Completar" quick-action | Button click | POST /complete, status updates | Button spinner → dot turns green |
| Click "No asistió" | Button click | Confirm dialog → POST /no-show | Dialog confirm → dot turns amber |
| Print | "Imprimir" button | Opens print layout | Browser print dialog |
| Auto-scroll on load | Mount | List scrolls to current time | Smooth scroll |
| Expand to full page | "Expand" icon | Navigate to `/agenda/hoy` | Page transition |

### Animations/Transitions

- Status dot: crossfade color + pulse animation for `in_progress`
- "Next up" row: appears with `bg-primary-50` highlight, subtle fade-in
- Quick-action buttons: fade-in on row hover/focus
- Completion bar: width transition 300ms ease-out on status change
- Auto-scroll: smooth scroll behavior on mount

---

## Loading & Error States

### Loading State
- Timeline: 10 skeleton rows — `animate-pulse` with: `w-10 h-3 rounded` (time), `w-3 h-3 rounded-full` (dot), `w-32 h-3 rounded` (name), `w-12 h-5 rounded-full` (badge)
- Completion counter: skeleton progress bar

### Error State
- Load failure: centered in panel "Error al cargar las citas de hoy." with `RefreshCcw` icon and "Reintentar" button
- Action failure (start/complete/no-show): toast `variant="error"` "Error al actualizar la cita. Intenta de nuevo."

### Empty State
- **Illustration:** Lucide `CalendarCheck` icon `w-12 h-12 text-gray-300`
- **Message:** "Sin citas para hoy"
- **Sub-text:** "Disfruta tu día libre o agenda una cita."
- **CTA:** "Nueva Cita" → opens FE-AG-02

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Full-page mode default (no sidebar widget on mobile — too small). Single column. Quick-action buttons always visible (no hover). Fixed current-time label. |
| Tablet (640-1024px) | Widget mode in calendar sidebar (280px wide). Single timeline column. Touch-optimized row height (52px min). Primary use case for doctors. |
| Desktop (> 1024px) | Widget mode OR full-page with 3-column time-of-day layout. Hover reveals quick-actions. |

**Tablet priority:** High — doctors use this panel between patients to see what's next and trigger status updates without touching the calendar.

---

## Accessibility

- **Focus order:** Panel header controls → appointment rows (top to bottom) → completion counter
- **Screen reader:** List has `role="list"`. Each row `role="listitem"` with `aria-label="{time} — {patient} — {type} — Estado: {status}"`. Status dot `aria-hidden="true"` (status conveyed by pill text). Quick-action buttons `aria-label="Iniciar cita de {patient}"`.
- **Keyboard navigation:** Tab through rows. Enter opens FE-AG-03 for focused row. Arrow keys navigate between rows. Action buttons focusable within row with Tab.
- **Color contrast:** WCAG AA. Status pills use color + text. "In progress" animation does not convey information alone — pill label "En consulta" used.
- **Language:** All labels, toasts, aria-labels in es-419.

---

## Design Tokens

**Colors:**
- Panel background: `bg-white dark:bg-gray-900`
- Row default: `bg-white hover:bg-gray-50`
- Row "next up": `bg-primary-50 border-l-4 border-l-primary-500`
- Row completed: `opacity-60`
- Row cancelled: `opacity-40`
- Current time line: `bg-red-500`
- Current time label: `text-red-600 text-xs font-medium`
- Completion bar: `bg-green-500`
- Completion bar track: `bg-gray-100`

**Typography:**
- Time: `text-sm font-mono text-gray-500 w-14`
- Patient name: `text-sm font-medium text-gray-900`
- Status pill: `text-xs font-medium rounded-full px-2 py-0.5`
- Counter label: `text-sm text-gray-600`
- Sub-counter: `text-xs text-gray-500`

**Spacing:**
- Row height: `min-h-[52px]` (tablet), `min-h-[44px]` (desktop)
- Row padding: `px-3 py-2`
- Row gap: `gap-2` (horizontal elements)
- Panel padding: `p-3`

**Border Radius:**
- Status pills: `rounded-full`
- Quick-action buttons: `rounded-full`
- Panel: `rounded-xl` (widget mode)

---

## Implementation Notes

**Dependencies (npm):**
- `lucide-react` — Play, Check, UserX, Stethoscope, Wrench, AlertTriangle, RefreshCcw, CalendarCheck, Printer, Expand
- `@tanstack/react-query` — data fetching with refetch interval
- `date-fns` — time formatting (format, isToday)
- `framer-motion` — status dot transition

**File Location:**
- Widget: `src/components/agenda/TodayViewPanel.tsx`
- Full-page: `src/app/(dashboard)/agenda/hoy/page.tsx`
- Row component: `src/components/agenda/TimelineRow.tsx`
- Completion counter: `src/components/agenda/DayCompletionCounter.tsx`

**Hooks Used:**
- `useAuth()` — role, user ID for filter default
- `useTodayAppointments(doctorId?)` — custom hook with refetch interval
- `useAppointmentActions()` — start/complete/no-show mutations
- `useAutoScroll(currentTimeRef)` — scrollIntoView on mount

**Refetch interval note:** 60-second polling is intentional. WebSocket real-time push is a future enhancement (see ADR-006 offline sync). Polling is sufficient for V1 — status updates from quick-actions immediately invalidate the query without waiting for the interval.

---

## Test Cases

### Happy Path
1. Doctor sees daily timeline, auto-scrolled to current time
   - **Given:** 12 appointments today, current time 10:30
   - **When:** Navigate to `/agenda/hoy`
   - **Then:** Timeline loads, auto-scrolls to 10:30 position, "next up" highlight on 10:30 appointment, 4 completed appointments dimmed

2. Receptionist marks patient as started
   - **Given:** Patient arrived, appointment is `confirmed`
   - **When:** Click "Iniciar" quick-action on row
   - **Then:** POST /start fires, dot turns teal+pulse, pill changes to "En consulta"

### Edge Cases
1. Two appointments at same time (double-booking)
   - **Given:** Two appointments at 09:00 (different doctors)
   - **When:** Timeline renders
   - **Then:** Both rows shown at 09:00 position, stacked with clear separation

2. All appointments completed
   - **Given:** Last appointment completed at 17:00
   - **When:** Today view renders
   - **Then:** Completion bar at 100%, counter "18 de 18 completadas", "next up" highlight absent, no current-time line shown

### Error Cases
1. Status update fails with stale data
   - **Given:** Appointment already completed by doctor, receptionist tries to also mark complete
   - **When:** POST /complete returns 409
   - **Then:** Toast "La cita ya fue marcada como completada." — query refetched, row updates to completed state.

---

## Acceptance Criteria

- [ ] Vertical timeline of today's appointments sorted by time
- [ ] Auto-scroll to current time position on load
- [ ] Current time red indicator line with "Ahora" label
- [ ] "Next up" highlight on first non-complete appointment
- [ ] Status dot + pill for each appointment (all 6 statuses)
- [ ] Type icon per appointment type
- [ ] Quick-action buttons: Iniciar, Completar, No asistió (contextual by status + role)
- [ ] Confirmation dialog for no-show action
- [ ] Click row → opens FE-AG-03 detail panel
- [ ] Click patient name → navigate to patient profile
- [ ] Completion counter with progress bar
- [ ] Auto-refetch every 60 seconds
- [ ] Doctor filter in standalone mode (full-page)
- [ ] Print action opens browser print dialog with clean layout
- [ ] Loading skeletons for timeline rows
- [ ] Error state with retry button
- [ ] Empty state when no appointments
- [ ] Responsive: widget mode tablet/desktop, full-page mobile
- [ ] Touch targets min 44px (row height, action buttons)
- [ ] ARIA: list role, listitem, action button labels
- [ ] All labels in es-419

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
