# Aceptar Invitacion (Accept Invite) — Frontend Spec

## Overview

**Screen:** Invitation acceptance page. A new staff member clicks the invite link sent to their email and completes their profile to activate their account. Email, clinic name, and assigned role are pre-filled from the invite token. The user sets their name, password, and optional phone.

**Route:** `/accept-invite?token={token}`

**Priority:** Critical

**Backend Specs:** `specs/auth/accept-invite.md` (A-10)

**Dependencies:** `specs/frontend/auth/login.md`

---

## User Flow

**Entry Points:**
- Click "Aceptar invitacion" link in invitation email
- URL always contains a `token` query parameter

**Exit Points:**
- Success → redirect to `/dashboard` with welcome toast "Bienvenido/a a {clinic_name}. Tu cuenta esta lista."
- Expired/invalid token → error state with contact-admin instruction
- "Volver al inicio de sesion" link → `/login` at any time

**User Story:**
> As a new doctor | assistant | receptionist, I want to accept my clinic invitation and create my password so that I can start using DentalOS without going through a full registration.

**Roles with access:** Public (unauthenticated). Redirects to `/dashboard` if already authenticated.

---

## Layout Structure

```
+------------------------------------------+
|            DentalOS Logo (centered)       |
+------------------------------------------+
|                                          |
|     +-----------------------------+      |
|     |   Clinic invite header      |      |
|     |  "Te han invitado a..."     |      |
|     |  [Clinic name badge]        |      |
|     |  [Role badge]               |      |
|     +-----------------------------+      |
|     |   Complete Your Profile     |      |
|     |                             |      |
|     |  [Token error banner]       |      |
|     |                             |      |
|     |  Email (read-only)          |      |
|     |  Nombre completo            |      |
|     |  Telefono (optional)        |      |
|     |  Nueva contrasena           |      |
|     |  [Password strength bar]    |      |
|     |  Confirmar contrasena       |      |
|     |                             |      |
|     |  [Aceptar Invitacion btn]   |      |
|     |  [Volver al login link]     |      |
|     +-----------------------------+      |
|                                          |
+------------------------------------------+
```

**Sections:**
1. Logo area — DentalOS logo centered above card
2. Invite context header — clinic name, role, inviting doctor name
3. Profile form — email (read-only), name, phone, password fields
4. Actions — primary CTA button and back-to-login link

---

## UI Components

### Component 1: InviteContextHeader

**Type:** Info card / banner

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.6

**Content (derived from token decode):**
- Headline: `"Te han invitado a unirte a"` + clinic name in bold teal
- Role badge: `bg-teal-100 text-teal-800 text-xs font-medium px-2.5 py-0.5 rounded-full` with role label in Spanish

**Role label mapping:**

| role value | Display label |
|-----------|---------------|
| `doctor` | Medico / Odontólogo |
| `assistant` | Asistente Dental |
| `receptionist` | Recepcionista |
| `clinic_owner` | Propietario |

**States:**
- `loading` — skeleton placeholders for clinic name and role while token validates
- `loaded` — clinic name + role badge displayed
- `error` — entire card replaced by error state

### Component 2: ReadOnlyEmailField

**Type:** Input (disabled)

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.3

**Behavior:**
- `disabled` + `bg-gray-50 text-gray-500 cursor-not-allowed`
- `aria-label="Correo electronico (no editable)"`
- Lock icon `LockIcon` from Lucide at right side of input
- Tooltip on hover: "El correo no puede modificarse"

### Component 3: PasswordStrengthBar

**Type:** Visual indicator (same as reset-password spec)

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.9

**Behavior:** 4-segment bar, real-time update per keystroke. Labels: Muy debil / Debil / Moderada / Fuerte.

---

## Form Fields

| Field | Type | Required | Validation | Error Message (es-419) | Placeholder |
|-------|------|----------|------------|------------------------|-------------|
| email | email | Yes | Read-only, from token | — | — |
| nombre_completo | text | Yes | Min 3 chars, max 100 chars | "El nombre debe tener al menos 3 caracteres" | "Nombre completo" |
| telefono | tel | No | E.164 format if provided, max 20 chars | "Ingresa un numero de telefono valido" | "+57 300 000 0000" |
| nueva_contrasena | password | Yes | Min 8 chars, max 128 chars | "La contrasena debe tener al menos 8 caracteres" | "Crea tu contrasena" |
| confirmar_contrasena | password | Yes | Must match `nueva_contrasena` | "Las contrasenas no coinciden" | "Confirma tu contrasena" |

**Zod Schema:**
```typescript
const acceptInviteSchema = z.object({
  nombre_completo: z
    .string()
    .min(3, "El nombre debe tener al menos 3 caracteres")
    .max(100),
  telefono: z
    .string()
    .regex(/^\+?[1-9]\d{6,19}$/, "Ingresa un numero de telefono valido")
    .optional()
    .or(z.literal("")),
  nueva_contrasena: z
    .string()
    .min(8, "La contrasena debe tener al menos 8 caracteres")
    .max(128),
  confirmar_contrasena: z.string(),
}).refine(
  (d) => d.nueva_contrasena === d.confirmar_contrasena,
  { message: "Las contrasenas no coinciden", path: ["confirmar_contrasena"] }
);
```

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Validate invite token | `/api/v1/auth/invite/validate` | GET | `specs/auth/accept-invite.md` | None |
| Accept invite | `/api/v1/auth/invite/accept` | POST | `specs/auth/accept-invite.md` | None |

### Request Body (POST)

```typescript
{
  token: string;
  nombre_completo: string;
  telefono?: string;
  password: string;
}
```

### Response (POST success)

```typescript
{
  access_token: string;
  user: { id, email, nombre, role };
  tenant: { id, nombre, slug };
}
```

### State Management

**Local State (useState):**
- `tokenStatus: 'validating' | 'valid' | 'expired' | 'invalid'`
- `inviteData: { email, clinic_name, role, inviter_name } | null`
- `serverError: string | null`

**Global State (Zustand):**
- `authStore.user` — set after successful accept
- `authStore.tenant` — set after successful accept
- `authStore.accessToken` — stored in memory

**Server State (TanStack Query):**
- Query: `useQuery(['invite-validate', token])` on mount
- Mutation: `useMutation({ mutationFn: acceptInvite })` for POST

### Error Code Mapping

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `invite_expired` | 410 | "Esta invitacion ha expirado. Pide al administrador que te envie una nueva." |
| `invite_invalid` | 400 | "El enlace de invitacion no es valido." |
| `invite_already_used` | 409 | "Esta invitacion ya fue aceptada. Inicia sesion con tu correo." |
| `email_already_registered` | 409 | "Ya existe una cuenta con este correo." |

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Page load | URL with token | Validate token, pre-fill email | Skeleton → invite context header |
| Type name | Keystroke | Field updates | Validate on blur |
| Type phone | Keystroke | Field updates | Format hint shown |
| Type password | Keystroke | Strength bar updates | Real-time bar color change |
| Leave password field | Blur | Validate length | Inline error if < 8 |
| Type confirm password | Keystroke | Check match on blur | Error cleared when matching |
| Submit | Click button or Enter | POST accept invite | Spinner, then redirect or error |
| Click "Volver al login" | Click | Navigate to `/login` | Standard navigation |

### Animations/Transitions

- Page entry: card fades in `opacity-0 → opacity-100` over 200ms on mount
- Invite header: clinic name text highlights with `text-teal-700` pulse for 600ms after token validates
- Error banner: slides down `motion.div initial={{ height: 0 }} animate={{ height: 'auto' }}`
- Success: full-page success overlay with checkmark icon, then redirect after 1.5s

---

## Loading & Error States

### Loading State
- Token validation: skeleton placeholders for clinic name `h-5 w-40`, role badge `h-5 w-20`
- Form fields disabled with `opacity-60` while token validates
- Submit: button shows "Activando cuenta..." with spinner, all inputs disabled

### Error State
- Expired/invalid token: entire form area replaced with centered error message, large XCircle icon, description, and "Contacta a tu administrador" note
- Server error: `bg-red-50 border-red-200` banner inside card above submit button
- Field errors: `text-xs text-red-600` below each field

### Empty State
- Not applicable

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Card fills viewport width `px-4`. Fields stack vertically. Invite header stacks clinic name below headline. |
| Tablet (640-1024px) | Card `max-w-md` centered with `shadow-md rounded-xl`. All fields full-width. |
| Desktop (> 1024px) | Same as tablet. Vertically centered `min-h-screen flex items-center justify-center`. |

**Tablet priority:** High — clinic administrators often send invites and staff accept on tablets. Touch targets min 44px.

---

## Accessibility

- **Focus order:** Nombre completo → Telefono → Nueva contrasena → Toggle visibility → Confirmar contrasena → Toggle visibility → Submit button → "Volver al login" link
- **Screen reader:** `role="alert"` on token error and server error banners. `aria-live="polite"` on password strength label. Email field has `aria-readonly="true"` and descriptive `aria-label`. Role badge reads "Tu rol sera: {role}".
- **Keyboard navigation:** Enter submits from any field. Tab follows defined order. Escape clears server error.
- **Color contrast:** WCAG AA. Role badge and clinic name use sufficient contrast on white background.
- **Language:** All labels, placeholders, and messages in es-419.

---

## Design Tokens

**Colors:**
- Primary button: `bg-teal-600 hover:bg-teal-700 text-white`
- Invite header background: `bg-teal-50 border border-teal-200 rounded-xl`
- Clinic name: `text-teal-700 font-bold`
- Role badge: `bg-teal-100 text-teal-800`
- Read-only field: `bg-gray-50 text-gray-500 border-gray-200`
- Page background: `bg-gray-50 dark:bg-gray-950`
- Card: `bg-white dark:bg-gray-900`

**Typography:**
- Invite headline: `text-sm text-gray-600`
- Clinic name: `text-lg font-bold text-teal-700`
- Card section title: `text-base font-semibold text-gray-800`
- Labels: `text-sm font-medium text-gray-700`
- Error: `text-xs text-red-600`

**Spacing:**
- Card padding: `p-6 md:p-8`
- Invite header padding: `p-4`
- Field gap: `space-y-4`
- Section gap: `space-y-6`

**Border Radius:**
- Card: `rounded-xl`
- Invite header: `rounded-xl`
- Inputs: `rounded-md`
- Button: `rounded-lg`
- Role badge: `rounded-full`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `@hookform/resolvers` + `zod`
- `lucide-react` — Lock, Eye, EyeOff, Loader2, CheckCircle2, XCircle
- `framer-motion` — error banner animation

**File Location:**
- Page: `src/app/(public)/accept-invite/page.tsx`
- Components: `src/components/auth/AcceptInviteForm.tsx`, `src/components/auth/InviteContextHeader.tsx`
- Schema: `src/lib/schemas/auth.ts`
- API: `src/lib/api/auth.ts`

**Hooks Used:**
- `useSearchParams()` — extract `token` from URL
- `useQuery(['invite-validate', token])` — validate on mount, `staleTime: 0`
- `useMutation()` — accept invite POST
- `useForm()` — React Hook Form, `mode: "onBlur"`
- `useRouter()` — redirect after success
- `useAuthStore()` — set user + tenant + token after success

---

## Test Cases

### Happy Path
1. Valid invite, successful account creation
   - **Given:** Admin invites a new receptionist; receptionist clicks email link
   - **When:** Token validates, user fills name + password, clicks submit
   - **Then:** Account created, authStore populated, redirect to `/dashboard`, welcome toast shown

### Edge Cases
1. User already has an account and clicks invite link
   - **Given:** `email_already_registered` returned from accept endpoint
   - **When:** User submits form
   - **Then:** Error banner "Ya existe una cuenta con este correo." with link to login

2. Token missing from URL
   - **Given:** User navigates to `/accept-invite` without token param
   - **When:** Page loads
   - **Then:** Invalid invite error shown immediately, no API call

### Error Cases
1. Expired invite (> 72 hours)
   - **Given:** Invite was sent 4 days ago
   - **When:** Page loads, token validation returns 410
   - **Then:** Error "Esta invitacion ha expirado. Pide al administrador que te envie una nueva."

2. Already accepted invite
   - **Given:** User already accepted and tries link again
   - **When:** Validation or submission returns 409
   - **Then:** "Esta invitacion ya fue aceptada. Inicia sesion con tu correo." with login link

---

## Acceptance Criteria

- [ ] Token validated on mount; clinic name, email, and role pre-filled from token
- [ ] Email field is read-only (not editable by user)
- [ ] Role displayed in Spanish with correct badge styling
- [ ] Zod schema validates name, phone format, password length, and match
- [ ] Password strength bar updates in real-time
- [ ] Successful accept → authStore populated → redirect to `/dashboard` with welcome toast
- [ ] All error codes mapped to Spanish messages
- [ ] Loading states: skeleton during validation, spinner during submit
- [ ] Expired/invalid token shows actionable error without form
- [ ] Responsive on mobile, tablet, desktop
- [ ] Accessibility: ARIA alerts, focus order, keyboard navigation
- [ ] Spanish (es-419) labels throughout
- [ ] Touch targets minimum 44px

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
