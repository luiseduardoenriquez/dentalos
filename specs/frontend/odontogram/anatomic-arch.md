# Odontograma Anatomico (Arco Dental) — Frontend Spec

## Overview

**Screen:** Anatomic arch odontogram for Plan Starter and above. Renders teeth in SVG dental arch shape following actual mouth anatomy. Upper arch in U-shape (maxillary), lower arch in inverted U-shape (mandibular). Clicking a tooth opens a detail modal with 6 zones (5 crown + root). Dark theme by default.

**Route:** `/patients/{id}/odontogram` (when `tenant.odontogram_mode = "anatomic"`)

**Priority:** High

**Backend Specs:**
- `specs/odontogram/OD-01` — Get odontogram
- `specs/odontogram/OD-02` — Update odontogram
- `specs/odontogram/OD-09` — Condition catalog

**Dependencies:**
- `specs/frontend/patients/patient-header.md` — patient banner
- `specs/frontend/odontogram/condition-panel.md` (FE-OD-03) — condition selector inside modal
- `specs/frontend/odontogram/history-panel.md` (FE-OD-04) — history sidebar
- `specs/frontend/odontogram/tooth-detail.md` (FE-OD-06) — detailed tooth modal
- `specs/frontend/odontogram/toolbar.md` (FE-OD-07) — top toolbar

---

## User Flow

**Entry Points:**
- From patient detail page (`/patients/{id}`) — "Odontograma" tab when plan >= Starter and mode = anatomic
- Redirect from classic grid when plan is upgraded and mode changed to anatomic

**Exit Points:**
- Navigate to another patient tab
- Close tooth detail modal (returns to arch view)
- Print view triggered from toolbar
- Navigate back to patient list

**User Story:**
> As a doctor with a Starter or Professional plan, I want to examine a patient's teeth on an anatomically accurate dental arch diagram so that conditions are visually intuitive and easier to communicate to the patient.

**Roles with access:** clinic_owner, doctor, assistant (read + write); receptionist (read-only)

---

## Layout Structure

```
+----------------------------------------------------------+
|  [Toolbar: FE-OD-07]                                     |
+----------------------------------------------------------+
|  [Patient Header Banner]                                  |
+----------------------------------------------+-----------+
|                                              |           |
|   -- paladar --                              | [History  |
|       SVG Upper Arch                         |  Panel    |
|   18 17 16 15 14 13 12 11 | 21 22 23 24..28  |  FE-OD-04 |
|                                              |  sidebar] |
|   48 47 46 45 44 43 42 41 | 31 32 33 34..38  |           |
|       SVG Lower Arch                         |           |
|   -- lengua --                               |           |
|                                              |           |
+----------------------------------------------+-----------+
|   [PatientSummary: % sano | hallazgos count ]            |
+----------------------------------------------------------+

[ToothDetailModal — overlay when tooth clicked]
+----------------------------------------------------------+
|  backdrop-filter: blur(8px)                              |
|  +----------------------------------------------------+  |
|  |  Diente #16 — Primer molar superior derecho        |  |
|  |  [6-zone diagram: 5 corona + root]                 |  |
|  |  [ConditionGrid: FE-OD-03]                         |  |
|  |  [ZoneChips: active conditions]                    |  |
|  |  [Notes] [Registrar] [Ver historial completo]      |  |
|  +----------------------------------------------------+  |
+----------------------------------------------------------+
```

**Sections:**
1. Toolbar (FE-OD-07) — controls including mode toggle
2. Patient header banner
3. SVG arch area — anatomic tooth placement, dark background
4. Anatomical reference labels — "paladar" (upper), "lengua" (lower)
5. History panel sidebar (FE-OD-04) — collapsible on tablet
6. Patient summary bar — % sano, hallazgos
7. Tooth detail modal — overlay when tooth clicked (FE-OD-06)

---

## UI Components

### Component 1: ToothArchSVG

**Type:** SVG Container

**Design System Ref:** `frontend/design-system/design-system.md` Section 6 (Clinical — Anatomic)

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| teeth | Tooth[] | [] | 32 tooth objects with zone conditions |
| arch | "upper" \| "lower" \| "both" | "both" | Which arches to render |
| selectedToothId | number \| null | null | Currently zoomed/selected tooth |
| onToothClick | (toothId: number) => void | — | Click handler for tooth selection |
| readOnly | boolean | false | Disables clicks (receptionist mode) |
| dentition | "adult" \| "pediatric" | "adult" | FDI or primary dentition |

**Tooth positioning (SVG):**
- Viewbox: `0 0 900 420`
- Upper arch: U-curve path. Teeth 18→11 right side, 21→28 left side
- Lower arch: Inverted U-curve path. Teeth 48→41 right side, 31→38 left side
- Each tooth placed along the arch curve at anatomically correct angle

**Tooth size by type (SVG height):**
| Tooth type | SVG height | SVG width |
|------------|-----------|-----------|
| Incisivo central | 18px | 12px |
| Incisivo lateral | 18px | 10px |
| Canino | 20px | 10px |
| Premolar | 24px | 12px |
| Molar | 28px | 16px |
| Molar del juicio (#18,#28,#38,#48) | 24px | 14px |

**States:**
- Default: dark background `bg-gray-950`, teeth `fill-gray-700 stroke-gray-500`
- Zone with condition: zone fill from condition catalog color
- Hovered: tooth scales to 1.25× with `transition-transform duration-200 ease-elastic`
- Selected: tooth has blue glow `drop-shadow(0 0 8px #3B82F6)`
- Loading: skeleton animation over arch area

**Behavior:**
- Hover: individual tooth animates scale ×1.25 with spring/elastic easing. Blue tooltip badge appears above showing FDI number and tooth name.
- Click: opens `ToothDetailModal` overlay. No inline zone painting in arch view — always goes through modal.
- FDI labels render below each tooth in the arch in small monospaced text.

---

### Component 2: ToothDetailModal

**Type:** Modal overlay

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.5 (Modals)

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| toothId | number | — | FDI tooth number |
| toothData | ToothState | — | Zones and conditions for this tooth |
| onClose | () => void | — | Modal close handler |
| onSave | (changes) => void | — | Save handler after Registrar click |
| readOnly | boolean | false | Hides edit controls |

**Zone layout (6 zones):**
```
         [V — Vestibular]
  [M]  [O — Oclusal/Incisal]  [D]
         [L — Lingual/P]
         [R — Root/Raiz]
```

**States:**
- Open: `fixed inset-0 z-50`, backdrop `backdrop-blur-md bg-black/60`
- Close: fades out 200ms
- Zone selected within modal: ring highlight
- Saving: "Registrar" button shows spinner, zones disabled
- Saved: toast, modal stays open for continued editing

**Behavior:**
- Clicking outside backdrop dismisses modal (Escape key also closes)
- Zone chips below diagram show active conditions for quick overview
- "Ver historial completo" button navigates to history panel (FE-OD-04) filtered by tooth

---

### Component 3: ZoneChips

**Type:** Badge/chip list

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| zones | ZoneCondition[] | [] | Array of zone + condition pairs for a tooth |
| onChipClick | (zone) => void | — | Navigate to that zone in diagram |

**Behavior:**
- Each chip: `[ZoneName]: [ConditionName]` with condition color dot
- Empty zones not shown
- "Sin hallazgos" shown when all zones are healthy

---

## Form Fields

Not applicable — conditions applied via zone click in modal + ConditionGrid (FE-OD-03). Notes textarea available in modal (free text, max 500 chars).

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Load odontogram | `/api/v1/patients/{id}/odontogram` | GET | `specs/odontogram/OD-01` | 2min stale |
| Save zone change | `/api/v1/patients/{id}/odontogram` | PATCH | `specs/odontogram/OD-02` | Invalidate on mutation |
| Load condition catalog | `/api/v1/odontogram/conditions` | GET | `specs/odontogram/OD-09` | 1 hour stale |

### State Management

**Local State (useState):**
- `selectedToothId: number | null` — FDI of tooth whose modal is open
- `modalOpen: boolean` — whether detail modal is visible
- `hoveredToothId: number | null` — tooltip display

**Global State (Zustand — useOdontogramStore):**
- `odontogramData: OdontogramState` — full 32-tooth zone condition map
- `conditionCatalog: Condition[]` — shared with classic view
- `selectedConditionId: string | null` — active condition within modal
- `changeLog: ChangeEntry[]` — session change log
- `isSaving: boolean` — save in progress

**Server State (TanStack Query):**
- Query key: `['odontogram', patientId, tenantId]`
- Stale time: 2 minutes
- Mutation: `useMutation()` for PATCH with optimistic update
  - Optimistic: update `odontogramData` in store immediately; revert on error

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Hover tooth | Mouse enter / touch press | Scale ×1.25 elastic animation; FDI badge tooltip | Smooth spring scale |
| Click tooth | Click / tap | Opens `ToothDetailModal` | Backdrop blur overlay slides in |
| Click zone in modal | Click zone in 6-zone diagram | Zone selected; `ConditionGrid` in modal updates | Ring highlight on zone |
| Select condition | Click in ConditionGrid (FE-OD-03) | Condition staged for zone | Condition highlighted |
| Click "Registrar" | Click in modal | PATCH API; zone color updates in arch | Arch tooth updates; toast "Guardado" |
| Close modal | Click backdrop or Escape | Modal dismisses | Fade out 200ms |
| Keyboard shortcut 1-9 | Key press when modal open | Select condition | ConditionGrid updates |

### Animations/Transitions

- Tooth hover scale: `transform scale-125 transition-all duration-200 ease-[cubic-bezier(0.34,1.56,0.64,1)]` (elastic/spring curve)
- Tooth hover tooltip badge: `opacity-0 → opacity-100` 100ms, slides up 4px
- Modal open: backdrop `opacity-0 → opacity-100` 150ms; modal card `scale-95 → scale-100` 200ms ease-out
- Modal close: reverse — `scale-100 → scale-95`, `opacity-100 → opacity-0` 150ms
- Zone condition paint in arch: instant fill color update after successful PATCH
- History panel new entry: slide in from right 150ms

---

## Loading & Error States

### Loading State
- SVG arch area: dark skeleton with `animate-pulse` gray tooth shapes in arch positions
- History sidebar: 3 skeleton entries
- Patient summary: `-- %` and `-- hallazgos`

### Error State
- Odontogram load fails: centered error card on dark background
  - Message: "No se pudo cargar el odontograma. Intenta de nuevo."
  - Button: "Reintentar"
- Save fails inside modal: toast error (modal stays open, zone reverts)
  - Message: "Error al guardar. El cambio no fue registrado."

### Empty State
- Patient with no conditions: all teeth render in healthy state (default `fill-gray-700`)
- Modal for healthy tooth: all zones empty, shows "Sin hallazgos en este diente"

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Not supported. Shows message: "El odontograma anatomico requiere una pantalla mas grande." Redirect prompt to switch to patient summary. |
| Tablet (640-1024px) | PRIMARY USE CASE. History panel collapses to bottom drawer (swipe up). SVG arch scales to fill available width. Modal is full-screen on portrait, centered panel on landscape. Touch targets: each tooth SVG element min 44×44px bounding box. |
| Desktop (> 1024px) | Default layout. History panel as right sidebar (260px). Modal centered 640px wide. |

**Tablet priority:** Critical. SVG tooth hit areas extended to minimum 44×44px bounding boxes regardless of visual tooth size. Elastic hover animation triggered on touch long-press (50ms delay) instead of mouse-enter.

---

## Accessibility

- **Focus order:** Toolbar → Upper arch teeth (right-to-left FDI order, 18→11, 21→28) → Lower arch teeth (48→41, 31→38) → Patient summary → History panel
- **Screen reader:** Each tooth SVG element has `role="button"` and `aria-label="Diente {FDI} — {tooth_name}, {N} hallazgos"`. Modal has `role="dialog"` with `aria-labelledby` pointing to tooth name heading. Backdrop has `aria-hidden="true"`.
- **Keyboard navigation:** Tab moves between teeth in FDI order. Enter/Space opens detail modal. Inside modal: Tab navigates zones → condition grid → notes → Registrar → close. Escape closes modal and returns focus to tooth.
- **Color contrast:** Condition zone colors paired with icon patterns (not color-only). FDI labels: `text-gray-300` on dark background meets WCAG AA (4.5:1). Tooltip badges: white text on blue background.
- **Language:** All labels in es-419. Arch reference labels: "Paladar" (upper), "Lengua" (lower). Quadrant labels: "Superior Derecho", "Superior Izquierdo", "Inferior Derecho", "Inferior Izquierdo". Modal heading: "Diente {FDI} — {nombre anatomico}".
- **Reduced motion:** Respect `prefers-reduced-motion`. Replace elastic scale with `opacity` transition only when reduced motion is set.

---

## Design Tokens

**Dark theme (default):**
- Page background: `bg-gray-950`
- Arch container: `bg-gray-950 rounded-2xl`
- Healthy tooth fill: `fill-gray-700`
- Tooth stroke: `stroke-gray-500`
- Selected tooth glow: `drop-shadow(0 0 8px #3B82F6)`
- Anatomical label: `text-gray-500 text-xs italic`
- FDI label: `text-gray-400 text-xs font-mono`

**Modal (dark themed):**
- Modal background: `bg-gray-900 border border-gray-700`
- Zone diagram background: `bg-gray-800`
- Zone healthy: `fill-gray-700`
- Zone with condition: condition color from catalog

**Patient summary bar:**
- Background: `bg-gray-900`
- Healthy %: `text-green-400 text-3xl font-bold`
- Findings count: `text-amber-400 text-xl font-semibold`

**Typography:**
- Arch label: `text-xs text-gray-500 italic font-normal`
- FDI numbers: `text-xs font-mono text-gray-400`
- Modal tooth name: `text-lg font-semibold text-white`
- Zone chip: `text-xs font-medium`

**Spacing:**
- SVG viewBox: `900 × 420`
- Modal max-width: `640px`
- Modal padding: `p-6`
- Zone diagram padding: `p-4`

---

## Implementation Notes

**Dependencies (npm):**
- `zustand` — `useOdontogramStore`
- `@tanstack/react-query` — data fetching and mutations
- `lucide-react` — ZoomIn, X, AlertTriangle, CheckCircle, Clock icons
- `framer-motion` — tooth hover spring animation, modal transitions

**File Location:**
- Page: `src/app/(dashboard)/patients/[id]/odontogram/page.tsx`
- Components: `src/components/odontogram/anatomic/ToothArchSVG.tsx`
- Components: `src/components/odontogram/anatomic/ToothDetailModal.tsx`
- Components: `src/components/odontogram/anatomic/ZoneChips.tsx`
- Store: `src/stores/odontogramStore.ts` (shared with classic)
- Types: `src/types/odontogram.ts`
- SVG tooth paths: `src/assets/odontogram/tooth-paths.ts` (precomputed arch positions)
- API: `src/lib/api/odontogram.ts`

**Hooks Used:**
- `useOdontogramStore()` — shared Zustand store
- `useQuery(['odontogram', patientId])` — load odontogram state
- `useQuery(['odontogram-conditions'])` — condition catalog
- `useMutation()` — save zone change (optimistic update)
- `useAuth()` — role check
- `useTenantPlan()` — verify plan >= Starter and mode = anatomic

**SVG Architecture:**
- Tooth arch positions precomputed as static coordinate arrays in `tooth-paths.ts`
- Each tooth is a `<g>` element with its SVG paths for crown and root zones
- Tooth shapes are simplified anatomic outlines (not photorealistic)
- Condition colors applied as SVG `fill` attributes on zone `<path>` elements
- Use `React.memo` on individual tooth `<g>` components to avoid full arch re-render on single zone change

**Plan Gate:**
- Render only if `tenant.plan >= "starter"` and `tenant.odontogram_mode = "anatomic"`
- If plan is Free, redirect to classic-grid view (FE-OD-01)
- Mode toggle in toolbar allows switching back to classic (FE-OD-07)

**Reference:**
- Based on Notion UX Spec: `DentalOS-Odontogram-v2-Arch.jsx`

---

## Test Cases

### Happy Path
1. Doctor loads anatomic odontogram for patient with existing conditions
   - **Given:** Patient has caries on tooth 16 zone O (crown Oclusal)
   - **When:** Doctor navigates to odontogram (mode = anatomic)
   - **Then:** Arch renders with tooth 16 showing red zone; arch dark background; FDI labels visible

2. Doctor hovers over tooth
   - **Given:** Arch loaded
   - **When:** Mouse enters tooth 26 SVG element
   - **Then:** Tooth scales ×1.25 with elastic spring animation; tooltip "26 — Primer premolar superior izquierdo" appears

3. Doctor clicks tooth and applies condition in modal
   - **Given:** Condition "Obturado" selected in ConditionGrid (modal), zone M selected
   - **When:** Click "Registrar"
   - **Then:** PATCH fires; modal stays open; tooth 26 zone M updates to blue in arch; history entry added; toast "Guardado"

4. Receptionist opens page in read-only mode
   - **Given:** Logged in as receptionist
   - **When:** Navigate to odontogram
   - **Then:** Modal opens on click but "Registrar" button hidden; zones in modal not clickable; condition grid disabled

### Edge Cases
1. All 32 teeth rendered without performance issues
   - **Given:** Full odontogram with conditions on multiple teeth
   - **When:** Page loads
   - **Then:** Initial render < 200ms; hover animation smooth (60fps); no dropped frames on tablet

2. Modal dismissed mid-edit
   - **Given:** Doctor clicked a zone and selected a condition but did not click "Registrar"
   - **When:** Click backdrop or press Escape
   - **Then:** Modal closes; no change saved; no history entry; arch unchanged

3. Touch on tablet — long press triggers hover state
   - **Given:** Tablet landscape, touch device
   - **When:** Finger held on tooth for 50ms
   - **Then:** Scale animation activates; tap completes opens modal

### Error Cases
1. Odontogram fails to load
   - **Given:** OD-01 returns 503
   - **When:** Page loads
   - **Then:** Dark error card on arch area; "No se pudo cargar. Reintentar" button; arch SVG not rendered

2. Save fails inside modal
   - **Given:** OD-02 returns 500
   - **When:** Doctor clicks "Registrar"
   - **Then:** Modal shows error toast; zone reverts in store; arch remains unchanged; modal stays open

3. Tenant plan downgraded to Free
   - **Given:** Tenant plan was Starter, now downgraded
   - **When:** Doctor tries to load anatomic view
   - **Then:** Redirect to classic grid (FE-OD-01) with toast "El plan actual no incluye el odontograma anatomico."

---

## Acceptance Criteria

- [ ] SVG dental arch renders with anatomically correct tooth positions in U and inverted-U shapes
- [ ] Tooth sizes vary by type: incisivo (18px), canino (20px), premolar (24px), molar (28px)
- [ ] Hover: ×1.25 elastic spring animation + FDI tooltip badge
- [ ] Click: opens `ToothDetailModal` with backdrop blur(8px) overlay
- [ ] Modal has 6 zones (5 crown + root); zones are interactive
- [ ] Condition applied via modal "Registrar" button; arch updates immediately (optimistic)
- [ ] Dark theme applied to arch view and modal
- [ ] Anatomical labels: "Paladar" (upper), "Lengua" (lower)
- [ ] History panel sidebar present (FE-OD-04)
- [ ] Patient summary bar: % sano + hallazgos count
- [ ] Modal: Escape closes; click-outside closes; focus returns to tooth
- [ ] Plan gate: only accessible for plan >= Starter with mode = anatomic
- [ ] Read-only mode for receptionist (no editing in modal)
- [ ] Loading skeleton matches dark theme arch shape
- [ ] All 32 tooth touch targets >= 44px bounding box on tablet
- [ ] `prefers-reduced-motion` respected — no spring animation when set
- [ ] All labels in Spanish (es-419)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
