# Panel de Detalle de Diente — Frontend Spec

## Overview

**Screen:** Tooth detail panel or modal showing all zones and conditions for a single tooth, full change history for that tooth, linked treatments, attached photos, and X-rays. Includes quick actions: add condition, attach photo, add to treatment plan, and record voice note.

**Route:** Accessed as:
- Right panel update in classic grid (FE-OD-01) when tooth selected
- Modal overlay in anatomic arch (FE-OD-02) — primary usage
- Standalone deep-link: `/patients/{id}/odontogram/tooth/{fdi}` (for direct access)

**Priority:** Medium

**Backend Specs:**
- `specs/odontogram/OD-10` — Get tooth detail (zones + history + linked treatments)
- `specs/odontogram/OD-02` — Update zone condition
- `specs/odontogram/P-16` — Attach photo to tooth
- `specs/odontogram/V-01` — Voice note (if voice add-on enabled)

**Dependencies:**
- `specs/frontend/odontogram/condition-panel.md` (FE-OD-03) — embedded for adding conditions
- `specs/frontend/odontogram/history-panel.md` (FE-OD-04) — filtered to this tooth
- `specs/frontend/odontogram/anatomic-arch.md` (FE-OD-02) — parent in anatomic mode

---

## User Flow

**Entry Points:**
- Click any tooth in classic grid (FE-OD-01) — updates right panel
- Click any tooth in anatomic arch (FE-OD-02) — opens as modal
- "Ver detalle completo" link from HistoryPanel entry (FE-OD-04)
- Direct URL `/patients/{id}/odontogram/tooth/{fdi}` (shared link or from treatment plan)

**Exit Points:**
- Close modal (anatomic mode) → returns to arch view
- Navigate to treatment plan from "Agregar a plan" quick action
- Navigate to patient photos from photo attachment preview
- Navigate back via browser (deep-link mode)

**User Story:**
> As a doctor, I want to see all clinical information about a specific tooth — its current conditions, history, linked treatments, and attached images — so that I can make informed decisions without switching between multiple screens.

**Roles with access:** clinic_owner, doctor, assistant (read + write); receptionist (read-only)

---

## Layout Structure

```
+----------------------------------------------------+
|  [X close]  Diente 36 — Primer molar inferior izq. |
|             FDI #36                                |
+----------------------------------------------------+
|  [ToothZoneDiagram — 6 zones with conditions]      |
|                                                    |
|  Condiciones actuales:                             |
|  [ZoneChip: O: Caries] [ZoneChip: M: Obturado]    |
+----------------------------------------------------+
|  Acciones rapidas:                                 |
|  [+ Condicion] [Adjuntar foto] [+ Tratamiento]     |
|  [Nota de voz] (if voice add-on)                   |
+----------------------------------------------------+
|  Historial de este diente (tab):                   |
|  [HistoryPanel filtered to tooth 36 — FE-OD-04]   |
+----------------------------------------------------+
|  Tratamientos vinculados (tab):                    |
|  [LinkedTreatmentList]                             |
+----------------------------------------------------+
|  Fotos y radiografias (tab):                       |
|  [ImageGallery]                                    |
+----------------------------------------------------+
```

**Sections:**
1. Header — tooth FDI number, anatomical name, close button
2. Zone diagram — 6-zone visual with current conditions colored
3. Zone chips — active conditions as colored pill badges
4. Quick actions row — primary clinical actions
5. Tabbed content — Historial, Tratamientos, Fotos (3 tabs)

---

## UI Components

### Component 1: ToothZoneDiagram

**Type:** Interactive or read-display SVG/div zone diagram (6 zones)

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| toothId | number | — | FDI tooth number |
| zones | ZoneConditions | — | Map of zone → condition with color |
| selectedZone | ToothZone \| null | null | Highlighted zone |
| onZoneClick | (zone: ToothZone) => void | — | Zone selection handler |
| readOnly | boolean | false | Receptionist mode |
| showRoot | boolean | true | Show root zone (always true in tooth detail) |

**Zone layout:**
```
         [V — Vestibular]
 [M]  [O — Oclusal/Incisal]  [D]
         [L — Lingual/P]
         [R — Raiz/Root]
```

**Zone names in Spanish:**
- O: Oclusal (for posteriors) / Incisal (for anteriors)
- M: Mesial
- D: Distal
- V: Vestibular
- L: Lingual (anteriors) / Palatino (upper posteriors)
- R: Raiz (root — additional zone not in classic 5-zone view)

**States:**
- Zone with condition: filled with condition color
- Zone selected: `ring-2 ring-blue-500 ring-offset-2`
- Zone hovered (interactive): `ring-1 ring-blue-300`
- Zone healthy: `bg-gray-100`
- Zone root: displayed below other zones; slightly different shape
- Read-only: no hover/click interaction

---

### Component 2: QuickActions

**Type:** Action button row

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| toothId | number | — | FDI tooth number |
| hasVoiceAddon | boolean | false | Show voice note button |
| readOnly | boolean | false | Hide write actions |
| onAddCondition | () => void | — | Opens ConditionPanel (FE-OD-03) |
| onAttachPhoto | () => void | — | Opens photo upload modal |
| onAddToTreatment | () => void | — | Opens treatment plan selector |
| onRecordVoice | () => void | — | Opens voice note recorder (FE-V-01) |

**Action buttons:**
1. "+ Condicion" — `variant="outline"`, opens inline ConditionPanel below zone diagram
2. "Adjuntar foto" — opens file picker (accepts image/jpeg, image/png, image/webp, max 10MB)
3. "+ Tratamiento" — opens TreatmentPlanSelector modal
4. "Nota de voz" — only shown if `hasVoiceAddon = true`; links to FE-V-01

**States:**
- Default: all buttons enabled
- Loading (after action): spinner on triggered button
- Read-only: buttons hidden (receptionist role)

---

### Component 3: LinkedTreatmentList

**Type:** List of linked treatment plan items

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| treatments | LinkedTreatment[] | [] | Treatment items linked to this tooth |
| patientId | string | — | Patient UUID for navigation |

**Each treatment item:**
```
[Status badge] Endodoncia        [15 ene 2026]
               Plan: Plan anual  Estado: Aprobado
```
- Status badge: colored (pendiente=gray, aprobado=blue, en-progreso=amber, completado=green)
- Click row: navigate to treatment plan detail page
- "Sin tratamientos vinculados" empty state

---

### Component 4: ImageGallery (Fotos y Radiografias)

**Type:** Thumbnail grid with lightbox

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| images | ToothImage[] | [] | Photos and X-rays attached to tooth |
| onUpload | (file: File) => void | — | Upload handler |
| readOnly | boolean | false | Hide upload button |

**Layout:**
- 3-column thumbnail grid
- Each thumbnail: image preview + badge (FOTO / RX)
- Click: opens lightbox with full-size image + metadata (date, uploaded by)
- Upload button: "+ Agregar foto" (doctor/assistant only)

---

## Form Fields

| Field | Type | Required | Validation | Error Message (es-419) | Notes |
|-------|------|----------|------------|------------------------|-------|
| Photo file | file | Yes (if attaching) | image/jpeg, image/png, image/webp, max 10MB | "El archivo debe ser una imagen (JPEG, PNG o WebP) de hasta 10MB." | Drag-and-drop or file picker |

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Get tooth detail | `/api/v1/patients/{id}/odontogram/tooth/{fdi}` | GET | `specs/odontogram/OD-10` | 1min stale |
| Update zone condition | `/api/v1/patients/{id}/odontogram` | PATCH | `specs/odontogram/OD-02` | Invalidate |
| Attach photo | `/api/v1/patients/{id}/photos` | POST (multipart) | `specs/odontogram/P-16` | Invalidate images |
| Get treatment links | included in OD-10 response | — | `specs/odontogram/OD-10` | 1min stale |
| Voice note | `/api/v1/patients/{id}/voice-notes` | POST | `specs/odontogram/V-01` | None |

### State Management

**Local State (useState):**
- `activeTab: 'historial' | 'tratamientos' | 'fotos'` — active tab
- `isUploadingPhoto: boolean` — photo upload in progress
- `lightboxImage: ToothImage | null` — open image in lightbox

**Global State (Zustand — useOdontogramStore):**
- `selectedConditionId: string | null` — read from condition panel
- `odontogramData` — updated on PATCH success

**Server State (TanStack Query):**
- Query key: `['tooth-detail', patientId, toothId]`
- Stale time: 1 minute
- Mutation: `useMutation()` for PATCH (condition), POST (photo upload)

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click zone in diagram | Click zone | Zone selected; ConditionPanel expands if hidden | Zone ring highlight |
| Click "+ Condicion" | Quick action button | ConditionPanel slides down below zone diagram | Smooth expand |
| Select condition + Registrar | Via ConditionPanel | PATCH API; zone updates | Zone repaints; toast "Guardado" |
| Click "Adjuntar foto" | Quick action | File picker opens | System dialog |
| Select file | File picker | Upload POST; thumbnail added to gallery | Spinner on button; thumbnail added |
| Click "+ Tratamiento" | Quick action | TreatmentPlanSelector modal opens | Modal overlay |
| Click "Nota de voz" | Quick action (if add-on) | Navigates to voice recorder (FE-V-01) | Navigation |
| Switch tab | Click tab | Tab content loads | Tab underline transition |
| Click image thumbnail | Click | Lightbox opens with full image | Backdrop overlay, image centered |

### Animations/Transitions

- ConditionPanel expand: `motion.div` height animation 200ms ease-out (slides down)
- Tab switch: content fade 150ms
- Lightbox open: backdrop fade 150ms + image scale `0.9 → 1.0` 200ms
- Photo thumbnail added: fade-in slide from right 150ms

---

## Loading & Error States

### Loading State
- Tooth detail fetch: skeleton layout matching all sections — zone diagram skeleton (gray boxes), zone chips skeleton (2 gray pills), tabs skeleton (3 gray tab labels), content skeleton (3 lines)
- Photo upload: spinner on "Adjuntar foto" button; thumbnail slot shows `animate-pulse` gray square

### Error State
- Tooth detail fails: full panel error state
  - Message: "No se pudo cargar el detalle del diente. Intenta de nuevo."
  - Button: "Reintentar"
- Photo upload fails: toast error
  - Message: "No se pudo subir la foto. Verifica el formato y tamano."
- Condition save fails: toast error (same as FE-OD-01/02)

### Empty State
- No conditions (all zones healthy): zone diagram all `bg-gray-100`; chips area shows "Sin condiciones registradas en este diente"
- No linked treatments (Tratamientos tab): illustration + "Sin tratamientos vinculados a este diente." CTA: "+ Agregar a plan de tratamiento"
- No photos (Fotos tab): illustration + "Sin fotos ni radiografias adjuntas." CTA: "+ Agregar foto" (doctor/assistant only)

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Not primary. If accessed via deep-link, renders as full-page view with stacked sections (no tabs — all sections visible with scroll). |
| Tablet (640-1024px) | PRIMARY USE CASE. Modal is full-screen (anatomic mode) or fills right panel (classic mode). Zone diagram: 80% width centered. Quick actions as 2×2 grid. Tabs rendered. Touch-friendly tab targets (44px height). |
| Desktop (> 1024px) | Modal: 640px centered. Right panel: 320px in classic mode. Zone diagram: 200px × 200px. Quick actions as row. |

**Tablet priority:** High — all zone elements minimum 44×44px. Tab bar buttons minimum 44px height. "Adjuntar foto" file upload supports camera capture on tablet (`<input accept="image/*" capture="environment">`).

---

## Accessibility

- **Focus order:** Close button → Tooth name heading → Zone diagram (tab through zones: O, M, D, V, L, R) → Zone chips → Quick action buttons → Tabs (Historial, Tratamientos, Fotos) → Active tab content
- **Screen reader:** Panel/modal has `role="dialog"` with `aria-labelledby` pointing to tooth name heading. Zone diagram is a `role="group"` with `aria-label="Zonas del diente {FDI}"`. Each zone button: `aria-label="{zone_name}: {condition_name}" aria-pressed={isSelected}`. Lightbox: `role="dialog"` with `aria-label="Imagen adjunta — {date}"`.
- **Keyboard navigation:** Escape closes modal. Tab navigates zones and actions. Arrow keys navigate between tabs. Enter/Space selects zone or activates action. In lightbox: Escape closes, Arrow keys navigate images.
- **Color contrast:** Zone condition colors supplemented by Spanish zone label text. All condition names readable as text (not solely color). Tab labels WCAG AA contrast.
- **Language:** All in es-419. Tooth anatomical name in Spanish. Zone names: "Oclusal", "Mesial", "Distal", "Vestibular", "Lingual/Palatino", "Raiz". Tab labels: "Historial", "Tratamientos", "Fotos y Radiografias". Quick action buttons in Spanish.

---

## Design Tokens

**Colors:**
- Modal/panel background: `bg-white dark:bg-gray-900`
- Header background: `bg-gray-50 dark:bg-gray-800 border-b border-gray-200`
- Zone diagram background: `bg-gray-50 dark:bg-gray-800`
- Zone healthy: `bg-gray-200 dark:bg-gray-700`
- Quick action buttons: `variant="outline"` — `border-gray-300 text-gray-700`
- Tab active: `border-b-2 border-blue-600 text-blue-600`
- Tab inactive: `text-gray-500 hover:text-gray-700`

**Typography:**
- Tooth name: `text-lg font-semibold text-gray-900 dark:text-white`
- FDI label: `text-sm font-mono text-gray-500`
- Zone label (inside diagram): `text-xs text-gray-600`
- Zone chip text: `text-xs font-medium`
- Section label: `text-sm font-medium text-gray-700`

**Spacing:**
- Modal padding: `p-5`
- Zone diagram: `min-h-[160px]` centered
- Quick actions gap: `gap-2`
- Tab content padding: `pt-4`

**Border Radius:**
- Modal: `rounded-2xl`
- Zone chip: `rounded-full`
- Quick action buttons: `rounded-lg`
- Image thumbnails: `rounded-lg`

---

## Implementation Notes

**Dependencies (npm):**
- `@tanstack/react-query` — tooth detail query + mutations
- `zustand` — reads condition from `useOdontogramStore`
- `lucide-react` — X, Plus, Camera, Mic, FileText, ZoomIn icons
- `framer-motion` — ConditionPanel expand, lightbox animation

**File Location:**
- Component: `src/components/odontogram/ToothDetail.tsx`
- Sub-components:
  - `src/components/odontogram/ToothZoneDiagram.tsx`
  - `src/components/odontogram/QuickActions.tsx`
  - `src/components/odontogram/LinkedTreatmentList.tsx`
  - `src/components/odontogram/ImageGallery.tsx`
- Page (deep-link): `src/app/(dashboard)/patients/[id]/odontogram/tooth/[fdi]/page.tsx`
- API: `src/lib/api/odontogram.ts`

**Hooks Used:**
- `useQuery(['tooth-detail', patientId, toothId])` — tooth detail + linked data
- `useMutation()` — PATCH condition, POST photo
- `useOdontogramStore()` — read selectedConditionId
- `useTenantAddons()` — check voice add-on enabled
- `useAuth()` — role check for read-only mode

**Camera capture on tablet:**
```typescript
<input
  type="file"
  accept="image/*"
  capture="environment"
  onChange={handlePhotoSelect}
  className="hidden"
  ref={fileInputRef}
/>
```

**Tone on "Nota de voz" click:**
- If `hasVoiceAddon = false`: button not rendered
- If `hasVoiceAddon = true`: opens voice recorder (FE-V-01) pre-scoped to this `tooth_id`

---

## Test Cases

### Happy Path
1. Doctor opens tooth detail for tooth with multiple conditions
   - **Given:** Tooth 36 has Caries (zone O) and Obturado (zone M)
   - **When:** Click tooth 36 in odontogram
   - **Then:** Detail panel opens; zone diagram shows O=red, M=blue; chips show "O: Caries" and "M: Obturado"

2. Doctor adds condition via quick action
   - **Given:** Tooth detail open, tooth 11 zone D is healthy
   - **When:** Click "+ Condicion" → ConditionPanel expands → select "Fractura" → click "Registrar"
   - **Then:** PATCH fires; zone D paints purple in diagram; chip "D: Fractura" added; history tab updates

3. Doctor attaches photo
   - **Given:** Tooth detail open, Fotos tab active
   - **When:** Click "Adjuntar foto" → select image file (JPEG, 3MB)
   - **Then:** Upload POST fires; thumbnail appears in gallery; "Adjuntar foto" spinner then restores

4. Switch tabs
   - **Given:** Tooth detail open on Historial tab
   - **When:** Click "Tratamientos" tab
   - **Then:** Tratamientos content loads; LinkedTreatmentList shows linked plans

5. Receptionist sees read-only view
   - **Given:** Logged in as receptionist
   - **When:** Tooth detail opened
   - **Then:** Zone diagram non-interactive; Quick action buttons hidden; tabs visible and readable

### Edge Cases
1. Tooth with no conditions and no history
   - **Given:** Healthy tooth, never edited
   - **When:** Open tooth detail
   - **Then:** All zones show `bg-gray-100`; "Sin condiciones registradas"; Historial tab empty state; Tratamientos empty; Fotos empty

2. Photo upload with oversized file
   - **Given:** File selected is 25MB JPEG
   - **When:** File picker completes selection
   - **Then:** Client-side validation blocks upload; toast "El archivo debe ser una imagen de hasta 10MB."; no API call

3. Deep-link to tooth on mobile
   - **Given:** User accesses `/patients/{id}/odontogram/tooth/36` on mobile
   - **When:** Page loads
   - **Then:** Full-page layout, sections stacked (no tabs), all content accessible

### Error Cases
1. Tooth detail API fails
   - **Given:** OD-10 returns 503
   - **When:** Tooth detail opens
   - **Then:** Full error state in panel; "No se pudo cargar el detalle del diente. Reintentar."

2. Photo upload fails (server error)
   - **Given:** POST /photos returns 500
   - **When:** Doctor uploads photo
   - **Then:** Toast error "No se pudo subir la foto."; thumbnail not added; "Adjuntar foto" re-enabled

---

## Acceptance Criteria

- [ ] Tooth detail shows zone diagram with all 6 zones (O, M, D, V, L, R) and current conditions
- [ ] Zone chips list all active conditions as colored pills with condition names
- [ ] Zone diagram: click zone → zone selected ring + ConditionPanel expands below
- [ ] Quick action "+ Condicion": opens ConditionPanel inline, saves via PATCH on Registrar
- [ ] Quick action "Adjuntar foto": file picker opens; accepts JPEG, PNG, WebP up to 10MB; tablet uses camera capture
- [ ] Quick action "+ Tratamiento": opens treatment plan selector
- [ ] Quick action "Nota de voz": only visible with voice add-on; links to FE-V-01
- [ ] Three tabs: Historial, Tratamientos, Fotos y Radiografias — all load independently
- [ ] Historial tab shows HistoryPanel (FE-OD-04) filtered to this tooth
- [ ] Tratamientos tab shows linked treatment items with status badges
- [ ] Fotos tab shows image gallery with lightbox; upload button for doctor/assistant
- [ ] Empty states per section with appropriate messages
- [ ] Read-only mode: no editing for receptionist
- [ ] Loading skeleton for initial load
- [ ] Error state with retry
- [ ] Escape closes modal (anatomic mode); focus returns to tooth in arch
- [ ] All touch targets minimum 44px
- [ ] All labels in Spanish (es-419)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
