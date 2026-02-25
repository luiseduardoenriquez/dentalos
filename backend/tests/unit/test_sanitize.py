"""Unit tests for input sanitization utilities.

Tests sanitize_string, reject_null_bytes, and sanitize_html from app.core.sanitize.
"""
import pytest

from app.core.sanitize import ALLOWED_TAGS, reject_null_bytes, sanitize_html, sanitize_string


@pytest.mark.unit
class TestRejectNullBytes:
    def test_clean_string_passes_through(self):
        assert reject_null_bytes("hello world") == "hello world"

    def test_null_byte_raises(self):
        with pytest.raises(ValueError, match="null bytes"):
            reject_null_bytes("bad\x00string")

    def test_null_byte_at_start_raises(self):
        with pytest.raises(ValueError):
            reject_null_bytes("\x00prefix")

    def test_null_byte_at_end_raises(self):
        with pytest.raises(ValueError):
            reject_null_bytes("suffix\x00")

    def test_multiple_null_bytes_raises(self):
        with pytest.raises(ValueError):
            reject_null_bytes("a\x00b\x00c")

    def test_empty_string_passes(self):
        assert reject_null_bytes("") == ""

    def test_unicode_without_null_passes(self):
        assert reject_null_bytes("García Martínez") == "García Martínez"


@pytest.mark.unit
class TestSanitizeString:
    def test_strips_leading_whitespace(self):
        assert sanitize_string("  hello") == "hello"

    def test_strips_trailing_whitespace(self):
        assert sanitize_string("hello  ") == "hello"

    def test_strips_both_sides(self):
        assert sanitize_string("  hello world  ") == "hello world"

    def test_internal_whitespace_preserved(self):
        assert sanitize_string("  first  last  ") == "first  last"

    def test_null_byte_raises_after_strip(self):
        with pytest.raises(ValueError, match="null bytes"):
            sanitize_string("  valid\x00bad  ")

    def test_empty_string_after_strip(self):
        assert sanitize_string("   ") == ""

    def test_plain_string_unchanged(self):
        assert sanitize_string("Dr. María López") == "Dr. María López"


@pytest.mark.unit
class TestSanitizeHtml:
    def test_allowed_tags_preserved(self):
        for tag in ALLOWED_TAGS:
            result = sanitize_html(f"<{tag}>text</{tag}>")
            assert f"<{tag}>" in result, f"Expected <{tag}> to be preserved"

    def test_script_tag_stripped(self):
        """bleach strips the <script> element but preserves its text content.
        The critical guarantee is that executable tags are removed — the inner
        text is harmless without the tag wrapping it.
        """
        result = sanitize_html("<script>alert('xss')</script>clean text")
        assert "<script>" not in result
        assert "</script>" not in result
        assert "clean text" in result

    def test_onclick_attribute_stripped(self):
        result = sanitize_html('<p onclick="evil()">text</p>')
        assert "onclick" not in result
        assert "text" in result

    def test_href_attribute_stripped(self):
        """No attributes are allowed — href must be stripped even on <a>."""
        result = sanitize_html('<a href="http://evil.com">click</a>')
        assert "href" not in result

    def test_style_attribute_stripped(self):
        result = sanitize_html('<p style="color:red">note</p>')
        assert "style" not in result
        assert "note" in result

    def test_disallowed_tag_stripped_content_kept(self):
        result = sanitize_html("<div>keep this</div>")
        assert "<div>" not in result
        assert "keep this" in result

    def test_iframe_fully_removed(self):
        result = sanitize_html('<iframe src="evil.com"></iframe>')
        assert "iframe" not in result

    def test_nested_allowed_tags(self):
        html = "<ul><li><strong>item</strong></li></ul>"
        result = sanitize_html(html)
        assert "<ul>" in result
        assert "<li>" in result
        assert "<strong>" in result

    def test_plain_text_unchanged(self):
        result = sanitize_html("plain clinical note without tags")
        assert result == "plain clinical note without tags"

    def test_br_tag_preserved(self):
        result = sanitize_html("line1<br>line2")
        assert "<br>" in result

    def test_empty_string(self):
        assert sanitize_html("") == ""
