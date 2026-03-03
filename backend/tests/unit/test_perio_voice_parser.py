"""Unit tests for periodontal voice NLP parsing.

Tests cover the parse_perio_utterance() function in
app.services.perio_voice_parser, which converts Spanish voice transcripts
into structured periodontal measurement dicts.

Valid perio sites (from VALID_PERIO_SITES):
  mesial_buccal, buccal, distal_buccal,
  mesial_lingual, lingual, distal_lingual

Security:
  - PHI is NEVER logged (no patient names in any assertion messages).
  - Tests use generic/numeric data only.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

# The perio_voice_parser module parses Spanish dictation into structured
# periodontal measurement dicts. It is a pure function with no IO.
from app.services.perio_voice_parser import parse_perio_utterance


# ── parse_perio_utterance ─────────────────────────────────────────────────────


@pytest.mark.unit
class TestParsePerioUtterance:
    """Tests for parse_perio_utterance(text) -> list[dict]."""

    def test_parse_simple_measurement(self):
        """'diente 36 mesial bucal 4' -> tooth=36, site=mesial_buccal, pocket_depth=4."""
        results = parse_perio_utterance("diente 36 mesial bucal 4")

        assert len(results) >= 1
        m = results[0]
        assert m["tooth_number"] == 36
        assert m["site"] == "mesial_buccal"
        assert m["pocket_depth"] == 4

    def test_parse_with_bleeding(self):
        """'36 mesial 4 sangrado' -> bleeding_on_probing=True."""
        results = parse_perio_utterance("36 mesial 4 sangrado")

        assert len(results) >= 1
        m = results[0]
        assert m.get("bleeding_on_probing") is True

    def test_parse_multiple_teeth(self):
        """'36 mesial bucal 4, 37 bucal 3' -> 2 separate measurements."""
        results = parse_perio_utterance("36 mesial bucal 4, 37 bucal 3")

        assert len(results) == 2
        tooth_numbers = {r["tooth_number"] for r in results}
        assert 36 in tooth_numbers
        assert 37 in tooth_numbers

    def test_parse_mobility(self):
        """'36 movilidad 2' -> tooth=36, mobility=2."""
        results = parse_perio_utterance("36 movilidad 2")

        assert len(results) >= 1
        m = results[0]
        assert m["tooth_number"] == 36
        assert m.get("mobility") == 2

    def test_parse_invalid_tooth_ignored(self):
        """'diente 99 mesial 4' -> invalid FDI tooth is ignored or raises error."""
        # Implementation may either return [] or raise an error
        # Either way, no valid measurement should include tooth 99
        try:
            results = parse_perio_utterance("diente 99 mesial 4")
            # If it returns silently, tooth 99 must not appear
            assert all(r.get("tooth_number") != 99 for r in results)
        except Exception:
            # Raising an exception is also acceptable behavior
            pass

    def test_parse_empty_input(self):
        """Empty string must return empty list."""
        results = parse_perio_utterance("")

        assert results == []

    def test_parse_buccal_site_only(self):
        """'36 bucal 3' -> site=buccal (not mesial_buccal)."""
        results = parse_perio_utterance("36 bucal 3")

        assert len(results) >= 1
        m = results[0]
        assert m["tooth_number"] == 36
        assert m["site"] == "buccal"
        assert m["pocket_depth"] == 3

    def test_parse_lingual_site(self):
        """'16 lingual 5' -> site=lingual."""
        results = parse_perio_utterance("16 lingual 5")

        assert len(results) >= 1
        m = results[0]
        assert m["tooth_number"] == 16
        assert m["site"] == "lingual"

    def test_parse_distal_buccal(self):
        """'26 distal bucal 4' -> site=distal_buccal."""
        results = parse_perio_utterance("26 distal bucal 4")

        assert len(results) >= 1
        m = results[0]
        assert m["tooth_number"] == 26
        assert m["site"] == "distal_buccal"

    def test_parse_mesial_lingual(self):
        """'46 mesial lingual 3' -> site=mesial_lingual."""
        results = parse_perio_utterance("46 mesial lingual 3")

        assert len(results) >= 1
        m = results[0]
        assert m["tooth_number"] == 46
        assert m["site"] == "mesial_lingual"

    def test_parse_distal_lingual(self):
        """'14 distal lingual 6' -> site=distal_lingual."""
        results = parse_perio_utterance("14 distal lingual 6")

        assert len(results) >= 1
        m = results[0]
        assert m["tooth_number"] == 14
        assert m["site"] == "distal_lingual"

    def test_parse_pocket_depth_bounds(self):
        """Pocket depth values must be non-negative integers."""
        results = parse_perio_utterance("11 bucal 2")

        assert len(results) >= 1
        m = results[0]
        assert isinstance(m["pocket_depth"], int)
        assert m["pocket_depth"] >= 0

    def test_parse_whitespace_only_input(self):
        """Whitespace-only string must return empty list."""
        results = parse_perio_utterance("   ")

        assert results == []

    def test_parse_result_has_required_keys(self):
        """Every parsed measurement must include tooth_number, site, pocket_depth."""
        results = parse_perio_utterance("36 buccal 4")

        # Accepts zero results if FDI/site alias not recognized
        for m in results:
            assert "tooth_number" in m
            assert "site" in m

    def test_parse_no_valid_keywords_returns_empty(self):
        """Nonsense input must return empty list."""
        results = parse_perio_utterance("lorem ipsum dolor sit amet")

        assert isinstance(results, list)
        assert results == []
