/**
 * Precomputed arch positions for 32 adult teeth in a 520x620 SVG viewBox.
 *
 * Upper arch: U-curve with teeth 18->11, 21->28 (crown facing mouth, roots toward palate).
 * Lower arch: inverted U with teeth 48->41, 31->38 (crown facing mouth, roots toward chin).
 * 80px mouth gap between arches simulates a slightly open mouth.
 *
 * Tooth sizes follow the Notion anatomic design spec:
 *   Incisor:  18x28, 1 root
 *   Canine:   20x32, 1 root
 *   Premolar: 24x28, 2 roots
 *   Molar:    28x30, 3 roots
 *
 * Rotation rules:
 *   - 3 edge teeth per side (i < 3 || i >= total - 3): angle = 0 (vertical)
 *   - Central teeth: angle = arcTangent * 0.25 (subtle rotation)
 *
 * Also exports TOOTH_NAMES_ES with full Spanish tooth names for tooltip labels.
 */

// ─── Types ────────────────────────────────────────────────────────────────────

/** Anatomic tooth type classification */
export type ToothType = "incisor" | "canine" | "premolar" | "molar";

export interface ToothArchPosition {
  toothNumber: number;
  /** Center x in 520x620 SVG viewBox */
  cx: number;
  /** Center y in 520x620 SVG viewBox */
  cy: number;
  /** Rotation angle (degrees) — 0 for edge teeth, subtle for central */
  angle: number;
  arch: "upper" | "lower";
  /** Width varies by tooth type (from Notion spec) */
  width: number;
  /** Height varies by tooth type (from Notion spec) */
  height: number;
  /** Anatomic tooth classification */
  toothType: ToothType;
  /** Number of roots (1 for incisors/canines, 2 for premolars, 3 for molars) */
  rootCount: number;
}

// ─── Tooth type classification ───────────────────────────────────────────────

interface ToothTypeInfo {
  type: ToothType;
  width: number;
  height: number;
  rootCount: number;
}

/** Tooth sizes from the Notion anatomic design spec */
const TOOTH_TYPE_INFO: Record<ToothType, Omit<ToothTypeInfo, "type">> = {
  incisor: { width: 18, height: 28, rootCount: 1 },
  canine: { width: 20, height: 32, rootCount: 1 },
  premolar: { width: 24, height: 28, rootCount: 2 },
  molar: { width: 28, height: 30, rootCount: 3 },
};

/**
 * Determine the tooth type from the FDI tooth number.
 * The last digit of the FDI number indicates position within quadrant:
 *   1,2 = incisors | 3 = canine | 4,5 = premolars | 6,7,8 = molars
 */
function getToothTypeInfo(toothNumber: number): ToothTypeInfo {
  const digit = toothNumber % 10;
  let toothType: ToothType;

  switch (digit) {
    case 1:
    case 2:
      toothType = "incisor";
      break;
    case 3:
      toothType = "canine";
      break;
    case 4:
    case 5:
      toothType = "premolar";
      break;
    case 6:
    case 7:
    case 8:
      toothType = "molar";
      break;
    default:
      toothType = "molar";
  }

  const info = TOOTH_TYPE_INFO[toothType];
  return {
    type: toothType,
    width: info.width,
    height: info.height,
    rootCount: info.rootCount,
  };
}

// ─── ViewBox and arch geometry constants ─────────────────────────────────────

/** SVG viewBox dimensions */
const VIEWBOX_WIDTH = 520;
const VIEWBOX_HEIGHT = 620;

/** Horizontal center of the viewBox */
const CENTER_X = VIEWBOX_WIDTH / 2; // 260

/** Gap between upper and lower arches (simulates mouth slightly open) */
const MOUTH_GAP = 80;

/**
 * Upper arch: U-curve opening downward.
 * Center of the ellipse is near the top of the viewBox.
 * Teeth sit along the lower half of the ellipse.
 */
const UPPER_CENTER_Y = 100;
const UPPER_RX = 210; // horizontal radius of the upper arch ellipse
const UPPER_RY = 150; // vertical radius of the upper arch ellipse

/**
 * Lower arch: inverted U-curve opening upward.
 * Positioned below the upper arch with the mouth gap.
 * Lower arches are typically slightly narrower than upper.
 */
const LOWER_CENTER_Y = VIEWBOX_HEIGHT - 100; // 520
const LOWER_RX = 195; // slightly narrower than upper
const LOWER_RY = 140;

// ─── Arch position computation ───────────────────────────────────────────────

/**
 * Compute positions for one quadrant of teeth along a half-ellipse.
 *
 * The teeth array is ordered from the wisdom tooth (outermost) to
 * the central incisor (innermost, near the center line).
 *
 * Angles sweep from the horizontal edge inward toward the vertical center:
 *   - Right side (Q1/Q4): from small angle to ~90 degrees
 *   - Left side is mirrored after computation
 *
 * Rotation rules from the Notion spec:
 *   - Edge teeth (first 3 and last 3 in the quadrant): angle = 0
 *   - Central teeth: angle = arcTangent * 0.25 (subtle rotation for aesthetics)
 */
function computeQuadrantPositions(
  teeth: number[],
  centerX: number,
  centerY: number,
  radiusX: number,
  radiusY: number,
  arch: "upper" | "lower",
): ToothArchPosition[] {
  const positions: ToothArchPosition[] = [];
  const count = teeth.length; // 8 teeth per quadrant

  // Sweep angles from the horizontal edge toward vertical center.
  // Start at ~10 degrees (near horizontal) and go to ~85 degrees (near vertical center).
  const startAngleDeg = 10;
  const endAngleDeg = 85;

  for (let i = 0; i < count; i++) {
    // Distribute teeth evenly along the arc
    const t = count > 1 ? i / (count - 1) : 0.5;
    const angleDeg = startAngleDeg + t * (endAngleDeg - startAngleDeg);
    const angleRad = (angleDeg * Math.PI) / 180;

    const typeInfo = getToothTypeInfo(teeth[i]);

    // Position on the right side of the ellipse
    const px = centerX + radiusX * Math.cos(angleRad);
    const py =
      arch === "upper"
        ? centerY + radiusY * Math.sin(angleRad) // U-curve: teeth hang below center
        : centerY - radiusY * Math.sin(angleRad); // Inverted U: teeth rise above center

    // Compute the tangent angle at this point on the ellipse.
    // The tangent direction of an ellipse at angle theta is:
    //   dx/dtheta = -radiusX * sin(theta)
    //   dy/dtheta = radiusY * cos(theta)  (upper) or -radiusY * cos(theta) (lower)
    const tangentX = -radiusX * Math.sin(angleRad);
    const tangentY =
      arch === "upper"
        ? radiusY * Math.cos(angleRad)
        : -radiusY * Math.cos(angleRad);
    const tangentAngleDeg = (Math.atan2(tangentY, tangentX) * 180) / Math.PI;

    // Convert tangent to a rotation relative to vertical (0 = upright)
    const rawRotation = tangentAngleDeg - 90;

    // Apply rotation rules from the Notion spec:
    //   - Edge teeth (i < 3 or i >= count - 3): angle = 0 for readability
    //   - Central teeth: subtle rotation (25% of arc tangent)
    const isEdgeTooth = i < 3 || i >= count - 3;
    const rotation = isEdgeTooth ? 0 : rawRotation * 0.25;

    positions.push({
      toothNumber: teeth[i],
      cx: px,
      cy: py,
      angle: rotation,
      arch,
      width: typeInfo.width,
      height: typeInfo.height,
      toothType: typeInfo.type,
      rootCount: typeInfo.rootCount,
    });
  }

  return positions;
}

// ─── Quadrant tooth arrays (ordered from wisdom to central incisor) ──────────

/** Q1: Upper right — wisdom (18) to central incisor (11) */
const Q1_TEETH = [18, 17, 16, 15, 14, 13, 12, 11];

/** Q2: Upper left — central incisor (21) to wisdom (28) */
const Q2_TEETH = [21, 22, 23, 24, 25, 26, 27, 28];

/** Q4: Lower right — wisdom (48) to central incisor (41) */
const Q4_TEETH = [48, 47, 46, 45, 44, 43, 42, 41];

/** Q3: Lower left — central incisor (31) to wisdom (38) */
const Q3_TEETH = [31, 32, 33, 34, 35, 36, 37, 38];

// ─── Build all 32 positions ──────────────────────────────────────────────────

function buildArchPositions(): ToothArchPosition[] {
  const positions: ToothArchPosition[] = [];

  // Q1: Upper right — compute directly (right side of upper arch)
  const q1 = computeQuadrantPositions(
    Q1_TEETH,
    CENTER_X,
    UPPER_CENTER_Y,
    UPPER_RX,
    UPPER_RY,
    "upper",
  );
  positions.push(...q1);

  // Q2: Upper left — compute as right side, then mirror across centerX
  const q2Base = computeQuadrantPositions(
    Q2_TEETH,
    CENTER_X,
    UPPER_CENTER_Y,
    UPPER_RX,
    UPPER_RY,
    "upper",
  );
  for (const pos of q2Base) {
    positions.push({
      ...pos,
      cx: 2 * CENTER_X - pos.cx, // mirror horizontally
      angle: -pos.angle, // mirror rotation
    });
  }

  // Q4: Lower right — compute directly (right side of lower arch)
  const q4 = computeQuadrantPositions(
    Q4_TEETH,
    CENTER_X,
    LOWER_CENTER_Y,
    LOWER_RX,
    LOWER_RY,
    "lower",
  );
  positions.push(...q4);

  // Q3: Lower left — compute as right side, then mirror across centerX
  const q3Base = computeQuadrantPositions(
    Q3_TEETH,
    CENTER_X,
    LOWER_CENTER_Y,
    LOWER_RX,
    LOWER_RY,
    "lower",
  );
  for (const pos of q3Base) {
    positions.push({
      ...pos,
      cx: 2 * CENTER_X - pos.cx, // mirror horizontally
      angle: -pos.angle, // mirror rotation
    });
  }

  return positions;
}

/** All 32 precomputed adult tooth positions for the anatomic arch view */
export const TOOTH_ARCH_POSITIONS: readonly ToothArchPosition[] =
  buildArchPositions();

/** Quick lookup: tooth number -> arch position */
export const TOOTH_POSITION_MAP: ReadonlyMap<number, ToothArchPosition> =
  new Map(TOOTH_ARCH_POSITIONS.map((p) => [p.toothNumber, p]));

// ─── Arch geometry exports (used by the SVG component for guide curves) ──────

export const ARCH_GEOMETRY = {
  viewBoxWidth: VIEWBOX_WIDTH,
  viewBoxHeight: VIEWBOX_HEIGHT,
  centerX: CENTER_X,
  mouthGap: MOUTH_GAP,
  upper: {
    centerY: UPPER_CENTER_Y,
    rx: UPPER_RX,
    ry: UPPER_RY,
  },
  lower: {
    centerY: LOWER_CENTER_Y,
    rx: LOWER_RX,
    ry: LOWER_RY,
  },
} as const;

// ─── Spanish tooth names ─────────────────────────────────────────────────────

export const TOOTH_NAMES_ES: Record<number, string> = {
  // Q1 — Upper right
  11: "Incisivo central superior derecho",
  12: "Incisivo lateral superior derecho",
  13: "Canino superior derecho",
  14: "Primer premolar superior derecho",
  15: "Segundo premolar superior derecho",
  16: "Primer molar superior derecho",
  17: "Segundo molar superior derecho",
  18: "Tercer molar superior derecho",

  // Q2 — Upper left
  21: "Incisivo central superior izquierdo",
  22: "Incisivo lateral superior izquierdo",
  23: "Canino superior izquierdo",
  24: "Primer premolar superior izquierdo",
  25: "Segundo premolar superior izquierdo",
  26: "Primer molar superior izquierdo",
  27: "Segundo molar superior izquierdo",
  28: "Tercer molar superior izquierdo",

  // Q3 — Lower left
  31: "Incisivo central inferior izquierdo",
  32: "Incisivo lateral inferior izquierdo",
  33: "Canino inferior izquierdo",
  34: "Primer premolar inferior izquierdo",
  35: "Segundo premolar inferior izquierdo",
  36: "Primer molar inferior izquierdo",
  37: "Segundo molar inferior izquierdo",
  38: "Tercer molar inferior izquierdo",

  // Q4 — Lower right
  41: "Incisivo central inferior derecho",
  42: "Incisivo lateral inferior derecho",
  43: "Canino inferior derecho",
  44: "Primer premolar inferior derecho",
  45: "Segundo premolar inferior derecho",
  46: "Primer molar inferior derecho",
  47: "Segundo molar inferior derecho",
  48: "Tercer molar inferior derecho",
};
