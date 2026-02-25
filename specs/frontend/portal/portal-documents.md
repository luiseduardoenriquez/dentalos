# Mis Documentos — Portal del Paciente (Portal Documents) — Frontend Spec

## Overview

**Screen:** Document library in patient portal. Grid/list view of all patient documents: X-rays (with thumbnail preview), signed consent forms, prescriptions, treatment plan PDFs. Filter by document type. Download button per document.

**Route:** `/portal/[clinicSlug]/documents`

**Priority:** Medium

**Backend Specs:** `specs/portal/PP-07.md`

**Dependencies:** `specs/frontend/portal/portal-dashboard.md`

---

## User Flow

**Entry Points:**
- "Documentos" in portal navigation
- "Documentos por firmar" card on dashboard (filtered to pending consents)

**Exit Points:**
- Download button → browser download
- "← Inicio" → dashboard

**User Story:**
> As a patient, I want to access my dental records, X-rays, and consent forms from my phone so that I can share them with other doctors or keep personal records.

**Roles with access:** patient (portal session)

---

## Layout Structure

```
+------------------------------------------+
|  [Navbar]                                 |
+------------------------------------------+
|  ← Inicio     Mis Documentos             |
|                                           |
|  Filtros: [Todos] [Rx] [Consentimientos]  |
|           [Recetas] [Planes]              |
|                                           |
|  ○ Cuadrícula   ○ Lista                  |
|                                           |
|  CUADRÍCULA:                              |
|  +----------+ +----------+ +----------+  |
|  | [Rx img] | | [PDF]    | | [PDF]    |  |
|  | Rx 14/Feb| | Consent. | | Plan Trat|  |
|  | [↓]      | | [↓]      | | [↓]      |  |
|  +----------+ +----------+ +----------+  |
|                                           |
|  LISTA:                                   |
|  [icon] Rx panorámica       14 Feb  [↓]  |
|  [icon] Consentimiento ext. 10 Feb  [↓]  |
+------------------------------------------+
```

**Sections:**
1. Page header — back link, title "Mis Documentos"
2. Filter tabs — document type filter (pills)
3. View toggle — grid / list toggle
4. Document grid or list — documents with thumbnails (grid) or icons (list)

---

## UI Components

### Component 1: DocumentTypeFilter

**Type:** Pill filter tabs (horizontal scroll on mobile)

**Options:**

| Value | Label | Icon |
|-------|-------|------|
| all | Todos | — |
| xray | Radiografías | Camera |
| consent | Consentimientos | FileSignature |
| prescription | Recetas | Pill |
| treatment_plan | Planes de tratamiento | ClipboardList |
| other | Otros | File |

### Component 2: ViewToggle

**Type:** Icon toggle (grid / list)

**Default:** Grid on tablet/desktop, List on mobile (auto based on breakpoint)

### Component 3: DocumentGridItem

**Type:** Card (grid layout, ~3 columns on mobile, 4 on desktop)

**Content:**
- Thumbnail: X-ray image (actual image if available), PDF icon, consent form icon (based on type)
- Document name (2 lines max, truncate)
- Date (dd MMM yyyy)
- Download button (bottom of card)

**Tap behavior:** Opens document preview (X-ray → full-screen image viewer, PDF → browser PDF viewer or native)

### Component 4: DocumentListItem

**Type:** Horizontal list row

**Content:**
- Type icon (left, 24px)
- Document name (flex-1)
- Date (dd MMM)
- Download icon button (right)

### Component 5: DocumentPreviewModal

**Type:** Modal (full-screen on mobile)

**Trigger:** Tap on grid item

**Content:**
- Header: document name + close button + download button
- Body:
  - Image type: `<img>` (zoomable with pinch/scroll)
  - PDF type: `<iframe>` or link to open in new tab

---

## Form Fields

Not applicable — document library is browsable, no forms.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| List documents | `/api/v1/portal/documents` | GET | `specs/portal/PP-07.md` | 5min |
| Download document | `/api/v1/portal/documents/{id}/download` | GET | `specs/portal/PP-07.md` | — |

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `type` | string | Filter by document type |
| `page` | number | Page number |
| `per_page` | number | Default 20 |

### State Management

**Local State (useState):**
- `activeFilter: DocumentType | 'all'`
- `viewMode: 'grid' | 'list'`
- `previewDocument: Document | null`

**Server State (TanStack Query):**
- Query key: `['portal-documents', patientId, activeFilter, page]` — stale 5min
- Download: direct fetch (not cached), triggers file download

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click filter pill | Tap | Filter applied, documents refresh | Active pill highlighted |
| Toggle view | Click grid/list icon | Layout changes | View icon updates |
| Tap document (grid) | Tap | Preview modal opens | Full-screen modal |
| Tap download | Tap download icon | Fetch blob, trigger download | Download icon spinner |
| Close preview | Tap "×" or backdrop | Modal closes | Standard close |

### Animations/Transitions

- Filter change: crossfade (150ms)
- Grid items: stagger fade in on load (100ms each)
- Preview modal: fade + scale in (200ms)

---

## Loading & Error States

### Loading State
- Grid: skeleton cards (gray rectangle thumbnails + text lines)
- List: skeleton list items

### Error State
- Load failure: "Error al cargar tus documentos. Intenta de nuevo."
- Download failure: toast "No se pudo descargar el documento."

### Empty State
- No documents (all): illustration + "Aún no tienes documentos. Tu doctor los añadirá después de tu cita."
- No documents for type filter: "Sin documentos de este tipo."

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Grid: 2 columns. List: compact. View toggle defaults to list. Filter pills horizontal scroll. Preview: full-screen modal (no border radius). |
| Tablet (640-1024px) | Grid: 3-4 columns. View toggle visible. |
| Desktop (> 1024px) | Grid: 4-5 columns. |

---

## Accessibility

- **Focus order:** Filter pills → view toggle → document items → pagination
- **Screen reader:** Each document card: `aria-label="{type}: {name}, fecha {date}"`. Download button: `aria-label="Descargar {name}"`. Preview modal: `role="dialog"` with `aria-label`.
- **Keyboard navigation:** Tab through filter pills (arrow keys within pill group). Tab through document items. Enter to open preview. Escape to close.
- **Language:** Document type names in patient-friendly Spanish. es-419.

---

## Design Tokens

**Colors:**
- Active filter pill: `bg-primary-50 text-primary-700 border-primary-200`
- Xray thumbnail bg: `bg-gray-900` (radiology dark)
- PDF icon: `text-red-500` (PDF red)
- Consent icon: `text-green-500`
- Prescription icon: `text-blue-500`
- Download button: `text-primary-600 hover:text-primary-800`

**Spacing:**
- Grid gap: `gap-3`
- List item: `py-3`
- Card padding: `p-3`

---

## Implementation Notes

**File Location:**
- Page: `src/app/(portal)/[clinicSlug]/documents/page.tsx`
- Components: `src/components/portal/DocumentGrid.tsx`, `src/components/portal/DocumentListView.tsx`, `src/components/portal/DocumentPreviewModal.tsx`
- Hooks: `src/hooks/usePortalDocuments.ts`

---

## Test Cases

### Happy Path
1. View X-ray in grid
   - **Given:** Patient has 2 X-rays
   - **When:** Taps "Radiografías" filter
   - **Then:** 2 X-ray thumbnails shown in grid

2. Download consent PDF
   - **Given:** Signed consent document exists
   - **When:** Taps download icon
   - **Then:** PDF downloads to device

### Edge Cases
1. Large X-ray image
   - **Given:** X-ray is 5MB JPEG
   - **When:** Tap opens preview
   - **Then:** Pinch-to-zoom works on mobile. Low-res thumbnail shown until full image loads.

---

## Acceptance Criteria

- [ ] Document list with type filter (todos, rx, consentimientos, recetas, planes, otros)
- [ ] Grid and list view toggle
- [ ] Thumbnail preview for images (X-rays), PDF icon for documents
- [ ] Document preview modal (image viewer / PDF view)
- [ ] Download button per document
- [ ] Empty state per filter type
- [ ] Loading skeletons
- [ ] Responsive: 2-col grid mobile, 4-col desktop
- [ ] Accessibility: ARIA labels, keyboard navigation
- [ ] Non-clinical language, es-419

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
