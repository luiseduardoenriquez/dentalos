# Vista de Calendario (Agenda) — Frontend Spec

## Overview

**Screen:** Main calendar/agenda view for scheduling and managing appointments. Supports day, week, and month views. Default is daily view. Color-coded by appointment type and status. Supports drag-and-drop rescheduling and multi-doctor column layout in week mode. Clicking an empty slot triggers the 3-tap appointment creation flow.

**Route:** `/agenda`

**Priority:** Critical

**Backend Specs:**
- `specs/appointments/AP-03` — List appointments (with date/doctor filters)
- `specs/appointments/AP-11` — Update appointment datetime (drag-drop reschedule)
- `specs/appointments/AP-02` — Get appointment detail
- `specs/appointments/AP-01` — Create appointment

**Dependencies:**
- `specs/frontend/agenda/appointment-create.md` (FE-AG-02) — create modal triggered from empty slot click
- `specs/frontend/agenda/appointment-detail.md` (FE-AG-03) — detail panel triggered from appointment click
- `specs/frontend/agenda/today-view.md` (FE-AG-06) — compact today panel in sidebar
- `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Sidebar navigation "Agenda"
- Dashboard widget "Ver todas" link
- Notification redirect for appointment reminders
- Direct URL `/agenda`, `/agenda?date=2026-03-15`, `/agenda?view=week`

**Exit Points:**
- Click appointment → opens FE-AG-03 detail slide-in
- Click empty slot → opens FE-AG-02 create modal (3-tap flow)
- Drag appointment → reposition (inline reschedule)
- Navigate to patient from appointment detail card
- Settings → doctor schedule → `/settings/schedule`

**User Story:**
> As a receptionist or doctor, I want to see all appointments in a visual calendar so that I can manage the daily schedule, detect conflicts, and quickly reschedule or book new appointments.

**Roles with access:** clinic_owner (all doctors), doctor (own schedule + full read), assistant (full read + write), receptionist (full read + write)

---

## Layout Structure

```
+--------+----------------------------------------------------------+
|        |  Header: "Agenda" | [Hoy] [< >] [Day|Week|Month] [+ Nueva Cita] |
|        +----------------------------------------------------------+
|        |  Doctor filter chips: [Todos] [Dr. García] [Dra. López]  |
| Side-  +----------------------------------------------------------+
|  bar   |                                                          |
|        |  TIME  |  DR. GARCIA  |  DRA. LOPEZ  |  DR. MORENO     |
|        |  08:00 |              |              |                  |
|        |  08:30 | [Cita Block] |              |                  |
|        |  09:00 | [Cita Block] | [Cita Block] |                  |
|        |  09:30 |              | [Cita Block] |                  |
|        |  10:00 |   empty slot |              | [Cita Block]     |
|        |  ...   |              |              |                  |
|        |  18:00 |              |              |                  |
+--------+----------------------------------------------------------+
```

**Sections:**
1. Calendar toolbar — title, navigation arrows, view mode tabs, "Nueva Cita" primary button
2. Doctor filter row — horizontal chips to show/hide individual doctors
3. Time grid — scrollable vertical timeline (day/week) or month grid
4. Appointment blocks — color-coded, draggable event cards
5. Current time indicator — red horizontal line showing current time in day/week view

---

## UI Components

### Component 1: CalendarToolbar

**Type:** Sticky toolbar

**Design System Ref:** `frontend/design-system/design-system.md` Section 4

**Content:**
- Page title: "Agenda" (`text-xl font-bold text-gray-800`)
- Navigation: `< Anterior` | date label (e.g., "Lunes 25 Feb 2026") | `Siguiente >`
- "Hoy" button: returns to current date, `variant="outline"`
- View mode tabs: `[Día] [Semana] [Mes]` — active tab `bg-primary-600 text-white`
- "+ Nueva Cita" button: `variant="primary"`, `h-11 px-4`, triggers FE-AG-02 modal

### Component 2: DoctorFilterChips

**Type:** Horizontal scrollable chip group

**Content:**
- "Todos los doctores" chip (default selected): shows all columns
- Per-doctor chip with avatar color indicator and name
- Selected state: `bg-primary-100 border-primary-600 text-primary-700`
- Unselected: `bg-white border-gray-200 text-gray-600`
- Min touch target: 44px height, `rounded-full px-4 py-2`

### Component 3: TimeGrid (Day / Week View)

**Type:** Scrollable grid with CSS Grid or custom layout

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| view | "day" \| "week" \| "month" | "day" | Active view mode |
| date | Date | today | Focal date |
| doctors | Doctor[] | all | Visible doctor columns |
| appointments | Appointment[] | [] | Events to render |

**Behavior:**
- Day view: single column timeline from 07:00–21:00, 30-min slot rows (h-10 per 30min)
- Week view: 7 columns × time rows; multi-doctor stacks within each day column
- Month view: standard month grid, appointment dots per day, click day → day view
- Empty slot click: opens FE-AG-02 with pre-filled date/time/doctor
- Scroll position persists per session (restore to current time on reload)
- Current time red line updates every 60 seconds via `setInterval`

### Component 4: AppointmentBlock

**Type:** Draggable event card

**Color coding by type:**
- `consulta`: `bg-blue-100 border-l-4 border-blue-500 text-blue-900`
- `procedimiento`: `bg-green-100 border-l-4 border-green-500 text-green-900`
- `emergencia`: `bg-red-100 border-l-4 border-red-500 text-red-900`
- `seguimiento`: `bg-gray-100 border-l-4 border-gray-400 text-gray-700`
- `primera_vez`: `bg-purple-100 border-l-4 border-purple-500 text-purple-900`

**Status overlay:**
- `scheduled`: no overlay
- `confirmed`: `✓` checkmark icon (top-right, `text-xs`)
- `in_progress`: pulsing green dot
- `completed`: `opacity-60` + strikethrough on name
- `cancelled`: `opacity-40 line-through`
- `no_show`: `opacity-40 bg-gray-50 border-gray-300`

**Content:** Patient name (truncated), procedure type icon, time range (`08:30–09:00`)
**Min height:** 40px (1 slot). Taller appointments scale proportionally.
**Drag handle:** Entire block is draggable. On drag start → ghost card at original position.

### Component 5: DragDropContext

**Type:** Logic wrapper (react-beautiful-dnd or @dnd-kit/core)

**Behavior:**
- Drag appointment block to new time slot / doctor column
- On drop: optimistic update (move block immediately), then `PATCH /api/v1/appointments/{id}` with new `scheduled_at` and `doctor_id`
- If API fails: revert to original position + toast error "No se pudo reprogramar la cita"
- Conflict detection: if target slot overlaps another appointment, show warning modal before confirming

---

## Form Fields

Not applicable — calendar view is read/drag interaction. Form fields are in FE-AG-02 (create) and FE-AG-03 (edit).

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Load appointments | `/api/v1/appointments?date_from={}&date_to={}&doctor_id={}` | GET | `specs/appointments/AP-03` | 2min |
| Drag-drop reschedule | `/api/v1/appointments/{id}` | PATCH | `specs/appointments/AP-11` | none |
| Load doctors list | `/api/v1/users?role=doctor` | GET | `specs/users/U-01` | 10min |

### State Management

**Local State (useState):**
- `view: 'day' | 'week' | 'month'` — current view mode (default `'day'`)
- `focalDate: Date` — currently displayed date
- `activeDoctorIds: string[]` — selected doctor filter
- `draggingAppointmentId: string | null` — active drag target

**Global State (Zustand):**
- `agendaStore.view` — persisted view preference across navigation
- `agendaStore.focalDate` — last viewed date
- `authStore.user.role` — determines edit permissions
- `authStore.tenant` — for timezone and working hours

**Server State (TanStack Query):**
- Query key: `['appointments', tenantId, focalDate, view, activeDoctorIds]`
- Stale time: 2min
- Refetch on window focus: true
- Mutation: `useMutation()` for drag-drop PATCH with optimistic update
- Query key: `['doctors', tenantId]` — stale time 10min

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click appointment block | Click | Opens FE-AG-03 slide-in panel | Block highlights with ring |
| Click empty slot | Click | Opens FE-AG-02 create modal pre-filled | Slot highlights on hover |
| Drag appointment | Drag to new slot | Optimistic move + PATCH | Ghost at origin, block snaps to target |
| Drop on conflict | Drop | Warning modal "Conflicto de horario" | Modal with confirm/cancel |
| Change view | Tab click | Re-render grid | Smooth fade transition |
| Navigate date | Arrow click | Load new date range | Skeleton while loading |
| "Hoy" button | Click | Jump to today | Scroll grid to current time |
| Doctor chip filter | Click chip | Toggle doctor column | Column appears/disappears |
| + Nueva Cita | Click | Open FE-AG-02 modal | Modal slides up |

### Animations/Transitions

- Appointment blocks: `framer-motion` layout animation on drag
- View switch: `opacity` fade 150ms
- Date navigation: slide left/right (100ms) matching direction of navigation
- Current time line: smooth top position update every 60s

---

## Loading & Error States

### Loading State
- Time grid: skeleton rows — `animate-pulse bg-gray-100 rounded h-10` per slot row
- Appointment blocks: 5–8 skeleton blocks of varying widths and heights
- Doctor chips: 3 skeleton chips

### Error State
- Full grid error: centered card "Error al cargar la agenda" with Lucide `CalendarX` icon and "Reintentar" button
- Reschedule fail: toast `variant="error"` "No se pudo reprogramar. Intenta de nuevo."

### Empty State
- **Illustration:** Lucide `Calendar` icon `w-16 h-16 text-gray-300`
- **Message:** "Sin citas para este día"
- **CTA:** "+ Agendar primera cita" → opens FE-AG-02

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Day view only (week/month tabs hidden). Single column. Doctor filter becomes dropdown. Appointment blocks show name only. "+ Nueva Cita" is FAB (floating action button, bottom right, 56px). |
| Tablet (640-1024px) | Day + week view available. Doctor chips horizontal scroll. Appointment blocks show name + type. Drag-and-drop enabled. Primary clinical device. |
| Desktop (> 1024px) | All three views. Multi-doctor columns in week. Sidebar expanded. Appointment blocks show full detail. |

**Tablet priority:** High — primary scheduling device for receptionists and assistants. All touch targets min 44px. Drag zones at least 44px tall per slot.

---

## Accessibility

- **Focus order:** Toolbar controls → doctor chips → grid slots (row by row, left to right)
- **Screen reader:** Each appointment block has `aria-label="{patient} — {type} — {time} — Estado: {status}"`. Empty slots have `aria-label="Slot disponible {time}"`. View mode tabs use `role="tablist"` and `role="tab"` with `aria-selected`.
- **Keyboard navigation:** Arrow keys to move between slots. Enter to open appointment or create modal. Escape to close panels. `T` key to jump to today. `D/W/M` to switch views.
- **Color contrast:** WCAG AA. Appointment block colors always paired with text that meets 4.5:1 ratio. Status not conveyed by color alone (icons + labels).
- **Language:** All labels, ARIA, tooltips in es-419.

---

## Design Tokens

**Colors:**
- Page background: `bg-gray-50 dark:bg-gray-950`
- Toolbar background: `bg-white border-b border-gray-200`
- Slot hover: `bg-primary-50 cursor-pointer`
- Current time line: `bg-red-500 h-0.5`
- Column header (doctor name): `text-sm font-medium text-gray-600 bg-gray-50`
- Weekend columns (week view): `bg-gray-50/50`

**Typography:**
- Time labels: `text-xs font-mono text-gray-400 w-12 text-right`
- Doctor column headers: `text-sm font-semibold text-gray-700`
- Appointment patient name: `text-sm font-medium truncate`
- Appointment time: `text-xs text-current opacity-75`

**Spacing:**
- Slot height (30 min): `h-10` (40px)
- Time column width: `w-14`
- Doctor column min-width: `min-w-[160px]`
- Appointment block padding: `px-2 py-1`

**Border Radius:**
- Appointment blocks: `rounded-md`
- Doctor chips: `rounded-full`
- View tabs: `rounded-lg`

---

## Implementation Notes

**Dependencies (npm):**
- `@dnd-kit/core` `@dnd-kit/sortable` — drag-and-drop rescheduling
- `framer-motion` — layout animations
- `date-fns` — date arithmetic, formatting (`format`, `addDays`, `startOfWeek`, `eachDayOfInterval`)
- `lucide-react` — Calendar, ChevronLeft, ChevronRight, Plus, Clock
- `@tanstack/react-query` — data fetching and optimistic updates

**File Location:**
- Page: `src/app/(dashboard)/agenda/page.tsx`
- Components: `src/components/agenda/CalendarView.tsx`, `src/components/agenda/TimeGrid.tsx`, `src/components/agenda/AppointmentBlock.tsx`, `src/components/agenda/DoctorFilterChips.tsx`, `src/components/agenda/CalendarToolbar.tsx`
- Store: `src/stores/agendaStore.ts`

**Hooks Used:**
- `useAuth()` — role + tenant context
- `useAppointments(dateFrom, dateTo, doctorIds)` — custom TanStack Query hook
- `useRescheduleAppointment()` — mutation with optimistic update
- `useAgendaStore()` — Zustand store for view/date state
- `useMediaQuery('(max-width: 640px)')` — mobile-only restrictions

**Timezone handling:** All times displayed in `tenant.timezone` (default `America/Bogota`). Use `date-fns-tz` for conversion.

---

## Test Cases

### Happy Path
1. Receptionist views today's agenda in day view
   - **Given:** Logged in as receptionist, appointments exist for today
   - **When:** Navigate to `/agenda`
   - **Then:** Day view shows appointments color-coded by type, current time line visible, doctor columns match active doctors

2. Drag-drop reschedule
   - **Given:** Appointment at 09:00, target slot 10:00 is free
   - **When:** Drag appointment block to 10:00 slot
   - **Then:** Block moves optimistically, PATCH fires, confirmation toast shown

### Edge Cases
1. Conflict on drag-drop
   - **Given:** Target slot already has an appointment
   - **When:** Appointment dropped on occupied slot
   - **Then:** Warning modal "Conflicto de horario detectado — ¿Confirmar de todos modos?" with Confirmar/Cancelar

2. No doctors assigned to clinic
   - **Given:** Clinic has no users with role=doctor
   - **When:** Agenda loads
   - **Then:** Single column view with empty state and "Agregar doctor" CTA

### Error Cases
1. PATCH fails on drag
   - **Given:** Network error during reschedule
   - **When:** Drop fires, API returns 500
   - **Then:** Appointment reverts to original position, toast error displayed

---

## Acceptance Criteria

- [ ] Day view default on page load
- [ ] Week and month view available and functional
- [ ] Color-coded appointment blocks by type (consulta, procedimiento, emergencia, seguimiento)
- [ ] Status visual overlays (confirmed checkmark, in_progress pulse, completed opacity)
- [ ] Multi-doctor column layout in week/day view
- [ ] Drag-and-drop reschedule with optimistic update and revert on error
- [ ] Conflict detection modal on overlapping drops
- [ ] Doctor filter chips functional (show/hide columns)
- [ ] "Hoy" button returns to today and scrolls to current time
- [ ] Current time red line updates every 60s
- [ ] Empty slot click opens FE-AG-02 pre-filled
- [ ] Loading skeletons for appointment blocks
- [ ] Toast errors for reschedule failures
- [ ] Empty state when no appointments
- [ ] Responsive: FAB on mobile, full DnD on tablet/desktop
- [ ] Keyboard navigation (arrows, Enter, Escape, T/D/W/M shortcuts)
- [ ] ARIA labels on all blocks and slots
- [ ] All labels in es-419

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
