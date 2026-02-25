# Calendar — Design System Component Spec

## Overview

**Spec ID:** FE-DS-13

**Component:** `AppCalendar`

**File:** `src/components/ui/calendar.tsx`

**Description:** Full-featured appointment calendar component supporting day, week, and month views with drag-and-drop rescheduling, multi-doctor columns, color-coded appointment types, and touch-friendly tablet interaction. This is the primary scheduling interface for DentalOS and must support the "max 3 taps to book" North Star goal.

**Design System Ref:** `FE-DS-01` (§4.12)

---

## Props Table

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `view` | `'day' \| 'week' \| 'month'` | `'day'` | No | Active calendar view |
| `onViewChange` | `(view: View) => void` | — | No | View switch callback |
| `currentDate` | `Date` | Today | No | The date being viewed |
| `onDateChange` | `(date: Date) => void` | — | No | Navigation callback |
| `events` | `CalendarEvent[]` | `[]` | Yes | Array of appointment events |
| `doctors` | `Doctor[]` | `[]` | No | Doctors for multi-column day view |
| `selectedDoctors` | `string[]` | All | No | Which doctor columns are visible |
| `onEventClick` | `(event: CalendarEvent) => void` | — | No | Event click handler |
| `onSlotClick` | `(date: Date, doctorId?: string) => void` | — | No | Empty slot click (opens create form) |
| `onEventDrop` | `(event: CalendarEvent, newDate: Date, newDoctorId?: string) => void` | — | No | Drag-drop callback |
| `onEventResize` | `(event: CalendarEvent, newDuration: number) => void` | — | No | Resize callback |
| `workStart` | `number` | `7` | No | Start hour for time grid (7 = 07:00) |
| `workEnd` | `number` | `21` | No | End hour for time grid (21 = 21:00) |
| `slotDuration` | `number` | `30` | No | Slot size in minutes (15 or 30) |
| `isLoading` | `boolean` | `false` | No | Shows skeleton state |
| `timezone` | `string` | Tenant timezone | No | IANA timezone for display |

---

## CalendarEvent Type

```typescript
interface CalendarEvent {
  id: string
  title: string                  // Patient name or appointment title
  start: Date
  end: Date
  type: AppointmentType          // consulta | procedimiento | urgencia | control
  status: AppointmentStatus
  doctorId: string
  patientName: string
  notes?: string
  color?: string                 // Override type color
}

type AppointmentType = 'consulta' | 'procedimiento' | 'urgencia' | 'control' | 'bloqueo'
```

---

## Calendar Views

### Day View

**Default view.** Shows a single day as a vertical time grid.

**Layout:**
```
+---------------------------------------------------------+
| [◀] 25 Feb 2026, Miércoles [▶]  [Hoy]  [Día|Sem|Mes] |
+---------------------------------------------------------+
| 07:00 |  Dr. Gómez col 1  |  Dra. García col 2  |      |
|       |  [Appointment]    |                      |      |
| 07:30 |                   |  [Appointment]       |      |
| 08:00 |  [Appointment]    |                      |      |
|  ...  |                   |                      |      |
| 21:00 |                   |                      |      |
+---------------------------------------------------------+
```

**Time axis:** Left column, `w-16`, showing hours `07:00`, `07:30`, ..., `21:00`. Label anchored at top of slot row.

**Doctor columns:** When multiple doctors are visible, each gets an equal-width column. Appointments placed in their doctor's column.

**Slot height:** Each 30-minute slot = `h-12` (48px). 1 hour = `h-24` (96px). Appointment height calculated from duration.

**Current time indicator:** Horizontal red line at the exact current minute position. `bg-red-500 h-[2px] absolute w-full z-10`. Updates every minute.

**Today highlight:** Today's date header has `bg-teal-50` background.

### Week View

Shows 7 days in columns (Mon–Sun, or Sun–Sat by region config).

**Layout:**
- Time axis on left (`w-16`)
- 7 day columns, each equal width
- Column header: `"Lun 24"`, `"Mar 25"` etc. Today is highlighted `bg-teal-50`
- Time grid: same slot height as day view
- Appointments: blocks in the appropriate day column + time row

**Multi-doctor in week view:** Not columned per doctor — appointments overlap within a day column (up to 3 side-by-side, then "+N more" indicator).

### Month View

Traditional month grid.

**Layout:**
```
+------------------------------------------+
| Lun  Mar  Mié  Jue  Vie  Sáb  Dom       |
+------------------------------------------+
|  23   24   25   26   27   28   1        |
|  [●]  [●●] [●]                          |
+------------------------------------------+
|   2    3    4    5    6    7    8        |
+------------------------------------------+
```

**Day cell:** Contains appointment dots (colored by type). If > 3 events: shows 2 events + "+N más" link.

**Today cell:** `bg-teal-600 text-white rounded-full` on the date number.

**Click behavior:** Click a date → switches to day view for that date.

---

## Appointment Event Block

### Day/Week View — Block Style

```
+--------------------------------+
| [Type indicator bar 4px left] |
| Patient Name                   |
| 14:00 – 14:30 · Consulta       |
+--------------------------------+
```

**Base classes:**
```
rounded-md text-white text-xs font-medium
overflow-hidden cursor-pointer
px-2 py-1 select-none
absolute left-1 right-1
transition-shadow hover:shadow-md
```

**Height:** Calculated from duration: `(duration_minutes / 30) * 48px - 2px` gap.

**Minimum height:** `h-8` (32px) even for very short appointments.

**Appointment type colors:**

| Type | Background | Border Left | Text |
|------|-----------|-------------|------|
| `consulta` | `bg-blue-500` | `border-l-4 border-blue-700` | white |
| `procedimiento` | `bg-teal-500` | `border-l-4 border-teal-700` | white |
| `urgencia` | `bg-red-500` | `border-l-4 border-red-700` | white |
| `control` | `bg-amber-500` | `border-l-4 border-amber-700` | white |
| `bloqueo` | `bg-gray-300` | `border-l-4 border-gray-400` | `text-gray-600` |

**Cancelled appointments:** `opacity-50 line-through` on title.

**Content by size:**
- Block >= 60min: Patient name + time + type label
- Block 30-59min: Patient name + time
- Block 15-29min: Patient name only (truncated)
- Block < 15min: Initials only

### Month View — Dot Style

Compact dot + truncated event text per day cell:

```tsx
<div className="flex items-center gap-1 text-xs">
  <span className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', typeColors[event.type])} />
  <span className="truncate">{event.patientName}</span>
</div>
```

---

## Drag and Drop

**Technology:** `@dnd-kit/core` with custom pointer/touch sensor.

**Behavior:**
1. Click-hold on appointment block (mouse: 200ms hold, touch: 150ms hold)
2. Block lifts: `shadow-xl opacity-90 scale-[1.02]` visual feedback
3. Drag over time slots: green highlight on valid drop targets
4. Drop: `onEventDrop(event, newStart, newDoctorId?)` called
5. Optimistic update: event moves immediately before API confirmation
6. API failure: event snaps back with error toast

**Resize (bottom handle):**
- When appointment > 30min, bottom edge shows resize handle (8px high, `cursor-ns-resize`)
- Drag bottom handle up/down to change duration in 15-minute increments
- Minimum duration: 15 minutes

**Touch support:**
- On tablet, touch sensors with 150ms delay (prevent accidental drag while scrolling)
- Touch cancel: lift finger while holding but moving horizontally → scroll, not drag

---

## Navigation Controls

**Layout (above the calendar grid):**

```
[◀ Anterior]  [Rango actual text]  [Siguiente ▶]  |  [Hoy]  |  [Día] [Semana] [Mes]
```

**Range text:**
- Day: `"25 feb 2026, miércoles"`
- Week: `"24 feb — 2 mar 2026"`
- Month: `"Febrero 2026"`

**View switcher:** Segmented button group (pills style):
- Selected: `bg-teal-600 text-white`
- Unselected: `bg-white border border-gray-300 text-gray-700`

---

## Doctor Filter (Multi-doctor)

Above the calendar grid, when multiple doctors exist:

```
Médico: [All] [Dr. Gómez] [Dra. García] [Dr. Silva]
```

Pill toggles per doctor. Deselecting hides their column in day/week view. "All" toggles all visible.

---

## Empty Slot (Click to Create)

**Day/week view:** Click on any empty time slot → calls `onSlotClick(date, doctorId)`. Typically opens the appointment creation modal.

**Visual feedback:** Hover over empty slot: subtle teal dotted border outline.

---

## Loading State

When `isLoading={true}`:
- Day view: 5-6 skeleton event blocks randomly placed in different columns and times
- Month view: day cell rectangles with gray background, no dots
- Uses FE-DS-17 skeleton `animate-pulse bg-gray-200` blocks

---

## Responsive Behavior

| Breakpoint | Default View | Notes |
|------------|-------------|-------|
| Mobile (< 640px) | Day | Week and month views accessible but may require scroll. Columns condensed. |
| Tablet (640-1023px) | Day | Multi-doctor columns fully visible. Day is primary use case. |
| Desktop (≥ 1024px) | Week | Full week view by default. Month view for overview. |

**Tablet touch targets:** Time slots minimum 44px height (2 slots = 96px per hour works). Appointment blocks minimum 32px to be tappable.

---

## Accessibility

- **Role:** Calendar grid has `role="grid"`. Day column headers have `role="columnheader"`. Time slots have `role="gridcell"` with `aria-label="07:30, martes 25 de febrero"`.
- **Appointment blocks:** `role="button"`, `aria-label="Cita: María García, 14:00–14:30, consulta"`, `tabIndex={0}`
- **Keyboard:** Arrow keys navigate between time slots. Enter opens appointment detail. `T` key jumps to today.
- **Screen reader:** Current time indicator has `aria-hidden="true"` (decorative).
- **Drag:** Appointments can also be moved via keyboard (arrow keys while focused + space/enter).
- **Language:** All day names, month names in Spanish (es-419). Time in 24h format.

---

## Implementation Notes

**File Location:** `src/components/ui/calendar.tsx`, `src/components/agenda/CalendarView.tsx`

**Dependencies:**
- `@dnd-kit/core`, `@dnd-kit/sortable` — drag and drop
- `date-fns` with `es` locale — date formatting
- Custom time grid layout (no external calendar library — built in-house for flexibility)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial component spec |
