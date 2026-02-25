# Lista de Consentimientos — Frontend Spec

## Overview

**Screen:** Consent forms list displayed within the patient detail page as a tab. Shows all consent forms associated with the patient: template name, status badge (draft, signed, voided), date, doctor responsible, and action buttons (view, download PDF). Quick-create button launches the consent creation flow.

**Route:** `/patients/{id}/consentimientos` (tab within patient detail)

**Priority:** High

**Backend Specs:**
- `specs/consents/IC-07` — List consent forms for patient

**Dependencies:**
- `specs/frontend/consents/consent-create.md` (FE-IC-02) — "Nueva" button triggers create flow
- `specs/frontend/consents/consent-sign.md` (FE-IC-03) — "Firmar" action triggers sign screen
- `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Patient detail page → "Consentimientos" tab
- Direct URL `/patients/{id}/consentimientos`

**Exit Points:**
- Click "Nuevo Consentimiento" → FE-IC-02 create flow
- Click "Ver" → opens consent preview modal (read-only PDF viewer)
- Click "Firmar" (on draft) → FE-IC-03 signing screen
- Click "Descargar PDF" → triggers PDF download
- Click "Anular" (on signed) → voiding confirmation dialog

**User Story:**
> As a doctor or assistant, I want to see all consent forms for a patient in one place so that I can verify what has been signed and quickly create new consents before a procedure.

**Roles with access:**
- clinic_owner: full access + void
- doctor: view + create + request signature (own patients)
- assistant: view + create + request signature
- receptionist: view only (cannot create or sign)

---

## Layout Structure

```
+----------------------------------------------------------+
|  [Patient Detail Tabs: Resumen | Odontograma | Historial | ... | Consentimientos]  |
+----------------------------------------------------------+
|                                                          |
|  Consentimientos Informados         [+ Nuevo]           |
|  ──────────────────────────────────────────────────      |
|                                                          |
|  [Filter: Todos ▼]  [Estado: Todos ▼]  [Buscar...]     |
|                                                          |
|  +------------------------------------------------------+|
|  | Formulario              | Estado   | Fecha  | Doctor  | Acciones |
|  |-------------------------|----------|--------|---------|----------|
|  | CI Extracción Molar     | Firmado  |25 Feb  | García  | Ver | PDF |
|  | CI Blanqueamiento       | Borrador |24 Feb  | García  | Firmar | PDF |
|  | CI Cirugía Periodontal  | Anulado  |20 Feb  | López   | Ver |      |
|  +------------------------------------------------------+|
|                                                          |
+----------------------------------------------------------+
```

**Sections:**
1. Patient tab navigation (shared across patient detail)
2. Section header with title and "Nuevo Consentimiento" primary button
3. Filter row — template type filter, status filter, search input
4. Consent table — sortable columns, action buttons per row
5. Empty state — shown when no consents exist

---

## UI Components

### Component 1: ConsentTable

**Type:** Data table

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.9

**Columns:**

| Column | Content | Sortable | Width |
|--------|---------|----------|-------|
| Formulario | Template name (text) | Yes | flex |
| Estado | Status badge | No | 120px |
| Fecha | Created date formatted `dd MMM yyyy` | Yes (default: desc) | 110px |
| Doctor | Doctor avatar + name | No | 150px |
| Acciones | Action buttons | No | 160px |

**Row behavior:**
- Click anywhere on row → opens consent preview modal (read-only)
- Hover: `bg-gray-50` highlight

### Component 2: ConsentStatusBadge

**Type:** Colored pill badge

| Status | Label | Color |
|--------|-------|-------|
| `draft` | Borrador | `bg-gray-100 text-gray-600` |
| `pending_signature` | Pendiente | `bg-amber-100 text-amber-700` |
| `signed` | Firmado | `bg-green-100 text-green-700` |
| `voided` | Anulado | `bg-red-100 text-red-600 line-through` |
| `expired` | Expirado | `bg-orange-100 text-orange-700` |

### Component 3: ActionButtons

**Type:** Button group per row

**Actions (conditional by status + role):**

| Status | Actions shown |
|--------|---------------|
| `draft` | [Firmar →] [PDF] [Eliminar] |
| `pending_signature` | [Enviar recordatorio] [Ver] [PDF] |
| `signed` | [Ver] [PDF] [Anular] (clinic_owner only) |
| `voided` | [Ver] |
| `expired` | [Ver] [Nueva versión →] |

**Button styles:**
- "Firmar" / "Nueva versión": `variant="primary" size="sm"`
- "Ver": `variant="outline" size="sm"`
- "PDF": icon button with `FileDown` icon, tooltip "Descargar PDF"
- "Anular": `variant="ghost" size="sm" text-red-600`
- "Eliminar": `variant="ghost" size="sm" text-red-600` (draft only)

**Void confirmation dialog:**
- Title: "Anular consentimiento"
- Body: "Esta acción marcará el consentimiento como anulado y no podrá revertirse. El registro quedará en el historial del paciente."
- Reason textarea: required, max 200 chars
- Buttons: "Cancelar" + "Confirmar anulación" (red)

### Component 4: FilterRow

**Type:** Horizontal filter bar

**Filters:**
- Template type dropdown: "Todos los tipos" | per category (Cirugía, Procedimiento, Anestesia, etc.)
- Status dropdown: "Todos los estados" | individual status options
- Search input: filters by template name, `debounce 300ms`, client-side filter

### Component 5: NewConsentButton

**Type:** Primary button

**Content:** `Plus` icon + "Nuevo Consentimiento"
**Behavior:** Navigates to FE-IC-02 create flow at `/patients/{id}/consentimientos/nuevo`
**Hidden for:** receptionist role

---

## Form Fields

Not applicable — this is a list view. Form fields are in FE-IC-02 (create) and FE-IC-03 (sign).

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Load consents | `/api/v1/patients/{id}/consents?limit=50&order=created_at:desc` | GET | `specs/consents/IC-07` | 5min |
| Download PDF | `/api/v1/consents/{id}/pdf` | GET | `specs/consents/IC-07` | 30min |
| Void consent | `/api/v1/consents/{id}/void` | POST | `specs/consents/IC-07` | none |
| Delete draft | `/api/v1/consents/{id}` | DELETE | `specs/consents/IC-07` | none |

### State Management

**Local State (useState):**
- `filterType: string` — template type filter value
- `filterStatus: string` — status filter value
- `searchQuery: string` — search text (client-side)
- `voidDialogOpen: boolean`
- `selectedConsentId: string | null`

**Global State (Zustand):**
- `authStore.user.role` — determines visible actions
- `patientStore.patient` — patient context (name, id)

**Server State (TanStack Query):**
- Query key: `['consents', patientId, tenantId]`
- Stale time: 5min
- Mutation: `useVoidConsent(id)` — POST with reason
- Mutation: `useDeleteDraftConsent(id)` — DELETE with optimistic removal

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click "Nuevo Consentimiento" | Button click | Navigate to FE-IC-02 | Navigation |
| Click "Firmar" | Button click | Navigate to FE-IC-03 | Navigation |
| Click "Ver" | Button click | PDF preview modal opens | Modal |
| Click "PDF" icon | Button click | PDF downloads | Browser download |
| Click "Anular" | Button click | Void confirmation dialog opens | Dialog |
| Confirm void | Dialog confirm | POST /void, row updates | Badge changes to "Anulado", toast |
| Click "Eliminar" | Button click | Delete confirmation dialog | Dialog |
| Filter change | Select change | Client-side filter applied | Instant |
| Search input | Typing (debounce) | Client-side name filter | Instant |
| Sort column header | Click | Sort applied, icon shows direction | Instant |

### Animations/Transitions

- Row appears on status change: brief `bg-green-50` flash then normalizes (200ms)
- Deleted row: fade-out before removal (150ms)
- PDF download: "PDF" icon spins briefly during generation

---

## Loading & Error States

### Loading State
- Table: 5 skeleton rows — `animate-pulse` with cells: `w-48 h-4`, `w-20 h-6 rounded-full`, `w-20 h-4`, `w-24 h-4`, `w-24 h-8`

### Error State
- Load failure: "Error al cargar los consentimientos." with `RefreshCcw` icon and "Reintentar" inside the table area

### Empty State
- **Illustration:** Lucide `FileSignature` icon `w-16 h-16 text-gray-300`
- **Message:** "Sin consentimientos registrados"
- **Sub-text:** "Crea el primer consentimiento informado para este paciente."
- **CTA:** "Nuevo Consentimiento" → FE-IC-02

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Table becomes card list. Each card: template name, status badge, date, action buttons. Filters collapse to single "Filtrar" button opening bottom sheet. |
| Tablet (640-1024px) | Full table but "Doctor" column hidden (shown in row expand). Action buttons fit in row. Primary device. |
| Desktop (> 1024px) | Full table with all columns. All actions visible. |

**Tablet priority:** Medium — consents are checked before procedures on tablets in the clinic.

---

## Accessibility

- **Focus order:** "Nuevo Consentimiento" button → filter row → table header (sortable) → table rows → row action buttons
- **Screen reader:** Table `role="table"` with `aria-label="Consentimientos del paciente"`. Status badges `aria-label="Estado: {status}"`. Action buttons `aria-label="{action} consentimiento: {template name}"`.
- **Keyboard navigation:** Tab to each row. Enter opens preview. Action buttons reachable via Tab within row. Sort headers activatable with Enter/Space.
- **Color contrast:** WCAG AA. Status badges use color + text label.
- **Language:** All labels, column headers, empty state in es-419.

---

## Design Tokens

**Colors:**
- Table header: `bg-gray-50 text-xs font-semibold text-gray-500 uppercase`
- Row border: `border-b border-gray-100`
- Row hover: `hover:bg-gray-50`
- "Firmar" button: `bg-primary-600 text-white`
- "Anular" button: `text-red-600`
- PDF icon: `text-gray-400 hover:text-primary-600`

**Typography:**
- Template name: `text-sm font-medium text-gray-900`
- Date: `text-sm text-gray-500`
- Doctor name: `text-sm text-gray-700`

**Spacing:**
- Table row padding: `px-4 py-3`
- Filter row gap: `gap-3`
- Action button gap: `gap-1`
- Section margin: `mt-6`

**Border Radius:**
- Status badges: `rounded-full`
- Action buttons: `rounded-lg`
- Table container: `rounded-xl overflow-hidden border border-gray-200`

---

## Implementation Notes

**Dependencies (npm):**
- `lucide-react` — Plus, FileDown, Eye, FileSignature, RefreshCcw, Trash2
- `@tanstack/react-query` — data fetching + mutations
- `date-fns` — date formatting

**File Location:**
- Component: `src/components/consents/ConsentList.tsx`
- Sub-components: `src/components/consents/ConsentStatusBadge.tsx`, `src/components/consents/VoidConsentDialog.tsx`
- Hook: `src/hooks/usePatientConsents.ts`

**Hooks Used:**
- `useAuth()` — role for action visibility
- `useQuery(['consents', patientId])` — list data
- `useVoidConsent()` — POST void mutation
- `useDeleteDraftConsent()` — DELETE optimistic mutation

---

## Test Cases

### Happy Path
1. Doctor views patient consent list
   - **Given:** Patient has 3 consents (1 signed, 1 draft, 1 voided)
   - **When:** Navigate to Consentimientos tab
   - **Then:** Table shows all 3 rows with correct status badges and role-appropriate actions

2. Doctor clicks "Firmar" on draft
   - **Given:** Draft consent exists
   - **When:** Click "Firmar" button
   - **Then:** Navigate to FE-IC-03 signing screen with consent pre-loaded

### Edge Cases
1. Receptionist viewing consents
   - **Given:** Logged in as receptionist
   - **When:** Navigate to Consentimientos tab
   - **Then:** "Nuevo Consentimiento" button hidden. "Firmar" and "Anular" buttons hidden. "Ver" and "PDF" visible.

2. Filter returns no results
   - **Given:** Filter set to "Anulado", but patient has no voided consents
   - **When:** Status filter changed to "Anulado"
   - **Then:** Table shows empty state "Sin consentimientos con este filtro. Prueba con otro estado."

### Error Cases
1. PDF generation fails
   - **Given:** PDF endpoint returns 500
   - **When:** Click PDF download button
   - **Then:** Toast "Error al generar el PDF. Intenta de nuevo."

---

## Acceptance Criteria

- [ ] Table with all columns: template name, status, date, doctor, actions
- [ ] Status badges with correct colors for all 5 statuses
- [ ] "Nuevo Consentimiento" button (hidden for receptionist)
- [ ] "Firmar" action for draft/pending consents
- [ ] "Ver" opens read-only PDF preview modal
- [ ] "PDF" triggers download
- [ ] "Anular" opens confirmation dialog with reason textarea (clinic_owner only)
- [ ] "Eliminar" for draft consents with confirmation
- [ ] Filter by type and status (client-side)
- [ ] Search by template name (client-side, debounced)
- [ ] Sortable columns (template name, date)
- [ ] Loading skeleton (5 rows)
- [ ] Error state with retry
- [ ] Empty state with "Nuevo Consentimiento" CTA
- [ ] Responsive: card list mobile, full table tablet/desktop
- [ ] Touch targets min 44px
- [ ] ARIA table roles and action button labels
- [ ] All labels in es-419

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
