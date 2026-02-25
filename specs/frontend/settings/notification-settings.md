# Configuración de Notificaciones — Frontend Spec

## Overview

**Spec ID:** FE-S-05

**Screen:** Notification settings — clinic-wide reminders and per-user channel preferences.

**Route:** `/settings/notificaciones`

**Priority:** Medium

**Backend Specs:** `specs/appointments/AP-17.md`, `specs/appointments/AP-18.md`, `specs/users/U-09.md`

**Dependencies:** `FE-DS-01`, `FE-DS-02` (button), `FE-DS-03` (input), `FE-DS-04` (select), `FE-DS-10` (card)

---

## User Flow

**Entry Points:**
- Sidebar: Configuración → Notificaciones

**Exit Points:**
- Any other settings section

**User Story:**
> As a clinic_owner, I want to configure when and how my clinic sends appointment reminders so that patients show up on time. As any staff member, I want to control which events I am notified about and via which channels.

**Roles with access:**
- Tab "Recordatorios de clínica": `clinic_owner` (edit), all roles (read-only view)
- Tab "Mis preferencias": all roles (each user edits their own preferences)

---

## Layout Structure

```
+------------------------------------------+
|              Header (h-16)               |
+--------+---------------------------------+
|        |  "Notificaciones"               |
| Side-  |  [Tab: Recordatorios Clínica]   |
|  bar   |  [Tab: Mis Preferencias]        |
|        +---------------------------------+
|        |  [Active tab content]           |
+--------+---------------------------------+
```

**Tabs:** Two tabs using underline variant.

---

## Tab 1: Recordatorios de Clínica

**Owner only section.** Non-owners see a read-only view with a note: "Solo el propietario de la clínica puede modificar esta configuración."

### Reminder List

**Layout:** Vertical list of reminder rules inside a Card. Each rule is a row.

**Reminder row structure:**

```
+----------------------------------------------------+
| [Trash icon] [Hours input] horas antes | Canales:  |
|                                        | [Email] [SMS] [WhatsApp] |
+----------------------------------------------------+
```

**Row fields:**

| Field | Type | Validation | Description |
|-------|------|------------|-------------|
| horas_antes | number input | Integer 1-720, required | Hours before appointment |
| canales | checkbox group | At least 1 required | Email, SMS, WhatsApp |

**Default rules (pre-populated):**
- 48 horas antes: Email, WhatsApp
- 24 horas antes: Email, SMS, WhatsApp
- 2 horas antes: SMS, WhatsApp

**Add rule button:** "+ Agregar recordatorio" (ghost button with plus icon, below the list).

**Constraints:**
- Maximum 5 rules per clinic
- Hours must be unique across rules (no duplicate timings)
- If SMS or WhatsApp selected but integration not connected: warning tooltip "Requiere integración activa" with link to Configuración → Integraciones

**Delete rule:** Trash icon on the left of each row. Click → row disappears immediately (optimistic) with undo toast "Recordatorio eliminado. Deshacer."

### SMS/WhatsApp Message Preview

Below the reminder list, a collapsible section "Ver mensaje de ejemplo":

```
[Expand toggle]
Vista previa del mensaje:

"Hola {nombre_paciente}, te recordamos que tienes
una cita en Clínica Dental Sonrisa el {fecha} a las
{hora}. Confirma respondiendo SI o NO."
```

Variables shown as `{variable}` in teal monospace text.

**Channel tabs:** Email preview | SMS preview | WhatsApp preview

**Save button:** "Guardar recordatorios" at bottom of section.

---

## Tab 2: Mis Preferencias

**Per-user notification matrix.** Each user sees only their own preferences.

### Toggle Matrix Table

**Layout:** Table where rows = event types, columns = channels.

| Event Type | In-app | Email | SMS | WhatsApp |
|------------|--------|-------|-----|----------|
| Nuevas citas | [toggle] | [toggle] | [toggle] | [toggle] |
| Cancelaciones | [toggle] | [toggle] | [toggle] | [toggle] |
| Facturación | [toggle] | [toggle] | [toggle] | [toggle] |
| Registros clínicos | [toggle] | [toggle] | [toggle] | [toggle] |
| Mensajes internos | [toggle] | [toggle] | [toggle] | [toggle] |
| Actualizaciones sistema | [toggle] | [toggle] | [toggle] | [toggle] |

**Toggle component:** Standard iOS-style toggle switch (h-6, w-11, `bg-teal-600` when on, `bg-gray-200` when off, animated knob).

**Column headers:** Show channel icon (Lucide) + label. If channel not connected for this user (e.g., no phone number on file): column header shows warning icon, individual toggles for that column are disabled with tooltip "Agrega tu teléfono en tu perfil para activar SMS".

**Role-specific event types:** Certain events only shown to relevant roles:
- "Facturación" only shown to clinic_owner
- "Registros clínicos" only shown to doctor and assistant

**Save behavior:** Each toggle change auto-saves with a brief spinner on the toggle (no explicit save button needed). Success: no toast (too frequent), just visual confirmation (toggle settles). Failure: toggle reverts + error toast.

**"Desactivar todo" link:** Below table, "Desactivar todas las notificaciones" in text-sm text-red-600. Click → all toggles turn off + confirmation: "Se desactivaron todas las notificaciones."

---

## Channel Status Banner

**Position:** Top of the page (below page title, above tabs), only visible if relevant.

**Types:**

- Warning (amber): "SMS no configurado. Conecta tu integración para enviar recordatorios por SMS." [Configurar] button
- Warning (amber): "WhatsApp no configurado. El canal de WhatsApp Business no está conectado." [Configurar] button
- Info (blue): "Email activo. Enviando desde recordatorios@clinica.com" (if connected)

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Load clinic reminders | `/api/v1/tenants/{id}/reminder-config` | GET | `specs/appointments/AP-17.md` | 5min |
| Save clinic reminders | `/api/v1/tenants/{id}/reminder-config` | PATCH | `specs/appointments/AP-17.md` | Invalidate |
| Load user preferences | `/api/v1/users/me/notification-preferences` | GET | `specs/users/U-09.md` | 5min |
| Update user preference | `/api/v1/users/me/notification-preferences` | PATCH | `specs/users/U-09.md` | Invalidate |

### State Management

**Local State (useState):**
- `activeTab: 'clinic' | 'personal'`
- `reminderRules: ReminderRule[]` — local copy for editing
- `isDirty: boolean` — for clinic reminders tab

**Server State (TanStack Query):**
- Query keys: `['clinic-reminders', tenantId]`, `['user-notification-prefs', userId]`
- Auto-save mutation for preferences: debounced 500ms

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Add reminder | Click "+ Agregar recordatorio" | New row appended with defaults (24h, Email) | Focus moves to new row hours input |
| Delete reminder | Click trash icon | Row removed optimistically | Undo toast |
| Change hours | Input change | Local state updates | — |
| Toggle channel | Checkbox click | Local state updates | — |
| Save reminders | "Guardar recordatorios" button | PATCH | Toast "Recordatorios guardados" |
| Toggle preference | Toggle switch | PATCH immediately (auto-save) | Toggle spinner → settles |
| Preview message | Click "Ver mensaje de ejemplo" | Expandable section reveals | Smooth expand animation |

---

## Loading & Error States

### Loading State
- Tab 1 skeleton: 3 rows with number input bar + 3 checkbox skeletons each
- Tab 2 skeleton: 6x4 grid of toggle skeletons

### Error State
- Load failure: error card with retry
- Save failure: error toast persists

### Empty State
- No reminder rules: "No hay recordatorios configurados. Agrega uno para empezar." with "+ Agregar" button

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Reminder rows stack vertically (hours on top, channels below). Matrix table scrolls horizontally. |
| Tablet (640-1024px) | Standard layout. Toggle matrix fully visible. |
| Desktop (> 1024px) | Max-w-3xl content area. Same as tablet. |

---

## Accessibility

- **Focus order:** Tabs → active tab content → form elements top-to-bottom → Save
- **Screen reader:** Tabs have `role="tab"` and `aria-selected`. Toggle switches are `role="switch"` with `aria-checked`. Matrix table has `scope="col"` column headers.
- **Keyboard navigation:** Arrow keys between tabs. Space toggles switches. Tab moves through matrix.
- **Language:** All labels es-419. Channel names in Spanish ("Correo", "Mensaje de texto", "WhatsApp").

---

## Implementation Notes

**File Location:**
- Page: `src/app/(dashboard)/settings/notificaciones/page.tsx`
- Components: `src/components/settings/ReminderRuleList.tsx`, `src/components/settings/ReminderRuleRow.tsx`, `src/components/settings/NotificationMatrix.tsx`, `src/components/settings/MessagePreview.tsx`

---

## Test Cases

### Happy Path
1. Add a new reminder rule
   - **Given:** clinic_owner on Recordatorios tab
   - **When:** clicks "+ Agregar recordatorio", sets 12 hours, checks WhatsApp, clicks "Guardar"
   - **Then:** PATCH sent, new rule appears, toast success

2. Toggle personal preference off
   - **Given:** user on Mis Preferencias tab
   - **When:** toggles "Nuevas citas / Email" off
   - **Then:** PATCH sent immediately, toggle settles in off position

### Edge Cases
1. Duplicate reminder hours (24h added twice): error "Ya existe un recordatorio para 24 horas. Usa un valor diferente."
2. Max 5 rules reached: "+ Agregar recordatorio" button disabled with tooltip "Máximo 5 recordatorios"

---

## Acceptance Criteria

- [ ] Two tabs switch correctly
- [ ] Reminder rules CRUD works (add, edit hours, toggle channels, delete with undo)
- [ ] Max 5 rules enforced
- [ ] Duplicate hours validated
- [ ] Preference matrix auto-saves on toggle
- [ ] Channel status banner shows when integrations disconnected
- [ ] Role-based access: non-owners see clinic tab read-only
- [ ] Mobile responsive with horizontal scroll on matrix
- [ ] All toggles keyboard-accessible with Space key

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
