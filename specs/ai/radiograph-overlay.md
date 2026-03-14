# AI Radiograph Overlay (Visual) — Spec (AI-12)

> **Spec ID:** AI-12
> **Status:** Draft
> **Last Updated:** 2026-03-14
> **Feature Flag:** `ai_radiograph_overlay`
> **Add-on:** AI Radiograph ($20/doctor/mo) — bundled with Radiograph Analysis (AI-01)
> **Sprint:** S39-40 (Tier 3 — Leapfrog)
> **Priority:** Medium-High
> **Depends on:** AI-01 (`specs/ai/radiograph-analysis.md`) — must be completed first

---

## 1. Overview

**Feature:** After the AI Radiograph Analysis (AI-01) produces findings, the overlay feature renders color-coded bounding boxes and semi-transparent highlight regions directly on the radiograph image inside the browser. Each finding type has a distinct color. Overlays are toggle-able per finding category — the doctor can isolate caries findings, for example, by hiding all others.

Hovering over a bounding box shows a tooltip with finding details (tooth FDI, severity, confidence, AI-01 finding ID). Clicking a bounding box opens the corresponding finding in the review panel.

**Client-side rendering:** All overlay drawing is done in the browser using HTML Canvas API. No server round-trip for rendering. The backend only serves the bounding box coordinates as part of the AI-01 findings data.

**Regulatory disclaimer (persistent, below image):**
> "Los hallazgos son sugerencias de IA. El diagnóstico final es responsabilidad del profesional."

### Dependencies

- `specs/ai/radiograph-analysis.md` (AI-01) — Source of findings data
- `backend/app/models/tenant/radiograph_analysis.py` — `radiograph_analyses` table
- `frontend/components/clinical/radiograph-viewer.tsx` — Host component (existing)

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Frontend: RadiographViewerWithOverlay                           │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  <img> — radiograph image (loaded from signed S3 URL)  │    │
│  │  <canvas> — positioned absolute, same dimensions       │    │
│  │    ├── Bounding boxes (stroke only, 2px)               │    │
│  │    └── Semi-transparent fills (opacity 0.25)           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Toggle controls: [✓ Caries] [✓ Pérdida ósea] [✓ Restauración] │
│                   [✓ Periapical] [✓ Sano]                       │
│                                                                  │
│  Hover tooltip: Tooth 16 | Caries proximal | Severidad: media   │
└──────────────────────────────────────────────────────────────────┘
```

**No server-side image processing.** The backend provides normalized coordinates (0.0–1.0 relative to image dimensions). The canvas scales them to actual pixel positions at render time.

---

## 3. Overlay Data Format

### Extension to AI-01 `findings` JSONB

Each finding object in `radiograph_analyses.findings` gains an optional `overlay` sub-object:

```json
{
  "finding_id": "uuid",
  "tooth_fdi": 16,
  "finding_type": "caries",
  "location": "proximal",
  "severity": "medium",
  "confidence": 0.89,
  "accepted": true,
  "overlay": {
    "bounding_box": {
      "x": 0.312,
      "y": 0.445,
      "width": 0.058,
      "height": 0.042
    },
    "region_polygon": [
      [0.315, 0.448],
      [0.368, 0.448],
      [0.370, 0.486],
      [0.312, 0.487]
    ],
    "overlay_type": "bounding_box"
  }
}
```

- `bounding_box`: normalized coordinates (0.0–1.0 relative to image width/height). `x`, `y` = top-left corner.
- `region_polygon`: optional freeform polygon for non-rectangular findings (bone loss, etc.).
- `overlay_type`: `"bounding_box"` | `"polygon"` | `"none"` (if Claude did not locate a specific region).

### `overlay_type: "none"` behavior

Findings with `overlay_type: "none"` appear in the finding list panel but draw no box on the canvas. The toggle controls exclude them from the count.

---

## 4. API Changes (Extends AI-01)

### No new endpoints.

The existing AI-01 endpoints are extended:

**`GET /api/v1/radiograph-analyses/{id}`** — Response now includes `overlay` objects inside each `findings` element when `ai_radiograph_overlay` feature flag is active.

**Worker change (`clinical` worker, `radiograph_analyze` job):**

The Claude Vision prompt is extended to request bounding box coordinates alongside findings. When the feature flag is active for the tenant, the worker requests normalized coordinates in the structured output. When the flag is inactive, the `overlay` field is omitted from the response.

### Updated Claude prompt (worker, AI-01 extension)

Add to the existing AI-01 system prompt:

```
Additionally, for each finding, provide a bounding_box with normalized coordinates
(x, y, width, height) as floats 0.0-1.0 relative to the image dimensions,
where (0,0) is the top-left corner. If you cannot localize the finding to
a specific region, set overlay_type to "none".

Include "overlay": {"bounding_box": {...}, "overlay_type": "bounding_box"} in each finding.
```

### Response schema addition

```python
class FindingOverlay(BaseModel):
    bounding_box: dict[str, float] | None = None  # x, y, width, height
    region_polygon: list[list[float]] | None = None
    overlay_type: Literal["bounding_box", "polygon", "none"] = "none"

class RadiographFinding(BaseModel):
    # ... existing fields ...
    overlay: FindingOverlay | None = None
```

---

## 5. Color Scheme

| Finding type | Color (hex) | Stroke | Fill opacity |
|-------------|-------------|--------|-------------|
| `caries` | `#EF4444` (red-500) | 2px solid | 0.20 |
| `bone_loss` | `#F59E0B` (amber-500) | 2px solid | 0.18 |
| `restoration` | `#3B82F6` (blue-500) | 2px dashed | 0.15 |
| `healthy` | `#22C55E` (green-500) | 2px solid | 0.12 |
| `periapical_lesion` | `#F97316` (orange-500) | 2px solid | 0.22 |
| `calculus` | `#A855F7` (purple-500) | 2px dotted | 0.15 |
| `impacted_tooth` | `#06B6D4` (cyan-500) | 2px solid | 0.18 |
| `root_fragment` | `#EC4899` (pink-500) | 2px solid | 0.20 |

Colors chosen for colorblind accessibility (deuteranopia): red/blue/orange/cyan combination avoids pure red/green confusion.

---

## 6. Frontend Component

**Component:** `RadiographOverlayCanvas`

**Location:** `frontend/components/clinical/radiograph-overlay-canvas.tsx`

### Component Interface

```typescript
interface RadiographOverlayCanvasProps {
  imageUrl: string;            // Signed S3 URL
  findings: RadiographFinding[];
  activeTypes: FindingType[];  // Which overlay types are toggled on
  onFindingClick: (findingId: string) => void;
  onFindingHover: (findingId: string | null) => void;
}
```

### Rendering Logic

```typescript
// On image load or findings change:
function drawOverlays(canvas: HTMLCanvasElement, image: HTMLImageElement, findings: RadiographFinding[], activeTypes: FindingType[]) {
  const ctx = canvas.getContext('2d');
  canvas.width = image.naturalWidth;
  canvas.height = image.naturalHeight;

  findings
    .filter(f => f.overlay?.overlay_type !== 'none' && activeTypes.includes(f.finding_type))
    .forEach(finding => {
      const { x, y, width, height } = finding.overlay!.bounding_box!;
      const px = x * canvas.width;
      const py = y * canvas.height;
      const pw = width * canvas.width;
      const ph = height * canvas.height;

      const color = FINDING_COLORS[finding.finding_type];
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.fillStyle = color + '33'; // Hex alpha for 0.20 opacity

      ctx.fillRect(px, py, pw, ph);
      ctx.strokeRect(px, py, pw, ph);
    });
}
```

### Toggle Controls

```typescript
interface OverlayToggleBarProps {
  findings: RadiographFinding[];
  activeTypes: FindingType[];
  onChange: (activeTypes: FindingType[]) => void;
}
```

Renders one toggle pill per finding type that has at least one overlay. Inactive types are grayed out. Each pill shows the type label in Spanish and the count of findings:

```
[● Caries (3)] [○ Pérdida ósea (1)] [● Restauraciones (2)] [○ Periapical (0)]
```

### Tooltip

Rendered as an absolutely-positioned `div` that follows mouse position within the canvas bounds:

```
┌───────────────────────────────┐
│  Diente 16                    │
│  Caries proximal              │
│  Severidad: Media             │
│  Confianza: 89%               │
│  [Ver en panel de hallazgos]  │
└───────────────────────────────┘
```

### Interactions

| Action | Result |
|--------|--------|
| Toggle finding type | Redraw canvas with updated active types |
| Hover over bounding box | Show tooltip with finding details |
| Click bounding box | Scroll finding panel to that finding, highlight it |
| Click image outside any box | Dismiss tooltip |
| Image zoom (pinch/scroll) | Canvas scales proportionally (CSS transform, no redraw needed) |

---

## 7. Test Plan

| # | Scenario | Expected |
|---|----------|----------|
| T1 | AI-01 analysis with overlay coords returned | Boxes drawn at correct positions on canvas |
| T2 | Finding with `overlay_type: "none"` | No box drawn; finding still appears in list panel |
| T3 | Toggle off "Caries" | Red bounding boxes disappear, others remain |
| T4 | Toggle all off | Canvas clears completely |
| T5 | Hover over bounding box | Tooltip shows correct tooth, type, severity, confidence |
| T6 | Click bounding box | Finding panel scrolls to and highlights that finding |
| T7 | Feature flag `ai_radiograph_overlay` disabled | `overlay` field absent from API response; no toggle controls shown |
| T8 | Image dimensions 1200×800, coord x=0.5 y=0.5 | Box drawn at pixel (600, 400) |
| T9 | Two overlapping findings | Both boxes drawn; topmost is clickable first |
| T10 | AI-01 analysis with no overlay coords (old data) | Viewer renders without overlay; no JS error |
| T11 | Canvas resize on window resize | Boxes remain aligned with image content |
| T12 | Colorblind mode (future a11y) | Color scheme documented and changeable via prop |
