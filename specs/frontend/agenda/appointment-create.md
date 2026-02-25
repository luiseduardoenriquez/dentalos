# Crear Cita (Modal) — Frontend Spec

## Overview

**Screen:** Modal/bottom-sheet for creating a new appointment. Optimized for the 3-tap goal: (1) select patient, (2) select slot, (3) confirm. Includes patient search typeahead, doctor selector, intelligent duration auto-calculation based on appointment type, real-time availability check, and optional link to a treatment plan item.

**Route:** Modal overlay on `/agenda` (no dedicated route). Also accessible from `/patients/{id}` tab Citas via "+ Nueva Cita".

**Priority:** Critical

**Backend Specs:**
- `specs/appointments/AP-01` — Create appointment
- `specs/appointments/AP-09` — Check availability (real-time slot validation)
- `specs/patients/patient-search.md` — Patient typeahead search

**Dependencies:**
- `specs/frontend/agenda/calendar-view.md` (FE-AG-01) — parent calendar triggers this modal
- `specs/frontend/patients/patient-list.md` — patient search patterns
- `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Click "+ Nueva Cita" button in calendar toolbar (FE-AG-01)
- Click empty time slot in calendar grid (pre-fills date/time/doctor)
- Click "+ Agendar" from waitlist panel (FE-AG-05) — pre-fills patient
- Click "+ Nueva Cita" in patient detail page Citas tab — pre-fills patient

**Exit Points:**
- Appointment created successfully → modal closes, calendar refreshes, success toast
- Cancel / ESC → modal closes, no changes
- "Ver cita" link in success toast → opens FE-AG-03 detail panel

**User Story:**
> As a receptionist or doctor, I want to create an appointment in 3 taps or fewer so that scheduling is faster than writing it on paper.

**Roles with access:** clinic_owner, doctor (own appointments), assistant, receptionist

---

## Layout Structure

```
+-----------------------------------------------+
|  [X]  Nueva Cita                              |
+-----------------------------------------------+
|                                               |
|  Paso 1: Paciente                             |
|  [Search input: "Buscar paciente..."]         |
|  [Patient result chips / typeahead dropdown]  |
|                                               |
|  Paso 2: Horario                              |
|  [Doctor select]  [Date picker]               |
|  [Available time slots grid]                  |
|  [Tipo de cita select]  [Duración auto-label] |
|                                               |
|  Paso 3: Detalles (collapsible)               |
|  [Notas textarea]  [Link tratamiento select]  |
|  [Send reminder toggle]                       |
|                                               |
+-----------------------------------------------+
|  [Cancelar]              [Confirmar Cita →]  |
+-----------------------------------------------+
```

**Sections:**
1. Modal header — title, close button
2. Step 1: Patient search — typeahead input, recent patients quick-select
3. Step 2: Schedule — doctor, date, available slot grid, type selector, auto-duration
4. Step 3: Details — notes, treatment plan link, reminder toggle (collapsible, optional)
5. Footer — Cancel + Confirm actions

---

## UI Components

### Component 1: PatientSearchTypeahead

**Type:** Combobox / async search input

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.7

**Behavior:**
- Debounced search: 300ms after last keystroke → `GET /api/v1/patients/search?q={query}`
- Results dropdown: patient avatar initials, full name, document number, last visit date
- "Nuevo paciente" option at bottom of dropdown → opens patient create flow in new tab
- Selected patient: rendered as a chip with avatar + name + `[x]` to clear
- Recent patients: shows 5 most recently visited when input is empty and focused
- Min 2 chars to trigger search

**States:**
- Default: placeholder shown
- Searching: spinner in input right
- Results: dropdown with max 8 results, virtualized if more
- Selected: chip display, input hides
- No results: "Sin resultados. ¿Crear nuevo paciente?" with link

### Component 2: DoctorSelect

**Type:** Select dropdown

**Content:** Doctor avatar + name. "Cualquier doctor disponible" option for auto-assign.
**Rules:**
- For role=doctor: defaults to self, can change if has `manage_others_schedule` permission
- For receptionist/assistant: shows all active doctors
**Behavior:** Changing doctor re-triggers availability check.

### Component 3: DatePicker

**Type:** Inline calendar or popover date picker

**Behavior:**
- Defaults to date of clicked slot (or today if opened from toolbar button)
- Past dates disabled (greyed out, unclickable)
- Max booking horizon: 90 days
- Mobile: native `<input type="date">` for better UX

### Component 4: AvailableSlotGrid

**Type:** Grid of time slot buttons

**Behavior:**
- Loads after doctor + date are selected
- `GET /api/v1/appointments/availability?doctor_id={}&date={}`
- Slots: every 30 minutes from doctor's working hours
- States per slot:
  - Available: `bg-white border border-gray-200 hover:bg-primary-50 hover:border-primary-400`
  - Selected: `bg-primary-600 text-white border-primary-600`
  - Occupied: `bg-gray-50 text-gray-300 line-through cursor-not-allowed`
  - Break/Blocked: `bg-amber-50 text-amber-400 italic cursor-not-allowed`
- Grid: 3 columns on tablet, 4 on desktop, full-width scroll on mobile
- Min touch target per slot: 44px height

### Component 5: AppointmentTypeSelect

**Type:** Select with icon

**Options:**
- `consulta` — Consulta general (default)
- `procedimiento` — Procedimiento
- `emergencia` — Emergencia
- `seguimiento` — Seguimiento
- `primera_vez` — Primera vez

**Behavior:** Selection auto-sets `duration` label via `getDurationForType()` lookup. Doctor can override duration manually.

### Component 6: AutoDurationLabel

**Type:** Read-only info badge (editable on expansion)

**Content:** "Duración estimada: 30 min" with pencil icon to open manual override
**Duration defaults by type:**
- `consulta`: 30 min
- `procedimiento`: 60 min
- `emergencia`: 45 min
- `seguimiento`: 20 min
- `primera_vez`: 45 min

---

## Form Fields

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| patient_id | search/select | Yes | Must select existing patient | "Selecciona un paciente" | "Buscar por nombre o cédula..." |
| doctor_id | select | Yes | Must be active doctor | "Selecciona un doctor" | "Doctor" |
| scheduled_at | date+time | Yes | Future datetime, within working hours | "Selecciona fecha y hora disponibles" | — |
| appointment_type | select | Yes | Valid enum value | "Selecciona tipo de cita" | — |
| duration_minutes | number | Yes | 10–240, multiple of 5 | "Duración entre 10 y 240 minutos" | "30" |
| notes | textarea | No | Max 500 chars | "Máximo 500 caracteres" | "Motivo de consulta o notas..." |
| treatment_plan_item_id | select | No | Valid UUID if provided | — | "Vincular a plan de tratamiento (opcional)" |
| send_reminder | boolean | No | — | — | — |

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Patient search | `/api/v1/patients/search?q={}&limit=8` | GET | `specs/patients/patient-search.md` | 30s |
| Recent patients | `/api/v1/patients?recent=true&limit=5` | GET | `specs/patients/patient-list.md` | 5min |
| Check availability | `/api/v1/appointments/availability?doctor_id={}&date={}` | GET | `specs/appointments/AP-09` | 1min |
| Load treatment plans | `/api/v1/treatment-plans?patient_id={}&status=active` | GET | `specs/treatment-plans/plan-get.md` | 5min |
| Create appointment | `/api/v1/appointments` | POST | `specs/appointments/AP-01` | none |

### State Management

**Local State (useState):**
- `step: 1 | 2 | 3` — current active section (all sections visible, step highlights CTA)
- `selectedPatient: Patient | null`
- `selectedSlot: string | null` — ISO datetime string
- `isSubmitting: boolean`
- `conflictWarning: string | null`

**Global State (Zustand):**
- `agendaStore.createModalOpen: boolean`
- `agendaStore.prefillData: { date?, time?, doctorId?, patientId? }` — from slot click

**Server State (TanStack Query):**
- Query key: `['patients', 'search', query, tenantId]` — staleTime 30s
- Query key: `['availability', doctorId, date, tenantId]` — staleTime 1min
- Mutation: `useCreateAppointment()` — `useMutation` with calendar query invalidation on success

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Type in patient search | Input change (300ms debounce) | Load matching patients | Spinner in input |
| Select patient from dropdown | Click result | Patient chip appears, focus moves to slot selection | Chip render |
| Select doctor | Select change | Reload availability grid | Skeleton slots |
| Select date | Date picker change | Reload availability grid | Skeleton slots |
| Click available slot | Click | Slot selected (highlighted), duration label updates | Slot turns primary blue |
| Change appointment type | Select change | Duration label updates | Label animates |
| Click "Confirmar Cita" | Click button | Validate → POST → success | Spinner on button → toast |
| Click "Cancelar" or ESC | Click/key | Modal closes | None |

### Animations/Transitions

- Modal: slides up from bottom on mobile (spring), fades+scales on desktop (200ms)
- Slot grid: skeleton pulse while loading, fade-in on load
- Patient chip: scale-in animation when patient is selected
- Confirm button: loading spinner replaces icon during submission

---

## Loading & Error States

### Loading State
- Availability grid: 12 skeleton slot buttons `animate-pulse bg-gray-100 h-11 rounded-lg`
- Patient search results: 3 skeleton rows with avatar circle + two text lines
- Submit button: disabled + spinner icon

### Error State
- Form validation: inline error below each field, `text-sm text-red-600`
- Patient search error: "Error al buscar pacientes. Intenta de nuevo."
- Availability error: "No se pudo cargar la disponibilidad. Intenta de nuevo." with Reintentar button
- Create failure 409 (conflict): inline warning "Conflicto de horario. Selecciona otro slot."
- Create failure 422: show field-level server errors mapped to form
- Create failure 500: toast "Error al crear la cita. Intenta de nuevo."

### Empty State
- No available slots: "Sin disponibilidad para este día con este doctor. Prueba otra fecha." with calendar icon.

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Bottom-sheet full screen. Steps stacked vertically. Date picker native input. Slot grid 2 columns. |
| Tablet (640-1024px) | Modal centered, 600px wide, 80vh max. Slot grid 3 columns. 44px slot height. Primary use case. |
| Desktop (> 1024px) | Modal centered, 640px wide. Slot grid 4 columns. Side-by-side doctor + date pickers. |

**Tablet priority:** High — primary scheduling device. All interactive elements min 44px. Slot buttons 44px height.

---

## Accessibility

- **Focus order:** Modal heading → patient search → doctor select → date picker → slot grid → type select → notes → submit
- **Screen reader:** Modal has `role="dialog"` `aria-modal="true"` `aria-labelledby="modal-title"`. Slot buttons `aria-label="Slot {time} — disponible"` or `aria-disabled="true"` for occupied. Selected slot `aria-pressed="true"`.
- **Keyboard navigation:** ESC closes modal. Tab through fields. Enter selects focused slot. Arrow keys navigate slot grid.
- **Color contrast:** WCAG AA for all text on colored slot backgrounds.
- **Language:** All labels, placeholders, errors in es-419.

---

## Design Tokens

**Colors:**
- Modal backdrop: `bg-black/50`
- Modal surface: `bg-white dark:bg-gray-900 rounded-2xl shadow-2xl`
- Available slot: `bg-white border-gray-200 hover:bg-primary-50`
- Selected slot: `bg-primary-600 text-white`
- Occupied slot: `bg-gray-50 text-gray-300`
- Error text: `text-red-600 text-sm`

**Typography:**
- Modal title: `text-lg font-bold text-gray-900`
- Section label: `text-sm font-semibold text-gray-500 uppercase tracking-wide`
- Slot time text: `text-sm font-medium`
- Duration badge: `text-xs bg-teal-50 text-teal-700 px-2 py-1 rounded-full`

**Spacing:**
- Modal padding: `p-6`
- Field gap: `gap-4`
- Slot grid gap: `gap-2`
- Footer: `pt-4 border-t border-gray-200`

**Border Radius:**
- Modal: `rounded-2xl`
- Slot buttons: `rounded-lg`
- Patient chip: `rounded-full`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `zod` — form validation
- `@tanstack/react-query` — async search + availability + mutation
- `lucide-react` — Search, Clock, User, Calendar, X, Check
- `framer-motion` — modal entrance animation
- `date-fns` — date formatting, availability parsing

**File Location:**
- Component: `src/components/agenda/AppointmentCreateModal.tsx`
- Sub-components: `src/components/agenda/PatientSearchTypeahead.tsx`, `src/components/agenda/AvailableSlotGrid.tsx`
- Schema: `src/lib/schemas/appointmentSchema.ts`
- Hook: `src/hooks/useCreateAppointment.ts`

**Hooks Used:**
- `useAuth()` — role + tenant context
- `useForm()` (React Hook Form) with Zod schema
- `useDebounce(query, 300)` — patient search debounce
- `useQuery(['availability', ...])` — slot loading
- `useMutation()` — appointment creation
- `useAgendaStore()` — prefill data from slot click

**Zod Schema:**
```typescript
const appointmentSchema = z.object({
  patient_id: z.string().uuid('Selecciona un paciente'),
  doctor_id: z.string().uuid('Selecciona un doctor'),
  scheduled_at: z.string().datetime({ message: 'Selecciona fecha y hora' }),
  appointment_type: z.enum(['consulta','procedimiento','emergencia','seguimiento','primera_vez']),
  duration_minutes: z.number().min(10).max(240),
  notes: z.string().max(500).optional(),
  treatment_plan_item_id: z.string().uuid().optional().nullable(),
  send_reminder: z.boolean().default(true),
});
```

---

## Test Cases

### Happy Path
1. 3-tap appointment creation
   - **Given:** Receptionist on calendar, empty 10:00 slot clicked
   - **When:** Modal opens pre-filled with 10:00 date/time → selects patient → clicks "Confirmar Cita"
   - **Then:** Appointment created, modal closes, calendar shows new block at 10:00, success toast "Cita agendada"

2. From patient detail tab
   - **Given:** Viewing patient profile, patient_id pre-filled
   - **When:** Opens modal → selects slot → confirms
   - **Then:** Appointment linked to patient, calendar updated

### Edge Cases
1. Doctor without available hours on selected date
   - **Given:** Doctor has no schedule configured for Saturday
   - **When:** Saturday selected
   - **Then:** Slot grid shows empty state "Sin horario disponible para este día"

2. Treatment plan link optional
   - **Given:** Patient has no active treatment plans
   - **When:** Treatment plan dropdown opened
   - **Then:** Shows "Sin planes activos" — field remains optional

### Error Cases
1. Slot taken between load and submit
   - **Given:** Slot appeared available, another user booked it before confirm
   - **When:** POST returns 409
   - **Then:** Inline error on slot "Este horario ya no está disponible. Selecciona otro."

---

## Acceptance Criteria

- [ ] Patient search typeahead with debounce (300ms)
- [ ] Recent patients shown when search is empty and focused
- [ ] Doctor select with all active doctors
- [ ] Date picker disabling past dates and >90-day horizon
- [ ] Availability grid loads real data from API
- [ ] Slot states: available, selected, occupied, blocked
- [ ] Appointment type auto-sets duration (overridable)
- [ ] 3-tap optimization: patient → slot → confirm without extra steps
- [ ] Treatment plan link (optional)
- [ ] Form validation with Zod (client + server errors)
- [ ] Loading skeletons for slots and search results
- [ ] Modal closes on success, calendar query invalidated
- [ ] Responsive: bottom-sheet mobile, centered modal tablet/desktop
- [ ] All touch targets min 44px (slots, buttons, chips)
- [ ] Keyboard: ESC closes, Tab navigation, Enter selects slot
- [ ] ARIA: dialog role, labels on slots
- [ ] All labels in es-419

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
