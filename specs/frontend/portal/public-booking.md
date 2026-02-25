# Reserva de Cita Publica (Public Appointment Booking) — Frontend Spec

## Overview

**Screen:** Public appointment booking page — no login required. Clinic-branded with logo, name, and primary color from tenant config. 4-step flow: select service type, select doctor (optional), pick date and time slot, submit contact info (new patient) or login (existing patient). Confirmation screen includes "Agregar a calendario" button.

**Route:** `/book/{clinic-slug}` (public, no auth required)

**Priority:** High

**Backend Specs:** `specs/appointments/public-booking.md` (AP-15), `specs/appointments/availability.md` (AP-16)

**Dependencies:** `specs/frontend/design-system/design-system.md`, `specs/frontend/portal/portal-login.md`

---

## User Flow

**Entry Points:**
- QR code or link shared by clinic on social media, website, WhatsApp
- "Reservar cita" button on clinic's public profile page
- Google Business listing link

**Exit Points:**
- Success → confirmation screen with "Agregar a calendario" and "Volver al inicio" options
- "Cancelar" or browser back on any step → previous step or landing page

**User Story:**
> As a new or existing patient, I want to book a dental appointment online from my phone without calling the clinic so that I can schedule at any time and avoid phone tag.

**Roles with access:** Public (unauthenticated). Existing patients can optionally log in for faster booking.

---

## Layout Structure

```
+------------------------------------------+
|  [Clinic logo]  [Clinic name]             |
|  "Reserva tu cita"                        |
+------------------------------------------+
|  [Step progress: 1 2 3 4]                |
+------------------------------------------+
|                                          |
|  [Step Content Area]                     |
|                                          |
+------------------------------------------+
|  [Atras]  [Siguiente / Confirmar]        |
+------------------------------------------+
|  Powered by DentalOS (subtle footer)     |
+------------------------------------------+
```

**Sections:**
1. Clinic branding header — logo + name + "Reserva tu cita" headline
2. Step progress indicator — 4 steps
3. Step content area — varies per step
4. Navigation — back + next/confirm
5. Footer — "Powered by DentalOS" (subtle branding)

---

## Clinic Branding System

Tenant branding fetched via `/api/v1/public/clinics/{slug}/branding`:
```typescript
{
  logo_url: string;
  clinic_name: string;
  primary_color: string;   // hex color, e.g., "#0D9488" (teal)
  secondary_color: string;
  timezone: string;        // "America/Bogota"
  address: string;
  phone: string;
}
```

**CSS custom property:** `style={{ '--clinic-primary': brandingData.primary_color }}` — all primary-colored elements use `var(--clinic-primary)` via inline style or Tailwind's `[color:var(--clinic-primary)]`.

---

## Step Specifications

### Step 1: Selecciona el Tipo de Servicio

**Layout:** Card grid — 2 columns on tablet/desktop, 1 column on mobile

**Service type card:**
- Large icon (48px) from predefined icon set per service type
- Service name `text-base font-semibold text-gray-900`
- Duration estimate `text-sm text-gray-500` — "Aprox. 30 minutos"
- Optional price range `text-sm text-gray-500` — "Desde $50.000" (if clinic enables public pricing)

**Service types (examples):**
- Consulta General (CalendarCheck icon)
- Limpieza Dental (Sparkles icon)
- Ortodoncia (AlignCenter icon)
- Endodoncia (Zap icon)
- Extraccion (Scissors icon)
- Blanqueamiento (Sun icon)
- Urgencia Dental (AlertTriangle icon)
- Primera Consulta (Star icon)

**Clinic customizes which services appear.** Data from `/api/v1/public/clinics/{slug}/services`.

**Selection state:**
- Unselected: `border-2 border-gray-200 bg-white hover:border-[--clinic-primary]`
- Selected: `border-2 border-[--clinic-primary] bg-[--clinic-primary]/5 ring-2 ring-[--clinic-primary]/20`

**"Siguiente" disabled until a service is selected.**

---

### Step 2: Selecciona tu Odontologo (Opcional)

**Header:** `"¿Prefieres un odontologo en particular?"` `text-base font-medium text-gray-600`

**"Sin preferencia" option:** First card — always shown.
- `UserCircle` icon + `"Sin preferencia"` `text-base font-semibold` + `"Asignaremos el odontologo disponible"` `text-sm text-gray-500`

**Doctor cards:** One per available doctor for selected service type.
- Photo (circular 56px) or initials avatar
- Name: `"Dr. {nombre}"` `text-base font-semibold`
- Specialty: `text-sm text-gray-500`
- Next availability: `"Disponible {dia}"` — e.g., `"Disponible hoy"`, `"Disponible manana"`, `"Disponible el jueves"`

**This step is SKIPPABLE** — "Sin preferencia" is always pre-selected. User can proceed without explicit doctor selection.

**"Siguiente" always enabled** (default = no preference).

---

### Step 3: Selecciona Fecha y Hora

**Two-panel layout on tablet/desktop:**
- Left panel (40%): Calendar picker
- Right panel (60%): Time slots grid

**Mobile:** Calendar then time slots stacked vertically.

**Calendar:**
- Month view with navigation arrows `ChevronLeft / ChevronRight`
- Available dates: standard styling, clickable
- Unavailable dates (no slots): `text-gray-300 cursor-not-allowed line-through`
- Today: `font-bold text-[--clinic-primary]`
- Selected date: `bg-[--clinic-primary] text-white rounded-full`
- Past dates: `text-gray-200 cursor-not-allowed`

**Time slot grid (after date selected):**
- Title: `"Horarios disponibles para el {dia, fecha}"` `text-sm font-medium text-gray-600`
- Grid: 2-column, each slot `h-10 rounded-lg` button
- Available: `bg-white border border-gray-200 hover:border-[--clinic-primary] text-sm font-medium text-gray-700`
- Selected: `bg-[--clinic-primary] text-white border-[--clinic-primary]`
- Booked/unavailable: `bg-gray-50 text-gray-300 border-gray-100 cursor-not-allowed`

**Loading slots:** When date selected, fetch slots → skeleton grid `animate-pulse`.

**No slots available on selected date:** `"No hay horarios disponibles para este dia. Selecciona otra fecha."` — calendar auto-highlights next available date.

**"Siguiente" disabled until date + time selected.**

---

### Step 4: Tus Datos de Contacto

**Two paths — toggle at top:**
- [Paciente nuevo] [Ya soy paciente] — tab toggle

**Tab: Paciente Nuevo (default)**

| Field | Type | Required | Validation | Error Message (es-419) | Placeholder |
|-------|------|----------|------------|------------------------|-------------|
| primer_nombre | text | Yes | Min 2 chars | "El nombre es obligatorio" | "Nombre" |
| primer_apellido | text | Yes | Min 2 chars | "El apellido es obligatorio" | "Apellido" |
| telefono | tel | Yes | E.164 format | "Ingresa un numero de telefono valido" | "+57 300 000 0000" |
| correo | email | No | Valid format | "Correo invalido" | "correo@ejemplo.com" |
| numero_documento | text | No | — | — | "Cedula o documento (opcional)" |
| notas | textarea | No | Max 200 chars | — | "Motivo de la cita (opcional)" |

**Terms acceptance:**
- Checkbox: `"Acepto que la clinica contacte al numero proporcionado para confirmar mi cita"` — required
- Privacy link: `"Politica de privacidad"` opens in new tab

**Tab: Ya soy Paciente**

- Shows mini login form: email + password
- Or: "Continuar sin cuenta" link that switches back to new patient form

**Confirmation summary (at bottom of Step 4, before submit):**
- Clinic name + address
- Service: "{service name}"
- Doctor: "Dr. {name}" or "Sin preferencia"
- Date + time: "Martes, 25 de febrero 2026 a las 10:30 AM"
- Duration estimate: "Aprox. 30 minutos"

**Submit button:** `"Confirmar Cita"` `h-14 w-full bg-[--clinic-primary] text-white text-base font-semibold rounded-xl`

---

## Confirmation Screen

After successful booking:

```
+------------------------------------------+
|  [Clinic logo]                            |
|  [Large CalendarCheck icon, green, 64px] |
|  "¡Cita confirmada!"                     |
|  "Te veremos el martes 25 de feb a las   |
|   10:30 AM"                              |
|                                          |
|  [Booking ref: #B-2026-00234]            |
|  [Add to calendar btn]                   |
|  [WhatsApp reminder checkbox — opt-in]   |
|  [Agregar recordatorio por WhatsApp]     |
|  [Volver al inicio btn]                  |
+------------------------------------------+
```

**"Agregar a calendario" button:**
- Generates `data:text/calendar` blob with ICS content
- Filename: `cita-dental-{date}.ics`
- Click: browser downloads ICS file, opens in default calendar app
- ICS content: `SUMMARY: Cita Dental — {clinic_name}\nDTSTART: {datetime}\nDTEND: {datetime+duration}\nLOCATION: {clinic_address}`

**WhatsApp reminder opt-in:**
- Checkbox (default unchecked): `"Recibir recordatorio por WhatsApp el dia anterior"`
- Only shown if clinic has WhatsApp integration enabled
- Checking sends `PATCH /api/v1/public/appointments/{id}/reminder-optin`

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Get clinic branding | `/api/v1/public/clinics/{slug}/branding` | GET | `specs/appointments/public-booking.md` | 10min |
| Get service types | `/api/v1/public/clinics/{slug}/services` | GET | `specs/appointments/public-booking.md` | 10min |
| Get available doctors | `/api/v1/public/clinics/{slug}/doctors?service_id={id}` | GET | `specs/appointments/public-booking.md` | 5min |
| Get available dates | `/api/v1/public/clinics/{slug}/availability?service_id={id}&doctor_id={id}&month={YYYY-MM}` | GET | `specs/appointments/availability.md` | 2min |
| Get time slots | `/api/v1/public/clinics/{slug}/slots?service_id={id}&doctor_id={id}&date={YYYY-MM-DD}` | GET | `specs/appointments/availability.md` | 30s |
| Create booking | `/api/v1/public/clinics/{slug}/appointments` | POST | `specs/appointments/public-booking.md` | None |
| Opt-in reminder | `/api/v1/public/appointments/{id}/reminder-optin` | PATCH | — | None |

### Booking POST Request

```typescript
{
  service_id: string;
  doctor_id: string | null;
  date: string;             // YYYY-MM-DD
  time_slot: string;        // HH:MM
  patient: {
    primer_nombre: string;
    primer_apellido: string;
    telefono: string;
    correo?: string;
    numero_documento?: string;
    notas?: string;
  };
  terms_accepted: true;
}
```

### State Management

**Local State (useState):**
- `currentStep: 1 | 2 | 3 | 4`
- `selectedService: ServiceType | null`
- `selectedDoctor: Doctor | null | 'no_preference'`
- `selectedDate: string | null`
- `selectedSlot: string | null`
- `bookingConfirmation: { id, reference } | null`

**Server State (TanStack Query):**
- Branding: `useQuery(['clinic-branding', slug], { staleTime: 10 * 60 * 1000 })`
- Services: `useQuery(['clinic-services', slug], { staleTime: 10 * 60 * 1000 })`
- Availability (calendar): `useQuery(['availability', slug, serviceId, doctorId, month])`
- Slots: `useQuery(['slots', slug, serviceId, doctorId, date], { enabled: !!selectedDate })`
- Booking: `useMutation({ mutationFn: createBooking })`

### Error Code Mapping

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `slot_taken` | 409 | "Este horario fue reservado por otro paciente. Selecciona otro horario." |
| `clinic_closed` | 422 | "La clinica no atiende en el horario seleccionado." |
| `service_unavailable` | 422 | "Este servicio no esta disponible en la fecha seleccionada." |

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click service card | Click | Card selected, "Siguiente" enabled | Border highlight |
| Click "Siguiente" Step 1 | Button | Advance to Step 2 | Slide animation |
| Click doctor card | Click | Doctor selected | Card highlight |
| Click month nav arrow | Click | Load new month availability | Calendar skeleton |
| Click available date | Click | Fetch time slots | Slot grid skeleton |
| Click time slot | Click | Slot selected, "Siguiente" enabled | Slot fills with primary color |
| Click "Siguiente" Step 3 | Button | Advance to Step 4 | Slide animation |
| Submit form (Step 4) | Click "Confirmar Cita" | POST booking | Loading state → confirmation screen |
| Click "Agregar a calendario" | Click | Download ICS file | Browser download |
| Slot taken error (409) | API error | Show error, return to Step 3 | Toast + step back |

### Animations/Transitions

- Step transitions: slide from right (forward) `x: 40 → 0, opacity 0 → 1` 250ms
- Step back: slide from left `x: -40 → 0` 250ms
- Service card selection: border + background transition `duration-150`
- Calendar date selection: `scale 1 → 1.1 → 1` + fill color 200ms
- Time slot selection: same scale + fill
- Confirmation screen: confetti-like CSS animation + checkmark SVG stroke 600ms

---

## Loading & Error States

### Loading State
- Service types: 4 skeleton cards `h-24 animate-pulse rounded-xl`
- Calendar dates: month skeleton `animate-pulse` on individual date cells
- Time slots: grid of 6 skeleton slot buttons
- Submit: button "Procesando..." + spinner, form fields disabled

### Error State
- Slot taken: toast `"Este horario fue reservado. Selecciona otro."` + auto-return to Step 3
- Network error: banner `"Error de conexion. Verifica tu internet."` + retry within current step
- Invalid booking data: field-level errors in Step 4

### Empty State
- No services configured: "La clinica no tiene servicios disponibles para reserva en linea. Llama al {phone}"
- No available dates in month: calendar shows all grayed, "Sin disponibilidad en {month}. Prueba el proximo mes." + auto-advance month

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Service cards 1 column. Calendar full-width. Slots 2 columns. Step 4 fields full-width. Submit button full-width, 56px height. |
| Tablet (640-1024px) | Service cards 2 columns. Calendar + slots side by side. Step 4 `max-w-lg` centered. |
| Desktop (> 1024px) | Service cards 3 columns. Max width `max-w-2xl` centered. Same as tablet layout. |

**Mobile priority:** Critical — this is a public patient-facing page. Most bookings will happen on mobile. Form inputs 16px to prevent iOS auto-zoom. Touch targets min 44px throughout.

---

## Accessibility

- **Focus order:** Service cards (keyboard selectable) → "Siguiente" → Doctor cards → Calendar dates → Time slots → Form fields → Submit
- **Screen reader:** Service cards: `role="radio" aria-checked` within `role="radiogroup" aria-label="Tipo de servicio"`. Calendar: `role="grid" aria-label="Seleccionar fecha"`, each date `role="gridcell"`. Time slots: `role="radio"`. Confirmation: `role="status" aria-live="polite"` announces "Cita confirmada" on success.
- **Keyboard navigation:** Arrow keys between service cards, doctor cards, and time slots. Tab between step sections. Enter selects focused item.
- **Color customization:** Clinic's primary color applied — contrast ratio verified client-side. If `primary_color` fails WCAG AA contrast against white text, fall back to `#0D9488` (DentalOS teal).
- **Language:** All patient-facing text in es-419. Date formats: `new Intl.DateTimeFormat('es-419', ...)`.

---

## Design Tokens

**Colors:**
- Primary (clinic branded): `var(--clinic-primary)` — fallback `#0D9488`
- Unselected card: `border-gray-200 bg-white`
- Selected card: `border-[--clinic-primary] bg-[--clinic-primary]/5`
- Calendar today: `text-[--clinic-primary] font-bold`
- Calendar selected: `bg-[--clinic-primary] text-white`
- Slot selected: `bg-[--clinic-primary] text-white`
- Confirmation icon: `text-green-500`
- Footer branding: `text-gray-300 text-xs`

**Typography:**
- Clinic name: `text-xl font-bold text-gray-900`
- Page headline: `text-2xl font-bold text-gray-900`
- Step titles: `text-lg font-semibold text-gray-700`
- Service name: `text-base font-semibold text-gray-900`
- Duration: `text-sm text-gray-500`
- Slot time: `text-sm font-medium`

**Spacing:**
- Page max width: `max-w-2xl mx-auto px-4 py-6`
- Service card: `p-5 rounded-2xl`
- Service grid gap: `gap-3`
- Navigation row: `mt-8 flex gap-3`

---

## Implementation Notes

**Dependencies (npm):**
- `lucide-react` — CalendarCheck, ChevronLeft, ChevronRight, User, Clock, MapPin, Download
- `framer-motion` — step slide transitions
- `react-hook-form` + `zod` — Step 4 form

**File Location:**
- Page: `src/app/(public)/book/[slug]/page.tsx`
- Components: `src/components/booking/PublicBookingWizard.tsx`, `src/components/booking/steps/ServiceStep.tsx`, `src/components/booking/steps/DoctorStep.tsx`, `src/components/booking/steps/DateTimeStep.tsx`, `src/components/booking/steps/ContactStep.tsx`, `src/components/booking/BookingConfirmation.tsx`
- Utils: `src/lib/utils/generateICS.ts`

**ICS Generation:**
```typescript
export function generateICS(appointment: BookingConfirmation): string {
  return [
    'BEGIN:VCALENDAR', 'VERSION:2.0',
    'BEGIN:VEVENT',
    `SUMMARY:Cita Dental — ${appointment.clinic_name}`,
    `DTSTART:${formatICSDate(appointment.datetime)}`,
    `DTEND:${formatICSDate(addMinutes(appointment.datetime, appointment.duration_min))}`,
    `LOCATION:${appointment.clinic_address}`,
    `DESCRIPTION:${appointment.service_name}`,
    'END:VEVENT', 'END:VCALENDAR'
  ].join('\r\n');
}
```

---

## Test Cases

### Happy Path
1. New patient books first appointment
   - **Given:** Clinic has services configured, slots available tomorrow
   - **When:** Patient selects service → doctor → date → time → fills form → confirms
   - **Then:** Confirmation screen shown, ICS download available, booking reference displayed

### Edge Cases
1. Slot taken between Step 3 and submit
   - **Given:** Patient selected time, fills Step 4 form, submits
   - **When:** API returns 409 (slot taken while filling form)
   - **Then:** Toast "Este horario fue reservado", auto-return to Step 3, slots refreshed

2. No doctor preference selected
   - **Given:** Patient clicks "Sin preferencia" (default) in Step 2
   - **When:** Advances through flow
   - **Then:** Booking sent with `doctor_id: null`, clinic assigns available doctor

### Error Cases
1. Invalid phone number
   - **Given:** Patient enters "123" as phone
   - **When:** Zod validates on submit
   - **Then:** Inline error "Ingresa un numero de telefono valido", no API call

---

## Acceptance Criteria

- [ ] Clinic-branded header with logo, name, and primary color from tenant config
- [ ] 4-step flow with progress indicator
- [ ] Step 1: service type cards with icon, name, duration
- [ ] Step 2: doctor cards with photo, name, specialty, next availability (or "Sin preferencia")
- [ ] Step 3: interactive calendar with available/unavailable date indicators
- [ ] Step 3: time slot grid, disabled for booked slots
- [ ] Step 4: new patient form OR login for existing patient
- [ ] Step 4: booking summary before submit
- [ ] Terms acceptance required checkbox
- [ ] Confirmation screen with booking reference
- [ ] "Agregar a calendario" generates and downloads ICS file
- [ ] 409 slot-taken handled: user returned to Step 3 with fresh slots
- [ ] Mobile-first: 16px inputs (no iOS zoom), full-width buttons, 44px+ touch targets
- [ ] Clinic primary color applied throughout with WCAG contrast fallback
- [ ] Accessibility: radiogroup for cards, keyboard navigation, live announcements
- [ ] Spanish (es-419) with proper date formatting

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
