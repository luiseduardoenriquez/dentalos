# Editor de Plantillas de Consentimiento — Frontend Spec

## Overview

**Screen:** Custom consent template editor for clinic owners. Rich text editor (TipTap or Lexical) for creating and editing consent form templates. Includes a placeholder insertion toolbar for DentalOS variables (`{{patient_name}}`, `{{patient_document}}`, `{{date}}`, `{{procedure}}`, `{{doctor_name}}`). Preview mode shows how the form will look with sample data filled in. Save as draft or publish. Access restricted to clinic_owner role only.

**Route:** `/settings/consentimientos/plantillas/nueva` (create) | `/settings/consentimientos/plantillas/{id}` (edit)

**Priority:** Medium

**Backend Specs:**
- `specs/consents/IC-02` — Create consent template
- `specs/consents/IC-03` — Update consent template (implied)
- `specs/consents/consent-template-list.md` — List templates

**Dependencies:**
- `specs/frontend/consents/consent-list.md` (FE-IC-01) — consents use templates created here
- `specs/frontend/consents/consent-create.md` (FE-IC-02) — templates appear in FE-IC-02 step 1
- `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Settings → Consentimientos → "Plantillas" → "+ Nueva Plantilla"
- Settings → Consentimientos → Plantillas list → click existing template to edit
- FE-IC-02 empty state → "Crear nueva plantilla" link

**Exit Points:**
- Save (publish) → toast "Plantilla publicada" → return to template list
- Save draft → toast "Borrador guardado" → remain on page
- Cancel → discard confirmation if dirty → return to template list
- Preview mode → back to edit mode

**User Story:**
> As a clinic_owner, I want to create custom consent form templates with our clinic's specific procedures and legal language so that doctors can quickly generate consents without rewriting legal text each time.

**Roles with access:** clinic_owner only (read-only view for doctor, hidden for receptionist/assistant)

---

## Layout Structure

```
+--------+---------------------------------------------------+
|        |  [← Plantillas]  Nueva Plantilla de Consentimiento|
|        +---------------------------------------------------+
|        |  Nombre: [_________________________________]       |
|        |  Categoría: [Select ▼]  [Estado: Borrador/Activa] |
|        |---------------------------------------------------|
|        |  [Edit] [Preview]                [Guardar ▼]     |
|        |---------------------------------------------------|
| Side-  |                                                   |
|  bar   |  Insertar variable:                              |
|        |  [Nombre pac.][Documento][Fecha][Proced.][Doctor] |
|        |---------------------------------------------------|
|        |  +-------------------------------------------+   |
|        |  |                                           |   |
|        |  |         RICH TEXT EDITOR AREA             |   |
|        |  |                                           |   |
|        |  |  CLÍNICA DENTAL XYZ                       |   |
|        |  |  CONSENTIMIENTO INFORMADO PARA...         |   |
|        |  |                                           |   |
|        |  |  Yo, {{patient_name}}, identificado con   |   |
|        |  |  cédula {{patient_document}}, en pleno    |   |
|        |  |  uso de mis facultades...                 |   |
|        |  |                                           |   |
|        |  +-------------------------------------------+   |
+--------+---------------------------------------------------+
```

**Sections:**
1. Page header — back link, title
2. Template metadata — name input, category select, status badge
3. Editor/Preview mode toggle tabs
4. Variable insertion toolbar — quick-insert placeholder buttons
5. Rich text editor area (edit mode) or rendered preview (preview mode)
6. Save actions — "Guardar borrador" | "Publicar plantilla"

---

## UI Components

### Component 1: TemplateMetadataBar

**Type:** Inline form fields above editor

**Fields:**
- Template name: `text input`, large, `text-lg font-semibold`, placeholder "Nombre de la plantilla..."
- Category: `Select` dropdown — Cirugía, Periodoncia, Estética, Anestesia, Ortodoncia, General, Otro
- Status badge: "Borrador" (`bg-amber-100 text-amber-700`) or "Activa" (`bg-green-100 text-green-700`) — read-only, changes on publish
- Last saved: `text-xs text-gray-400` "Guardado hace 2 minutos" (auto-save feedback)

### Component 2: EditPreviewTabs

**Type:** Tab toggle

**Tabs:** `[Editar]` | `[Vista previa]`
**Active:** `bg-white shadow-sm text-primary-700`
**Behavior:** Switching to Preview renders template with sample data; does not call API

### Component 3: VariableInsertionToolbar

**Type:** Horizontal button bar

**Buttons (one per variable):**

| Button Label | Inserts | Icon |
|--------------|---------|------|
| "Nombre del paciente" | `{{patient_name}}` | `User` |
| "Documento" | `{{patient_document}}` | `CreditCard` |
| "Fecha" | `{{date}}` | `Calendar` |
| "Procedimiento" | `{{procedure}}` | `Wrench` |
| "Doctor" | `{{doctor_name}}` | `Stethoscope` |

**Button style:** `text-xs bg-primary-50 text-primary-700 border border-primary-200 rounded px-2 py-1.5 hover:bg-primary-100`
**Behavior:**
- Clicking inserts placeholder at current cursor position in editor
- Editor must be focused; if not focused, inserts at end
- Visual: placeholder appears as inline chip `{{patient_name}}` in distinct style within editor

**Validation helper:** "Validar variables" button at end of toolbar — scans editor content, highlights any unrecognized `{{...}}` patterns in red

### Component 4: RichTextEditor

**Type:** TipTap editor (or Lexical)

**Extensions:**
- Bold, Italic, Underline
- Heading (H1, H2, H3)
- Unordered + Ordered lists
- Text alignment (left, center, right, justify)
- Horizontal rule
- Hard break
- History (undo/redo) — `Cmd+Z` / `Ctrl+Z`

**Toolbar:**
```
[B] [I] [U] | [H1][H2][H3] | [List][OList] | [Left][Center][Right] | [—] | [↩][↺]
```

**Variable placeholder rendering in editor:**
- Variables `{{patient_name}}` etc. render as inline chip nodes: `bg-yellow-100 text-yellow-800 text-xs rounded px-1 py-0.5 font-mono`
- Custom TipTap extension: `VariablePlaceholder` node — non-editable inline element
- Right-click on chip: context menu "Eliminar variable"

**Editor area style:**
- `min-h-[500px]` `p-6 bg-white border border-gray-200 rounded-xl`
- Font: Inter, 14px, `leading-relaxed`

**Word count:** `text-xs text-gray-400` shown at bottom-right of editor "1.234 palabras"

### Component 5: PreviewRenderer (preview mode)

**Type:** Read-only HTML render with variable substitution

**Sample data used in preview:**
```
patient_name: "PACIENTE DE EJEMPLO"
patient_document: "1.234.567.890"
date: "25 de febrero de 2026"
procedure: "PROCEDIMIENTO A REALIZAR"
doctor_name: "Dr. Juan García"
```

**Variable highlighting:** Same `bg-yellow-100` chip style as in editor — helps clinic owner see what will be substituted

**Scroll gate simulation:** Shows the same scroll progress bar as FE-IC-03, but non-functional (greyed) — helps clinic owner understand the signing UX

### Component 6: SaveMenu

**Type:** Split button (primary action + dropdown)

**Primary:** "Guardar borrador" — POST/PUT with `status=draft`
**Dropdown options:**
- "Guardar borrador" (same as primary)
- "Publicar plantilla" — POST/PUT with `status=active` → confirmation dialog if updating active template with existing consents using it
- "Archivar plantilla" (edit mode only) — sets status=archived

**Auto-save:** Every 30 seconds if editor is dirty: silent PATCH, "Guardado automáticamente" label updates

---

## Form Fields

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| name | text | Yes | 3–200 chars, unique per tenant | "El nombre de la plantilla es requerido" / "Ya existe una plantilla con este nombre" | "Ej: CI Extracción Dental" |
| category | select | Yes | Valid category | "Selecciona una categoría" | — |
| body | rich text | Yes | Min 100 chars (word count check) | "El contenido es demasiado corto para un consentimiento" | — |

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Load template (edit) | `/api/v1/consent-templates/{id}` | GET | `specs/consents/IC-02` | 5min |
| Create template | `/api/v1/consent-templates` | POST | `specs/consents/IC-02` | none |
| Update template | `/api/v1/consent-templates/{id}` | PUT | `specs/consents/IC-02` | none |
| Auto-save (draft) | `/api/v1/consent-templates/{id}` | PATCH | `specs/consents/IC-02` | none |
| Archive template | `/api/v1/consent-templates/{id}` | PATCH body: `{status: 'archived'}` | `specs/consents/IC-02` | none |

### State Management

**Local State (useState):**
- `mode: 'edit' | 'preview'`
- `isDirty: boolean`
- `lastSavedAt: Date | null`
- `isAutoSaving: boolean`
- `isSubmitting: boolean`

**Global State (Zustand):**
- `authStore.user.role` — role gate (clinic_owner only)

**Server State (TanStack Query):**
- Query key: `['consent-template', templateId, tenantId]` — staleTime 5min
- Mutation: `useCreateTemplate()` — POST
- Mutation: `useUpdateTemplate(id)` — PUT/PATCH
- Auto-save: `useMutation` with 30s debounce on editor change

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Type in editor | Keyboard input | Editor updates, isDirty=true | Auto-save triggers after 30s |
| Click variable button | Button click | Placeholder inserted at cursor | Chip appears in editor |
| Switch to Preview | Tab click | Preview renders with sample data | Content crossfades |
| Switch back to Edit | Tab click | Editor re-renders with original content | Content crossfades |
| Click "Validar variables" | Button | Unknown vars highlighted red | Inline highlights in editor |
| Click "Guardar borrador" | Button click | PATCH with draft status | Spinner → "Guardado" label |
| Click "Publicar" | Dropdown select | PUT with active status + dialog if in use | Confirm dialog → success toast |
| Cancel | Link click | Discard dialog if dirty | Dialog |
| Auto-save trigger | 30s after last edit | PATCH draft silently | "Guardado automáticamente hh:mm" label |

### Animations/Transitions

- Edit/Preview tab switch: content crossfade 150ms
- Variable chip insertion: chip fades-in at cursor position
- Save button loading: spinner
- Auto-save label: "Guardando..." → "Guardado automáticamente 10:32" (updates timestamp)

---

## Loading & Error States

### Loading State
- Editor area: `animate-pulse bg-gray-100 rounded-xl h-[500px]`
- Metadata bar: 2 skeleton inputs

### Error State
- Load failure: "Error al cargar la plantilla. Intenta de nuevo."
- Save failure 422 (duplicate name): inline error below name field "Ya existe una plantilla con este nombre"
- Save failure 500: toast "Error al guardar. Intenta de nuevo." — content preserved in editor
- Auto-save failure: "Guardado automático falló" label in `text-amber-600` — user can manually save

### Empty State
Not applicable — editor starts with empty content or loaded template.

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Variable toolbar scrollable horizontally. Editor full width. Save button full width. Preview mode hides toolbar. |
| Tablet (640-1024px) | All components visible. Editor height adapts. Variable buttons wrap if needed. Primary for clinic_owner use. |
| Desktop (> 1024px) | Full layout as designed. Editor min-height 600px. Variable toolbar fits in single row. |

**Tablet priority:** Medium — template creation is primarily a setup task done on desktop, but accessible on tablets.

---

## Accessibility

- **Focus order:** Name input → category → edit/preview tabs → variable buttons → editor area → save button
- **Screen reader:** Editor `role="textbox"` `aria-multiline="true"` `aria-label="Contenido del consentimiento"`. Variable buttons `aria-label="Insertar variable: {variable name}"`. Preview container `role="document"` `aria-label="Vista previa del consentimiento"`. Status badge `aria-live="polite"` for auto-save updates.
- **Keyboard navigation:** Tab to each variable button, Enter/Space to insert. Standard editor keyboard shortcuts (Cmd+B bold, Cmd+I italic, Cmd+Z undo). Tab into editor, arrow keys to navigate content.
- **Color contrast:** WCAG AA. Variable chips `bg-yellow-100 text-yellow-800` — ratio 4.8:1 (passes AA).
- **Language:** All toolbar labels, placeholders, buttons in es-419.

---

## Design Tokens

**Colors:**
- Editor background: `bg-white`
- Editor border: `border border-gray-200`
- Toolbar background: `bg-gray-50 border-b border-gray-200`
- Variable chip (in editor): `bg-yellow-100 text-yellow-800`
- Unknown variable (validation error): `bg-red-100 text-red-700`
- Auto-save label (normal): `text-gray-400`
- Auto-save label (error): `text-amber-600`
- Preview mode background: `bg-gray-50`

**Typography:**
- Editor content: `font-inter text-sm leading-relaxed text-gray-800`
- Template name input: `text-lg font-semibold text-gray-900`
- Toolbar labels: `text-xs font-medium`
- Word count: `text-xs text-gray-400`
- Variable chip: `text-xs font-mono`

**Spacing:**
- Editor padding: `p-6`
- Toolbar padding: `px-4 py-2`
- Variable button gap: `gap-2`
- Page padding: `px-4 py-6 md:px-6 lg:px-8`

**Border Radius:**
- Editor container: `rounded-xl`
- Variable chips: `rounded`
- Variable buttons: `rounded`
- Toolbar: `rounded-t-xl` (top edge if combined with editor)

---

## Implementation Notes

**Dependencies (npm):**
- `@tiptap/react` `@tiptap/starter-kit` `@tiptap/extension-text-align` `@tiptap/extension-underline` — rich text editor
- Custom TipTap extension: `VariablePlaceholder` node for non-editable inline chips
- `@tanstack/react-query` — data fetching + mutations
- `lucide-react` — User, CreditCard, Calendar, Wrench, Stethoscope, Save, Eye, Pencil
- `date-fns` — relative time formatting for auto-save label

**File Location:**
- Page: `src/app/(dashboard)/settings/consentimientos/plantillas/[id]/page.tsx`
- Components: `src/components/consents/ConsentTemplateEditor.tsx`, `src/components/consents/VariableToolbar.tsx`, `src/components/consents/ConsentPreview.tsx`
- TipTap extension: `src/lib/editor/VariablePlaceholder.ts`
- Hook: `src/hooks/useConsentTemplate.ts`

**Hooks Used:**
- `useAuth()` — role gate
- `useQuery(['consent-template', id])` — load existing template
- `useCreateTemplate()` — POST mutation
- `useUpdateTemplate(id)` — PUT/PATCH mutation
- `useAutoSave(editorContent, templateId)` — custom hook with 30s debounce

**TipTap VariablePlaceholder extension:**
```typescript
import { Node, mergeAttributes } from '@tiptap/core';
export const VariablePlaceholder = Node.create({
  name: 'variablePlaceholder',
  inline: true, group: 'inline', atom: true,
  addAttributes() { return { variable: { default: null } }; },
  renderHTML({ node }) {
    return ['span', mergeAttributes({ class: 'variable-chip', contenteditable: 'false' }), `{{${node.attrs.variable}}}`];
  },
  parseHTML() { return [{ tag: 'span[data-variable]' }]; },
});
```

---

## Test Cases

### Happy Path
1. Clinic owner creates new template and publishes
   - **Given:** No templates exist, clinic_owner logged in
   - **When:** Enter name "CI Blanqueamiento Dental" → select category "Estética" → type full consent text → insert `{{patient_name}}` via toolbar → switch to Preview → back to Edit → click "Publicar plantilla"
   - **Then:** POST creates template with `status=active`, toast "Plantilla publicada", redirected to template list

2. Auto-save during editing
   - **Given:** Editing existing template, 30 seconds pass after last keystroke
   - **When:** Auto-save triggers
   - **Then:** PATCH fires silently, "Guardado automáticamente 10:32" label updates

### Edge Cases
1. Publishing template that existing consents reference
   - **Given:** Template has 5 signed consents using it
   - **When:** Edit template → change text → Publicar
   - **Then:** Confirmation dialog "Hay 5 consentimientos firmados que usan esta plantilla. Los cambios solo afectarán consentimientos nuevos. ¿Continuar?" with Continuar/Cancelar

2. Unknown variable validation
   - **Given:** Editor contains `{{paciente_nombre}}` (typo — unrecognized)
   - **When:** Click "Validar variables"
   - **Then:** Chip highlighted red, tooltip "Variable desconocida — usa: patient_name", publish button disabled

### Error Cases
1. Duplicate template name
   - **Given:** Template "CI Extracción" already exists
   - **When:** New template named "CI Extracción" → save
   - **Then:** 422 response, inline error "Ya existe una plantilla con este nombre"

---

## Acceptance Criteria

- [ ] Accessible only by clinic_owner role
- [ ] Template name input (required, unique validation)
- [ ] Category select with predefined options
- [ ] Rich text editor with: bold, italic, underline, headings, lists, alignment, horizontal rule, undo/redo
- [ ] Variable insertion toolbar (5 variables)
- [ ] Variable chips rendered as non-editable inline elements in editor
- [ ] "Validar variables" highlights unknown variables
- [ ] Edit/Preview mode toggle
- [ ] Preview substitutes sample data and highlights variables
- [ ] Preview shows scroll gate simulation
- [ ] Auto-save every 30 seconds (silent PATCH)
- [ ] Auto-save label with relative time
- [ ] "Guardar borrador" explicit save
- [ ] "Publicar plantilla" with confirmation if template in use
- [ ] "Archivar plantilla" option in edit mode
- [ ] Dirty state detection → discard dialog on Cancel
- [ ] Word count label
- [ ] Loading skeleton for existing template
- [ ] Error handling for save failures
- [ ] Duplicate name 422 error inline
- [ ] Responsive: horizontal scroll on variable toolbar mobile
- [ ] Touch targets 44px on all toolbar buttons
- [ ] Keyboard: Cmd+B/I/U, Cmd+Z, Tab navigation
- [ ] ARIA: editor textbox role, variable button labels
- [ ] All labels in es-419

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
