# Plantillas de Consentimiento — Frontend Spec

## Overview

**Spec ID:** FE-S-06

**Screen:** Consent template management — list, preview, edit, duplicate, and delete consent templates.

**Route:** `/settings/consentimientos`

**Priority:** Medium

**Backend Specs:** `specs/consents/consent-template-list.md`, `specs/consents/consent-template-create.md`

**Dependencies:** `FE-DS-01`, `FE-DS-02` (button), `FE-DS-05` (table), `FE-DS-06` (modal), `FE-DS-11` (badge), `FE-DS-16` (empty-state)

---

## User Flow

**Entry Points:**
- Sidebar: Configuración → Consentimientos
- Patient flow: "Agregar consentimiento" → redirects to create template if none exist

**Exit Points:**
- Template editor (create or edit): navigates to `/settings/consentimientos/[id]/editar`
- Back to any other settings section

**User Story:**
> As a clinic_owner or doctor, I want to manage my informed consent templates so that I can quickly apply standardized consents to patients before procedures, complying with Colombia's legal requirements.

**Roles with access:** `clinic_owner` (full access), `doctor` (view + duplicate + edit own custom), `assistant` (view only)

---

## Layout Structure

```
+------------------------------------------+
|              Header (h-16)               |
+--------+---------------------------------+
|        |  "Plantillas de Consentimiento" |
|        |  [Search] [Filter: type] [+ Crear plantilla] |
| Side-  +---------------------------------+
|  bar   |  Templates table                |
|        |  Pagination                     |
+--------+---------------------------------+
```

---

## Templates Table

**Columns:**

| Column | Content | Sortable | Width |
|--------|---------|----------|-------|
| Nombre | Template name | Yes | flex-1 |
| Tipo | Badge: Incorporada / Personalizada | No | 140px |
| Procedimiento | Associated procedure type | No | 180px |
| Última modificación | Relative date or "—" for built-in | Yes | 150px |
| Acciones | Action button group | No | 120px |

**Type badges:**

| Type | Label | Background | Text |
|------|-------|-----------|------|
| built_in | Incorporada | `blue-100` | `blue-700` |
| custom | Personalizada | `purple-100` | `purple-700` |

### Row Actions

**For built-in templates (non-editable):**
- Preview icon (eye) — opens preview modal
- Duplicate icon (copy) — duplicates as custom template

**For custom templates:**
- Preview icon (eye) — opens preview modal
- Edit icon (pencil) — navigates to template editor
- Duplicate icon (copy) — creates a copy prefixed "Copia de [nombre]"
- Delete icon (trash) — opens delete confirmation modal

**Icon buttons:** 32x32px, `text-gray-400 hover:text-gray-700`, with tooltip labels.

**Non-editable row indicator:** Built-in rows have a subtle lock icon (16px) beside the template name. Hover tooltip: "Plantilla incorporada de DentalOS — no editable. Puedes duplicarla para personalizar."

---

## Built-in Templates (pre-loaded by DentalOS)

Displayed at the top of the list, separated by a subtle divider or "Incorporadas" section header:

| Template Name | Procedure |
|---------------|-----------|
| Consentimiento General | General |
| Extracción dental | Exodoncia |
| Endodoncia | Tratamiento de conductos |
| Ortodoncia | Brackets/Alineadores |
| Implante dental | Implantología |
| Blanqueamiento dental | Estética dental |
| Cirugía periodontal | Periodoncia |

---

## Preview Modal

**Trigger:** Eye icon in row actions

**Modal size:** `lg` (max-w-2xl)

**Title:** Template name

**Content:**
- Read-only rendered HTML/rich text view of the consent template
- Variable placeholders shown highlighted: `{nombre_paciente}`, `{fecha}`, `{nombre_doctor}`, `{procedimiento}`
- Highlighted in teal `bg-teal-50 text-teal-700 px-1 rounded`
- Legal disclaimer section clearly separated with a horizontal rule
- Signature block preview at bottom (grayed out, non-functional here)

**Footer:**
- "Cerrar" (secondary)
- "Duplicar y editar" (primary) — only for built-in; for custom: "Editar" (primary)

---

## Delete Confirmation Modal

**Trigger:** Trash icon on custom templates

**Size:** `sm`

**Content:**
- Warning icon (red, `AlertTriangle` 24px)
- Title: "Eliminar plantilla"
- Message: "¿Estás seguro de que deseas eliminar **[nombre plantilla]**? Esta acción no se puede deshacer. Los consentimientos ya firmados con esta plantilla no se verán afectados."
- Footer: "Cancelar" (secondary) + "Eliminar" (danger)

---

## Template Editor (Linked Page)

**Route:** `/settings/consentimientos/nueva` (create) or `/settings/consentimientos/[id]/editar` (edit)

**Note:** Full template editor spec is FE-IC-04. This settings page links to it but does not contain the editor itself.

**Navigation to editor:**
- "Crear plantilla" button → `/settings/consentimientos/nueva`
- Pencil icon → `/settings/consentimientos/[id]/editar`
- Duplicate action: creates copy via API, then navigates to editor for the new copy

---

## Filter Bar

**Search:** Text input with magnifying glass icon. Searches by template name (client-side if < 50 templates, server-side if more). Placeholder: "Buscar plantilla..."

**Type filter:** Dropdown select. Options: "Todos los tipos", "Incorporadas", "Personalizadas"

**Combination:** Search and type filter work together (AND logic).

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| List templates | `/api/v1/consents/templates` | GET | `specs/consents/consent-template-list.md` | 5min |
| Duplicate | `/api/v1/consents/templates/{id}/duplicate` | POST | `specs/consents/consent-template-create.md` | Invalidate |
| Delete | `/api/v1/consents/templates/{id}` | DELETE | `specs/consents/consent-template-create.md` | Invalidate |

### State Management

**Local State (useState):**
- `previewModalTarget: ConsentTemplate | null`
- `deleteModalTarget: ConsentTemplate | null`
- `searchQuery: string`
- `typeFilter: 'all' | 'built_in' | 'custom'`

**Server State (TanStack Query):**
- Query key: `['consent-templates', tenantId, { search, typeFilter }]`
- Stale time: 5 minutes
- Mutation: `useDuplicateTemplate()`, `useDeleteTemplate()`

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Preview template | Eye icon | Preview modal opens | — |
| Duplicate built-in | Copy icon (or modal button) | POST duplicate | Toast "Plantilla duplicada. Puedes editarla ahora." + navigate to editor |
| Duplicate custom | Copy icon | POST duplicate | Toast + new row appears |
| Edit custom | Pencil icon | Navigate to editor | Route change |
| Delete custom | Trash icon | Confirmation modal opens | — |
| Confirm delete | Delete button in modal | DELETE API | Toast "Plantilla eliminada", row disappears |
| Create new | "+ Crear plantilla" | Navigate to /nueva | Route change |
| Search | Type in search | Table filters | Results update |

---

## Loading & Error States

### Loading State
- Table skeleton: 7 rows (built-in count) + 3 custom rows, each with name bar + two badge skeletons + date bar + action icons

### Error State
- Load failure: "No se pudieron cargar las plantillas. Intenta de nuevo." with retry

### Empty State
**No custom templates (built-ins always show):**
- Custom section empty: "Aún no tienes plantillas personalizadas. Duplica una incorporada para comenzar."
- CTA: "Crear plantilla" button

**No search results:**
- "Sin resultados para '[query]'" with "Limpiar búsqueda" link

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Cards instead of table. Each card: template name + type badge + procedure + action buttons below. |
| Tablet (640-1024px) | Full table. All columns visible. |
| Desktop (> 1024px) | Full table, max-w-5xl. |

---

## Accessibility

- **Focus order:** Search → Type filter → Create button → Table (first row) → Pagination
- **Screen reader:** Table has proper `scope="col"` headers. Action icon buttons have `aria-label` in Spanish ("Previsualizar plantilla", "Duplicar plantilla", "Editar plantilla", "Eliminar plantilla").
- **Keyboard navigation:** Escape closes modals. Delete confirmation navigates focus back to table row after close.
- **Language:** All labels es-419. Built-in template names in Spanish.

---

## Implementation Notes

**File Location:**
- Page: `src/app/(dashboard)/settings/consentimientos/page.tsx`
- Editor page: `src/app/(dashboard)/settings/consentimientos/[id]/editar/page.tsx`
- Components: `src/components/settings/ConsentTemplateTable.tsx`, `src/components/settings/ConsentPreviewModal.tsx`

**Hooks Used:**
- `useConsentTemplates(filters)` — list query
- `useDuplicateConsentTemplate()` — mutation
- `useDeleteConsentTemplate()` — mutation

---

## Test Cases

### Happy Path
1. Duplicate built-in and view in editor
   - **Given:** built-in "Extracción dental" template visible
   - **When:** click copy icon
   - **Then:** POST duplicate, navigate to editor with "Copia de Extracción dental" pre-filled

2. Delete custom template
   - **Given:** custom template "Blanqueamiento personalizado" visible
   - **When:** click trash → click "Eliminar" in modal
   - **Then:** DELETE sent, row removed, toast shown

### Edge Cases
1. Delete built-in template: trash icon not rendered (action not available)
2. Duplicate while offline: error toast, no navigation

---

## Acceptance Criteria

- [ ] Built-in templates listed with lock indicator and no edit option
- [ ] Custom templates have all 4 actions (preview, edit, duplicate, delete)
- [ ] Preview modal shows template with highlighted variables
- [ ] Delete confirmation modal shows template name
- [ ] Duplicate navigates to editor with copy pre-filled
- [ ] Search and type filter work together
- [ ] Mobile card view renders correctly
- [ ] Role-based access enforced (assistants view-only)
- [ ] Empty state shown for no custom templates

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
