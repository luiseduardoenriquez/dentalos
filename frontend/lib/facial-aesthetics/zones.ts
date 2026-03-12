/**
 * Facial aesthetics zone catalog — ~28 zones for face_front diagram.
 *
 * Each zone has:
 * - id: unique identifier matching backend zone_id
 * - label: Spanish display name
 * - x, y: normalized SVG coordinates (0–1, mapped to viewBox 0 0 400 560)
 * - group: anatomical grouping for UI organization
 */

export interface FacialZone {
  id: string;
  label: string;
  x: number;
  y: number;
  group: string;
}

export const FACIAL_ZONES: FacialZone[] = [
  // Forehead
  { id: "forehead_left", label: "Frente izquierda", x: 0.35, y: 0.1, group: "forehead" },
  { id: "forehead_center", label: "Frente centro", x: 0.5, y: 0.08, group: "forehead" },
  { id: "forehead_right", label: "Frente derecha", x: 0.65, y: 0.1, group: "forehead" },
  { id: "glabella", label: "Glabela", x: 0.5, y: 0.16, group: "forehead" },

  // Temporal
  { id: "temporal_left", label: "Temporal izquierdo", x: 0.2, y: 0.18, group: "temporal" },
  { id: "temporal_right", label: "Temporal derecho", x: 0.8, y: 0.18, group: "temporal" },

  // Periorbital
  { id: "periorbital_left", label: "Periorbital izquierdo", x: 0.32, y: 0.24, group: "periorbital" },
  { id: "periorbital_right", label: "Periorbital derecho", x: 0.68, y: 0.24, group: "periorbital" },

  // Infraorbital
  { id: "infraorbital_left", label: "Infraorbital izquierdo", x: 0.35, y: 0.32, group: "infraorbital" },
  { id: "infraorbital_right", label: "Infraorbital derecho", x: 0.65, y: 0.32, group: "infraorbital" },

  // Nose
  { id: "nose_bridge", label: "Puente nasal", x: 0.5, y: 0.3, group: "nose" },
  { id: "nose_tip", label: "Punta nasal", x: 0.5, y: 0.4, group: "nose" },

  // Nasolabial
  { id: "nasolabial_left", label: "Surco nasogeniano izq.", x: 0.38, y: 0.46, group: "nasolabial" },
  { id: "nasolabial_right", label: "Surco nasogeniano der.", x: 0.62, y: 0.46, group: "nasolabial" },

  // Cheeks
  { id: "cheek_left", label: "Mejilla izquierda", x: 0.28, y: 0.42, group: "cheek" },
  { id: "cheek_right", label: "Mejilla derecha", x: 0.72, y: 0.42, group: "cheek" },

  // Lips
  { id: "lip_upper", label: "Labio superior", x: 0.5, y: 0.51, group: "lips" },
  { id: "lip_lower", label: "Labio inferior", x: 0.5, y: 0.57, group: "lips" },

  // Marionette
  { id: "marionette_left", label: "Línea marioneta izq.", x: 0.4, y: 0.6, group: "marionette" },
  { id: "marionette_right", label: "Línea marioneta der.", x: 0.6, y: 0.6, group: "marionette" },

  // Masseter
  { id: "masseter_left", label: "Masetero izquierdo", x: 0.22, y: 0.52, group: "masseter" },
  { id: "masseter_right", label: "Masetero derecho", x: 0.78, y: 0.52, group: "masseter" },

  // Chin
  { id: "chin", label: "Mentón", x: 0.5, y: 0.66, group: "chin" },

  // Jaw
  { id: "jaw_left", label: "Mandíbula izquierda", x: 0.28, y: 0.62, group: "jaw" },
  { id: "jaw_right", label: "Mandíbula derecha", x: 0.72, y: 0.62, group: "jaw" },

  // Neck
  { id: "neck_left", label: "Cuello izquierdo", x: 0.38, y: 0.78, group: "neck" },
  { id: "neck_center", label: "Cuello centro", x: 0.5, y: 0.78, group: "neck" },
  { id: "neck_right", label: "Cuello derecho", x: 0.62, y: 0.78, group: "neck" },
];

export const ZONES_BY_ID = new Map(FACIAL_ZONES.map((z) => [z.id, z]));

/**
 * Injection type color mapping.
 * BTX=blue, HA=pink, CaHA=purple, PLA=green, PRF=amber, other=gray
 */
export const INJECTION_TYPE_COLORS: Record<string, string> = {
  botulinum_toxin: "#3B82F6",
  hyaluronic_acid: "#EC4899",
  calcium_hydroxylapatite: "#8B5CF6",
  poly_lactic_acid: "#22C55E",
  prf: "#F59E0B",
  other: "#6B7280",
};

export const INJECTION_TYPE_LABELS: Record<string, string> = {
  botulinum_toxin: "Toxina botulínica",
  hyaluronic_acid: "Ácido hialurónico",
  calcium_hydroxylapatite: "Hidroxiapatita de calcio",
  poly_lactic_acid: "Ácido poliláctico",
  prf: "PRF",
  other: "Otro",
};

export const DEPTH_LABELS: Record<string, string> = {
  intradermal: "Intradérmica",
  subcutaneous: "Subcutánea",
  supraperiosteal: "Supraperióstica",
  intramuscular: "Intramuscular",
};
