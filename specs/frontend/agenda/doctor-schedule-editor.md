# Editor de Horario del Doctor — Frontend Spec

## Overview

**Screen:** Doctor schedule configuration page. Allows clinic owners and doctors to define weekly availability templates — working hours per day, break periods, default appointment duration, and blocked dates. Visual drag-handle blocks for time adjustments. Preview panel shows resulting availability slots. Located in Settings section.

**Route:** `/settings/schedule` (own schedule) | `/settings/team/{doctorId}/schedule` (clinic_owner editing other doctor)

**Priority:** High

**Backend Specs:**
- `specs/users/U-07` — Get doctor schedule
- `specs/users/U-08` — Update doctor schedule
- `specs/appointments/AP-10` — Get blocked dates

**Dependencies:**
- `specs/frontend/agenda/calendar-view.md` (FE-AG-01) — schedule affects availability in calendar
- `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Sidebar navigation Settings → "Mi Horario" (doctor self)
- Settings → Equipo → click doctor row → "Configurar horario" (clinic_owner)
- Onboarding wizard step 3 "Configura tu disponibilidad"
- Prompt from calendar "Sin horario configurado — configura tu disponibilidad"

**Exit Points:**
- Save → success toast → stay on page
- Cancel → discard changes confirmation → return to previous page
- Navigate to calendar → `/agenda`

**User Story:**
> As a doctor, I want to configure my weekly availability so that the system only offers valid appointment slots to patients and staff.
> As a clinic_owner, I want to configure schedules for all my doctors so that the agenda reflects accurate availability for each provider.

**Roles with access:**
- clinic_owner: edit any doctor's schedule
- doctor: edit own schedule only
- assistant, receptionist: read-only view of doctor schedules

---

## Layout Structure

```
+--------+-----------------------------------------------+
|        |  [← Volver] Horario de Dr. García            |
|        +-----------------------------------------------+
|        |                                               |
|        |  Plantilla Semanal         [Preview Toggle]  |
|        |  +---------------------------------------+   |
|        |  | Día     | Activo | Inicio | Fin | Dur |   |
|        |  |---------|--------|--------|-----|-----|   |
|        |  | Lunes   |  [X]   | 08:00  |18:00| 30  |   |
|        |  | Martes  |  [X]   | 08:00  |18:00| 30  |   |
|        |  | Miércoles| [X]   | 09:00  |17:00| 30  |   |
|        |  | Jueves  |  [X]   | 08:00  |18:00| 30  |   |
|        |  | Viernes |  [X]   | 08:00  |16:00| 30  |   |
|        |  | Sábado  |  [ ]   |  ---   | --- | --  |   |
|        |  | Domingo |  [ ]   |  ---   | --- | --  |   |
|        |  +---------------------------------------+   |
| Side-  |                                               |
|  bar   |  Descansos por Día                           |
|        |  [Lunes ▼]  [+ Agregar descanso]            |
|        |  13:00 – 14:00  [x]  Almuerzo              |
|        |                                               |
|        |  Fechas Bloqueadas                           |
|        |  [Date range picker] [Motivo input] [+ Add]  |
|        |  2026-03-15  Día festivo  [x]               |
|        |                                               |
|        +-----------------------------------------------+
|        |  [Preview de Disponibilidad]                 |
|        |  Mon  Tue  Wed  Thu  Fri                     |
|        |  |||  |||  ||   |||  ||                      |
+--------+-----------------------------------------------+
|  [Descartar cambios]         [Guardar horario]        |
```

**Sections:**
1. Page header — back button, doctor name, role context
2. Weekly template table — per-day toggles, time pickers, duration selector
3. Break periods — per-day break slots (lunch, etc.)
4. Blocked dates — specific dates/ranges to mark as unavailable
5. Availability preview — visual mini-calendar showing resulting open slots
6. Action footer — discard + save buttons

---

## UI Components

### Component 1: WeeklyTemplateTable

**Type:** Structured table with inline form controls

**Columns per row:**
- Day name (non-editable label)
- Active toggle (`Switch` component, 44px touch target)
- Start time (`TimePicker` select, 15-min increments)
- End time (`TimePicker` select, 15-min increments)
- Default duration (`Select`: 15, 20, 30, 45, 60, 90 min)

**Validation:**
- End time must be after start time by at least `default_duration`
- Disabling a day clears time values and adds `opacity-40` to row
- "Copiar de lunes" shortcut button appears when hovering inactive days

**Bulk actions:** "Aplicar mismo horario a todos los días" button above table — copies Monday settings to active days.

### Component 2: TimePicker

**Type:** Select dropdown or native time input

**Increments:** 15-minute increments (00, 15, 30, 45)
**Range:** 06:00 – 22:00
**Format:** 12h or 24h based on `tenant.time_format` setting
**Mobile:** Native `<input type="time">` for better keyboard

### Component 3: BreakPeriodManager

**Type:** Expandable section per day

**Behavior:**
- Day tab row shows the day with break count badge
- Click day → expand break list for that day
- "+ Agregar descanso" button: adds new break row with start/end time pickers and label input
- Max 3 breaks per day
- Each break row: `[time range pickers] [label input: "Almuerzo", "Pausa", etc.] [delete X]`
- Overlap validation: breaks cannot overlap working hours boundaries or other breaks

### Component 4: BlockedDatesManager

**Type:** List with date picker + reason input

**Content:**
- Date range picker: single date or range (e.g., vacation week)
- Reason input: text, max 100 chars (e.g., "Congreso médico", "Vacaciones")
- List of existing blocks: date/range — reason — delete button
- Import holidays button: "Importar festivos Colombia 2026" pre-loads official holidays

### Component 5: AvailabilityPreview

**Type:** Compact read-only mini-calendar

**Content:**
- 7-day week view showing available (green bars) vs. unavailable (gray) time blocks
- Breaks shown as amber gaps in green bars
- Updates in real-time as template is edited (computed client-side, not from API)
- Toggle show/hide: "Previsualizar disponibilidad" button (collapses on mobile)
- Slot count per day: "8 citas posibles" label below each day column

### Component 6: ActionFooter

**Type:** Sticky bottom bar

**Buttons:**
- "Descartar cambios": `variant="outline"`, triggers discard confirmation if form is dirty
- "Guardar horario": `variant="primary"`, `h-11`, disabled until form is dirty

---

## Form Fields

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| day_active | boolean | — | — | — | — |
| start_time | time | Yes (if active) | Valid time, < end_time | "Hora de inicio inválida" | "08:00" |
| end_time | time | Yes (if active) | > start_time | "Hora de fin debe ser mayor" | "18:00" |
| default_duration | select | Yes (if active) | 15–120 min | "Selecciona duración" | "30 min" |
| break_start | time | Yes (if break added) | Within working hours | "Descanso fuera del horario laboral" | "13:00" |
| break_end | time | Yes (if break added) | > break_start, within hours | "Fin del descanso inválido" | "14:00" |
| break_label | text | No | Max 50 chars | — | "Almuerzo" |
| blocked_date_start | date | Yes (if block added) | Future or today | "Selecciona fecha" | — |
| blocked_date_end | date | No | >= start | "Fecha fin debe ser mayor o igual" | — |
| blocked_reason | text | No | Max 100 chars | — | "Motivo (opcional)" |

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Load doctor schedule | `/api/v1/users/{doctorId}/schedule` | GET | `specs/users/U-07` | 5min |
| Save doctor schedule | `/api/v1/users/{doctorId}/schedule` | PUT | `specs/users/U-08` | none |
| Load blocked dates | `/api/v1/users/{doctorId}/blocked-dates` | GET | `specs/appointments/AP-10` | 5min |
| Add blocked date | `/api/v1/users/{doctorId}/blocked-dates` | POST | `specs/appointments/AP-10` | none |
| Delete blocked date | `/api/v1/users/{doctorId}/blocked-dates/{id}` | DELETE | `specs/appointments/AP-10` | none |

### State Management

**Local State (useState):**
- `weeklyTemplate: DaySchedule[]` — 7 days with active, start, end, duration, breaks
- `blockedDates: BlockedDate[]`
- `isDirty: boolean` — tracks unsaved changes
- `isSubmitting: boolean`

**Global State (Zustand):**
- `authStore.user` — to determine if editing own or other doctor's schedule

**Server State (TanStack Query):**
- Query key: `['doctor-schedule', doctorId, tenantId]` — staleTime 5min
- Query key: `['blocked-dates', doctorId, tenantId]` — staleTime 5min
- Mutation: `useSaveDoctorSchedule()` — PUT with full schedule payload
- Mutation: `useAddBlockedDate()` — POST single date/range
- Mutation: `useDeleteBlockedDate()` — DELETE by ID

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Toggle day active | Switch click | Row enables/disables | Row dims/brightens, times clear if disabled |
| Change start/end time | Select change | Preview updates, validates | Inline error if invalid |
| Change default duration | Select change | Preview updates | Slot count label updates |
| Add break | "+ Agregar" click | New break row added | Expands with empty fields |
| Delete break | X click | Break row removed | Row disappears |
| Add blocked date | "+" button click | Date added to list | List item appears |
| Delete blocked date | X on list item | Item removed | DELETE API call |
| Import holidays | Button click | 2026 Colombia holidays pre-filled | Toast "Festivos importados" |
| Save | "Guardar horario" click | PUT schedule | Spinner → success toast |
| Discard | "Descartar" click (dirty form) | Confirmation dialog | Dialog: "¿Descartar cambios?" |

### Animations/Transitions

- Day row disable: `opacity` transition 150ms
- Break section expand/collapse: smooth height animation (`framer-motion`)
- Preview update: instant (computed from local state)
- Save button: loading spinner during submission

---

## Loading & Error States

### Loading State
- Weekly table: 7 skeleton rows with switch + 3 select boxes each
- Blocked dates list: 3 skeleton rows
- Preview: skeleton mini-bars

### Error State
- Load failure: "Error al cargar el horario. Intenta de nuevo." with Reintentar
- Save failure 422 (validation): field-level errors shown in table rows
- Save failure 409 (conflict): "Ya existen citas programadas en los horarios eliminados. ¿Continuar de todos modos?" with list of affected appointments
- Save failure 500: toast "Error al guardar. Intenta de nuevo."

### Empty State
- No schedule configured: onboarding card "Aún no has configurado tu horario. Comencemos." with animated calendar icon

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Table becomes card stack (one card per day). Time pickers native inputs. Preview collapsed by default. Action buttons full-width stacked. |
| Tablet (640-1024px) | Table layout maintained. All 44px touch targets. Break manager as accordion tabs. Preview shown below table. |
| Desktop (> 1024px) | Two-column layout: table + break manager left, preview right. Full table visible. |

**Tablet priority:** Medium — primarily a setup task done once, but doctors may adjust on tablets between patients.

---

## Accessibility

- **Focus order:** Day rows top to bottom → each row: toggle → start time → end time → duration → Break section → Blocked dates → Save
- **Screen reader:** Toggle switches `aria-label="Habilitar {day}"`. Time pickers `aria-label="Hora de inicio {day}"`. Preview `aria-label="Vista previa de disponibilidad: {n} días con disponibilidad configurada"`.
- **Keyboard navigation:** Tab through all fields. Space to toggle day switches. Enter in time pickers opens select.
- **Color contrast:** WCAG AA. Disabled row uses `opacity-40` but underlying color still passes contrast in the accessible layer. Green/amber in preview paired with shape differences.
- **Language:** All labels, error messages, toasts in es-419.

---

## Design Tokens

**Colors:**
- Active day row: `bg-white`
- Inactive day row: `bg-gray-50 opacity-40`
- Active toggle: `bg-teal-500`
- Inactive toggle: `bg-gray-300`
- Break row: `bg-amber-50 border border-amber-100`
- Blocked date chip: `bg-red-50 border border-red-100`
- Preview available: `bg-teal-400`
- Preview blocked/break: `bg-amber-300`
- Preview inactive: `bg-gray-100`
- Save button: `bg-primary-600 hover:bg-primary-700`

**Typography:**
- Day name: `text-sm font-medium text-gray-700`
- Time values: `text-sm font-mono text-gray-900`
- Section headings: `text-sm font-semibold text-gray-500 uppercase tracking-wide`
- Break label: `text-sm text-amber-700`

**Spacing:**
- Table row height: `h-14` (56px, includes breathing room for toggles)
- Section gap: `gap-6`
- Page padding: `px-4 py-6 md:px-6 lg:px-8`

**Border Radius:**
- Table container: `rounded-xl overflow-hidden`
- Break rows: `rounded-lg`
- Preview bars: `rounded-sm`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `zod` — schedule form validation
- `@tanstack/react-query` — data fetching + mutations
- `framer-motion` — break section expand/collapse
- `lucide-react` — Clock, Trash2, Plus, Eye, CalendarOff, ChevronDown

**File Location:**
- Page: `src/app/(dashboard)/settings/schedule/page.tsx`
- Components: `src/components/schedule/WeeklyTemplateTable.tsx`, `src/components/schedule/BreakPeriodManager.tsx`, `src/components/schedule/BlockedDatesManager.tsx`, `src/components/schedule/AvailabilityPreview.tsx`
- Hook: `src/hooks/useDoctorSchedule.ts`

**Hooks Used:**
- `useAuth()` — role + user ID
- `useQuery(['doctor-schedule', doctorId])` — load schedule
- `useSaveDoctorSchedule(doctorId)` — PUT mutation
- `useBlockedDates(doctorId)` — load + add + delete mutations
- `useForm()` (React Hook Form) with Zod

**Preview computation (client-side):**
```typescript
function computeAvailableSlots(template: DaySchedule, breaks: BreakPeriod[]): number {
  if (!template.active) return 0;
  const totalMinutes = diffMinutes(template.end_time, template.start_time);
  const breakMinutes = breaks.reduce((sum, b) => sum + diffMinutes(b.end, b.start), 0);
  return Math.floor((totalMinutes - breakMinutes) / template.default_duration);
}
```

---

## Test Cases

### Happy Path
1. Doctor configures Mon–Fri 8:00–18:00, 30-min slots, lunch break 13:00–14:00
   - **Given:** No schedule configured
   - **When:** Sets Mon–Fri active, 08:00–18:00, adds break 13:00–14:00, clicks save
   - **Then:** PUT fires with full schedule, toast "Horario guardado", preview shows 19 slots/day

2. Clinic owner edits another doctor's schedule
   - **Given:** Logged in as clinic_owner, navigates to team member schedule
   - **When:** Changes Thursday end time to 16:00, saves
   - **Then:** PUT fires for that doctor's ID, schedule updated, warning shown if Thursday has appointments after 16:00

### Edge Cases
1. Saving schedule with existing appointments in removed hours
   - **Given:** Doctor had 17:00–18:00 slots, existing appointment at 17:30
   - **When:** End time changed to 17:00, save clicked
   - **Then:** Conflict dialog lists affected appointments. Requires confirmation.

2. All days disabled
   - **Given:** User disables all 7 days
   - **When:** Save clicked
   - **Then:** Inline warning "Este doctor no tendrá disponibilidad. ¿Continuar?" — save still allowed.

### Error Cases
1. Start time after end time
   - **Given:** User sets start 14:00, end 12:00
   - **When:** Blur from end time field
   - **Then:** Inline error "Hora de fin debe ser mayor que hora de inicio"

---

## Acceptance Criteria

- [ ] Weekly template table with per-day toggle, start/end time, default duration
- [ ] Days toggle on/off with visual disable state
- [ ] Time pickers with 15-min increments
- [ ] "Copiar de lunes" shortcut for other days
- [ ] "Aplicar a todos" bulk action
- [ ] Break periods per day (max 3), add/remove
- [ ] Break overlap validation
- [ ] Blocked dates manager with date range + reason
- [ ] Import Colombia 2026 holidays shortcut
- [ ] Real-time availability preview (client-side computed)
- [ ] Slot count per day label in preview
- [ ] Conflict warning when saving removes hours with existing appointments
- [ ] Dirty state detection → discard confirmation dialog
- [ ] Loading skeletons for schedule data
- [ ] Save success toast
- [ ] Responsive: card stack mobile, table tablet/desktop
- [ ] All touch targets 44px
- [ ] Keyboard navigation through all fields
- [ ] ARIA labels on toggles and time pickers
- [ ] All labels in es-419

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
