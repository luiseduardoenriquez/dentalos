"""Odontogram constants — condition catalog, FDI tooth sets, and helpers.

This module is the single source of truth for:
  - The 12-condition catalog (codes, colors, icons, valid zones)
  - FDI numbering validation sets (adult, pediatric, anterior)
  - Zone-to-tooth morphology mapping
  - Helper functions used by services and API validation
"""

from typing import Any

# ─── Condition Catalog ────────────────────────────────────────────────────────

ODONTOGRAM_CONDITIONS: list[dict[str, Any]] = [
    {
        "code": "caries",
        "name_es": "Caries",
        "name_en": "Caries",
        "color_hex": "#D32F2F",
        "icon": "circle-dot",
        "zones": ["mesial", "distal", "vestibular", "lingual", "palatino", "oclusal", "incisal"],
        "severity_applicable": True,
    },
    {
        "code": "restoration",
        "name_es": "Restauración",
        "name_en": "Restoration",
        "color_hex": "#1565C0",
        "icon": "square-check",
        "zones": ["mesial", "distal", "vestibular", "lingual", "palatino", "oclusal", "incisal"],
        "severity_applicable": False,
    },
    {
        "code": "extraction",
        "name_es": "Extracción indicada",
        "name_en": "Extraction indicated",
        "color_hex": "#424242",
        "icon": "x-circle",
        "zones": ["full"],
        "severity_applicable": False,
    },
    {
        "code": "absent",
        "name_es": "Ausente",
        "name_en": "Absent",
        "color_hex": "#9E9E9E",
        "icon": "minus-circle",
        "zones": ["full"],
        "severity_applicable": False,
    },
    {
        "code": "crown",
        "name_es": "Corona",
        "name_en": "Crown",
        "color_hex": "#F57C00",
        "icon": "crown",
        "zones": ["full"],
        "severity_applicable": False,
    },
    {
        "code": "endodontic",
        "name_es": "Endodoncia",
        "name_en": "Endodontic treatment",
        "color_hex": "#6A1B9A",
        "icon": "activity",
        "zones": ["root", "full"],
        "severity_applicable": False,
    },
    {
        "code": "implant",
        "name_es": "Implante",
        "name_en": "Implant",
        "color_hex": "#00796B",
        "icon": "pin",
        "zones": ["full"],
        "severity_applicable": False,
    },
    {
        "code": "fracture",
        "name_es": "Fractura",
        "name_en": "Fracture",
        "color_hex": "#E91E63",
        "icon": "zap",
        "zones": ["mesial", "distal", "vestibular", "lingual", "palatino", "oclusal", "incisal", "root"],
        "severity_applicable": True,
    },
    {
        "code": "sealant",
        "name_es": "Sellante",
        "name_en": "Sealant",
        "color_hex": "#388E3C",
        "icon": "shield",
        "zones": ["oclusal", "incisal"],
        "severity_applicable": False,
    },
    {
        "code": "fluorosis",
        "name_es": "Fluorosis",
        "name_en": "Fluorosis",
        "color_hex": "#FFB300",
        "icon": "droplets",
        "zones": ["vestibular", "lingual", "palatino", "full"],
        "severity_applicable": True,
    },
    {
        "code": "temporary",
        "name_es": "Restauración temporal",
        "name_en": "Temporary restoration",
        "color_hex": "#0097A7",
        "icon": "clock",
        "zones": ["mesial", "distal", "vestibular", "lingual", "palatino", "oclusal", "incisal"],
        "severity_applicable": False,
    },
    {
        "code": "prosthesis",
        "name_es": "Prótesis",
        "name_en": "Prosthesis",
        "color_hex": "#512DA8",
        "icon": "component",
        "zones": ["full"],
        "severity_applicable": False,
    },
]

# Build lookup by code for O(1) access
_CONDITIONS_BY_CODE: dict[str, dict[str, Any]] = {c["code"]: c for c in ODONTOGRAM_CONDITIONS}

# All valid condition codes
VALID_CONDITION_CODES: frozenset[str] = frozenset(_CONDITIONS_BY_CODE.keys())

# ─── FDI Tooth Number Sets ───────────────────────────────────────────────────

# Adult (permanent) dentition — FDI quadrants 1-4
VALID_FDI_ADULT: frozenset[int] = frozenset(
    [11, 12, 13, 14, 15, 16, 17, 18]   # Upper right
    + [21, 22, 23, 24, 25, 26, 27, 28]  # Upper left
    + [31, 32, 33, 34, 35, 36, 37, 38]  # Lower left
    + [41, 42, 43, 44, 45, 46, 47, 48]  # Lower right
)

# Pediatric (primary) dentition — FDI quadrants 5-8
VALID_FDI_PEDIATRIC: frozenset[int] = frozenset(
    [51, 52, 53, 54, 55]   # Upper right
    + [61, 62, 63, 64, 65]  # Upper left
    + [71, 72, 73, 74, 75]  # Lower left
    + [81, 82, 83, 84, 85]  # Lower right
)

# All valid FDI numbers (mixed dentition = both)
VALID_FDI_ALL: frozenset[int] = VALID_FDI_ADULT | VALID_FDI_PEDIATRIC

# Anterior teeth use "incisal" zone instead of "oclusal"
ANTERIOR_TEETH: frozenset[int] = frozenset(
    # Adult incisors + canines
    [11, 12, 13, 21, 22, 23, 31, 32, 33, 41, 42, 43]
    # Pediatric incisors + canines
    + [51, 52, 53, 61, 62, 63, 71, 72, 73, 81, 82, 83]
)

# ─── Zone Definitions ────────────────────────────────────────────────────────

# Zones for posterior teeth (premolars + molars)
POSTERIOR_ZONES: tuple[str, ...] = ("mesial", "distal", "vestibular", "lingual", "oclusal", "root")

# Zones for anterior teeth (incisors + canines)
ANTERIOR_ZONES: tuple[str, ...] = ("mesial", "distal", "vestibular", "lingual", "incisal", "root")

# All valid zone values
ALL_ZONES: frozenset[str] = frozenset(
    {"mesial", "distal", "vestibular", "lingual", "palatino", "oclusal", "incisal", "root", "full"}
)

# Severity values
VALID_SEVERITIES: frozenset[str] = frozenset({"mild", "moderate", "severe"})

# Source values
VALID_SOURCES: frozenset[str] = frozenset({"manual", "voice"})

# Dentition types
VALID_DENTITION_TYPES: frozenset[str] = frozenset({"adult", "pediatric", "mixed"})

# ─── Helper Functions ────────────────────────────────────────────────────────


def get_valid_zones_for_tooth(tooth_number: int) -> tuple[str, ...]:
    """Return the valid zones for a given FDI tooth number.

    Anterior teeth (incisors/canines) use "incisal" instead of "oclusal".
    All teeth accept "full" for whole-tooth conditions and "root".
    """
    if tooth_number in ANTERIOR_TEETH:
        return ANTERIOR_ZONES
    return POSTERIOR_ZONES


def validate_tooth_for_dentition(tooth_number: int, dentition_type: str) -> bool:
    """Check if a tooth number is valid for the given dentition type.

    adult     — FDI 11-48 only
    pediatric — FDI 51-85 only
    mixed     — both adult and pediatric numbers
    """
    if dentition_type == "adult":
        return tooth_number in VALID_FDI_ADULT
    elif dentition_type == "pediatric":
        return tooth_number in VALID_FDI_PEDIATRIC
    elif dentition_type == "mixed":
        return tooth_number in VALID_FDI_ALL
    return False


def get_condition_by_code(code: str) -> dict[str, Any] | None:
    """Retrieve a condition definition by its code. Returns None if not found."""
    return _CONDITIONS_BY_CODE.get(code)


def is_zone_valid_for_condition(zone: str, condition_code: str) -> bool:
    """Check if a zone is valid for a given condition code."""
    condition = _CONDITIONS_BY_CODE.get(condition_code)
    if condition is None:
        return False
    return zone in condition["zones"]


def get_teeth_for_dentition(dentition_type: str) -> list[int]:
    """Return sorted list of tooth numbers for a dentition type."""
    if dentition_type == "adult":
        return sorted(VALID_FDI_ADULT)
    elif dentition_type == "pediatric":
        return sorted(VALID_FDI_PEDIATRIC)
    elif dentition_type == "mixed":
        return sorted(VALID_FDI_ALL)
    return []
