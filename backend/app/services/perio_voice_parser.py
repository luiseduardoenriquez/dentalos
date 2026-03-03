"""Periodontal voice utterance parser.

Converts Spanish dental voice transcripts into structured periodontal
measurement dicts suitable for PeriodontalService.bulk_update_measurements().

This is a pure regex-based parser — no IO, no DB, no model calls.
It is intentionally simple and fast for the MVP. In a future sprint,
this will be replaced with the LLM-based pipeline (voice_nlp.py).

Security invariants:
  - PHI is NEVER logged (no patient names, document numbers).
  - This module performs no database access.
  - All inputs are strings; outputs are plain dicts.

Valid perio sites (matches VALID_PERIO_SITES in schemas/periodontal.py):
  mesial_buccal, buccal, distal_buccal,
  mesial_lingual, lingual, distal_lingual

Spanish alias mapping:
  mesial bucal  -> mesial_buccal
  bucal         -> buccal
  distal bucal  -> distal_buccal
  mesial lingual -> mesial_lingual
  lingual        -> lingual
  distal lingual -> distal_lingual
  mesial         -> mesial_buccal  (default position to buccal side)
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.odontogram_constants import VALID_FDI_ALL

logger = logging.getLogger("dentalos.perio_voice_parser")

# ── Constants ─────────────────────────────────────────────────────────────────

# Site keyword aliases (Spanish -> canonical site string)
_SITE_ALIASES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bmesial\s+bucal\b", re.IGNORECASE), "mesial_buccal"),
    (re.compile(r"\bdistal\s+bucal\b", re.IGNORECASE), "distal_buccal"),
    (re.compile(r"\bbucal\b", re.IGNORECASE), "buccal"),
    (re.compile(r"\bmesial\s+lingual\b", re.IGNORECASE), "mesial_lingual"),
    (re.compile(r"\bdistal\s+lingual\b", re.IGNORECASE), "distal_lingual"),
    (re.compile(r"\blingual\b", re.IGNORECASE), "lingual"),
    # "mesial" alone defaults to mesial_buccal
    (re.compile(r"\bmesial\b", re.IGNORECASE), "mesial_buccal"),
    # "distal" alone defaults to distal_buccal
    (re.compile(r"\bdistal\b", re.IGNORECASE), "distal_buccal"),
]

# Tooth number extraction pattern
_TOOTH_RE = re.compile(r"\b(?:diente\s+)?(\d{2})\b")

# Pocket depth extraction: a standalone 1-2 digit number after site keywords
_POCKET_DEPTH_RE = re.compile(r"\b(\d{1,2})\b")

# Bleeding on probing keywords
_BLEEDING_RE = re.compile(r"\bsangrado\b|\bsangra\b|\bBOP\b", re.IGNORECASE)

# Mobility keyword: "movilidad N"
_MOBILITY_RE = re.compile(r"\bmovilidad\s+(\d)\b", re.IGNORECASE)

# Segment delimiter — measurements may be comma-separated
_SEGMENT_RE = re.compile(r",\s*")


# ── Public API ────────────────────────────────────────────────────────────────


def parse_perio_utterance(text: str) -> list[dict[str, Any]]:
    """Parse a Spanish periodontal voice utterance into measurement dicts.

    Args:
        text: Raw transcribed Spanish text, e.g.
              "diente 36 mesial bucal 4 sangrado, 37 bucal 3"

    Returns:
        List of measurement dicts, each containing at minimum:
          - tooth_number (int)
          - site (str, canonical VALID_PERIO_SITES value)
          - pocket_depth (int | None)
        And optionally:
          - bleeding_on_probing (bool)
          - mobility (int | None)

        Returns empty list on invalid/empty input.
    """
    text = text.strip()
    if not text:
        return []

    # Split on commas to get individual measurement segments
    segments = [s.strip() for s in _SEGMENT_RE.split(text) if s.strip()]

    results: list[dict[str, Any]] = []
    for segment in segments:
        measurement = _parse_segment(segment)
        if measurement is not None:
            results.append(measurement)

    return results


# ── Private helpers ───────────────────────────────────────────────────────────


def _parse_segment(segment: str) -> dict[str, Any] | None:
    """Parse a single measurement segment into a dict, or return None if invalid."""
    # 1. Extract tooth number
    tooth_match = _TOOTH_RE.search(segment)
    if tooth_match is None:
        # Maybe just a number with no "diente" keyword
        nums = re.findall(r"\b(\d{2})\b", segment)
        tooth_num = None
        for n in nums:
            candidate = int(n)
            if candidate in VALID_FDI_ALL:
                tooth_num = candidate
                break
        if tooth_num is None:
            # Check for mobility without a known tooth
            mobility_match = _MOBILITY_RE.search(segment)
            if mobility_match:
                # Cannot record mobility without a tooth number
                return None
            return None
    else:
        tooth_num_raw = int(tooth_match.group(1))
        if tooth_num_raw not in VALID_FDI_ALL:
            logger.debug("Skipping invalid FDI tooth number: %d", tooth_num_raw)
            return None
        tooth_num = tooth_num_raw

    # 2. Extract site
    site = _extract_site(segment)
    if site is None:
        # Check if it's a mobility-only utterance
        mobility_match = _MOBILITY_RE.search(segment)
        if mobility_match:
            return {
                "tooth_number": tooth_num,
                "site": "buccal",  # default site for mobility
                "pocket_depth": None,
                "mobility": int(mobility_match.group(1)),
            }
        return None

    # 3. Remove tooth and site tokens, then find pocket depth
    remaining = _TOOTH_RE.sub("", segment)
    remaining = re.sub(
        r"\bdiente\b|\bmesial\s+bucal|\bdistal\s+bucal|\bbucal|\bmesial\s+lingual|\bdistal\s+lingual|\blingual|\bmesial|\bdistal\b",
        "",
        remaining,
        flags=re.IGNORECASE,
    )
    pocket_depth = _extract_pocket_depth(remaining)

    # 4. Bleeding
    bleeding = bool(_BLEEDING_RE.search(segment))

    # 5. Mobility
    mobility_match = _MOBILITY_RE.search(segment)
    mobility = int(mobility_match.group(1)) if mobility_match else None

    result: dict[str, Any] = {
        "tooth_number": tooth_num,
        "site": site,
        "pocket_depth": pocket_depth,
    }
    if bleeding:
        result["bleeding_on_probing"] = True
    if mobility is not None:
        result["mobility"] = mobility

    return result


def _extract_site(segment: str) -> str | None:
    """Extract the canonical site string from a segment using alias mapping."""
    # Test aliases in priority order (multi-word before single-word)
    for pattern, canonical in _SITE_ALIASES:
        if pattern.search(segment):
            return canonical
    return None


def _extract_pocket_depth(remaining: str) -> int | None:
    """Extract pocket depth from the remaining text after removing tooth and site tokens."""
    remaining = remaining.replace("sangrado", "").replace("sangra", "")
    # Remove mobility patterns
    remaining = re.sub(r"\bmovilidad\s+\d\b", "", remaining, flags=re.IGNORECASE)
    remaining = remaining.strip()

    matches = _POCKET_DEPTH_RE.findall(remaining)
    for m in matches:
        val = int(m)
        # Pocket depth 0-12 mm is clinically plausible
        if 0 <= val <= 12:
            return val
    return None
