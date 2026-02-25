# Panel de Lista de Espera — Frontend Spec

## Overview

**Screen:** Waitlist sidebar panel showing patients waiting for an appointment slot. Displays patient name, preferred doctor, preferred times, and procedure type. Supports drag-and-drop from waitlist entry into a calendar slot. One-click scheduling when a matching slot becomes available. Badge count on panel toggle button indicates pending waitlist entries.

**Route:** Collapsible side panel on `/agenda` (no dedicated route). Toggle button visible in calendar toolbar.

**Priority:** High

**Backend Specs:**
- `specs/appointments/AP-12` — List waitlist entries
- `specs/appointments/AP-13` — Create waitlist entry
- `specs/appointments/AP-14` — Update / schedule / remove waitlist entry

**Dependencies:**
- `specs/frontend/agenda/calendar-view.md` (FE-AG-01) — calendar is drop target for waitlist drag
- `specs/frontend/agenda/appointment-create.md` (FE-AG-02) — opens pre-filled from waitlist
- `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Click "Lista de Espera" toggle button in calendar toolbar (with badge count)
- Patient created with "agregar a lista de espera" flag during registration
- From appointment cancel flow: "¿Agregar a lista de espera?" prompt

**Exit Points:**
- Drag patient to calendar slot → opens FE-AG-02 pre-filled → appointment created → entry removed from waitlist
- "Agendar" quick-action button → opens FE-AG-02 pre-filled
- "Eliminar" from waitlist → confirm → entry removed
- Panel toggle → collapses panel, returns to full calendar view

**User Story:**
> As a receptionist, I want to see all patients on the waitlist and quickly schedule them when a matching slot opens, so that I can fill cancellation gaps and reduce empty appointment slots.

**Roles with access:** clinic_owner (all), doctor (own doctor's waitlist), assistant (all), receptionist (all)

---

## Layout Structure

```
+--------+---------------------------------------+--------+
|        |                                       | Lista  |
|        |  [Calendar View — FE-AG-01]           | de     |
|        |                                       | Espera |
| Side-  |                                       |--------|
|  bar   |                                       | [badge]|
|        |                                       | Panel  |
|        |                                       | below  |
+--------+---------------------------------------+--------+

--- Panel open state ---

+--------+----------------------------+-------------------+
|        |                            |  Lista de Espera  |
|        |  [Calendar View]           |  [X] [+ Agregar]  |
|        |                            |-------------------|
| Side-  |                            | 5 pacientes       |
|  bar   |                            |                   |
|        |                            | [Waitlist Card 1] |
|        |                            | [Waitlist Card 2] |
|        |                            | [Waitlist Card 3] |
|        |                            | [Waitlist Card 4] |
|        |                            | [Waitlist Card 5] |
|        |                            |                   |
|        |                            | [Filtrar doctor]  |
+--------+----------------------------+-------------------+
```

**Sections:**
1. Toggle button — "Lista de Espera" with badge count (in calendar toolbar)
2. Panel header — title, close button, "+ Agregar a lista" button, count label
3. Filter row — doctor filter dropdown (show entries for specific doctor)
4. Waitlist entries list — scrollable cards, sorted by wait duration (oldest first)
5. Empty state — when no entries

---

## UI Components

### Component 1: WaitlistToggleButton

**Type:** Toggle button with badge

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.3

**Content:**
- `ClipboardList` icon + "Lista de Espera" label
- Red badge with count (hidden when 0): `bg-red-500 text-white text-xs rounded-full w-5 h-5`
- Active state when panel is open: `bg-primary-100 text-primary-700`
- Inactive: `bg-white text-gray-600 border border-gray-200`
- Min size: 44px height

### Component 2: WaitlistPanel

**Type:** Side panel (right side, over calendar or push)

**Layout:** Fixed width `w-80` (320px) on tablet/desktop. Full-screen overlay on mobile.
**Behavior:**
- Slides in from right: `framer-motion` slide + fade, 200ms
- Calendar grid adjusts width when panel is pinned (desktop)
- Scrollable list with overflow-y-auto

### Component 3: WaitlistCard

**Type:** Draggable card

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| entry | WaitlistEntry | — | Waitlist entry data |
| isDragging | boolean | false | DnD drag state |

**Content per card:**
- Patient avatar (initials, colored circle) + full name: `text-sm font-semibold`
- Wait duration: "En espera: 3 días" (`text-xs text-amber-600` if > 2 days, `text-red-600` if > 7 days)
- Preferred doctor: avatar + name, or "Cualquier doctor"
- Preferred times: chip list (e.g., "Mañanas", "Tardes", "Martes y Jueves")
- Procedure type: badge (same colors as appointment types)
- Priority flag: `AlertTriangle` icon in red if marked urgent

**Actions (visible on hover/focus):**
- "Agendar" button: `text-xs bg-primary-600 text-white rounded px-2 py-1` → opens FE-AG-02 pre-filled
- "Eliminar" icon button: `Trash2`, opens confirm dialog

**Drag behavior:**
- Entire card is draggable via `@dnd-kit/core`
- On drag start: card gets `opacity-50 scale-95`, ghost shows in panel
- On hover over calendar slot: slot highlights green "Suelta aquí"
- On drop: auto-fills FE-AG-02 modal with patient + doctor + time from slot
- On successful appointment creation: entry removed from waitlist automatically

### Component 4: WaitlistFilterRow

**Type:** Dropdown select

**Content:** "Todos los doctores" (default) | individual doctor options
**Behavior:** Filters visible waitlist cards without API call (client-side filter of loaded data)

### Component 5: AddToWaitlistForm (mini-form in panel)

**Type:** Inline form shown when "+ Agregar" clicked

**Fields:**
- Patient search typeahead (reuses PatientSearchTypeahead from FE-AG-02)
- Preferred doctor select
- Preferred times multi-select: ["Mañanas (8-12)", "Tardes (12-18)", "Cualquier hora"]
- Preferred days multi-select: Mon–Sun chips
- Procedure type select
- Urgent toggle
- Notes textarea (optional, max 200 chars)
- "Agregar a lista" button

**Behavior:** Collapses after successful add. Inline in panel footer area.

---

## Form Fields (Add to Waitlist)

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| patient_id | search/select | Yes | Existing patient | "Selecciona un paciente" | "Buscar paciente..." |
| preferred_doctor_id | select | No | Active doctor | — | "Cualquier doctor" |
| preferred_times | multi-select | No | At least 1 if specified | — | "Horarios preferidos" |
| preferred_days | multi-select | No | — | — | "Días preferidos" |
| procedure_type | select | No | Valid enum | — | "Tipo de procedimiento" |
| is_urgent | boolean | No | — | — | — |
| notes | textarea | No | Max 200 chars | — | "Notas adicionales" |

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Load waitlist | `/api/v1/waitlist?limit=50&sort=created_at:asc` | GET | `specs/appointments/AP-12` | 2min |
| Add to waitlist | `/api/v1/waitlist` | POST | `specs/appointments/AP-13` | none |
| Remove from waitlist | `/api/v1/waitlist/{id}` | DELETE | `specs/appointments/AP-14` | none |
| Schedule from waitlist | `/api/v1/waitlist/{id}/schedule` | POST | `specs/appointments/AP-14` | none |

### State Management

**Local State (useState):**
- `isPanelOpen: boolean`
- `isAddFormOpen: boolean`
- `filterDoctorId: string | null`
- `draggingEntryId: string | null`

**Global State (Zustand):**
- `agendaStore.waitlistPanelOpen: boolean` — persisted panel open state

**Server State (TanStack Query):**
- Query key: `['waitlist', tenantId]` — staleTime 2min
- Refetch interval: 60s (entries may be added by other users)
- Mutation: `useAddToWaitlist()` — POST
- Mutation: `useRemoveFromWaitlist()` — DELETE with optimistic removal
- Mutation: `useScheduleFromWaitlist()` — POST (removes entry + creates appointment)

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Toggle panel | Toggle button click | Panel opens/closes | Slide animation |
| Click "Agendar" | Button on card | FE-AG-02 modal opens pre-filled | Modal slides up |
| Drag card to slot | Drag to calendar slot | FE-AG-02 opens pre-filled | Slot highlights green |
| Drop successful → confirm appointment | FE-AG-02 submit | Entry removed from panel | Card disappears, toast "Cita agendada" |
| Click "Eliminar" | Icon button click | Confirmation dialog | Dialog |
| Confirm delete | Dialog confirm | DELETE entry, card removed | Toast "Eliminado de la lista de espera" |
| "+ Agregar" | Button click | Add form expands in panel | Form slides down |
| Submit add form | "Agregar a lista" click | POST, new card appears at bottom | Card animates in, form collapses |
| Filter by doctor | Select change | Client-side filter | Instant update |
| Badge count | Auto | Updates every 60s | Badge number changes |

### Animations/Transitions

- Panel open/close: slide from right 200ms
- Card drag: scale-95 + opacity-50 on source card, drop zone highlight
- New card appear: slide-down + fade-in from bottom of list
- Card remove: fade-out + slide-up
- Badge: scale pulse animation when count increases

---

## Loading & Error States

### Loading State
- Waitlist list: 4 skeleton cards — avatar circle + 3 text lines + action buttons
- Badge: shows spinner while initial load

### Error State
- Load failure: "Error al cargar la lista de espera." with Reintentar button inside panel
- Add failure: toast "Error al agregar a la lista. Intenta de nuevo."
- Delete failure: card reverts (optimistic revert), toast "Error al eliminar."

### Empty State
- **Illustration:** Lucide `ClipboardList` icon `w-12 h-12 text-gray-300`
- **Message:** "La lista de espera está vacía"
- **Sub-text:** "Los pacientes sin cita disponible aparecerán aquí."
- **CTA:** "+ Agregar paciente" → expands add form

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Panel opens as full-screen overlay with X close button. Drag-and-drop disabled (tap "Agendar" instead). Badge visible on calendar toolbar. |
| Tablet (640-1024px) | Panel slides over calendar from right, 320px wide. Drag-and-drop enabled. Primary use case. Touch targets 44px on all card buttons. |
| Desktop (> 1024px) | Panel pushes calendar left (calendar grid shrinks). Panel pinnable. Drag-and-drop enabled. |

**Tablet priority:** High — receptionists manage waitlist on tablets at the front desk.

---

## Accessibility

- **Focus order:** Toggle button → panel header → filter dropdown → waitlist cards (top to bottom) → add form
- **Screen reader:** Panel `role="complementary"` `aria-label="Lista de espera"`. Cards `role="article"` with `aria-label="{patient} — en espera desde {date}"`. Badge `aria-label="{n} pacientes en lista de espera"`. Drag handle `aria-grabbed` attribute.
- **Keyboard navigation:** Tab through cards. Enter on "Agendar" opens modal. Delete/Backspace opens remove dialog. ESC closes add form or panel.
- **Color contrast:** WCAG AA. Wait duration color (amber/red) + text label — not color alone.
- **Language:** All labels, placeholders, toasts in es-419.

---

## Design Tokens

**Colors:**
- Panel background: `bg-white dark:bg-gray-900`
- Panel border: `border-l border-gray-200`
- Card border: `border border-gray-200 hover:border-primary-300`
- Card dragging: `opacity-50 shadow-xl border-primary-400`
- Wait urgent: `border-l-4 border-red-500`
- Drop zone highlight: `bg-green-100 border-2 border-green-400 border-dashed`
- Badge: `bg-red-500 text-white`

**Typography:**
- Panel title: `text-base font-bold text-gray-900`
- Count label: `text-sm text-gray-500`
- Patient name: `text-sm font-semibold text-gray-900`
- Wait duration: `text-xs font-medium` (amber or red by age)
- Preferred info: `text-xs text-gray-500`

**Spacing:**
- Panel padding: `p-4`
- Card padding: `p-3`
- Card gap: `gap-2`
- Action buttons: `gap-1`

**Border Radius:**
- Panel container: `rounded-l-xl` (right edge square)
- Cards: `rounded-xl`
- Add form: `rounded-xl bg-gray-50`
- Chips: `rounded-full`

---

## Implementation Notes

**Dependencies (npm):**
- `@dnd-kit/core` — drag-and-drop from panel to calendar
- `framer-motion` — panel slide, card appear/disappear
- `lucide-react` — ClipboardList, Plus, Trash2, AlertTriangle, Clock, UserClock
- `@tanstack/react-query` — waitlist data + mutations
- `date-fns` — wait duration formatting

**File Location:**
- Component: `src/components/agenda/WaitlistPanel.tsx`
- Sub-components: `src/components/agenda/WaitlistCard.tsx`, `src/components/agenda/AddToWaitlistForm.tsx`, `src/components/agenda/WaitlistToggleButton.tsx`
- Hook: `src/hooks/useWaitlist.ts`

**Hooks Used:**
- `useAuth()` — role filtering
- `useQuery(['waitlist', tenantId])` — list data
- `useAddToWaitlist()` — POST mutation
- `useRemoveFromWaitlist()` — DELETE optimistic mutation
- `useDndSensor()` — drag start/end handlers to interface with calendar FE-AG-01
- `useAgendaStore()` — panel open state

---

## Test Cases

### Happy Path
1. Receptionist schedules waitlist patient
   - **Given:** 3 patients on waitlist, available slot at 15:00
   - **When:** Click "Agendar" on first waitlist card → FE-AG-02 opens pre-filled → confirm appointment
   - **Then:** Appointment created, waitlist card removed, badge count decreases

2. Drag patient to slot
   - **Given:** Waitlist card visible, calendar slot at 11:00 open
   - **When:** Drag card to 11:00 slot
   - **Then:** FE-AG-02 opens pre-filled with patient + 11:00 time + preferred doctor

### Edge Cases
1. Multiple entries for same patient
   - **Given:** Same patient added twice (different procedure types)
   - **When:** Panel loads
   - **Then:** Both cards visible, differentiated by procedure type badge

2. Waitlist entry preferred doctor unavailable
   - **Given:** Preferred doctor has no slots on any upcoming date
   - **When:** "Agendar" clicked
   - **Then:** FE-AG-02 opens with doctor pre-filled but availability grid shows "Sin disponibilidad" warning and "Cualquier doctor" suggestion

### Error Cases
1. Drop to occupied slot
   - **Given:** Waitlist card dragged to occupied slot
   - **When:** Drop event fires
   - **Then:** FE-AG-02 opens, slot shown as occupied, user must pick another

---

## Acceptance Criteria

- [ ] Toggle button with badge count
- [ ] Badge updates every 60 seconds
- [ ] Waitlist panel slides in from right (tablet/desktop)
- [ ] Waitlist cards show: patient, wait duration, preferred doctor, preferred times, procedure type
- [ ] Wait duration color-codes by age (neutral, amber >2d, red >7d)
- [ ] Urgent flag indicator
- [ ] "Agendar" button pre-fills FE-AG-02 modal
- [ ] Drag-and-drop from panel to calendar slot (tablet/desktop)
- [ ] Drop target slot highlights green on drag hover
- [ ] Successful appointment creation removes card from waitlist
- [ ] "Eliminar" with confirmation dialog
- [ ] "+ Agregar" inline form with patient search typeahead
- [ ] Doctor filter (client-side)
- [ ] Sorted by wait duration (oldest first)
- [ ] Loading skeletons
- [ ] Empty state with CTA
- [ ] Responsive: full-screen overlay mobile, side panel tablet/desktop
- [ ] Touch targets min 44px on all card actions
- [ ] ARIA: complementary role, card labels, badge aria-label
- [ ] All labels in es-419

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
