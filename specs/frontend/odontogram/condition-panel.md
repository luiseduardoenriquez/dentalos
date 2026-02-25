# Panel de Seleccion de Condicion — Frontend Spec

## Overview

**Screen:** Shared condition selection panel used by both classic grid (FE-OD-01) and anatomic arch (FE-OD-02) odontogram views. Displays 12 dental conditions in a 2-column grid with color swatch, icon, and Spanish name. Includes a quick-notes textarea and a "Registrar" confirmation button. Supports keyboard shortcuts 1-9 for fast condition selection.

**Route:** Not a standalone route — embedded in:
- Right panel of `/patients/{id}/odontogram` (classic mode — FE-OD-01)
- Inside `ToothDetailModal` of `/patients/{id}/odontogram` (anatomic mode — FE-OD-02)

**Priority:** High

**Backend Specs:**
- `specs/odontogram/OD-09` — Get condition catalog (provides colors, icons, names)
- `specs/odontogram/OD-02` — Update odontogram (called when "Registrar" is clicked)

**Dependencies:**
- `specs/frontend/odontogram/classic-grid.md` (FE-OD-01) — parent in classic mode
- `specs/frontend/odontogram/anatomic-arch.md` (FE-OD-02) — parent in anatomic mode (inside modal)

---

## User Flow

**Entry Points:**
- Panel is always visible in the right panel (classic mode)
- Panel appears inside tooth detail modal (anatomic mode)
- User first selects a tooth zone, then selects a condition here, then clicks "Registrar"

**Exit Points:**
- "Registrar" submits the change → parent handles save (no navigation)
- Keyboard Escape deselects the active condition (does not navigate away)

**User Story:**
> As a doctor or assistant, I want to quickly select a dental condition and apply it to a tooth zone so that I can record clinical findings without interrupting the examination flow.

**Roles with access:** clinic_owner, doctor, assistant (interactive); receptionist (read-only — panel visible but conditions not selectable)

---

## Layout Structure

```
+----------------------------------+
|  Condicion seleccionada:         |
|  [ActiveConditionBadge]          |
+----------------------------------+
|  [ConditionGrid — 2 columns]     |
|  +----------+ +----------+       |
|  | [1] Caries| |[2] Obtur.|      |
|  +----------+ +----------+       |
|  | [3] Corona| |[4] Ausente|     |
|  +----------+ +----------+       |
|  | [5] Fract.| |[6] Incrst.|    |
|  +----------+ +----------+       |
|  | [7] Sellnt| |[8] ATM   |     |
|  +----------+ +----------+       |
|  | [9] Endo  | |[10] Pilar|     |
|  +----------+ +----------+       |
|  | [11] Impl.| |[12] Proto.|    |
|  +----------+ +----------+       |
+----------------------------------+
|  Notas rapidas:                  |
|  [textarea — 3 rows]             |
+----------------------------------+
|  [Limpiar] [Registrar]           |
+----------------------------------+
```

**Sections:**
1. Active condition badge — shows currently selected condition with its color
2. ConditionGrid — 2-column, 6-row grid of 12 condition buttons
3. QuickNotes — textarea for optional annotation
4. Action row — "Limpiar" (clear selection) and "Registrar" (save) buttons

---

## UI Components

### Component 1: ConditionGrid

**Type:** Interactive button grid

**Design System Ref:** `frontend/design-system/design-system.md` Section 6 (Clinical)

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| conditions | Condition[] | [] | Array of 12 conditions from OD-09 catalog |
| selectedConditionId | string \| null | null | ID of currently active condition |
| onSelect | (conditionId: string) => void | — | Selection handler |
| readOnly | boolean | false | Disables all buttons |
| disabledIds | string[] | [] | Conditions unavailable for current plan |

**States:**
- Default: all buttons visible, unselected
- Condition selected: active button has color ring `ring-2 ring-offset-2` matching condition color
- Hovered: subtle scale `scale-105` on button
- Disabled (plan gate): grayed out with lock icon overlay `opacity-40 cursor-not-allowed`
- Read-only: all buttons `pointer-events-none opacity-70`
- Loading (catalog not yet fetched): 12 skeleton buttons `animate-pulse`

**Behavior:**
- Each condition button is 100% width of its grid column
- Clicking a button: sets `selectedConditionId` in store; if same condition is already active, clicks deselects it (toggle)
- Keyboard shortcut: keys 1-9 trigger conditions at index 0-8 in catalog order
- Active condition immediately updates the selected zone color in the parent odontogram (optimistic)

---

### Component 2: ConditionButton

**Type:** Button

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| condition | Condition | — | Condition object from catalog |
| isActive | boolean | false | Whether this condition is selected |
| shortcutKey | number \| null | null | Keyboard shortcut number (1-9) |
| onClick | () => void | — | Selection handler |
| disabled | boolean | false | Grayed out state |

**Anatomy of each button:**
```
+------------------------------------+
| [ColorSwatch] [Icon] [Name]  [key] |
| ■ red-500     🦷  Caries       1  |
+------------------------------------+
```
- ColorSwatch: 12×12px filled circle in condition color
- Icon: 16px pictogram from condition catalog (SVG or Lucide icon name)
- Name: Spanish condition name, `text-sm font-medium`, truncated if too long
- Shortcut badge: small `text-xs text-gray-400` numeral at right edge (1-9, first 9 conditions)
- Active state: `ring-2 ring-offset-2` in condition color; background `bg-{color}-50`
- Height: min 44px (tablet touch target)

---

### Component 3: QuickNotes

**Type:** Textarea

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | string | "" | Current note text |
| onChange | (text: string) => void | — | Text change handler |
| maxLength | number | 500 | Max characters |
| readOnly | boolean | false | Disable editing |
| placeholder | string | "Notas adicionales para esta zona..." | Placeholder text |

**States:**
- Default: empty, placeholder visible
- Focused: blue border `ring-2 ring-blue-500`
- Filled: character count shown `{n}/500`
- Error (exceeds max): red border, count turns red
- Read-only: gray background `bg-gray-100`, not editable

**Behavior:**
- Notes are per zone (linked to `selectedToothId + selectedZone`)
- Notes are cleared when a different tooth zone is selected
- Notes are included in the PATCH payload when "Registrar" is clicked

---

### Component 4: ActiveConditionBadge

**Type:** Badge/indicator

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| condition | Condition \| null | null | The currently selected condition |
| zone | string \| null | null | The currently selected zone name |

**States:**
- No selection: `text-gray-400 italic text-sm` — "Selecciona una zona y una condicion"
- Condition selected but no zone: `text-amber-600 text-sm` — "Selecciona una zona del diente"
- Both selected: colored badge with condition color dot + text "Zona {zone}: {condicion}"

---

## Form Fields

| Field | Type | Required | Validation | Error Message (es-419) | Placeholder |
|-------|------|----------|------------|------------------------|-------------|
| notas | textarea | No | Max 500 chars | "Las notas no pueden superar los 500 caracteres." | "Notas adicionales para esta zona..." |

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Load conditions | `/api/v1/odontogram/conditions` | GET | `specs/odontogram/OD-09` | 1hr stale |
| Save zone change | `/api/v1/patients/{id}/odontogram` | PATCH | `specs/odontogram/OD-02` | Invalidate |

### State Management

**Local State (useState):**
- `notes: string` — current quick-note text for selected zone
- `isSaving: boolean` — "Registrar" button loading state

**Global State (Zustand — useOdontogramStore):**
- `selectedConditionId: string | null` — active condition (read + write)
- `conditionCatalog: Condition[]` — loaded once and shared (read)
- `selectedToothId: number | null` — which tooth is selected (read)
- `selectedZone: ToothZone | null` — which zone is selected (read)

**Server State (TanStack Query):**
- Query key: `['odontogram-conditions', tenantId]`
- Stale time: 1 hour (catalog rarely changes)
- Mutation: `useMutation()` — PATCH triggered from parent; ConditionPanel calls `onRegister(conditionId, notes)` prop to delegate to parent

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click condition | Click ConditionButton | Sets active condition; badge updates | Active ring on button; badge updates |
| Press key 1-9 | Keyboard shortcut | Selects condition at that index | Button ring animates |
| Click same condition | Second click on active | Deselects condition (toggle) | Ring removed; badge clears |
| Type in notes | Keyboard in textarea | Updates local note text | Character count updates |
| Click "Registrar" | Click button | Calls `onRegister(conditionId, notes)` prop | Button spinner; parent handles PATCH |
| Click "Limpiar" | Click button | Clears selectedConditionId and notes | Badge resets; textarea clears |
| Escape | Key press | Deselects condition | Badge resets |

### Animations/Transitions

- Condition button selection ring: `transition-all duration-100` — instant ring appearance
- Button hover: `scale-105 transition-transform duration-100`
- ActiveConditionBadge content change: `transition-opacity duration-150` fade between states
- "Registrar" loading: spinner replaces text, button width stable (no layout shift)

---

## Loading & Error States

### Loading State
- Catalog loading: 12 `animate-pulse` skeleton buttons in a 2-column grid
- "Registrar" saving: `<Loader2 className="animate-spin">` spinner inside button, button text "Guardando..."

### Error State
- Catalog load fails: error message inside panel
  - Message: "No se pudo cargar las condiciones. Intenta de nuevo."
  - Button: "Reintentar" → re-triggers `['odontogram-conditions']` query
- Save fails: handled by parent (toast error); panel remains interactive

### Empty State
- No condition selected: `ActiveConditionBadge` shows instruction text
- "Registrar" button disabled until both a zone and a condition are selected

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Not standalone — panel appears as bottom sheet within parent page |
| Tablet (640-1024px) | Fixed right panel (classic) or modal panel (anatomic). Condition buttons min 44px height. 2-column layout maintained. QuickNotes 2 visible rows. |
| Desktop (> 1024px) | Fixed 280px right panel (classic) or 300px column within modal (anatomic). Full 3-row notes textarea. |

**Tablet priority:** High — panel used heavily during clinical exam on tablet. All ConditionButtons min 44px height. "Registrar" button min 48px height.

---

## Accessibility

- **Focus order:** ActiveConditionBadge (read) → ConditionButton[1] → ... → ConditionButton[12] → QuickNotes textarea → Limpiar button → Registrar button
- **Screen reader:** Each ConditionButton has `aria-label="{condition_name} — Atajo: {key}"`. Active condition button has `aria-pressed="true"`. ActiveConditionBadge has `role="status"` and `aria-live="polite"` so screen reader announces condition selection.
- **Keyboard navigation:** Tab moves through buttons in grid order. Enter/Space selects. Keys 1-9 work regardless of current focus (captured at panel level). Escape deselects. When "Registrar" is disabled, it has `aria-disabled="true"` and `tabIndex={-1}`.
- **Color contrast:** Condition color swatches supplemented by text labels (color is not sole indicator). All text on white/gray backgrounds meets WCAG AA 4.5:1.
- **Language:** All labels in es-419. Button labels: "Registrar", "Limpiar". Placeholder: "Notas adicionales para esta zona...". Badge states in Spanish.

---

## Design Tokens

**Colors:**
- Panel background: `bg-white dark:bg-gray-900`
- Panel border: `border-l border-gray-200 dark:border-gray-700`
- Condition button default: `bg-gray-50 hover:bg-gray-100 border border-gray-200`
- Condition button active: `bg-{condition-color}-50 border-{condition-color}-300 ring-2 ring-{condition-color}-400`
- "Registrar" button: `bg-blue-600 hover:bg-blue-700 text-white`
- "Limpiar" button: `bg-gray-100 hover:bg-gray-200 text-gray-700`

**Condition colors (from OD-09 catalog — representative):**
- Caries: `#EF4444` (red-500)
- Obturado: `#3B82F6` (blue-500)
- Corona: `#F59E0B` (amber-500)
- Ausente: `#6B7280` (gray-500)
- Fractura: `#8B5CF6` (violet-500)
- Incrustacion: `#06B6D4` (cyan-500)
- Sellante: `#10B981` (emerald-500)
- ATM/Bruxismo: `#F97316` (orange-500)
- Endodoncia: `#EC4899` (pink-500)
- Pilar de puente: `#84CC16` (lime-500)
- Implante: `#14B8A6` (teal-500)
- Protesis removible: `#A855F7` (purple-500)

**Typography:**
- Condition name: `text-sm font-medium text-gray-800 dark:text-gray-100`
- Shortcut key: `text-xs text-gray-400 tabular-nums`
- Notes label: `text-sm font-medium text-gray-700 dark:text-gray-300`
- Character count: `text-xs text-gray-400`

**Spacing:**
- Panel padding: `p-4`
- Grid gap: `gap-2`
- Button height: `min-h-[44px]`
- Button padding: `px-3 py-2`
- Textarea: `rows={3}` (desktop), `rows={2}` (tablet)
- Action row gap: `gap-3 mt-4`

**Border Radius:**
- Condition buttons: `rounded-lg`
- Textarea: `rounded-md`
- "Registrar" button: `rounded-lg`

---

## Implementation Notes

**Dependencies (npm):**
- `zustand` — reads and writes to `useOdontogramStore`
- `@tanstack/react-query` — loads condition catalog
- `lucide-react` — Loader2 (spinner), X (Limpiar), Check (success state)

**File Location:**
- Component: `src/components/odontogram/ConditionPanel.tsx`
- Sub-components:
  - `src/components/odontogram/ConditionGrid.tsx`
  - `src/components/odontogram/ConditionButton.tsx`
  - `src/components/odontogram/QuickNotes.tsx`
  - `src/components/odontogram/ActiveConditionBadge.tsx`
- Store: `src/stores/odontogramStore.ts`
- Types: `src/types/odontogram.ts`

**Hooks Used:**
- `useOdontogramStore()` — selected tooth, zone, condition, catalog
- `useQuery(['odontogram-conditions'])` — load catalog (shared with parent)
- `useAuth()` — role check for read-only
- `useEffect()` — keyboard shortcut listener (1-9 keys)

**Keyboard shortcut implementation:**
```typescript
useEffect(() => {
  const handler = (e: KeyboardEvent) => {
    const index = parseInt(e.key) - 1;
    if (index >= 0 && index <= 8 && catalog[index] && !readOnly) {
      selectCondition(catalog[index].id);
    }
    if (e.key === 'Escape') clearCondition();
  };
  window.addEventListener('keydown', handler);
  return () => window.removeEventListener('keydown', handler);
}, [catalog, readOnly]);
```

**"Registrar" disabled states:**
- `selectedConditionId === null` (no condition chosen)
- `selectedZone === null` (no zone chosen)
- `isSaving === true` (save in progress)

---

## Test Cases

### Happy Path
1. Doctor selects condition via click
   - **Given:** Catalog loaded with 12 conditions; tooth zone selected in parent
   - **When:** Doctor clicks "Caries" button
   - **Then:** Caries button gets active ring; badge shows "Zona O: Caries"; "Registrar" becomes enabled

2. Doctor uses keyboard shortcut
   - **Given:** Panel focused, catalog loaded
   - **When:** Doctor presses key "2"
   - **Then:** Second condition (Obturado) selected; button ring appears; badge updates

3. Doctor types notes and registers
   - **Given:** Condition selected, zone selected, notes typed
   - **When:** Click "Registrar"
   - **Then:** Button shows spinner; `onRegister(conditionId, notes)` called; toast "Guardado" shown by parent

4. Doctor clicks same condition again to deselect
   - **Given:** Caries already active
   - **When:** Click Caries button again
   - **Then:** Condition deselected; ring removed; "Registrar" disabled

5. Clicking "Limpiar" clears state
   - **Given:** Condition selected, notes typed
   - **When:** Click "Limpiar"
   - **Then:** Condition deselected; notes cleared; badge resets to "Selecciona una zona y una condicion"

### Edge Cases
1. Catalog has fewer than 12 conditions (plan limitation)
   - **Given:** OD-09 returns only 8 conditions for this plan
   - **When:** Panel renders
   - **Then:** 8 buttons shown; remaining 4 slots hidden (not shown as disabled)

2. Pressing key "9" when fewer than 9 conditions exist
   - **Given:** Catalog has 7 conditions
   - **When:** Key "9" pressed
   - **Then:** No action — handler checks `catalog[8]` is undefined and ignores

3. Notes at character limit
   - **Given:** Notes textarea already has 500 characters
   - **When:** User types another character
   - **Then:** Character blocked; count shows "500/500" in red; "Registrar" remains enabled (notes are optional with valid length)

### Error Cases
1. Condition catalog fails to load
   - **Given:** OD-09 returns 500
   - **When:** Panel renders
   - **Then:** 12 skeleton buttons replaced by error message with "Reintentar" button

2. Receptionist in read-only mode
   - **Given:** Role = receptionist
   - **When:** Panel renders
   - **Then:** All ConditionButtons are `pointer-events-none opacity-70`; "Registrar" hidden; notes textarea `readOnly`

---

## Acceptance Criteria

- [ ] 12 condition buttons displayed in 2-column grid with color swatch, icon, and Spanish name
- [ ] Click condition → active ring appears; ActiveConditionBadge updates
- [ ] Click same active condition → deselects (toggle behavior)
- [ ] Keyboard shortcuts 1-9 select conditions correctly
- [ ] Escape deselects condition
- [ ] QuickNotes textarea: max 500 chars, character counter shown
- [ ] "Registrar" disabled until both zone and condition are selected
- [ ] "Registrar" calls `onRegister(conditionId, notes)` with correct payload
- [ ] "Limpiar" clears condition and notes
- [ ] Loading state: 12 skeleton buttons while catalog loads
- [ ] Error state: retry UI when catalog fails to load
- [ ] Read-only mode: buttons and textarea non-interactive for receptionist
- [ ] All touch targets min 44px height
- [ ] Keyboard accessible: Tab order, Enter/Space, aria-pressed, aria-live badge
- [ ] All labels and messages in Spanish (es-419)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
