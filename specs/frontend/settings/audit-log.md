# Registro de Auditoría — Frontend Spec

## Overview

**Spec ID:** FE-S-09

**Screen:** Audit log viewer — chronological record of all user actions within the tenant.

**Route:** `/settings/auditoria`

**Priority:** Medium

**Backend Specs:** `specs/infra/audit-logging.md`, `specs/analytics/AN-07.md`

**Dependencies:** `FE-DS-01`, `FE-DS-02` (button), `FE-DS-04` (select), `FE-DS-05` (table), `FE-DS-11` (badge), `FE-DS-12` (avatar), `FE-DS-17` (skeleton)

---

## User Flow

**Entry Points:**
- Sidebar: Configuración → Auditoría

**Exit Points:**
- Click user name in log → user profile
- Click resource → resource detail (patient, record, etc.)
- Export CSV download

**User Story:**
> As a clinic_owner, I want to see a complete chronological log of all actions performed in my clinic account so that I can audit changes, investigate incidents, and demonstrate compliance with data protection requirements.

**Roles with access:** `clinic_owner` only. Hard redirect to dashboard for all other roles.

---

## Layout Structure

```
+------------------------------------------+
|              Header (h-16)               |
+--------+---------------------------------+
|        |  "Registro de Auditoría"        |
|        |  [Filter bar: user, action,     |
| Side-  |   resource type, date range]    |
|  bar   |  [Export CSV button]            |
|        +---------------------------------+
|        |  Audit log table                |
|        |  Expandable rows                |
|        |  Pagination                     |
+--------+---------------------------------+
```

---

## Filter Bar

**Layout:** Horizontal row of 4 filters + Export button. Wraps on smaller screens.

| Filter | Type | Options | Placeholder |
|--------|------|---------|-------------|
| Usuario | Searchable select | All team members | "Todos los usuarios" |
| Tipo de acción | Multi-select dropdown | Create, Read, Update, Delete, Login, Export | "Todas las acciones" |
| Tipo de recurso | Select | Patient, Clinical Record, Appointment, Invoice, User, Settings, Consent | "Todos los recursos" |
| Período | Date range picker | Custom range or presets | "Últimos 7 días" |

**Date range presets:**
- Hoy
- Últimas 24 horas
- Últimos 7 días (default)
- Últimos 30 días
- Este mes
- Mes anterior
- Personalizado (shows dual date picker)

**"Limpiar filtros" link:** Resets all filters to defaults. Shown only when at least one filter is active (non-default).

**Export CSV button:** `secondary` variant with `Download` icon. Exports current filtered results (up to 10,000 rows). Shows spinner while generating.

---

## Audit Log Table

**Columns:**

| Column | Content | Sortable | Width |
|--------|---------|----------|-------|
| Fecha y hora | `"25 Feb 2026, 14:32:07"` | Yes (default desc) | 160px |
| Usuario | Avatar (xs) + full name | No | 180px |
| Acción | Action badge | No | 110px |
| Recurso | Resource type + description | No | flex-1 |
| IP | IP address in monospace | No | 120px |
| Detalles | Expand chevron icon | No | 60px |

**Compact density:** Row height 40px, `py-2 px-3` cell padding.

**Sticky header:** `sticky top-0 z-10 bg-white border-b`.

### Action Badges

Color-coded by CRUD operation type:

| Action | Label | Background | Text | Icon |
|--------|-------|-----------|------|------|
| create | Creó | `green-100` | `green-700` | `Plus` |
| read | Consultó | `blue-100` | `blue-700` | `Eye` |
| update | Modificó | `amber-100` | `amber-700` | `Pencil` |
| delete | Eliminó | `red-100` | `red-700` | `Trash2` |
| login | Ingresó | `teal-100` | `teal-700` | `LogIn` |
| logout | Salió | `gray-100` | `gray-600` | `LogOut` |
| export | Exportó | `purple-100` | `purple-700` | `Download` |
| invite | Invitó | `indigo-100` | `indigo-700` | `UserPlus` |

**Badge format:** `[icon] [label]` — 14px text, `px-2 py-0.5 rounded-sm`.

### Resource Column Format

```
[Resource icon 16px] [Resource type label]: [Resource description]
```

Examples:
- `👤 Paciente: María García Torres (ID: P-00234)`
- `📋 Registro clínico: Consulta 25 Feb 2026 — Muela del juicio`
- `🦷 Odontograma: Actualización condición pieza 36`
- `💳 Factura: FE-00123 — $250.000 COP`
- `⚙️ Configuración: Validación RDA activada`
- `👥 Usuario: Dr. Carlos Mendoza — Rol cambiado a Asistente`

Resource name is a clickable link if the resource still exists. Strikethrough if deleted.

### IP Column

Displayed in `font-mono text-xs text-gray-500`. Hovering shows tooltip: "Ubicación aproximada: Bogotá, Colombia" (via IP geolocation if available).

---

## Expandable Row — Diff View

**Trigger:** Click chevron icon (or anywhere on the row for create/update/delete events).

**Expanded content** (below the row, spanning full width):

```
+--------------------------------------------------+
|  Cambios realizados:                              |
|  Campo              Antes              Después    |
|  -----------        --------           ---------- |
|  nombre_clinica     "Clínica Sonrisa"  "Clínica Dental Sonrisa" |
|  telefono           "+57 300 000 0000" "+57 310 123 4567" |
|                                                   |
|  Metadatos:                                       |
|  User Agent: Mozilla/5.0 (iPad; ...)              |
|  Session ID: a7f3b2c1                             |
+--------------------------------------------------+
```

**Diff display rules:**
- For `create`: shows new values (no "Antes" column)
- For `update`: shows changed fields only (before + after)
- For `delete`: shows what was deleted (no "Después" column)
- For `read`/`login`: no diff — shows only metadata
- Sensitive fields (passwords, tokens) displayed as `[REDACTADO]`

**Before/After text:**
- "Antes" value: `text-red-600 bg-red-50 px-1 rounded font-mono text-xs line-through`
- "Después" value: `text-green-700 bg-green-50 px-1 rounded font-mono text-xs`

---

## Export CSV

**Trigger:** "Exportar CSV" button with `Download` icon.

**Behavior:**
1. Button shows spinner: "Preparando exportación..."
2. Backend generates CSV asynchronously for large datasets
3. For < 1,000 rows: instant download
4. For >= 1,000 rows: toast "La exportación está siendo preparada. Recibirás una notificación cuando esté lista."

**CSV columns:** timestamp, usuario_nombre, usuario_email, accion, recurso_tipo, recurso_descripcion, ip_address, detalles_json

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Load audit log | `/api/v1/audit-logs` | GET | `specs/infra/audit-logging.md` | no-cache |
| Export CSV | `/api/v1/audit-logs/export` | GET | `specs/analytics/AN-07.md` | — |

**Query params for load:** `user_id`, `action_type[]`, `resource_type`, `date_from`, `date_to`, `page`, `limit=50`

### State Management

**Local State (useState):**
- `filters: AuditFilters` — user, actions, resource type, date range
- `expandedRowId: string | null`
- `exportLoading: boolean`

**Server State (TanStack Query):**
- Query key: `['audit-logs', tenantId, filters, page]`
- Stale time: 0 (no-cache — audit logs must be real-time)
- Cursor-based pagination

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Apply filter | Change any filter | Table reloads with new filters | Loading state |
| Clear filters | "Limpiar filtros" link | All filters reset, table reloads | — |
| Expand row | Click chevron / row | Diff section expands | Smooth expand animation |
| Collapse row | Click chevron again / other row | Diff section collapses | Smooth collapse |
| Click user | User name link | Navigate to user profile | Route change |
| Click resource | Resource name link | Navigate to resource | Route change |
| Export CSV | Export button | Download initiated | Spinner → download/toast |
| Change page | Pagination | Next/prev page loaded | Loading state |

### Animations/Transitions

- Row expansion: `max-height 0 → auto` with 150ms ease-out
- New log entries (if auto-refresh): slide down from top (if implementing live updates)

---

## Loading & Error States

### Loading State
- 10 compact skeleton rows: timestamp bar + avatar circle + text bars + badge skeleton + expand icon
- Pagination skeleton: 5 page number placeholders

### Error State
- Load failure: "No se pudo cargar el registro de auditoría." with retry button
- Export failure: error toast "Error al exportar. Intenta de nuevo."

### Empty State
- No logs for filters: illustration (search with no results), "Sin registros para este período y filtro.", "Limpiar filtros" CTA

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Table shows only: Fecha, Usuario, Acción. IP and Resource type hidden. Expand shows all detail. Filter bar collapses to a "Filtros" button that opens a drawer. |
| Tablet (640-1024px) | All columns visible. IP column condensed. |
| Desktop (> 1024px) | Full table, max-w-7xl container. |

---

## Accessibility

- **Focus order:** Filter bar (left to right) → Export button → Table (first row) → Pagination
- **Screen reader:** Table headers have `scope="col"`. Expandable rows announce with `aria-expanded="true/false"`. Action badges have `aria-label="Acción: Creó"`. IP column tooltip accessible via `aria-describedby`.
- **Keyboard navigation:** Enter/Space expands/collapses rows. Arrow keys navigate table rows (optional enhancement). Escape closes expanded row.
- **Language:** All labels es-419. Action labels in Spanish. Dates formatted in es-CO locale.

---

## Design Tokens

**Colors:**
- Table background: `bg-white`
- Header: `bg-gray-50 text-gray-500 text-xs uppercase tracking-wider`
- Row hover: `hover:bg-gray-50`
- Expanded row: `bg-gray-50 border-t border-b`
- Monospace text: `font-mono text-xs text-gray-500`

**Typography:**
- Timestamp: `text-xs font-mono text-gray-600`
- User name: `text-sm font-medium text-gray-900`
- Resource: `text-sm text-gray-600`

---

## Implementation Notes

**File Location:**
- Page: `src/app/(dashboard)/settings/auditoria/page.tsx`
- Components: `src/components/audit/AuditLogTable.tsx`, `src/components/audit/AuditLogRow.tsx`, `src/components/audit/AuditDiffView.tsx`, `src/components/audit/AuditFilters.tsx`

**Hooks Used:**
- `useAuditLogs(filters, page)` — TanStack Query
- `useExportAuditLogs(filters)` — mutation

---

## Test Cases

### Happy Path
1. View audit log
   - **Given:** clinic_owner on audit page, past 7 days filter (default)
   - **When:** page loads
   - **Then:** table shows entries with timestamps, user names, action badges, resource descriptions

2. Expand row to see diff
   - **Given:** update action row visible
   - **When:** click chevron
   - **Then:** diff table expands showing changed fields with before/after values

3. Filter by user
   - **Given:** filter bar visible
   - **When:** select "Dr. Carlos Mendoza" in user filter
   - **Then:** table shows only entries by that user

### Edge Cases
1. No logs for selected period: empty state shown
2. Resource deleted: resource link text strikethrough, click does nothing
3. Sensitive field in diff: shows "[REDACTADO]" not actual value

### Error Cases
1. Non-owner accesses page: redirect to dashboard with info toast "Sin acceso"
2. Export fails: error toast, no download

---

## Acceptance Criteria

- [ ] Audit table shows all required columns
- [ ] Action badges use correct colors per action type
- [ ] Expandable rows show diff with before/after formatting
- [ ] All 4 filters work individually and in combination
- [ ] Date range presets work correctly
- [ ] Export CSV initiates download for small datasets
- [ ] Pagination (cursor-based) works correctly
- [ ] Compact row density (40px height)
- [ ] Sticky header on scroll
- [ ] Owner-only access — redirect for others
- [ ] Mobile filter drawer works
- [ ] IP geolocation tooltip shown on hover

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
