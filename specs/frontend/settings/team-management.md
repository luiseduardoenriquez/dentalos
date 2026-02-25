# Gestión de Equipo — Frontend Spec

## Overview

**Spec ID:** FE-S-02

**Screen:** Team member management page — list, invite, edit roles, and deactivate users.

**Route:** `/settings/equipo`

**Priority:** High

**Backend Specs:** `specs/users/list-team.md`, `specs/auth/invite-user.md`, `specs/users/update-team-member.md`, `specs/users/deactivate-user.md`

**Dependencies:** `FE-DS-01`, `FE-DS-02` (button), `FE-DS-05` (table), `FE-DS-06` (modal), `FE-DS-11` (badge), `FE-DS-12` (avatar)

---

## User Flow

**Entry Points:**
- Sidebar: Configuración → Equipo
- Post-onboarding invitation prompt

**Exit Points:**
- Any other settings section
- Click on team member name → member profile page

**User Story:**
> As a clinic_owner, I want to manage my team members, invite new staff, assign roles, and deactivate users who leave the clinic so that access is always appropriate to each person's role.

**Roles with access:** `clinic_owner` (full access). `doctor` can view the list (read-only). `assistant`, `receptionist` have no access (redirect to dashboard with 403 toast).

---

## Layout Structure

```
+------------------------------------------+
|              Header (h-16)               |
+--------+---------------------------------+
|        |  "Equipo" + "Invitar miembro"   |
| Side-  |  Search bar + Role filter       |
|  bar   +---------------------------------+
|        |  Team members table             |
|        |  Pagination                     |
+--------+---------------------------------+
```

**Sections:**
1. Page header with page title and primary "Invitar miembro" button
2. Filter bar: search by name/email + role filter dropdown
3. Team members data table
4. Invite modal (triggered by button)
5. Deactivate confirmation modal (triggered by row action)

---

## Team Members Table

**Columns:**

| Column | Content | Sortable | Width |
|--------|---------|----------|-------|
| Usuario | Avatar (sm) + full name + email | Yes (by name) | flex-1 |
| Rol | Role badge (color-coded) | Yes | 140px |
| Estado | Status pill | No | 120px |
| Último acceso | Relative date ("hace 2 días") | Yes | 140px |
| Acciones | Icon button group | No | 80px |

**Role badge colors:**

| Role | Label | Background | Text |
|------|-------|-----------|------|
| clinic_owner | Propietario | `purple-100` | `purple-700` |
| doctor | Doctor | `blue-100` | `blue-700` |
| assistant | Asistente | `teal-100` | `teal-700` |
| receptionist | Recepcionista | `amber-100` | `amber-700` |

**Status pill colors:**

| Status | Label | Background | Text |
|--------|-------|-----------|------|
| active | Activo | `green-100` | `green-700` |
| pending | Pendiente | `amber-100` | `amber-700` |
| inactive | Inactivo | `gray-100` | `gray-500` |

**Row actions (icon buttons, visible on hover + always on mobile):**
- Edit role: pencil icon → inline role dropdown (see below)
- Deactivate: slash icon → opens deactivation confirmation modal
- Resend invite (if pending): mail icon → re-sends invitation email

**Inline role editing:**
- Click pencil icon → role badge replaced by a Select dropdown
- Options: Doctor, Asistente, Recepcionista (cannot demote clinic_owner here)
- Select new role → immediate PATCH with success toast "Rol actualizado"
- Escape or click outside → cancels edit, restores badge

---

## Invite Member Modal

**Trigger:** "Invitar miembro" button (top-right of page header)

**Modal size:** `md` (max-w-lg)

**Title:** "Invitar nuevo miembro"

### Form Fields

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| email | email | Yes | Valid email format | "Correo electrónico inválido" | "doctor@clinica.com" |
| rol | select | Yes | Must select a role | "Selecciona un rol" | "Seleccionar rol..." |
| mensaje | textarea | No | Max 300 chars | "Máximo 300 caracteres" | "Bienvenido al equipo..." |

**Role options in dropdown:**
- Doctor
- Asistente
- Recepcionista

**Footer buttons:**
- "Cancelar" (secondary, left-aligned) — closes modal without action
- "Enviar invitación" (primary, right-aligned) — submits form

**Post-submit behavior:**
- Loading spinner on "Enviar invitación" button while API call in flight
- Success: modal closes, new row appears in table with "Pendiente" status, success toast "Invitación enviada a [email]"
- Error (email already in team): inline error below email field "Este usuario ya es parte del equipo"
- Error (plan limit): modal shows plan limit warning banner: "Has alcanzado el límite de tu plan. Actualiza para agregar más miembros." with "Ver planes" link

---

## Deactivate Member Modal

**Trigger:** Slash icon button in row actions

**Modal size:** `sm` (max-w-md)

**Type:** Confirmation

**Content:**
- Warning icon (amber, `AlertTriangle` 24px)
- Title: "Desactivar miembro"
- Message: "¿Estás seguro de que deseas desactivar a **[Nombre del usuario]**? Perderá acceso inmediatamente. Sus registros clínicos se conservarán."
- Footer: "Cancelar" (secondary) + "Desactivar" (danger variant, red)

**Post-confirm behavior:**
- Row status changes to "Inactivo"
- User can no longer log in to this tenant
- Success toast: "[Nombre] ha sido desactivado"

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Load team | `/api/v1/users/team` | GET | `specs/users/list-team.md` | 2min |
| Invite member | `/api/v1/auth/invite` | POST | `specs/auth/invite-user.md` | Invalidate |
| Update role | `/api/v1/users/{user_id}` | PATCH | `specs/users/update-team-member.md` | Invalidate |
| Deactivate | `/api/v1/users/{user_id}/deactivate` | POST | `specs/users/deactivate-user.md` | Invalidate |
| Resend invite | `/api/v1/auth/invite/{invite_id}/resend` | POST | `specs/auth/invite-user.md` | — |

### State Management

**Local State (useState):**
- `inviteModalOpen: boolean`
- `deactivateTarget: TeamMember | null`
- `editingRoleId: string | null` — which row is in inline edit mode
- `searchQuery: string`
- `roleFilter: string | null`

**Server State (TanStack Query):**
- Query key: `['team-members', tenantId, { search, roleFilter }]`
- Stale time: 2 minutes
- Mutations: `useInviteMember()`, `useUpdateMemberRole()`, `useDeactivateMember()`

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Open invite modal | Click "Invitar miembro" | Modal opens | Focus moves to email field |
| Send invitation | Click "Enviar invitación" | POST invite | Toast + row added as pending |
| Edit role | Click pencil icon | Inline dropdown appears | — |
| Select new role | Dropdown selection | PATCH role | Toast "Rol actualizado" |
| Click deactivate | Slash icon | Confirmation modal opens | — |
| Confirm deactivation | Click "Desactivar" | POST deactivate | Row status → Inactivo, toast |
| Search | Type in search bar | Table filters client-side (or server-side if > 50 members) | Results update in real-time |
| Filter by role | Select role in filter | Table filters | Results update |

### Animations/Transitions

- New invited row slides in from top of table (Framer Motion, 200ms)
- Deactivated row status badge transitions color (150ms)
- Modal open/close: standard (FE-DS-06)

---

## Loading & Error States

### Loading State
- Table skeleton: 5 rows, each with avatar circle + 3 text bars + 2 badge-size blocks (FE-DS-17 table-skeleton)
- Invite button shows spinner while POST in flight

### Error State
- Team load failure: empty state with error message "Error al cargar el equipo. Intenta de nuevo." and retry button
- Plan limit on invite: warning banner inside modal (not a toast)

### Empty State
- No team members (solo plan): illustration (single person silhouette), "Eres el único miembro del equipo", CTA: "Invitar primer miembro"
- No results after search: "Sin resultados para '[query]'", "Limpiar búsqueda" link

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Cards instead of table. Each card: avatar + name + role badge + status + actions menu (3-dot dropdown) |
| Tablet (640-1024px) | Table with all columns. Actions visible on row (not just hover). |
| Desktop (> 1024px) | Full table, row actions appear on hover. |

**Tablet priority:** High. 44px row height minimum for touch. Action buttons 44x44px minimum.

---

## Accessibility

- **Focus order:** Page title → Invitar button → Search → Role filter → Table (first row) → Pagination
- **Screen reader:** Table has `role="table"`, columns have `scope="col"`. Status badges have `aria-label` ("Estado: Activo"). Role inline edit announces change via `aria-live="polite"`.
- **Keyboard navigation:** Escape closes inline role editor and modals. Enter confirms inline role selection. Arrow keys navigate role dropdown options.
- **Language:** All labels es-419. Role names in Spanish.

---

## Design Tokens

**Colors:**
- Table header: `bg-gray-50 text-gray-500 text-xs font-medium uppercase`
- Table row hover: `hover:bg-gray-50`
- Action icon buttons: `text-gray-400 hover:text-gray-600`

**Spacing:**
- Table cell padding: `py-3 px-4`
- Filter bar gap: `gap-3`

---

## Implementation Notes

**File Location:**
- Page: `src/app/(dashboard)/settings/equipo/page.tsx`
- Components: `src/components/settings/TeamTable.tsx`, `src/components/settings/InviteMemberModal.tsx`, `src/components/settings/DeactivateConfirmModal.tsx`

**Hooks Used:**
- `useAuth()` — role check for edit permission
- `useTeamMembers(filters)` — TanStack Query hook
- `useInviteMember()`, `useUpdateMemberRole()`, `useDeactivateMember()`

**Form Library:** React Hook Form + Zod for invite modal form

---

## Test Cases

### Happy Path
1. Invite new doctor
   - **Given:** clinic_owner on team page, plan allows additional doctors
   - **When:** opens modal, enters email, selects Doctor, clicks "Enviar invitación"
   - **Then:** modal closes, new row appears as Pendiente, toast success shown

2. Change role
   - **Given:** active team member row visible
   - **When:** clicks pencil, selects Asistente, confirms
   - **Then:** role badge updates immediately, success toast shown

### Edge Cases
1. Invite email already exists in team: inline validation error shown
2. Plan limit reached: invite modal shows upgrade prompt
3. Resend invite to pending member: toast "Invitación reenviada"

### Error Cases
1. Role update API fails: inline edit reverts, error toast shown
2. Deactivation fails: modal stays open, error message shown inside modal

---

## Acceptance Criteria

- [ ] Table shows all team members with correct data
- [ ] Role badges and status pills use correct colors
- [ ] Invite modal validates email and role
- [ ] Inline role editing works without page reload
- [ ] Deactivate confirmation modal shows member name
- [ ] Plan limit check prevents over-inviting
- [ ] Search and role filter work together
- [ ] Mobile card view renders correctly
- [ ] Accessibility: all interactive elements keyboard-navigable
- [ ] Spanish labels throughout

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
