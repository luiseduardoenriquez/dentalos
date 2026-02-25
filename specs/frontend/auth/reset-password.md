# Restablecer Contrasena (Reset Password) — Frontend Spec

## Overview

**Screen:** Reset password page. Allows a user to set a new password using a one-time token delivered via email link. Validates the token on mount, displays a password strength indicator, and redirects to login on success.

**Route:** `/reset-password?token={token}`

**Priority:** Critical

**Backend Specs:** `specs/auth/reset-password.md` (A-06)

**Dependencies:** `specs/frontend/auth/forgot-password.md`

---

## User Flow

**Entry Points:**
- Click the "Restablecer contrasena" link in the password-reset email
- URL always includes a `token` query parameter

**Exit Points:**
- Success → redirect to `/login` with success toast "Contrasena actualizada. Inicia sesion."
- Invalid/expired token → stay on page, show error with link to `/forgot-password`
- "Volver al inicio de sesion" link → `/login` at any time

**User Story:**
> As a clinic_owner | doctor | assistant | receptionist, I want to set a new password using the link sent to my email so that I can regain access to my account.

**Roles with access:** Public (unauthenticated). Redirects to `/dashboard` if already authenticated.

---

## Layout Structure

```
+------------------------------------------+
|            DentalOS Logo (centered)       |
+------------------------------------------+
|                                          |
|       +---------------------------+      |
|       |   Reset Password Card     |      |
|       |                           |      |
|       |  [Token error banner]     |      |
|       |  (if expired/invalid)     |      |
|       |                           |      |
|       |  [Nueva contrasena input] |      |
|       |  [Password strength bar]  |      |
|       |                           |      |
|       |  [Confirmar input]        |      |
|       |                           |      |
|       |  [Guardar Contrasena btn] |      |
|       |                           |      |
|       |  [Volver al login link]   |      |
|       +---------------------------+      |
|                                          |
+------------------------------------------+
```

**Sections:**
1. Logo area — DentalOS logo centered above card
2. Token validation banner — shown only when token is invalid or expired
3. Password form — new password + confirm password with strength indicator
4. Success confirmation — inline success message before redirect

---

## UI Components

### Component 1: TokenStatusBanner

**Type:** Alert banner

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.6

**States:**
- `validating` — skeleton pulse `h-4 w-32 bg-gray-200 rounded animate-pulse` while verifying token on mount
- `valid` — banner hidden, form visible and enabled
- `expired` — `bg-amber-50 border border-amber-200 rounded-lg p-3` with clock icon + message + link to `/forgot-password`
- `invalid` — `bg-red-50 border border-red-200 rounded-lg p-3` with X icon + message + link

**Behavior:**
- Token is validated via GET `/api/v1/auth/reset-password/validate?token={token}` on component mount
- While validating, form fields are disabled with skeleton overlay
- On invalid/expired result, form is hidden and error state is displayed

### Component 2: PasswordStrengthIndicator

**Type:** Visual feedback bar

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.9

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| password | string | "" | Current password value |
| strength | 0\|1\|2\|3\|4 | 0 | Computed strength score |

**Strength levels:**

| Score | Label | Bar color | Condition |
|-------|-------|-----------|-----------|
| 0 | — | `bg-gray-200` | Empty |
| 1 | Muy debil | `bg-red-500` | < 8 chars |
| 2 | Debil | `bg-orange-400` | 8+ chars, no variety |
| 3 | Moderada | `bg-yellow-400` | 8+ chars, mixed case OR number |
| 4 | Fuerte | `bg-green-500` | 8+ chars, mixed case + number + special |

**Bar:** 4 segments, `h-1.5 rounded-full`, filled left to right per score.

**Behavior:**
- Updates on every keystroke in the password field
- Label text `text-xs font-medium` matches color of highest filled segment
- Does not block form submission — backend enforces final validation

### Component 3: PasswordInput

**Type:** Input with toggle

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.3

**States:** Default, Focus, Error, Disabled
**Behavior:** Eye/EyeOff Lucide icon toggles `input[type]` between `password` and `text`. Min touch target 44px for toggle button.

---

## Form Fields

| Field | Type | Required | Validation | Error Message (es-419) | Placeholder |
|-------|------|----------|------------|------------------------|-------------|
| nueva_contrasena | password | Yes | Min 8 chars, max 128 chars | "La contrasena debe tener al menos 8 caracteres" | "Nueva contrasena" |
| confirmar_contrasena | password | Yes | Must match `nueva_contrasena` | "Las contrasenas no coinciden" | "Confirma tu nueva contrasena" |

**Zod Schema:**
```typescript
const resetPasswordSchema = z.object({
  nueva_contrasena: z
    .string()
    .min(8, "La contrasena debe tener al menos 8 caracteres")
    .max(128, "La contrasena no puede superar 128 caracteres"),
  confirmar_contrasena: z.string(),
}).refine(
  (data) => data.nueva_contrasena === data.confirmar_contrasena,
  {
    message: "Las contrasenas no coinciden",
    path: ["confirmar_contrasena"],
  }
);
```

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Validate token | `/api/v1/auth/reset-password/validate` | GET | `specs/auth/reset-password.md` | None |
| Submit new password | `/api/v1/auth/reset-password` | POST | `specs/auth/reset-password.md` | None |

### Request Body

```typescript
{
  token: string;       // from URL query param
  password: string;    // nueva_contrasena field value
}
```

### State Management

**Local State (useState):**
- `tokenStatus: 'validating' | 'valid' | 'expired' | 'invalid'`
- `serverError: string | null`
- `isSuccess: boolean`

**Global State (Zustand):**
- Not applicable — user is unauthenticated during this flow

**Server State (TanStack Query):**
- Query: `useQuery({ queryKey: ['reset-token-validate', token], queryFn: validateToken })` on mount
- Mutation: `useMutation({ mutationFn: submitNewPassword })` for POST

### Error Code Mapping

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `token_expired` | 410 | "El enlace ha expirado. Solicita uno nuevo." |
| `token_invalid` | 400 | "El enlace no es valido. Solicita uno nuevo." |
| `token_already_used` | 409 | "Este enlace ya fue utilizado. Solicita uno nuevo." |
| `password_too_weak` | 422 | "La contrasena no cumple los requisitos de seguridad." |

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Page load | URL with token param | Validate token silently | Skeleton pulse while validating |
| Type new password | Keystroke | Update strength indicator | Real-time bar update |
| Leave password field | Blur | Validate min length | Inline error below field |
| Type confirm password | Keystroke | Check match on blur | Match error cleared when equal |
| Submit form | Click button or Enter | POST reset endpoint | Button spinner, then success or error |
| Click "Solicitar nuevo enlace" | Click (on error state) | Navigate to `/forgot-password` | Standard link navigation |
| Click "Volver al inicio de sesion" | Click link | Navigate to `/login` | Standard link navigation |

### Animations/Transitions

- Error banner slides in from top: `motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}` 200ms
- Success state: green checkmark icon fades in, message "Contrasena actualizada exitosamente", then auto-redirect after 2s
- Strength bar segments transition color: `transition-colors duration-200`

---

## Loading & Error States

### Loading State
- Token validation: skeleton bar `h-4 w-3/4 animate-pulse bg-gray-200 rounded` in place of form title
- Form submit: button shows `Guardando...` with `Loader2 animate-spin` icon, inputs disabled
- Form fields `opacity-60 pointer-events-none` during submission

### Error State
- Token invalid/expired: full-width banner inside card, form fields hidden, link to request new token
- Server validation error: inline banner `bg-red-50 border-red-200` above submit button
- Field errors: `text-xs text-red-600 mt-1` below each input, `border-red-400` on input border

### Empty State
- Not applicable

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Card fills full width `px-4`. Password strength label visible below bar. |
| Tablet (640-1024px) | Card centered `max-w-sm`, `shadow-md rounded-xl`. |
| Desktop (> 1024px) | Same as tablet, centered vertically `min-h-screen flex items-center justify-center`. |

**Tablet priority:** High — touch targets min 44px for all inputs and password visibility toggle.

---

## Accessibility

- **Focus order:** Nueva contrasena input → Password visibility toggle → Confirmar contrasena → Visibility toggle → Submit button → "Volver al login" link
- **Screen reader:** `role="alert"` on token error banner and server error banner. `aria-live="polite"` on strength label so it announces changes. `aria-describedby` linking each input to its error message element.
- **Keyboard navigation:** Enter submits form from any field. Tab follows defined focus order. Escape clears server error banner.
- **Color contrast:** WCAG AA. Strength indicator labels use text alongside color (never color alone for status).
- **Language:** All labels, placeholders, and messages in es-419.

---

## Design Tokens

**Colors:**
- Primary button: `bg-teal-600 hover:bg-teal-700 text-white`
- Page background: `bg-gray-50 dark:bg-gray-950`
- Card: `bg-white dark:bg-gray-900 shadow-md rounded-xl`
- Error banner: `bg-red-50 border-red-200 text-red-700`
- Warning banner (expired): `bg-amber-50 border-amber-200 text-amber-700`
- Success: `bg-green-50 border-green-200 text-green-700`
- Strength bar colors: `bg-red-500`, `bg-orange-400`, `bg-yellow-400`, `bg-green-500`

**Typography:**
- Card title: `text-xl font-bold font-inter text-gray-900`
- Labels: `text-sm font-medium text-gray-700`
- Strength label: `text-xs font-medium`
- Helper text: `text-xs text-gray-500`
- Error text: `text-xs text-red-600`

**Spacing:**
- Card padding: `p-6 md:p-8`
- Field gap: `space-y-4`
- Strength bar gap from input: `mt-2`

**Border Radius:**
- Card: `rounded-xl`
- Inputs: `rounded-md`
- Button: `rounded-lg`
- Strength segments: `rounded-full`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `@hookform/resolvers` + `zod`
- `lucide-react` — Eye, EyeOff, Loader2, CheckCircle, XCircle, Clock
- `framer-motion` — banner entry animation
- `zxcvbn` (optional) — password strength scoring library, or custom 4-tier logic

**File Location:**
- Page: `src/app/(public)/reset-password/page.tsx`
- Components: `src/components/auth/ResetPasswordForm.tsx`, `src/components/auth/PasswordStrengthBar.tsx`
- Schema: `src/lib/schemas/auth.ts`
- API: `src/lib/api/auth.ts`

**Hooks Used:**
- `useForm()` — React Hook Form with Zod resolver, `mode: "onBlur"`
- `useQuery()` — token validation on mount with `enabled: !!token`
- `useMutation()` — submit new password
- `useRouter()` — Next.js App Router navigation
- `useSearchParams()` — extract `token` from URL

**Special Logic:**
- Extract token from `useSearchParams().get('token')` on mount
- If token is null/empty, immediately show invalid state without API call
- Auto-redirect to `/login` 2 seconds after success using `setTimeout` + `router.replace`

---

## Test Cases

### Happy Path
1. Valid token, successful password reset
   - **Given:** User clicks valid, unexpired reset link from email
   - **When:** Page loads, user enters matching passwords ≥ 8 chars, clicks submit
   - **Then:** Success message shown, redirect to `/login` after 2s, toast "Contrasena actualizada"

### Edge Cases
1. User navigates to reset page without token
   - **Given:** URL is `/reset-password` with no `token` param
   - **When:** Page loads
   - **Then:** Invalid token banner shown immediately without API call

2. Passwords do not match
   - **Given:** Token is valid, form is visible
   - **When:** User enters mismatched passwords and submits
   - **Then:** Inline error "Las contrasenas no coinciden" on confirm field, no API call

3. Already authenticated user visits page
   - **Given:** User has active session
   - **When:** Navigates to `/reset-password`
   - **Then:** Redirected to `/dashboard`

### Error Cases
1. Expired token
   - **Given:** Reset link is older than 1 hour
   - **When:** Page loads and validates token
   - **Then:** Amber banner "El enlace ha expirado. Solicita uno nuevo." with link to `/forgot-password`

2. Token already used
   - **Given:** User already reset password with this link
   - **When:** Token validation returns 409
   - **Then:** Error banner "Este enlace ya fue utilizado. Solicita uno nuevo."

3. Network error during submission
   - **Given:** No internet connection
   - **When:** User submits valid form
   - **Then:** Error banner "Error de conexion. Verifica tu internet e intenta de nuevo."

---

## Acceptance Criteria

- [ ] Token extracted from URL query param on mount
- [ ] Token validated via API before form is enabled
- [ ] Invalid/expired token shows appropriate banner with link to `/forgot-password`
- [ ] Password strength indicator updates in real-time
- [ ] Zod schema validates min length and password match
- [ ] Successful reset shows confirmation and redirects to `/login` after 2s
- [ ] Loading states: skeleton during token validation, spinner during submit
- [ ] All error codes mapped to Spanish messages
- [ ] Password visibility toggle works on both fields
- [ ] Responsive on mobile, tablet, desktop
- [ ] Accessibility: ARIA alerts, focus order, keyboard navigation
- [ ] Spanish (es-419) labels and messages throughout
- [ ] Touch targets minimum 44px

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
