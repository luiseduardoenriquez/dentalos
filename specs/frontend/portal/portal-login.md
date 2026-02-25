# Inicio de Sesión — Portal del Paciente (Portal Login) — Frontend Spec

## Overview

**Screen:** Patient portal login page. Branded per clinic (logo, primary color). Supports email/phone + password login and a "magic link" option (sends email or WhatsApp link). Minimal, clean design optimized for patients, not clinical staff.

**Route:** `/portal/[clinicSlug]/login` (separate route group from admin app)

**Priority:** High

**Backend Specs:** `specs/portal/PP-01.md`

**Dependencies:** `specs/frontend/portal/portal-dashboard.md`

---

## User Flow

**Entry Points:**
- Direct link from SMS/email appointment reminder
- QR code printed at clinic
- "Portal de Pacientes" link on clinic website
- "Verificar cita" button from public booking confirmation screen

**Exit Points:**
- Successful login → `/portal/[clinicSlug]/dashboard`
- Magic link request → confirmation screen (stays on portal)
- "¿No tienes cuenta?" → contact clinic message (no self-registration)

**User Story:**
> As a patient, I want to log into my clinic's portal so that I can see my appointments, documents, and outstanding balance from my phone.

**Roles with access:** patient (unauthenticated entry point)

---

## Layout Structure

```
+------------------------------------------+
|                                           |
|         [Clinic Logo — centered]          |
|         Nombre de la Clínica              |
|                                           |
|  +--------------------------------------+ |
|  |                                      | |
|  |  Bienvenido a tu portal de salud     | |
|  |                                      | |
|  |  Correo o teléfono *                 | |
|  |  [                                 ] | |
|  |                                      | |
|  |  Contraseña *                        | |
|  |  [                          [👁]   ] | |
|  |                                      | |
|  |  [Iniciar sesión]                    | |
|  |                                      | |
|  |  ─────── o ───────                   | |
|  |                                      | |
|  |  [Recibir enlace de acceso]          | |
|  |                                      | |
|  +--------------------------------------+ |
|                                           |
|  ¿Problemas para ingresar? Contacta a     |
|  [Nombre Clínica] al [teléfono clínica]   |
|                                           |
|  Powered by DentalOS                      |
+------------------------------------------+
```

**Sections:**
1. Clinic branding — logo (from tenant settings), clinic name, optional tagline
2. Login card — email/phone input, password, primary submit button
3. Divider + magic link — "o" divider, "Recibir enlace de acceso" secondary button
4. Help text — clinic contact information for support
5. Footer — "Powered by DentalOS" (small, gray)

---

## UI Components

### Component 1: ClinicBrandingHeader

**Type:** Branded header block

**Content:**
- Clinic logo image (from `tenant.logo_url`; fallback: initials avatar with `tenant.primary_color` background)
- Clinic name (`text-xl font-semibold`)
- Optional tagline (from tenant settings, if set)

**Styling:** Primary color from `tenant.primary_color` used for:
- Submit button background
- Link text color
- Focus ring color
- Clinic name color

**Behavior:** All color customization applied via CSS custom property `--portal-primary` injected server-side from tenant settings.

### Component 2: LoginForm

**Type:** Form (React Hook Form + Zod)

**Fields:** See Form Fields section below.

**Submit behavior:**
- POST credentials to `/api/v1/portal/auth/login`
- On success: set session cookie, redirect to portal dashboard
- On 401: show inline error "Correo/teléfono o contraseña incorrectos"
- On 429 (rate limited): "Demasiados intentos. Intenta en 5 minutos."

### Component 3: PasswordInput

**Type:** Input with show/hide toggle

**Behavior:** Eye icon toggles `type="text"` / `type="password"`. Eye-off icon when shown.

### Component 4: MagicLinkButton

**Type:** Button (secondary/outline)

**Label:** "Recibir enlace de acceso"

**Behavior:**
1. Click → modal asking "¿Por cuál medio quieres recibir tu enlace?"
2. Options: Correo electrónico / WhatsApp (if clinic has WhatsApp integration)
3. Submit email/phone → POST `/api/v1/portal/auth/magic-link`
4. Success screen: "Te enviamos un enlace de acceso a [email/WhatsApp]. El enlace expira en 15 minutos."

### Component 5: MagicLinkModal

**Type:** Dialog modal (Radix UI)

**Content:**
- Radio group: "Correo electrónico" / "WhatsApp"
- Input: pre-filled from login form's email/phone field
- "Enviar enlace" button

---

## Form Fields

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| identifier | Email or Phone | Yes | Valid email format OR Colombian phone (10 digits) | "Ingresa un correo o número de teléfono válido" | "Correo o teléfono" |
| password | Password | Yes | Min 6 chars | "Ingresa tu contraseña" | "Contraseña" |

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Login | `/api/v1/portal/auth/login` | POST | `specs/portal/PP-01.md` | — |
| Request magic link | `/api/v1/portal/auth/magic-link` | POST | `specs/portal/PP-01.md` | — |
| Verify magic link token | `/api/v1/portal/auth/magic-link/verify` | POST | `specs/portal/PP-01.md` | — |
| Fetch tenant branding | `/api/v1/portal/tenant/[clinicSlug]` | GET | `specs/tenants/T-05.md` | 24h |

### State Management

**Local State (useState):**
- `showMagicLinkModal: boolean`
- `magicLinkSent: boolean`
- `isSubmitting: boolean`

**Global State (Zustand):**
- `portalAuthStore.patient` — set on successful login

**Server State (TanStack Query):**
- Query key: `['tenant-branding', clinicSlug]` — stale 24h (clinic branding rarely changes)

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Submit login | Click "Iniciar sesión" or Enter | POST credentials | Button spinner → redirect or inline error |
| Click magic link | Click "Recibir enlace de acceso" | MagicLinkModal opens | Modal slides up |
| Select channel + submit | Modal submit | POST magic link request | Modal closes → success screen |
| Wrong password | Submit with wrong credentials | 401 response | Inline error below password field |
| Rate limited | Too many attempts | 429 response | Error: "Demasiados intentos. Intenta en 5 minutos." with countdown timer |

### Animations/Transitions

- Login card: fade in on page load (300ms)
- MagicLinkModal: fade + scale in (200ms)
- Error messages: fade in (150ms) below field
- Success screen (magic link sent): crossfade with form (300ms)

---

## Loading & Error States

### Loading State
- Submit button: spinner icon + "Ingresando..." text, disabled
- Magic link modal submit: same pattern
- Tenant branding load: skeleton logo circle + skeleton title text (shows briefly on slow connections)

### Error State
- Wrong credentials (401): red inline error below password field "Correo/teléfono o contraseña incorrectos. Intenta de nuevo."
- Rate limit (429): red error below password "Demasiados intentos. Espera 5 minutos." with countdown
- Network error: toast "Error de conexión. Verifica tu internet e intenta de nuevo."
- Tenant not found (clinic slug invalid): full-page "Clínica no encontrada" with DentalOS logo

### Empty State
- Not applicable (login form is always shown)

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Full-screen layout. Login card = full width, no border/shadow. Logo and card vertically centered. Keyboard push: form scrolls up to keep fields visible. |
| Tablet (640-1024px) | Login card: 420px wide, centered with shadow. Background: subtle clinic-colored gradient or light gray. |
| Desktop (> 1024px) | Same as tablet. Max width 440px card, centered. Optional: split layout with clinic image on left half. |

---

## Accessibility

- **Focus order:** Logo (skip to main), identifier input → password → "Iniciar sesión" → "Recibir enlace de acceso"
- **Screen reader:** `<main aria-label="Portal de pacientes de {clinicName}">`. Login form has `role="form"`. Error messages in `aria-live="assertive"`. Success message in `aria-live="polite"`.
- **Keyboard navigation:** Tab through all fields. Enter submits form. Escape closes modal.
- **Color contrast:** Clinic primary color applied to button — if low contrast, DentalOS default `primary-600` used as minimum.
- **Language:** es-419 for all labels. `lang="es"` on `<html>`.

---

## Design Tokens

**Colors (dynamic from tenant):**
- Submit button: `bg-[--portal-primary]`
- Link/magic link text: `text-[--portal-primary]`
- Focus ring: `ring-[--portal-primary]`
- Fallback (if no tenant color): `--portal-primary: #0066CC`

**Static colors:**
- Card background: `bg-white`
- Page background: `bg-gray-50`
- Input: `border-gray-200 focus:ring-2`
- Help text: `text-gray-500 text-sm`
- Powered by: `text-gray-300 text-xs`

**Typography:**
- Clinic name: `text-xl font-semibold`
- Welcome message: `text-2xl font-bold text-gray-900`
- Field labels: `text-sm font-medium text-gray-700`
- Error text: `text-sm text-red-600`

**Spacing:**
- Card padding: `p-8`
- Field gap: `space-y-4`
- Logo margin: `mb-6`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `zod`
- `@tanstack/react-query`
- `@radix-ui/react-dialog` — magic link modal
- `lucide-react` — Eye, EyeOff, Mail, Phone

**File Location:**
- Page: `src/app/(portal)/[clinicSlug]/login/page.tsx`
- Components: `src/components/portal/ClinicBrandingHeader.tsx`, `src/components/portal/LoginForm.tsx`, `src/components/portal/MagicLinkModal.tsx`
- CSS: Tenant primary color injected via `style={{ '--portal-primary': tenant.primary_color }}`
- API: `src/lib/api/portal-auth.ts`

**Hooks Used:**
- `useTenantBranding(clinicSlug)` — fetch clinic logo + color
- `useMutation(portalLogin)` — submit login
- `useMutation(requestMagicLink)` — magic link

---

## Test Cases

### Happy Path
1. Patient logs in with email + password
   - **Given:** Patient account exists with email "ana@email.com" and valid password
   - **When:** Patient types credentials and clicks "Iniciar sesión"
   - **Then:** Redirect to `/portal/{clinicSlug}/dashboard`

2. Magic link via email
   - **Given:** Patient requests magic link
   - **When:** Modal opened, email selected, "Enviar enlace" clicked
   - **Then:** Success screen: "Te enviamos un enlace de acceso a ana@email.com"

### Edge Cases
1. Clinic slug not found
   - **Given:** URL `/portal/nonexistent-clinic/login`
   - **When:** Page loads
   - **Then:** "Clínica no encontrada" full-page message with DentalOS branding

2. Clinic with no WhatsApp integration
   - **Given:** Clinic has no WhatsApp Business configured
   - **When:** Patient opens magic link modal
   - **Then:** Only "Correo electrónico" option shown (WhatsApp option hidden)

### Error Cases
1. Wrong password
   - **Given:** Patient enters wrong password
   - **When:** Submits form
   - **Then:** Inline error "Correo/teléfono o contraseña incorrectos. Intenta de nuevo." No redirect.

---

## Acceptance Criteria

- [ ] Clinic logo and name (from tenant settings) displayed at top
- [ ] Clinic primary color applied to button, links, focus rings
- [ ] Identifier field accepts email or phone number
- [ ] Password field with show/hide toggle
- [ ] Login form with Zod validation (inline errors)
- [ ] "Iniciar sesión" → POST auth → redirect to portal dashboard
- [ ] "Recibir enlace de acceso" button → magic link modal
- [ ] Magic link modal: channel selection (email/WhatsApp) + send
- [ ] Magic link success screen after request
- [ ] Error handling: 401 inline, 429 with countdown, network toast
- [ ] Tenant not found: full-page error
- [ ] Responsive: full-screen mobile, centered card tablet/desktop
- [ ] Accessibility: focus trap, aria-live, keyboard navigation
- [ ] Spanish (es-419) labels

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
