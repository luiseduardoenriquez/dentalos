# Barra de Herramientas del Odontograma — Frontend Spec

## Overview

**Screen:** Odontogram toolbar rendered at the top of the odontogram view (both classic and anatomic modes). Provides controls for mode switching (classic/anatomic), dentition toggle (adult/pediatric), zoom controls, print, snapshot, and voice input. Each control is conditionally rendered based on tenant plan and enabled add-ons.

**Route:** Not a standalone route — embedded in `/patients/{id}/odontogram` (all modes)

**Priority:** Medium

**Backend Specs:**
- `specs/odontogram/OD-12` — Toggle odontogram mode (classic ↔ anatomic)
- `specs/odontogram/OD-05` — Take snapshot
- `specs/odontogram/V-01` — Voice note input (if voice add-on)

**Dependencies:**
- `specs/frontend/odontogram/classic-grid.md` (FE-OD-01) — parent page
- `specs/frontend/odontogram/anatomic-arch.md` (FE-OD-02) — parent page
- `specs/frontend/odontogram/comparison-view.md` (FE-OD-05) — snapshot leads here

---

## User Flow

**Entry Points:**
- Always visible at the top of the odontogram view
- Present in both classic and anatomic modes

**Exit Points:**
- Mode toggle: refreshes odontogram in new mode (no navigation)
- Print: opens system print dialog
- Snapshot: saves snapshot then shows confirmation; optional redirect to comparison view
- Voice button: navigates to voice recorder (FE-V-01) or opens inline recorder

**User Story:**
> As a doctor using the odontogram, I want quick access to mode switching, zoom, printing, and voice recording controls at the top of the screen so that I can efficiently manage my clinical workflow without interrupting the examination.

**Roles with access:** All roles that have odontogram access (clinic_owner, doctor, assistant, receptionist). Receptionist: all controls visible but write actions (snapshot, mode toggle, voice) are hidden.

---

## Layout Structure

```
+-------------------------------------------------------------------+
| [Mode Toggle: Clasico | Anatomico]  [Adult | Pediatrico]          |
| [Zoom -] [100%] [Zoom +]            [Imprimir] [Snapshot] [Voz]  |
+-------------------------------------------------------------------+
```

Desktop — single row, all controls visible:
```
+-------------------------------------------------------------------+
| [Clasico][Anatomico]  [Adulto][Pediatrico]  [-][100%][+]  [Print][Snap][Voz] |
+-------------------------------------------------------------------+
```

Tablet — two rows or condensed with icon-only buttons:
```
+-------------------------------------------------------------------+
| [Mode Toggle]  [Dentition]  [Zoom Group]  [Actions: ...][...]     |
+-------------------------------------------------------------------+
```

**Sections:**
1. Mode toggle group — classic/anatomic segmented control (conditional on plan)
2. Dentition toggle — adult/pediatric segmented control
3. Zoom controls — minus, percentage display, plus
4. Action buttons — print, snapshot, voice (conditional on add-on)

---

## UI Components

### Component 1: ModeToggle

**Type:** Segmented control (two buttons)

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.1 (Segmented Controls)

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| currentMode | "classic" \| "anatomic" | "classic" | Active mode |
| onChange | (mode) => void | — | Mode switch handler |
| planAllowsAnatomic | boolean | false | Whether plan >= Starter |
| isLoading | boolean | false | Switching in progress |

**States:**
- Active mode: `bg-blue-600 text-white`
- Inactive mode: `bg-gray-100 text-gray-700 hover:bg-gray-200`
- Loading (switching): spinner on active mode button; both buttons disabled
- Anatomic unavailable (plan = Free): "Anatomico" button is `opacity-40 cursor-not-allowed` with lock icon; tooltip "Disponible en plan Starter o superior."
- Hidden entirely: not rendered if `planAllowsAnatomic = false` and current mode is classic (no point showing a toggle with one effective option)

**Behavior:**
- Clicking inactive mode option: calls OD-12 API → `PUT /api/v1/tenants/me/odontogram-mode`
- On success: page re-renders in new mode (full odontogram reload)
- On failure: toast error, mode reverts to previous

**Confirmation dialog:**
- Switching modes while unsaved changes are pending: shows confirm dialog
  - Message: "Tienes cambios sin guardar. Si cambias de modo se perderan. ¿Continuar?"
  - Actions: "Cancelar" and "Cambiar de modo"

---

### Component 2: DentitionToggle

**Type:** Segmented control (two buttons)

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| currentDentition | "adult" \| "pediatric" | "adult" | Active dentition |
| onChange | (dentition) => void | — | Handler |
| isLoading | boolean | false | Switching in progress |

**States:**
- Adult active: "Adulto" button highlighted
- Pediatric active: "Pediatrico" button highlighted

**Behavior:**
- Switching to pediatric: odontogram switches to primary dentition FDI numbering (51-85)
- Pediatric grid shows 20 teeth (primary dentition) instead of 32
- Pediatric toggle stored in local component state (not persisted to server)
- Session-only: resets to adult on page reload

**Note:** Dentition toggle affects only the current session rendering. The stored odontogram data uses a dentition field per tooth to distinguish primary vs permanent teeth records.

---

### Component 3: ZoomControls

**Type:** Button group + display

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| zoomLevel | number | 100 | Current zoom percentage |
| onZoomIn | () => void | — | Increase zoom |
| onZoomOut | () => void | — | Decrease zoom |
| onReset | () => void | — | Reset to 100% |
| minZoom | number | 75 | Minimum zoom % |
| maxZoom | number | 150 | Maximum zoom % |

**Layout:**
```
[-]  [100%]  [+]
```
- `-` button: `ZoomOut` icon
- Center: current percentage, clickable to reset to 100%
- `+` button: `ZoomIn` icon

**States:**
- `-` disabled when `zoomLevel <= minZoom`
- `+` disabled when `zoomLevel >= maxZoom`
- Center label: `text-sm font-mono text-gray-700`

**Behavior:**
- Zoom steps: 25% increments (75%, 100%, 125%, 150%)
- Zoom applies via CSS `transform: scale({zoomLevel/100})` on the odontogram container
- Zoom level stored in `useOdontogramStore` (persists within session; resets on page reload)
- Also supports keyboard: Ctrl/Cmd+= (zoom in), Ctrl/Cmd+- (zoom out), Ctrl/Cmd+0 (reset)

---

### Component 4: PrintButton

**Type:** Icon button with label

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| patientName | string | — | Patient name for print document title |
| onPrint | () => void | — | Print handler |

**States:**
- Default: `Printer` icon + "Imprimir" label
- Loading: spinner (preparing print layout)

**Behavior:**
- Calls `window.print()` with a print-specific CSS layout applied
- Print layout: hides toolbar, sidebar, and navigation; renders only the odontogram grid and patient header
- Print layout uses light theme regardless of current theme setting
- Prints both arches on a single A4/Letter page

---

### Component 5: SnapshotButton

**Type:** Icon button with label

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| patientId | string | — | Patient UUID |
| onSnapshot | () => void | — | Snapshot handler |
| isLoading | boolean | false | Snapshot in progress |

**States:**
- Default: `Camera` icon + "Snapshot"
- Loading: spinner; button disabled
- Success: brief checkmark (1s) then restores

**Behavior:**
- Calls OD-05 `POST /api/v1/patients/{id}/odontogram/snapshots`
- On success: toast "Snapshot guardado. ¿Ver comparacion?" with action link to FE-OD-05
- On failure: toast error "No se pudo guardar el snapshot. Intenta de nuevo."
- Receptionist: button hidden

---

### Component 6: VoiceButton

**Type:** Icon button with label (conditional)

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| patientId | string | — | Patient UUID |
| toothId | number \| null | null | Pre-scoped tooth if selected |
| hasVoiceAddon | boolean | false | Whether tenant has voice add-on |
| onVoiceClick | () => void | — | Opens voice recorder (FE-V-01) |

**States:**
- Shown: only when `hasVoiceAddon = true`
- Default: `Mic` icon + "Voz" label, `bg-purple-50 text-purple-700 border-purple-200`
- Recording active: pulsing red ring `animate-pulse ring-2 ring-red-500`
- Processing: spinner
- Disabled (no voice add-on): button not rendered

**Behavior:**
- Click: opens voice recorder linked to FE-V-01
- If a tooth is currently selected in the odontogram, recorder is pre-scoped to that tooth
- Recording transcription result auto-fills into the ConditionPanel notes field

---

## Form Fields

Not applicable — toolbar has no form inputs.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Toggle mode | `/api/v1/tenants/me/odontogram-mode` | PUT | `specs/odontogram/OD-12` | Invalidate tenant config |
| Take snapshot | `/api/v1/patients/{id}/odontogram/snapshots` | POST | `specs/odontogram/OD-05` | Invalidate snapshots list |

### State Management

**Local State (useState):**
- `dentition: "adult" | "pediatric"` — session-only dentition toggle
- `isSnapshotLoading: boolean`
- `isModeLoading: boolean`

**Global State (Zustand — useOdontogramStore):**
- `zoomLevel: number` — current zoom (read + write)
- `odontogramMode: "classic" | "anatomic"` — current mode (read; updated by OD-12)

**Server State (TanStack Query):**
- Mutation: `useMutation()` for mode toggle (OD-12)
- Mutation: `useMutation()` for snapshot (OD-05)
- No persistent query — toolbar reads from store and props

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click "Anatomico" (plan OK) | Click mode toggle | Confirm if unsaved; PUT OD-12; reload odontogram in anatomic mode | Mode button spinner; odontogram reloads |
| Click "Clasico" | Click mode toggle | Confirm if unsaved; PUT OD-12; reload in classic | Mode button spinner; odontogram reloads |
| Click "Anatomico" (plan = Free) | Click disabled button | Upsell tooltip shown | Tooltip: "Disponible en plan Starter o superior." |
| Click "Pediatrico" | Click dentition toggle | Odontogram switches to 20-tooth primary dentition | Button highlights; odontogram re-renders |
| Click "+" zoom | Click | Zoom increases by 25%; odontogram scales | Zoom % updates |
| Click "-" zoom | Click | Zoom decreases by 25%; odontogram scales | Zoom % updates |
| Click "100%" | Click zoom display | Zoom resets to 100% | Zoom % resets |
| Ctrl+= | Keyboard | Zoom in | Same as click "+" |
| Ctrl+- | Keyboard | Zoom out | Same as click "-" |
| Ctrl+0 | Keyboard | Zoom reset | Same as click "100%" |
| Click "Imprimir" | Click | Print dialog opens | System print dialog |
| Click "Snapshot" | Click | POST OD-05; toast with comparison link | Spinner; toast "Snapshot guardado" |
| Click "Voz" (add-on active) | Click | Opens voice recorder (FE-V-01) | Voice button pulses red when recording |

### Animations/Transitions

- Mode toggle switch: button background transition `transition-colors duration-150`
- Snapshot success: checkmark icon replaces camera for 1s then restores `transition-opacity 200ms`
- Voice recording active: pulsing ring `animate-pulse` on mic button
- Zoom scale on odontogram container: CSS `transition-transform duration-200 ease-out`
- Unsaved changes confirmation dialog: modal slide in 150ms

---

## Loading & Error States

### Loading State
- Mode toggle loading: spinner on triggered button; both mode buttons disabled
- Snapshot loading: camera icon replaced by `<Loader2 className="animate-spin">` on snapshot button; button disabled

### Error State
- Mode toggle fails: toast error "No se pudo cambiar el modo del odontograma. Intenta de nuevo."; mode reverts to previous
- Snapshot fails: toast error "No se pudo guardar el snapshot."

### Empty State
- Not applicable — toolbar always renders with at least zoom + print controls

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Not applicable — odontogram not supported on mobile |
| Tablet (640-1024px) | PRIMARY USE CASE. Two-row toolbar: Row 1: mode toggle + dentition toggle. Row 2: zoom controls + action buttons. Action button labels hidden; icon-only buttons with tooltips. All buttons min 44px touch target. |
| Desktop (> 1024px) | Single row. All buttons show icon + text label. Toolbar height 56px. |

**Tablet priority:** High — toolbar is used constantly during clinical examination. All buttons icon-only on tablet with tooltip on long-press. Spacing between buttons min 8px to prevent accidental taps. VoiceButton shows mic pulsing ring clearly visible on tablet.

**Icon-only on tablet:**
- ModeToggle: "Cls" / "Ana" abbreviated text or grid/arch icons
- DentitionToggle: adult-icon / child-icon
- ZoomControls: `-` / `%` / `+` (no labels)
- PrintButton: `Printer` icon only
- SnapshotButton: `Camera` icon only
- VoiceButton: `Mic` icon only with pulsing state

---

## Accessibility

- **Focus order:** Mode toggle (Clasico → Anatomico) → Dentition toggle (Adulto → Pediatrico) → Zoom out → Zoom display (reset) → Zoom in → Print → Snapshot → Voice (if shown)
- **Screen reader:** Each toggle button has `aria-pressed` for active state. Mode toggle group has `role="group"` with `aria-label="Modo del odontograma"`. Dentition toggle group has `role="group"` with `aria-label="Tipo de denticion"`. Zoom display has `aria-label="Nivel de zoom: {n}%"`. VoiceButton when recording: `aria-label="Grabando nota de voz — haz clic para detener"` with `aria-live="assertive"`.
- **Keyboard navigation:** Tab through all buttons in focus order. Enter/Space activates. Ctrl/Cmd+= and Ctrl/Cmd+- for zoom. All keyboard shortcuts documented in `title` attribute on buttons.
- **Color contrast:** Mode toggle active state: white text on blue-600 meets WCAG AA. Inactive: gray-700 on gray-100 meets WCAG AA. VoiceButton active recording: `text-purple-700 on bg-purple-50` verified AA.
- **Language:** All labels in es-419. "Clasico", "Anatomico", "Adulto", "Pediatrico", "Imprimir", "Snapshot" (accepted loanword in dental context), "Voz". Tooltip for locked Anatomico: "Disponible en plan Starter o superior."

---

## Design Tokens

**Colors:**
- Toolbar background: `bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700`
- Active toggle segment: `bg-blue-600 text-white`
- Inactive toggle segment: `bg-gray-100 text-gray-700 hover:bg-gray-200`
- Disabled toggle (plan gate): `opacity-40 cursor-not-allowed`
- Zoom button: `bg-gray-50 hover:bg-gray-100 text-gray-700`
- Zoom display: `bg-gray-50 text-gray-800 font-mono text-sm`
- Print button: `bg-gray-50 hover:bg-gray-100 text-gray-700`
- Snapshot button: `bg-gray-50 hover:bg-gray-100 text-gray-700`
- Voice button default: `bg-purple-50 text-purple-700 border border-purple-200`
- Voice button recording: `bg-red-50 text-red-700 border-red-200 ring-2 ring-red-400 animate-pulse`

**Typography:**
- Button labels (desktop): `text-sm font-medium`
- Zoom display: `text-sm font-mono tabular-nums`
- Tooltip: `text-xs bg-gray-900 text-white rounded-md px-2 py-1`

**Spacing:**
- Toolbar height (desktop): `h-14` (56px)
- Toolbar height (tablet): `h-auto py-2` (two rows)
- Button padding: `px-3 py-2` desktop; `p-2` tablet (icon-only)
- Button gap: `gap-2`
- Group separator: `mx-3 w-px bg-gray-200` vertical divider between control groups

**Border Radius:**
- Toggle groups: `rounded-lg` with internal `rounded-md` per button
- Zoom group: `rounded-lg flex border border-gray-200`
- Action buttons: `rounded-lg`

---

## Implementation Notes

**Dependencies (npm):**
- `zustand` — reads/writes `zoomLevel` and `odontogramMode` from `useOdontogramStore`
- `@tanstack/react-query` — mutations for OD-12 and OD-05
- `lucide-react` — ZoomIn, ZoomOut, Printer, Camera, Mic, Grid2X2, Rows (mode icons), Baby (pediatric)
- `framer-motion` — snapshot success checkmark animation

**File Location:**
- Component: `src/components/odontogram/OdontogramToolbar.tsx`
- Sub-components:
  - `src/components/odontogram/toolbar/ModeToggle.tsx`
  - `src/components/odontogram/toolbar/DentitionToggle.tsx`
  - `src/components/odontogram/toolbar/ZoomControls.tsx`
  - `src/components/odontogram/toolbar/SnapshotButton.tsx`
  - `src/components/odontogram/toolbar/VoiceButton.tsx`
- Store: `src/stores/odontogramStore.ts`

**Hooks Used:**
- `useOdontogramStore()` — zoomLevel, odontogramMode
- `useMutation()` — OD-12 (mode toggle), OD-05 (snapshot)
- `useTenantPlan()` — determine if anatomic mode available
- `useTenantAddons()` — check voice add-on enabled
- `useAuth()` — role check for write controls visibility
- `useEffect()` — keyboard shortcut listeners (Ctrl+=, Ctrl+-, Ctrl+0)

**Unsaved changes detection:**
```typescript
const hasUnsavedChanges = useOdontogramStore(state => state.changeLog.length > 0 && !state.lastSaveTimestamp);
```

**Keyboard shortcut handler:**
```typescript
useEffect(() => {
  const handler = (e: KeyboardEvent) => {
    if (e.ctrlKey || e.metaKey) {
      if (e.key === '=') { e.preventDefault(); zoomIn(); }
      if (e.key === '-') { e.preventDefault(); zoomOut(); }
      if (e.key === '0') { e.preventDefault(); resetZoom(); }
    }
  };
  window.addEventListener('keydown', handler);
  return () => window.removeEventListener('keydown', handler);
}, []);
```

**Print styles:**
```css
@media print {
  .odontogram-toolbar,
  .sidebar,
  .nav-sidebar { display: none !important; }
  .odontogram-grid { transform: none !important; page-break-inside: avoid; }
  body { background: white !important; color: black !important; }
}
```

---

## Test Cases

### Happy Path
1. Clinic owner on Starter plan switches to anatomic mode
   - **Given:** Tenant plan = Starter, current mode = classic
   - **When:** Click "Anatomico" toggle
   - **Then:** No unsaved changes dialog; PUT OD-12 fires; mode toggle shows spinner; odontogram reloads in anatomic mode

2. Doctor switches to pediatric dentition
   - **Given:** Odontogram in adult mode (32 teeth)
   - **When:** Click "Pediatrico" toggle
   - **Then:** Grid/arch re-renders with 20 primary teeth; FDI numbers switch to 51-85 range

3. Doctor zooms in via keyboard shortcut
   - **Given:** Zoom at 100%
   - **When:** Press Ctrl+=
   - **Then:** Zoom increments to 125%; odontogram scales; zoom display shows "125%"

4. Doctor takes a snapshot
   - **Given:** Valid patient odontogram loaded
   - **When:** Click "Snapshot"
   - **Then:** POST OD-05 fires; spinner on button; success toast "Snapshot guardado. ¿Ver comparacion?" with comparison link

5. Zoom reset via click on percentage
   - **Given:** Zoom at 150%
   - **When:** Click "150%" zoom display
   - **Then:** Zoom resets to 100%

6. Voice button visible and functional (add-on enabled)
   - **Given:** Tenant has voice add-on; doctor role
   - **When:** Click "Voz" button
   - **Then:** Voice recorder (FE-V-01) opens; mic button enters pulsing state

### Edge Cases
1. Free plan user — Anatomico button is locked
   - **Given:** Tenant plan = Free
   - **When:** Click "Anatomico" button
   - **Then:** Button click blocked; upsell tooltip shown "Disponible en plan Starter o superior."

2. Mode toggle with unsaved changes pending
   - **Given:** Doctor has 2 unsaved condition changes in `changeLog`
   - **When:** Click "Anatomico"
   - **Then:** Confirmation dialog "Tienes cambios sin guardar..." appears; if confirmed, switches; if cancelled, stays in classic

3. Zoom at minimum — "-" button disabled
   - **Given:** Zoom at 75% (minimum)
   - **When:** Inspect toolbar
   - **Then:** "-" button is `disabled` and `aria-disabled="true"`; Ctrl+- keyboard shortcut does nothing

4. Receptionist role — write controls hidden
   - **Given:** Logged in as receptionist
   - **When:** Odontogram loaded
   - **Then:** Snapshot button hidden; Voice button hidden; Mode toggle hidden; zoom and print visible

### Error Cases
1. Snapshot POST fails
   - **Given:** OD-05 returns 500
   - **When:** Click "Snapshot"
   - **Then:** Toast error "No se pudo guardar el snapshot. Intenta de nuevo."; snapshot button re-enabled

2. Mode toggle PUT fails
   - **Given:** OD-12 returns 503
   - **When:** Click "Anatomico"
   - **Then:** Toast error "No se pudo cambiar el modo."; toolbar reverts to "Clasico" active; odontogram stays in classic

---

## Acceptance Criteria

- [ ] Mode toggle: shows "Clasico" and "Anatomico" buttons; active mode highlighted
- [ ] Mode toggle only shown when plan >= Starter; "Anatomico" locked with tooltip on Free plan
- [ ] Mode switch calls OD-12 PUT; odontogram reloads in new mode
- [ ] Confirmation dialog shown when switching mode with unsaved changes
- [ ] Dentition toggle: "Adulto" and "Pediatrico"; switches between 32-tooth and 20-tooth view
- [ ] Zoom controls: "+" increases by 25%, "-" decreases by 25%, display resets on click
- [ ] Zoom min 75%, max 150%; buttons disabled at limits
- [ ] Keyboard shortcuts: Ctrl/Cmd+=, -, 0 work for zoom
- [ ] Zoom persists within session via useOdontogramStore
- [ ] Print button: triggers print with toolbar/nav hidden via print CSS
- [ ] Snapshot button: POST OD-05; success toast with comparison link
- [ ] Snapshot button hidden for receptionist role
- [ ] Voice button: only shown when voice add-on enabled; triggers FE-V-01
- [ ] Voice button pulsing state during recording
- [ ] Tablet: icon-only buttons in two-row layout; all min 44px touch targets
- [ ] Desktop: icon + text labels, single-row
- [ ] All labels in Spanish (es-419)
- [ ] Accessibility: ARIA pressed states, keyboard shortcuts, screen reader announcements

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
