/**
 * Odontogram components barrel export.
 *
 * The odontogram is the core dental chart UI — a visual grid showing 32 teeth (adult)
 * in 4 quadrants, each with clickable SVG zones colored by dental conditions.
 */

export { ConditionBadge } from "./condition-badge";
export type { ConditionBadgeProps } from "./condition-badge";

export { ToothCell } from "./tooth-cell";
export type { ToothCellProps } from "./tooth-cell";

export { ToothGrid } from "./tooth-grid";
export type { ToothGridProps } from "./tooth-grid";

export { ConditionPanel } from "./condition-panel";
export type { ConditionPanelProps } from "./condition-panel";

export { HistoryPanel } from "./history-panel";
export type { HistoryPanelProps } from "./history-panel";

export { ToothDetailPanel } from "./tooth-detail-panel";
export type { ToothDetailPanelProps } from "./tooth-detail-panel";

export { OdontogramToolbar } from "./odontogram-toolbar";
export type { OdontogramToolbarProps } from "./odontogram-toolbar";
