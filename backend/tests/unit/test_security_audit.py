"""OWASP verification test suite for DentalOS.

Covers:
  - A1 (Injection)          — SQL injection via schema name validation
  - A3 (XSS)                — HTML sanitization with bleach
  - A4 (Insecure Design)    — File upload MIME-type allow-list + magic-byte check
  - A1/A5 (Broken Access)   — Schema-name prefix enforcement
  - A2 (Cryptographic)      — Email address masking for safe logging
"""

import pytest
from unittest.mock import patch

from app.core.tenant import validate_schema_name
from app.core.sanitize import sanitize_html
from app.core.storage import verify_mime_type
from app.core.email import _mask_email


# ---------------------------------------------------------------------------
# A1 — Injection: SQL injection payloads must be rejected by validate_schema_name
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSqlInjectionSchemaValidation:
    """validate_schema_name must refuse every string that is not a safe
    tn_<lowercase-alphanumeric> identifier, blocking SQL injection vectors
    that could be spliced into SET search_path statements."""

    @pytest.mark.parametrize("payload", [
        "tn_abc; DROP TABLE patients--",
        "tn_abc' OR '1'='1",
        "../../../etc/passwd",
        "tn_abc\x00injection",
        "",
    ])
    def test_injection_payloads_are_rejected(self, payload: str):
        assert validate_schema_name(payload) is False, (
            f"Expected SQL injection payload to be rejected: {payload!r}"
        )

    @pytest.mark.parametrize("valid_name", [
        "tn_abc123",
        "tn_test_clinic",
        "tn_abcd1234",
        "tn_a1b2c3d4",
    ])
    def test_valid_schema_names_are_accepted(self, valid_name: str):
        assert validate_schema_name(valid_name) is True, (
            f"Expected valid schema name to be accepted: {valid_name!r}"
        )


# ---------------------------------------------------------------------------
# A3 — XSS: bleach must strip dangerous tags while preserving allowed markup
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestXssSanitization:
    """sanitize_html (backed by bleach) must neutralise XSS payloads and
    preserve the subset of formatting tags allowed by the CLAUDE.md spec."""

    def test_script_tag_stripped(self):
        result = sanitize_html("<script>alert('xss')</script>")
        assert "<script>" not in result, "script open tag must be removed"
        assert "</script>" not in result, "script close tag must be removed"

    def test_img_onerror_stripped(self):
        result = sanitize_html('<img onerror="alert(1)" src="x">')
        assert "onerror" not in result, "onerror attribute must be removed"
        assert "<img" not in result, "img tag must be removed (not in allow-list)"

    @pytest.mark.parametrize("tag", ["b", "i", "p", "ul", "li"])
    def test_allowed_tags_are_preserved(self, tag: str):
        html_input = f"<{tag}>content</{tag}>"
        result = sanitize_html(html_input)
        assert f"<{tag}>" in result, f"Allowed tag <{tag}> must be preserved"


# ---------------------------------------------------------------------------
# A4 — Insecure Design: file MIME type must match magic bytes
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestFileUploadMimeAllowlist:
    """verify_mime_type uses python-magic to detect the actual file format
    from magic bytes and compares it against the claimed MIME type.
    The magic library is mocked so the test suite runs without libmagic."""

    # Minimal JPEG SOI marker — libmagic recognises this as image/jpeg.
    JPEG_MAGIC = b"\xff\xd8\xff\xe0" + b"\x00" * 60
    # Minimal PDF magic bytes.
    PDF_MAGIC = b"%PDF-1.4" + b"\x00" * 60

    def test_jpeg_bytes_accepted_with_correct_mime(self):
        with patch("magic.from_buffer", return_value="image/jpeg"):
            result = verify_mime_type(self.JPEG_MAGIC, "image/jpeg")
        assert result is True, "JPEG bytes with image/jpeg claim must pass"

    def test_pdf_bytes_accepted_with_correct_mime(self):
        with patch("magic.from_buffer", return_value="application/pdf"):
            result = verify_mime_type(self.PDF_MAGIC, "application/pdf")
        assert result is True, "PDF bytes with application/pdf claim must pass"

    def test_jpeg_bytes_rejected_when_claimed_as_pdf(self):
        # Magic detects JPEG; caller claims PDF — mismatch must fail.
        with patch("magic.from_buffer", return_value="image/jpeg"):
            result = verify_mime_type(self.JPEG_MAGIC, "application/pdf")
        assert result is False, (
            "JPEG magic bytes claimed as application/pdf must be rejected"
        )

    def test_dangerous_executable_bytes_rejected(self):
        # Simulate an ELF binary being claimed as an image.
        elf_bytes = b"\x7fELF" + b"\x00" * 60
        with patch("magic.from_buffer", return_value="application/x-executable"):
            result = verify_mime_type(elf_bytes, "image/jpeg")
        assert result is False, (
            "ELF binary bytes claimed as image/jpeg must be rejected"
        )

    def test_mime_alias_normalised_before_comparison(self):
        # image/jpg is a common client alias; storage.py maps it to image/jpeg.
        with patch("magic.from_buffer", return_value="image/jpeg"):
            result = verify_mime_type(self.JPEG_MAGIC, "image/jpg")
        assert result is True, (
            "image/jpg alias must be normalised to image/jpeg and accepted"
        )


# ---------------------------------------------------------------------------
# A1/A5 — Broken Access Control: schema names without tn_ prefix are blocked
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestBrokenAccessControlSchemaPattern:
    """Schemas that do not carry the tn_ prefix would allow a caller to
    target system schemas (public, pg_catalog, etc.) or bypass tenant
    isolation.  validate_schema_name must reject all such names."""

    @pytest.mark.parametrize("dangerous_schema", [
        "admin",
        "public",
        "pg_catalog",
        "information_schema",
        "pg_toast",
        "postgres",
    ])
    def test_system_schema_names_rejected(self, dangerous_schema: str):
        assert validate_schema_name(dangerous_schema) is False, (
            f"System/reserved schema name must be rejected: {dangerous_schema!r}"
        )

    @pytest.mark.parametrize("schema_without_prefix", [
        "abc123",
        "clinic_main",
        "test",
        "TENANT_abc",
        "tn",
        "tn_",
    ])
    def test_missing_or_malformed_prefix_rejected(self, schema_without_prefix: str):
        assert validate_schema_name(schema_without_prefix) is False, (
            f"Schema without valid tn_ prefix must be rejected: {schema_without_prefix!r}"
        )

    @pytest.mark.parametrize("special_chars", [
        "tn_abc!def",
        "tn_abc def",
        "tn_abc-def",
        "tn_ABC123",
        "tn_abc@def",
    ])
    def test_special_characters_in_schema_rejected(self, special_chars: str):
        assert validate_schema_name(special_chars) is False, (
            f"Schema name with special characters must be rejected: {special_chars!r}"
        )


# ---------------------------------------------------------------------------
# A2 — Sensitive data exposure: email masking for safe logging
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestEmailMasking:
    """_mask_email must obscure the local-part of an address before it
    reaches log sinks, leaving only the first character visible.
    PHI must never appear in log lines."""

    def test_standard_email_masked(self):
        result = _mask_email("john@example.com")
        assert result == "j***@example.com", (
            "Standard email must be masked to first-char + *** + @domain"
        )

    def test_empty_string_returns_empty(self):
        result = _mask_email("")
        assert result == "", "Empty input must return empty string"

    def test_string_without_at_sign_returned_unchanged(self):
        result = _mask_email("no-at-sign")
        assert result == "no-at-sign", (
            "Value without @ must be returned unchanged (not a valid email)"
        )

    def test_single_char_local_part(self):
        result = _mask_email("a@b.com")
        assert result == "a***@b.com", (
            "Single-character local part must still be masked as a***@domain"
        )

    def test_domain_preserved_exactly(self):
        result = _mask_email("doctor@clinica-bogota.co")
        assert result.endswith("@clinica-bogota.co"), (
            "Domain portion must be preserved verbatim after masking"
        )

    def test_first_char_only_is_visible(self):
        result = _mask_email("longname@example.com")
        local_visible = result.split("@")[0]
        assert local_visible == "l***", (
            "Only the first character of the local-part should remain visible"
        )
