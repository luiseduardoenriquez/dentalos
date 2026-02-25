# Iniciar Sesion (Login) -- Frontend Spec

## Overview

**Screen:** Login screen for clinic staff authentication. Email and password form with error handling for invalid credentials, locked accounts, and suspended tenants.

**Route:** `/login`

**Priority:** Critical

**Backend Specs:** `specs/infra/authentication-rules.md` (Sections 2.1, 6.3, 10)

**Dependencies:** None (entry point)

---

## User Flow

**Entry Points:**
- Direct navigation to `/login`
- Redirect from any `(dashboard)` route when unauthenticated
- Redirect after token expiry and failed refresh
- Link from `/register` ("Ya tengo cuenta")
- Redirect after successful password reset (`/reset-password`)

**Exit Points:**
- Successful login redirects to `/dashboard`
- "Olvide mi contrasena" link navigates to `/forgot-password`
- "Crear cuenta" link navigates to `/register`

**User Story:**
> As a clinic_owner | doctor | assistant | receptionist, I want to log in with my email and password so that I can access my clinic's dashboard.

**Roles with access:** Public (unauthenticated). Redirects to `/dashboard` if already authenticated.

---

## Layout Structure

```
+------------------------------------------+
|            DentalOS Logo (centered)       |
+------------------------------------------+
|                                          |
|         +------------------------+       |
|         |     Login Card         |       |
|         |                        |       |
|         |  [Email input]         |       |
|         |  [Password input]      |       |
|         |                        |       |
|         |  [Olvide contrasena]   |       |
|         |                        |       |
|         |  [Iniciar Sesion btn]  |       |
|         |                        |       |
|         |  --- o ---             |       |
|         |                        |       |
|         |  [Crear cuenta link]   |       |
|         +------------------------+       |
|                                          |
+------------------------------------------+
```

**Sections:**
1. Logo area -- DentalOS logo centered above the card
2. Login card -- `max-w-sm` centered container with form fields, actions, and links

---

## UI Components

### Component 1: LoginCard

**Type:** Card

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.4

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| variant | string | "default" | Card style |

**States:**
- Default -- form ready for input
- Submitting -- button shows spinner, fields disabled
- Error -- inline error banner above form
- Success -- brief checkmark before redirect

### Component 2: SubmitButton

**Type:** Button

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.1

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| variant | string | "primary" | `bg-blue-600 text-white` |
| size | string | "lg" | 48px height, full width |
| isLoading | boolean | false | Shows spinner during submission |

**Behavior:**
- Click submits the form
- Disabled while `isLoading` is true
- Full width: `w-full`

---

## Form Fields

| Field | Type | Required | Validation | Error Message (es-419) | Placeholder |
|-------|------|----------|------------|------------------------|-------------|
| email | email | Yes | Valid email format, max 255 chars | "Ingresa un correo electronico valido" | "correo@ejemplo.com" |
| password | password | Yes | Min 1 char (server validates strength) | "La contrasena es obligatoria" | "Tu contrasena" |

**Password field:** Includes visibility toggle icon (eye/eye-off) from Lucide React.

**Zod Schema:**
```typescript
const loginSchema = z.object({
  email: z.string().email("Ingresa un correo electronico valido").max(255),
  password: z.string().min(1, "La contrasena es obligatoria"),
});
```

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Login | `/api/v1/auth/login` | POST | `specs/infra/authentication-rules.md` Section 2.1 | None |
| Refresh | `/api/v1/auth/refresh` | POST | `specs/infra/authentication-rules.md` Section 2.2 | None |

### State Management

**Local State (useState):**
- `serverError: string | null` -- backend error message mapped to Spanish
- `isRedirecting: boolean` -- true after successful login, before navigation completes

**Global State (Zustand):**
- `authStore.user` -- set on successful login with user object from response
- `authStore.tenant` -- set on successful login with tenant object from response
- `authStore.accessToken` -- stored in memory (not localStorage)

**Server State (TanStack Query):**
- Mutation: `useMutation({ mutationFn: loginUser })` for login POST
- No query keys -- login is a one-shot mutation

### Error Code Mapping (Backend -> Spanish UI)

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `invalid_credentials` | 401 | "Correo o contrasena incorrectos" |
| `account_locked` | 423 | "Cuenta bloqueada temporalmente. Intenta de nuevo en {minutes} minutos." |
| `rate_limit_exceeded` | 429 | "Demasiados intentos. Espera {seconds} segundos." |
| `tenant_suspended` | 403 | "Tu clinica esta suspendida. Contacta soporte." |
| `tenant_cancelled` | 403 | "La cuenta de esta clinica ha sido cancelada." |
| `tenant_provisioning` | 503 | "Tu clinica se esta configurando. Intenta en unos momentos." |

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Submit form | Click button or Enter key | POST `/api/v1/auth/login` | Button spinner, then redirect or error |
| Toggle password | Click eye icon | Show/hide password text | Icon toggles between Eye and EyeOff |
| Click "Olvide contrasena" | Click link | Navigate to `/forgot-password` | Standard link navigation |
| Click "Crear cuenta" | Click link | Navigate to `/register` | Standard link navigation |

### Animations/Transitions

- Error banner slides in from top: `motion.div` with `initial={{ opacity: 0, y: -8 }}` and `animate={{ opacity: 1, y: 0 }}`
- Page fade-in on mount: 200ms ease-out opacity transition
- Success state: brief checkmark icon (300ms) before redirect

---

## Loading & Error States

### Loading State
- Button text changes to "Iniciando sesion..." with `animate-spin` spinner
- Both input fields become `disabled` with `opacity-50`
- No skeleton needed -- form is always available immediately

### Error State
- Inline error banner above the form inside the card: `bg-red-50 border border-red-200 rounded-lg p-3`
- Red `XCircle` icon + error message text in `text-sm text-red-700`
- Banner persists until user modifies a field or re-submits
- Field-level validation errors appear below each input in `text-xs text-red-600`

### Empty State
- Not applicable -- login form is always rendered

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Card fills full width with `px-4`. Logo smaller (`h-8`). No card shadow, flat design. |
| Tablet (640-1024px) | Card centered with `max-w-sm`. Logo `h-10`. Card has `shadow-md rounded-xl`. |
| Desktop (> 1024px) | Same as tablet. Centered vertically and horizontally in viewport. |

**Tablet priority:** High -- login is used on all devices including clinical tablets. Touch targets min 48px for inputs and button.

---

## Accessibility

- **Focus order:** Email input -> Password input -> Toggle visibility -> "Olvide contrasena" link -> Submit button -> "Crear cuenta" link
- **Screen reader:** `aria-label="Formulario de inicio de sesion"` on form. `role="alert"` on error banner for live announcements. `aria-describedby` linking inputs to error messages.
- **Keyboard navigation:** Enter submits from any field. Tab navigates focus order. Escape clears server error.
- **Color contrast:** WCAG AA -- all text on white card meets 4.5:1. Red error text on `red-50` background meets 4.5:1.
- **Language:** `lang="es-419"` on html element. All labels, placeholders, and errors in Latin American Spanish.

---

## Design Tokens

**Colors:**
- Primary button: `bg-blue-600 hover:bg-blue-700 text-white`
- Card background: `bg-white dark:bg-gray-900`
- Page background: `bg-gray-50 dark:bg-gray-950`
- Error banner: `bg-red-50 border-red-200 text-red-700`
- Links: `text-blue-600 hover:text-blue-700 dark:text-blue-400`

**Typography:**
- Logo: `text-2xl font-bold font-inter text-blue-600`
- Card title (implicit): None -- logo serves as heading
- Labels: `text-sm font-medium text-gray-700 dark:text-gray-300`
- Body/links: `text-sm text-gray-500`
- Error: `text-xs text-red-600`

**Spacing:**
- Page: `min-h-screen flex items-center justify-center px-4`
- Card padding: `p-6 md:p-8`
- Field gap: `space-y-4`
- Button margin top: `mt-6`

**Border Radius:**
- Card: `rounded-xl`
- Inputs: `rounded-md`
- Button: `rounded-lg`
- Error banner: `rounded-lg`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` -- form state management
- `zod` + `@hookform/resolvers` -- schema validation
- `lucide-react` -- Eye, EyeOff, XCircle, Loader2 icons
- `framer-motion` -- error banner animation

**File Location:**
- Page: `src/app/(public)/login/page.tsx`
- Components: `src/components/auth/LoginForm.tsx`
- Schema: `src/lib/schemas/auth.ts`
- API: `src/lib/api/auth.ts`

**Hooks Used:**
- `useForm()` -- React Hook Form with Zod resolver
- `useMutation()` -- TanStack Query for login POST
- `useRouter()` -- Next.js navigation after success
- `useAuthStore()` -- Zustand store to persist user/tenant/token

**Form Library:**
- React Hook Form + Zod schema validation
- `mode: "onBlur"` for field validation (validate when user leaves field)

**Token Storage:**
- Access token: stored in Zustand memory store (never localStorage)
- Refresh token: delivered via HttpOnly cookie by the backend (Set-Cookie header)
- On page reload: call `/api/v1/auth/refresh` to obtain new access token

---

## Test Cases

### Happy Path
1. Successful login with valid credentials
   - **Given:** User has an active account in an active tenant
   - **When:** User enters valid email and password, clicks "Iniciar Sesion"
   - **Then:** Button shows spinner, user is redirected to `/dashboard`, authStore is populated

### Edge Cases
1. Already authenticated user visits `/login`
   - **Given:** User has a valid session
   - **When:** User navigates to `/login`
   - **Then:** Immediately redirected to `/dashboard`

2. Rapid double-click on submit
   - **Given:** Form is filled and valid
   - **When:** User double-clicks the submit button
   - **Then:** Only one API call is made (button disabled after first click)

### Error Cases
1. Invalid credentials
   - **Given:** User enters wrong email or password
   - **When:** Form is submitted
   - **Then:** Error banner shows "Correo o contrasena incorrectos"

2. Account locked
   - **Given:** User has exceeded 10 failed login attempts
   - **When:** Form is submitted
   - **Then:** Error banner shows lockout message with remaining minutes

3. Tenant suspended
   - **Given:** Clinic account has been suspended
   - **When:** User logs in with valid credentials
   - **Then:** Error banner shows "Tu clinica esta suspendida. Contacta soporte."

4. Network error
   - **Given:** No internet connection
   - **When:** Form is submitted
   - **Then:** Error banner shows "Error de conexion. Verifica tu internet e intenta de nuevo."

---

## Acceptance Criteria

- [ ] Matches design spec / mockup
- [ ] Email and password fields validate with Zod schema
- [ ] Successful login stores tokens and redirects to `/dashboard`
- [ ] Access token stored in memory, refresh token in HttpOnly cookie
- [ ] Error states: invalid_credentials, account_locked, rate_limit_exceeded, tenant_suspended
- [ ] Password visibility toggle works
- [ ] Loading state: spinner on button, inputs disabled
- [ ] "Olvide mi contrasena" link navigates to `/forgot-password`
- [ ] "Crear cuenta" link navigates to `/register`
- [ ] Authenticated users redirected away from `/login`
- [ ] Responsive on all breakpoints (mobile, tablet, desktop)
- [ ] Accessibility: focus order, ARIA labels, keyboard navigation, screen reader alerts
- [ ] Spanish (es-419) labels and messages throughout
- [ ] Touch targets minimum 48px on tablet

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
