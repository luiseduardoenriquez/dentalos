# ADR-005: SVG-based Odontogram Rendering

**Status:** Accepted
**Date:** 2026-02-24
**Authors:** DentalOS Architecture Team

---

## Context

The odontogram is DentalOS's centerpiece clinical interface. Dentists interact with it dozens of times per day during patient examinations, treatment planning, and clinical record review. The odontogram must render all 32 adult teeth (or 20 pediatric teeth, or a mix during mixed dentition) with per-surface interactivity, condition overlays, and two distinct layout modes.

### Requirements

**Layout modes:**

- **Classic mode (Modo clasico):** Grid-based layout with teeth arranged in rows by quadrant, using FDI notation. This is the traditional paper odontogram format familiar to every LATAM dentist.
- **Anatomic mode (Modo anatomico):** Arch-shaped layout mimicking the natural curvature of the upper (maxillary) and lower (mandibular) jaws. Preferred by some clinicians for its spatial accuracy.

**Per-tooth structure:**

Each tooth is a composite visual element with 5 interactive crown surfaces plus the root:

| Surface | Code | Location |
|---------|------|----------|
| Oclusal / Incisal | O | Top/biting surface (center of the tooth diagram) |
| Mesial | M | Side facing the dental midline |
| Distal | D | Side facing away from the midline |
| Vestibular (Bucal) | V | Side facing the cheek/lip |
| Lingual / Palatino | L | Side facing the tongue/palate |
| Root | R | Sub-gingival area below the crown |

**Clinical conditions (12):**

Each surface or whole tooth can display one of 12 clinical conditions, each with a specific color and visual treatment defined in the design system (see `infra/design-system.md`, Section 1.3):

| Condition | Code | SVG Fill Color |
|-----------|------|----------------|
| Sano | SAN | `#4CAF50` |
| Caries | CAR | `#EF4444` |
| Resina | RES | `#3B82F6` |
| Amalgama | AMA | `#78909C` |
| Corona | COR | `#FFC107` |
| Ausente | AUS | `#37474F` |
| Implante | IMP | `#7C3AED` |
| Endodoncia | END | `#EC4899` |
| Sellante | SEL | `#10B981` |
| Fractura | FRA | `#F97316` |
| Caries Profunda | CPR | `#991B1B` |
| Abrasion | ABR | `#D97706` |

**Scale of interactivity:**

32 adult teeth x 5 surfaces each = 160 interactive crown surface elements, plus 32 root elements, plus condition overlay elements. Total interactive DOM elements: 200+.

**Device targets:**

- Tablets are the primary clinical device (iPad, Samsung Galaxy Tab). Touch targets must meet the 44x44px minimum (WCAG 2.1 guideline 2.5.5).
- Desktop monitors for administrative review.
- Must be printable to paper and exportable to PDF without quality loss.
- Must remain performant during rapid clinical input (e.g., a dentist tapping through all teeth in sequence during a full-mouth charting).

**Accessibility:**

- ARIA labels for each tooth (e.g., "Tooth 36, lower left first molar") and each surface condition.
- Screen reader support for clinical condition announcements.
- Keyboard navigation between teeth.

### Evaluation Criteria

We evaluated rendering approaches against five criteria:

1. **Vector precision:** Can it render at any zoom level without pixelation?
2. **DOM interactivity:** Can individual surfaces receive click/touch events and React state?
3. **Print fidelity:** Does it render cleanly to PDF/paper without rasterization?
4. **Accessibility:** Can it produce semantic, screen-reader-compatible markup?
5. **Performance:** Can it handle 200+ interactive elements at 60fps on a mid-range tablet?

---

## Decision

We will render the odontogram using **inline SVG with React components**. Each tooth is a composite SVG `<g>` (group) element containing individual `<path>` elements for each surface, condition overlays as additional SVG elements (circles for crowns, lines for root canals, X marks for missing teeth), and transparent hit-area `<rect>` elements for touch targets.

The SVG uses a `viewBox` attribute for resolution-independent scaling. The entire odontogram is a single `<svg>` element that scales responsively within its container using CSS `width: 100%; height: auto;`.

### Component Architecture

```
<OdontogramCanvas>               -- Top-level SVG with viewBox
  <OdontogramLayout>             -- Classic or Anatomic positioning logic
    <ToothGroup tooth={11}>      -- SVG <g> per tooth, positioned by layout
      <ToothCrown>               -- 5 surface <path> elements
        <Surface surface="O" />  -- Oclusal path with condition fill
        <Surface surface="M" />  -- Mesial path
        <Surface surface="D" />  -- Distal path
        <Surface surface="V" />  -- Vestibular path
        <Surface surface="L" />  -- Lingual path
      </ToothCrown>
      <ToothRoot />              -- Root SVG element(s)
      <ConditionOverlay />       -- Visual indicator for whole-tooth conditions
      <ToothLabel />             -- FDI number text element
      <ToothHitArea />           -- Invisible rect for touch target (44px min)
    </ToothGroup>
    ... (32 teeth)
  </OdontogramLayout>
</OdontogramCanvas>
```

### React Memoization Strategy

Each `<ToothGroup>` component is wrapped in `React.memo` with a custom comparator that checks only the tooth's condition state, selected state, and hover state. This ensures that when a dentist modifies one tooth's condition, only that tooth re-renders -- not all 32.

```tsx
const ToothGroup = React.memo(
  ({ toothNumber, conditions, isSelected, onSurfaceClick, onContextMenu }) => {
    // Render SVG group for this tooth
  },
  (prev, next) =>
    prev.toothNumber === next.toothNumber &&
    prev.isSelected === next.isSelected &&
    shallowEqual(prev.conditions, next.conditions)
);
```

The parent `<OdontogramCanvas>` manages state for all 32 teeth via a `useReducer` hook with a flat state shape:

```tsx
type OdontogramState = Record<ToothNumber, ToothConditions>;

// Actions dispatched per surface click
type OdontogramAction =
  | { type: 'SET_SURFACE_CONDITION'; tooth: ToothNumber; surface: SurfaceCode; condition: ConditionCode }
  | { type: 'SET_WHOLE_TOOTH_CONDITION'; tooth: ToothNumber; condition: ConditionCode }
  | { type: 'CLEAR_TOOTH'; tooth: ToothNumber }
  | { type: 'LOAD_ODONTOGRAM'; data: OdontogramState };
```

### Event Handling

- **Left click on a surface:** Opens the condition selector popover anchored to that surface. The selected condition is applied immediately with optimistic UI.
- **Right click (long press on tablet) on a tooth:** Opens a context menu with options: apply whole-tooth condition, clear all conditions, view tooth history, add note.
- **Hover (desktop only):** Highlights the surface and shows a tooltip with the current condition name and date last modified.
- **Keyboard navigation:** Arrow keys move between teeth in FDI order. Enter opens the condition selector. Escape closes it.

### Print and PDF Rendering

SVG renders natively to PDF via the browser's print stylesheet without rasterization artifacts. The print stylesheet:

- Hides interactive elements (hit areas, hover indicators, selection outlines).
- Ensures condition colors print correctly by using `@media print` overrides with `-webkit-print-color-adjust: exact`.
- Adds a border and patient header information above the odontogram.
- Renders at the SVG's intrinsic viewBox resolution, producing crisp vector output at any DPI.

For server-side PDF generation (treatment plan documents), the SVG markup is passed to Playwright headless Chromium or embedded directly in the PDF template as inline SVG.

### ARIA Accessibility

```xml
<g role="img" aria-label="Tooth 36 - Lower left first molar">
  <path
    role="button"
    aria-label="Oclusal surface - Caries"
    tabindex="0"
    d="M..."
    fill="#EF4444"
  />
  <!-- ... other surfaces ... -->
</g>
```

Each tooth group has a descriptive `aria-label` with the FDI number and tooth name in the tenant's locale. Each surface path has a `role="button"` with an `aria-label` describing the surface name and current condition. `tabindex` enables keyboard focus traversal.

### Touch Target Compliance

Each tooth's hit area is enforced at a minimum of 44x44 CSS pixels through invisible `<rect>` elements overlaying each surface path. On tablet viewports where the SVG scales smaller, the hit areas expand proportionally using `pointer-events: all` on the invisible rects while the visual paths remain at their designed proportions.

---

## Alternatives Considered

### Alternative 1: HTML/CSS Div-based Rendering

Each tooth would be a `<div>` with CSS-positioned child divs for surfaces, using `clip-path` or `border-radius` for shapes.

**Why rejected:**

- CSS cannot produce the complex geometric shapes required for anatomically accurate tooth surface paths (especially the Anatomic layout mode). Clip-paths are limited and non-interactive.
- Printing fidelity suffers -- CSS `clip-path` and `border-radius` rendering varies across print engines.
- No resolution independence. Div dimensions are pixel-based; scaling requires media queries and recalculation.
- Accessibility is actually easier (native HTML semantics), but this advantage does not outweigh the rendering limitations.

### Alternative 2: HTML5 Canvas (2D Context)

Render the entire odontogram as a bitmap on a `<canvas>` element using `CanvasRenderingContext2D`.

**Why rejected:**

- Canvas is a single bitmap surface. Individual surface hit detection requires manual coordinate math (point-in-polygon tests) rather than native DOM events.
- No DOM nodes for surfaces means no native React state binding, no ARIA labels, no `tabindex` focus management.
- Canvas output is rasterized -- scaling up produces pixelation, and printing requires re-rendering at the target DPI.
- Canvas excels for data visualization with thousands of elements (charts, graphs) but is overkill for 200 interactive elements where DOM event handling is more natural.

### Alternative 3: WebGL (Three.js / react-three-fiber)

Render the odontogram as a 3D or hardware-accelerated 2D scene.

**Why rejected:**

- Extreme overkill for a 2D dental chart. WebGL introduces GPU driver dependencies, shader compilation overhead, and a much larger bundle size.
- WebGL has no native DOM accessibility. All ARIA labels and keyboard navigation would need to be implemented as HTML overlays on top of the GL canvas.
- Printing a WebGL scene requires capturing a rasterized screenshot, which loses vector fidelity.
- Development complexity is 5-10x higher for the same visual result. The dental odontogram does not require 3D rendering, particle effects, or GPU-intensive computations.

---

## Consequences

### Positive

- **Pixel-perfect at any zoom level.** SVG `viewBox` provides resolution independence. A dentist zooming in on a specific quadrant on their tablet sees crisp lines and fills at any magnification.
- **Native DOM interactivity.** Each SVG element is a DOM node. Click events, hover events, React state, and ARIA attributes work exactly like HTML elements. No coordinate math needed for hit detection.
- **Print and PDF fidelity.** SVG is a vector format. Printing to paper or exporting to PDF preserves full visual quality without rasterization. This is critical for clinical documentation that may be printed and filed.
- **React integration.** Inline SVG in JSX is first-class in React. Each tooth component manages its own state. React's reconciliation engine efficiently updates only the changed surfaces.
- **Accessibility.** SVG elements support `role`, `aria-label`, `tabindex`, and focus events. The odontogram can be navigated by keyboard and announced by screen readers -- a requirement for accessibility compliance.
- **Dual layout support.** Switching between Classic (grid) and Anatomic (arch) layouts is a matter of changing the `transform` attributes on each `<ToothGroup>` element. The tooth SVG paths themselves are identical in both modes.

### Negative

- **DOM element count.** 32 teeth x ~8 SVG elements each (5 surfaces + root + overlay + label) = ~256 DOM nodes for the odontogram alone. On low-end Android tablets, this requires careful performance optimization. Mitigated by `React.memo` per tooth and avoiding unnecessary re-renders.
- **SVG path authoring complexity.** The surface path `d` attributes (Bezier curves defining each surface shape) must be hand-crafted or exported from a design tool (Figma/Illustrator). This is a one-time upfront cost, but changes to tooth geometry require updating path data.
- **No built-in animation framework.** SVG animations (for highlighting, selection effects) require CSS transitions or a library like Framer Motion. This is manageable but adds a dependency.
- **Touch target overlapping.** On small screens, adjacent surface hit areas may overlap. Requires careful z-index management of invisible hit-area rects and potentially a "zoomed tooth" detail view for precise surface selection on phones.

### Neutral

- **Bundle size impact.** Inline SVG path data for 32 teeth adds approximately 15-25 KB to the component bundle (uncompressed). This is negligible compared to the React runtime itself.
- **Server-side rendering.** SVG can be server-rendered by Next.js/React SSR if needed in the future, unlike Canvas or WebGL which require a browser environment.
- **Testing.** SVG components can be tested with React Testing Library using standard DOM queries (`getByRole`, `getByLabelText`). Snapshot tests capture the rendered SVG markup for regression detection.
- **Mixed dentition.** The same SVG component architecture supports pediatric teeth (quadrants 5-8) by swapping the tooth path data and adjusting layout positions. No architectural change needed.

---

## References

- [SVG 2 Specification (W3C)](https://www.w3.org/TR/SVG2/)
- [WCAG 2.1 Target Size (2.5.5)](https://www.w3.org/WAI/WCAG21/Understanding/target-size.html) -- 44x44px minimum touch targets
- [React.memo API](https://react.dev/reference/react/memo) -- Memoization for performance
- [WAI-ARIA Graphics Module](https://www.w3.org/TR/graphics-aria-1.0/) -- ARIA roles for SVG
- DentalOS `infra/design-system.md` -- Clinical condition color palette (Section 1.3)
- DentalOS `DOMAIN-GLOSSARY.md` -- FDI notation, surface codes, condition codes
- DentalOS `ADR-LOG.md` -- ADR-005 summary
