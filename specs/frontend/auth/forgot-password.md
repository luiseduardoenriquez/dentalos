# Recuperar Contrasena (Forgot Password) -- Frontend Spec

## Overview

**Screen:** Forgot password screen. Single email input to request a password reset link. Always displays a generic success message regardless of whether the email exists in the system (security: prevents email enumeration).

**Route:** `/forgot-password`

**Priority:** High

**Backend Specs:** `specs/infra/authentication-rules.md` (Section 10.1, error `magic_link_expired`), `specs/M1-NAVIGATION-MAP.md` Section 6.1

**Dependencies:** `specs/frontend/auth/login.md`

---

## User Flow

**Entry Points:**
- "Olvide mi contrasena" link from `/login`
- Direct navigation to `/forgot-password`

**Exit Points:**
- "Volver a iniciar sesion" link navigates to `/login`
- After submission, user stays on the same page with a success message

**User Story:**
> As a clinic_owner | doctor | assistant | receptionist, I want to request a password reset link so that I can regain access to my account when I forget my password.

**Roles with access:** Public (unauthenticated). Redirects to `/dashboard` if already authenticated.

---

## Layout Structure

```
+------------------------------------------+
|            DentalOS Logo (centered)       |
+------------------------------------------+
|                                          |
|     +----------------------------+       |
|     |   Forgot Password Card     |       |
|     |                            |       |
|     |   BEFORE SUBMIT:           |       |
|     |   "Recupera tu contrasena" |       |
|     |   [description text]       |       |
|     |   [Email input]            |       |
|     |   [Enviar instrucciones]   |       |
|     |                            |       |
|     |   AFTER SUBMIT:            |       |
|     |   [Checkmark icon]         |       |
|     |   "Revisa tu correo"       |       |
|     |   [success description]    |       |
|     |   [Reenviar correo btn]    |       |
|     |                            |       |
|     |   <- Volver a iniciar      |       |
|     |      sesion                |       |
|     +----------------------------+       |
|                                          |
+------------------------------------------+
```

**Sections:**
1. Logo area -- DentalOS logo centered above the card
2. Forgot password card -- `max-w-sm` centered container. Two visual states: form state and success state.

---

## UI Components

### Component 1: ForgotPasswordCard

**Type:** Card

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.4

**States:**
- Form state (default): heading, description, email input, submit button
- Success state: checkmark icon, success heading, confirmation text, resend button
- Error state: inline error banner if network fails

### Component 2: SuccessIllustration

**Type:** Icon + text composition

**Visual:** Large `Mail` icon (Lucide, 48px) in `text-blue-500` with a soft `bg-blue-50 rounded-full p-4` circle behind it. Below: heading "Revisa tu correo" and description paragraph.

### Component 3: ResendButton

**Type:** Button (secondary)

**Behavior:**
- Visible only after first successful submission
- Disabled for 60 seconds after each send (cooldown timer)
- Shows countdown: "Reenviar en {seconds}s"
- After cooldown: "Reenviar correo"

---

## Form Fields

| Field | Type | Required | Validation | Error Message (es-419) | Placeholder |
|-------|------|----------|------------|------------------------|-------------|
| email | email | Yes | Valid email format, max 255 chars | "Ingresa un correo electronico valido" | "correo@ejemplo.com" |

**Zod Schema:**
```typescript
const forgotPasswordSchema = z.object({
  email: z.string().email("Ingresa un correo electronico valido").max(255),
});
```

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Request reset | `/api/v1/auth/forgot-password` | POST | `specs/infra/authentication-rules.md` | None |

**Request Body:**
```json
{
  "email": "doctor@clinica.co"
}
```

**Response:** Always `200 OK` with `{ "message": "If the email exists, instructions will be sent." }` regardless of whether the email is registered.

### State Management

**Local State (useState):**
- `isSubmitted: boolean` -- toggles between form and success view
- `submittedEmail: string` -- stores the email for display in success message
- `resendCooldown: number` -- countdown seconds for resend button (0 = enabled)

**Global State (Zustand):**
- None -- this screen does not modify auth state

**Server State (TanStack Query):**
- Mutation: `useMutation({ mutationFn: requestPasswordReset })` for forgot-password POST

### Error Code Mapping

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `rate_limit_exceeded` | 429 | "Demasiadas solicitudes. Espera unos minutos antes de intentar de nuevo." |
| Network error | -- | "Error de conexion. Verifica tu internet e intenta de nuevo." |

**Security Note:** The backend always returns 200 OK even if the email does not exist. The frontend must NEVER reveal whether the email is registered. The success message is always: "Si el correo existe en nuestro sistema, recibiras instrucciones para restablecer tu contrasena."

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Submit email | Click button or Enter | POST to forgot-password endpoint | Button spinner, then success view |
| Click "Reenviar correo" | Click button (after cooldown) | POST same endpoint again | Button spinner, toast "Correo reenviado", cooldown resets |
| Click "Volver a iniciar sesion" | Click link | Navigate to `/login` | Standard navigation |

### Animations/Transitions

- Form-to-success transition: `framer-motion` crossfade. Form fades out (opacity 0, scale 0.98), success fades in (opacity 1, scale 1). Duration 300ms.
- Checkmark icon on success: scale animation from 0.5 to 1.0 with spring easing
- Error banner: slide down with opacity

---

## Loading & Error States

### Loading State
- Button text: "Enviando..." with `animate-spin` Loader2 icon
- Email input disabled during submission
- No skeleton needed

### Error State
- Network errors only (backend never returns errors for this endpoint except rate limiting)
- Rate limit: inline banner `bg-amber-50 text-amber-700` with "Demasiadas solicitudes" message
- Network: inline banner `bg-red-50 text-red-700` with connection error message

### Empty State
- Not applicable

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Card fills full width `px-4`. Logo smaller `h-8`. No card shadow. |
| Tablet (640-1024px) | Card centered `max-w-sm`. Card `shadow-md rounded-xl`. |
| Desktop (> 1024px) | Same as tablet. Centered vertically and horizontally. |

**Tablet priority:** Medium -- password reset is less frequent but must be accessible on all devices.

---

## Accessibility

- **Focus order:** Email input -> "Enviar instrucciones" button -> "Volver a iniciar sesion" link. After success: "Reenviar correo" button -> "Volver a iniciar sesion" link.
- **Screen reader:** `aria-label="Formulario de recuperacion de contrasena"` on form. `role="status"` with `aria-live="polite"` on success message container so screen readers announce the state change. `aria-label="Volver a la pagina de inicio de sesion"` on back link.
- **Keyboard navigation:** Enter submits the form. Tab navigates focus order.
- **Color contrast:** WCAG AA on all elements. Blue icon on blue-50 background meets contrast requirements for decorative elements.
- **Language:** All content in es-419.

---

## Design Tokens

**Colors:**
- Primary button: `bg-blue-600 hover:bg-blue-700 text-white`
- Success icon circle: `bg-blue-50` with `text-blue-500` icon
- Success heading: `text-gray-700 font-semibold`
- Success description: `text-sm text-gray-500`
- Back link: `text-blue-600 hover:text-blue-700`
- Resend button (secondary): `bg-gray-100 text-gray-700 hover:bg-gray-200`
- Resend disabled: `bg-gray-50 text-gray-400 cursor-not-allowed`

**Typography:**
- Card heading (form): `text-xl font-semibold text-gray-700`
- Description text: `text-sm text-gray-500 leading-relaxed`
- Success heading: `text-lg font-semibold text-gray-700`
- Email in success: `font-medium text-gray-700` (the submitted email address)
- Cooldown text: `text-xs text-gray-400`

**Spacing:**
- Card padding: `p-6 md:p-8`
- Field gap: `space-y-4`
- Success icon to heading: `mt-4`
- Description to input: `mt-6`
- Button to back link: `mt-6`
- Back link area: `mt-4 text-center`

**Border Radius:**
- Card: `rounded-xl`
- Input: `rounded-md`
- Button: `rounded-lg`
- Icon circle: `rounded-full`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `zod` + `@hookform/resolvers`
- `lucide-react` -- Mail, ArrowLeft, Loader2, CheckCircle2
- `framer-motion` -- form/success crossfade animation

**File Location:**
- Page: `src/app/(public)/forgot-password/page.tsx`
- Components: `src/components/auth/ForgotPasswordForm.tsx`
- Schema: `src/lib/schemas/auth.ts`
- API: `src/lib/api/auth.ts`

**Hooks Used:**
- `useForm()` -- React Hook Form with Zod resolver
- `useMutation()` -- TanStack Query for forgot-password POST
- `useState()` -- submission state, cooldown timer
- `useEffect()` -- countdown timer interval for resend cooldown

**Form Library:**
- React Hook Form + Zod schema validation
- `mode: "onBlur"` for email validation

**Resend Cooldown Implementation:**
```typescript
const [cooldown, setCooldown] = useState(0);

useEffect(() => {
  if (cooldown <= 0) return;
  const timer = setInterval(() => setCooldown((c) => c - 1), 1000);
  return () => clearInterval(timer);
}, [cooldown]);

const handleResend = () => {
  mutation.mutate({ email: submittedEmail });
  setCooldown(60);
};
```

---

## Test Cases

### Happy Path
1. Request password reset
   - **Given:** User is on `/forgot-password`
   - **When:** User enters a valid email and clicks "Enviar instrucciones"
   - **Then:** Success view is shown with "Si el correo existe en nuestro sistema, recibiras instrucciones para restablecer tu contrasena"

### Edge Cases
1. Email does not exist in system
   - **Given:** User enters a non-registered email
   - **When:** Form is submitted
   - **Then:** Same success message is shown (no information leak)

2. Resend cooldown
   - **Given:** User has submitted and is on the success view
   - **When:** User clicks "Reenviar correo"
   - **Then:** Button is disabled for 60 seconds with countdown text

3. Navigate back to login
   - **Given:** User is on forgot-password page (any state)
   - **When:** User clicks "Volver a iniciar sesion"
   - **Then:** Navigated to `/login`

### Error Cases
1. Rate limited
   - **Given:** User has made too many requests
   - **When:** Form is submitted
   - **Then:** Warning banner with "Demasiadas solicitudes" message

2. Network failure
   - **Given:** No internet connection
   - **When:** Form is submitted
   - **Then:** Error banner with "Error de conexion" message; form remains in input state

---

## Acceptance Criteria

- [ ] Email input with Zod validation
- [ ] Submit always shows generic success message (never reveals email existence)
- [ ] Success message: "Si el correo existe en nuestro sistema, recibiras instrucciones para restablecer tu contrasena"
- [ ] Resend button with 60-second cooldown timer
- [ ] Animated transition from form state to success state
- [ ] "Volver a iniciar sesion" link navigates to `/login`
- [ ] Loading state: spinner on button, input disabled
- [ ] Error handling: rate limit (429), network errors
- [ ] Authenticated users redirected away from this page
- [ ] Responsive on all breakpoints (mobile, tablet, desktop)
- [ ] Accessibility: focus management on state transition, ARIA live region for success
- [ ] Spanish (es-419) labels and messages throughout
- [ ] Touch targets minimum 44px

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
