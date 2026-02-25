# Registrar Clinica (Register) -- Frontend Spec

## Overview

**Screen:** Multi-step registration form for new clinic owners. Creates a tenant and the first user (clinic_owner role). Two steps: account credentials, then clinic and personal details.

**Route:** `/register`

**Priority:** Critical

**Backend Specs:** `specs/infra/authentication-rules.md` (Section 6), `specs/M1-NAVIGATION-MAP.md` Section 6.1

**Dependencies:** None (entry point)

---

## User Flow

**Entry Points:**
- Direct navigation to `/register`
- "Crear cuenta" link from `/login`
- Marketing landing page CTA

**Exit Points:**
- Successful registration redirects to `/onboarding`
- "Ya tengo cuenta" link navigates to `/login`
- Browser back returns to previous step (or `/login` from Step 1)

**User Story:**
> As a clinic_owner, I want to register my dental clinic so that I can start managing patients, appointments, and billing on DentalOS.

**Roles with access:** Public (unauthenticated). Redirects to `/dashboard` if already authenticated.

---

## Layout Structure

```
+------------------------------------------+
|            DentalOS Logo (centered)       |
+------------------------------------------+
|                                          |
|  +------------------------------------+  |
|  |  Step Indicator: [1]----[2]        |  |
|  +------------------------------------+  |
|                                          |
|  +------------------------------------+  |
|  |         Registration Card          |  |
|  |                                    |  |
|  |  STEP 1: Cuenta                    |  |
|  |  [Email]                           |  |
|  |  [Contrasena]                      |  |
|  |  [Confirmar contrasena]            |  |
|  |                                    |  |
|  |  STEP 2: Tu clinica               |  |
|  |  [Nombre de la clinica]            |  |
|  |  [Tu nombre completo]             |  |
|  |  [Telefono]                        |  |
|  |  [Pais selector]                   |  |
|  |                                    |  |
|  |  [x] Acepto terminos y cond.      |  |
|  |                                    |  |
|  |  [Siguiente / Crear cuenta btn]   |  |
|  +------------------------------------+  |
|                                          |
|  Ya tengo cuenta -> /login               |
|                                          |
+------------------------------------------+
```

**Sections:**
1. Logo area -- DentalOS logo centered above the card
2. Step indicator -- horizontal progress bar showing current step (1 of 2)
3. Registration card -- `max-w-md` centered container with step-specific form fields
4. Footer link -- "Ya tengo cuenta" link to `/login`

---

## UI Components

### Component 1: StepIndicator

**Type:** Custom progress indicator

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| currentStep | number | 1 | Active step (1 or 2) |
| totalSteps | number | 2 | Total number of steps |

**States:**
- Step 1 active: circle 1 filled `bg-blue-600`, circle 2 outline `border-gray-300`
- Step 2 active: circle 1 checkmark `bg-green-500`, circle 2 filled `bg-blue-600`
- Connecting line: `bg-blue-600` for completed segments, `bg-gray-200` for upcoming

### Component 2: CountrySelector

**Type:** Select (single)

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.3

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| options | array | LATAM countries | CO, MX, CL, AR, PE |
| defaultValue | string | "CO" | Colombia preselected |

**Options:**

| Value | Label | Flag |
|-------|-------|------|
| CO | Colombia | CO flag emoji |
| MX | Mexico | MX flag emoji |
| CL | Chile | CL flag emoji |
| AR | Argentina | AR flag emoji |
| PE | Peru | PE flag emoji |

### Component 3: PasswordStrengthIndicator

**Type:** Custom visual indicator

**Rules displayed (from `authentication-rules.md` Section 6.2):**
- Min 8 characters -- "Minimo 8 caracteres"
- At least 1 uppercase -- "Al menos una mayuscula"
- At least 1 number -- "Al menos un numero"

**Visual:** Three small pills below password field. Gray when unmet, green when met. Each pill shows check icon + rule text.

---

## Form Fields

### Step 1: Cuenta

| Field | Type | Required | Validation | Error Message (es-419) | Placeholder |
|-------|------|----------|------------|------------------------|-------------|
| email | email | Yes | Valid email, max 255 chars | "Ingresa un correo electronico valido" | "correo@tuclinica.com" |
| password | password | Yes | Min 8, 1 uppercase, 1 digit | "La contrasena no cumple los requisitos" | "Crea tu contrasena" |
| confirm_password | password | Yes | Must match password | "Las contrasenas no coinciden" | "Confirma tu contrasena" |

### Step 2: Tu clinica

| Field | Type | Required | Validation | Error Message (es-419) | Placeholder |
|-------|------|----------|------------|------------------------|-------------|
| clinic_name | text | Yes | Min 2, max 100 chars | "Ingresa el nombre de tu clinica" | "Clinica Dental Sonrisa" |
| owner_name | text | Yes | Min 2, max 100 chars | "Ingresa tu nombre completo" | "Dr. Maria Rodriguez" |
| phone | tel | Yes | Valid phone with country code (7-15 digits) | "Ingresa un numero de telefono valido" | "+57 300 123 4567" |
| country | select | Yes | One of CO, MX, CL, AR, PE | "Selecciona un pais" | -- |
| terms_accepted | checkbox | Yes | Must be true | "Debes aceptar los terminos y condiciones" | -- |

**Zod Schema:**
```typescript
const step1Schema = z.object({
  email: z.string().email("Ingresa un correo electronico valido").max(255),
  password: z.string()
    .min(8, "Minimo 8 caracteres")
    .regex(/[A-Z]/, "Debe contener al menos una mayuscula")
    .regex(/\d/, "Debe contener al menos un numero"),
  confirm_password: z.string(),
}).refine((data) => data.password === data.confirm_password, {
  message: "Las contrasenas no coinciden",
  path: ["confirm_password"],
});

const step2Schema = z.object({
  clinic_name: z.string().min(2, "Minimo 2 caracteres").max(100),
  owner_name: z.string().min(2, "Minimo 2 caracteres").max(100),
  phone: z.string().regex(/^\+?\d{7,15}$/, "Ingresa un numero de telefono valido"),
  country: z.enum(["CO", "MX", "CL", "AR", "PE"], {
    errorMap: () => ({ message: "Selecciona un pais" }),
  }),
  terms_accepted: z.literal(true, {
    errorMap: () => ({ message: "Debes aceptar los terminos y condiciones" }),
  }),
});
```

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Register | `/api/v1/auth/register` | POST | `specs/infra/authentication-rules.md` | None |

**Request Body:**
```json
{
  "email": "doctor@clinica.co",
  "password": "SecurePass1",
  "clinic_name": "Clinica Dental Sonrisa",
  "owner_name": "Dr. Maria Rodriguez",
  "phone": "+573001234567",
  "country": "CO"
}
```

### State Management

**Local State (useState):**
- `currentStep: number` -- 1 or 2
- `step1Data: Step1Data | null` -- persisted when moving to step 2
- `serverError: string | null` -- backend error message

**Global State (Zustand):**
- `authStore.user` -- set after successful registration
- `authStore.tenant` -- set after successful registration
- `authStore.accessToken` -- stored in memory

**Server State (TanStack Query):**
- Mutation: `useMutation({ mutationFn: registerClinic })` for register POST

### Error Code Mapping

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `email_already_exists` | 409 | "Este correo ya esta registrado. Intenta iniciar sesion." |
| `weak_password` | 422 | "La contrasena no cumple los requisitos de seguridad." |
| `invalid_country` | 422 | "Pais no soportado actualmente." |
| `registration_disabled` | 503 | "El registro esta temporalmente deshabilitado. Intenta mas tarde." |

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Fill Step 1, click "Siguiente" | Button click | Validate Step 1 fields, advance to Step 2 | Step indicator updates. Fields animate out/in. |
| Click "Atras" on Step 2 | Button click | Return to Step 1 with preserved data | Step indicator updates. Fields animate. |
| Fill Step 2, click "Crear cuenta" | Button click | POST to register endpoint | Button spinner. On success: redirect to `/onboarding`. |
| Toggle password visibility | Click eye icon | Show/hide password | Icon toggles |
| Click "Terminos y condiciones" | Click link | Opens terms modal or new tab | Modal overlay or `target="_blank"` |

### Animations/Transitions

- Step transition: `framer-motion` slide -- Step 1 slides left out, Step 2 slides in from right (and reverse)
- Error banner: slide down from top with `opacity` and `y` animation
- Password strength pills: fade in green with `transition-colors duration-200`

---

## Loading & Error States

### Loading State
- "Crear cuenta" button: text changes to "Creando cuenta..." with spinner
- All form fields disabled during submission
- Step indicator non-interactive during submission

### Error State
- Server errors: inline banner above the form within the card (`bg-red-50 rounded-lg p-3`)
- Field validation: inline below each field in `text-xs text-red-600`
- Email conflict: banner with link "Intenta iniciar sesion" pointing to `/login`

### Empty State
- Not applicable -- registration form is always rendered

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Card fills full width `px-4`. Single column. Phone field full width. |
| Tablet (640-1024px) | Card centered `max-w-md`. Step indicator with labels. Card `shadow-md rounded-xl`. |
| Desktop (> 1024px) | Same as tablet. Optional: split layout with illustration on left, form on right. |

**Tablet priority:** High -- clinic owners may register from a tablet during initial setup.

---

## Accessibility

- **Focus order:** Step 1: email -> password -> confirm_password -> "Siguiente" button. Step 2: clinic_name -> owner_name -> phone -> country -> terms checkbox -> "Crear cuenta" button.
- **Screen reader:** `aria-label="Formulario de registro, paso {n} de 2"` on form. `aria-live="polite"` on step indicator for step change announcements. `role="alert"` on error banner.
- **Keyboard navigation:** Enter advances step or submits (context-aware). Tab navigates fields. Escape clears server error.
- **Color contrast:** WCAG AA on all text and interactive elements.
- **Language:** All labels, placeholders, errors, and ARIA attributes in es-419.

---

## Design Tokens

**Colors:**
- Primary button: `bg-blue-600 hover:bg-blue-700 text-white`
- Secondary button (Atras): `bg-gray-100 text-gray-700 hover:bg-gray-200`
- Step active: `bg-blue-600 text-white`
- Step completed: `bg-green-500 text-white`
- Step upcoming: `border-gray-300 text-gray-400`
- Strength pill met: `bg-green-100 text-green-700`
- Strength pill unmet: `bg-gray-100 text-gray-400`

**Typography:**
- Step title: `text-lg font-semibold text-gray-700`
- Labels: `text-sm font-medium text-gray-700`
- Helper text: `text-xs text-gray-400`

**Spacing:**
- Card padding: `p-6 md:p-8`
- Field gap: `space-y-4`
- Step indicator margin: `mb-6`
- Button row gap: `gap-3` (Atras + Siguiente side by side on Step 2)

**Border Radius:**
- Card: `rounded-xl`
- Inputs: `rounded-md`
- Buttons: `rounded-lg`
- Step circles: `rounded-full`
- Strength pills: `rounded-full`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `zod` + `@hookform/resolvers`
- `lucide-react` -- Eye, EyeOff, Check, ChevronRight, ChevronLeft, Loader2
- `framer-motion` -- step transition animations

**File Location:**
- Page: `src/app/(public)/register/page.tsx`
- Components: `src/components/auth/RegisterForm.tsx`, `src/components/auth/StepIndicator.tsx`, `src/components/auth/PasswordStrengthIndicator.tsx`, `src/components/auth/CountrySelector.tsx`
- Schema: `src/lib/schemas/auth.ts`
- API: `src/lib/api/auth.ts`

**Hooks Used:**
- `useForm()` -- React Hook Form with per-step Zod resolver
- `useMutation()` -- TanStack Query for register POST
- `useRouter()` -- Next.js navigation after success
- `useAuthStore()` -- Zustand store for post-registration auth state
- `useState()` -- step tracking and step 1 data persistence

**Form Library:**
- React Hook Form with separate Zod schemas per step
- `mode: "onBlur"` for field validation
- Step 1 data preserved in local state when advancing to Step 2

---

## Test Cases

### Happy Path
1. Complete two-step registration
   - **Given:** User is on `/register`
   - **When:** User fills Step 1 (email, password, confirm), clicks "Siguiente", fills Step 2 (clinic, name, phone, country, terms), clicks "Crear cuenta"
   - **Then:** Account is created, user is redirected to `/onboarding`

### Edge Cases
1. Navigate back from Step 2 to Step 1
   - **Given:** User has completed Step 1 and is on Step 2
   - **When:** User clicks "Atras"
   - **Then:** Step 1 fields are pre-filled with previously entered data

2. Password mismatch
   - **Given:** User is on Step 1
   - **When:** Password and confirm_password do not match
   - **Then:** "Las contrasenas no coinciden" error appears on confirm_password field

3. Browser refresh on Step 2
   - **Given:** User is on Step 2
   - **When:** User refreshes the page
   - **Then:** Form resets to Step 1 (step 1 data is in memory only)

### Error Cases
1. Email already registered
   - **Given:** Email is already in the system
   - **When:** Registration is submitted
   - **Then:** Error banner: "Este correo ya esta registrado" with link to `/login`

2. Weak password
   - **Given:** Password does not meet requirements
   - **When:** User leaves password field (onBlur)
   - **Then:** Strength indicator shows unmet rules in gray; field error in red

---

## Acceptance Criteria

- [ ] Two-step form with animated transitions between steps
- [ ] Step 1: email, password, confirm_password with Zod validation
- [ ] Step 2: clinic_name, owner_name, phone, country selector, terms checkbox
- [ ] Password strength indicator showing 3 rules in real-time
- [ ] Country selector with CO, MX, CL, AR, PE options
- [ ] Terms checkbox required before submission
- [ ] Back navigation preserves Step 1 data
- [ ] Successful registration redirects to `/onboarding`
- [ ] Error handling: email conflict (409), weak password (422), server errors
- [ ] Loading state: spinner on submit button, fields disabled
- [ ] "Ya tengo cuenta" link navigates to `/login`
- [ ] Responsive on all breakpoints (mobile, tablet, desktop)
- [ ] Accessibility: focus order, ARIA labels, keyboard navigation
- [ ] Spanish (es-419) labels and messages throughout

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
