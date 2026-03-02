"""Unit tests for the QRCodeService class.

Tests cover:
  - generate_base64: returns a non-empty base64-encoded string when qrcode is available
  - generate_base64: different data strings produce different outputs
  - generate_base64 (fallback): when ImportError is raised, returns the 1x1 PNG placeholder

PHI never appears in test assertions.
"""

import base64
import sys
from unittest.mock import MagicMock, patch

import pytest

from app.services.qr_code_service import QRCodeService


# ── Helpers ───────────────────────────────────────────────────────────────────

# The real 1x1 transparent PNG placeholder bytes hard-coded in qr_code_service.py.
# We replicate it here so the fallback test can compare against the exact value.
_PLACEHOLDER_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
    b"\r\n\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)
_PLACEHOLDER_B64 = base64.b64encode(_PLACEHOLDER_BYTES).decode("utf-8")


def _make_service() -> QRCodeService:
    """Return a fresh QRCodeService instance."""
    return QRCodeService()


# ── generate_base64 ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGenerateQrCodeReturnsBase64:
    def test_generate_base64_returns_non_empty_string(self):
        """generate_base64 must return a non-empty string."""
        service = _make_service()

        result = service.generate_base64(data="https://example.com/pay/123")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_base64_output_is_valid_base64(self):
        """The returned string must be decodable as standard base64."""
        service = _make_service()

        result = service.generate_base64(data="https://test.dentalos.co/pay/abc")

        # Should not raise
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    def test_generate_base64_output_starts_with_png_signature(self):
        """Decoded bytes must begin with the PNG file signature (8 bytes)."""
        service = _make_service()

        result = service.generate_base64(data="https://test.dentalos.co/pay/def")
        decoded = base64.b64decode(result)

        # PNG magic bytes: 0x89 0x50 0x4E 0x47 ...
        assert decoded[:4] == b"\x89PNG"


@pytest.mark.unit
class TestGenerateQrCodeWithCustomData:
    def test_different_data_produces_different_output(self):
        """Two different data strings must produce different base64 outputs."""
        service = _make_service()

        result_a = service.generate_base64(data="https://payment.example/qr/invoice-001")
        result_b = service.generate_base64(data="https://payment.example/qr/invoice-002")

        assert result_a != result_b

    def test_same_data_produces_same_output(self):
        """The same input data must always produce the same base64 output."""
        service = _make_service()
        data = "https://stable.example/qr/stable-ref"

        result_a = service.generate_base64(data=data)
        result_b = service.generate_base64(data=data)

        assert result_a == result_b

    def test_empty_data_string_still_returns_base64(self):
        """Even an empty data string should not crash the generator."""
        service = _make_service()

        result = service.generate_base64(data="")

        assert isinstance(result, str)
        # Minimal: must at least be a non-empty string (QR or placeholder)
        assert len(result) > 0


@pytest.mark.unit
class TestGenerateQrCodeFallback:
    def test_fallback_when_qrcode_not_installed(self):
        """When the qrcode library is absent (ImportError), return the 1x1 placeholder."""
        service = _make_service()

        # Temporarily remove qrcode from sys.modules to trigger ImportError
        original_module = sys.modules.get("qrcode")
        sys.modules["qrcode"] = None  # type: ignore[assignment]

        try:
            result = service.generate_base64(data="https://any.url/pay/fallback")
        finally:
            # Restore original state
            if original_module is None:
                sys.modules.pop("qrcode", None)
            else:
                sys.modules["qrcode"] = original_module

        assert result == _PLACEHOLDER_B64

    def test_fallback_is_valid_base64(self):
        """The placeholder returned during fallback must itself be valid base64."""
        decoded = base64.b64decode(_PLACEHOLDER_B64)
        assert len(decoded) > 0

    def test_fallback_placeholder_starts_with_png_signature(self):
        """The placeholder must be a valid PNG (has correct magic bytes)."""
        decoded = base64.b64decode(_PLACEHOLDER_B64)
        assert decoded[:4] == b"\x89PNG"

    def test_fallback_is_returned_as_string_not_bytes(self):
        """The fallback return type must be str, not bytes."""
        service = _make_service()

        sys.modules["qrcode"] = None  # type: ignore[assignment]
        try:
            result = service.generate_base64(data="fallback-type-check")
        finally:
            sys.modules.pop("qrcode", None)

        assert isinstance(result, str)
