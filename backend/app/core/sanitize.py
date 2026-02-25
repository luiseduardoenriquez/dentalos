"""Input sanitization utilities for DentalOS.

Provides null byte rejection and HTML sanitization for rich text fields.
"""
import re

import bleach

# Allowed HTML tags for rich text fields (clinical notes, etc.)
ALLOWED_TAGS = ["b", "i", "u", "br", "p", "ul", "ol", "li", "strong", "em"]
ALLOWED_ATTRIBUTES: dict[str, list[str]] = {}

# Null byte pattern
NULL_BYTE_PATTERN = re.compile(r"\x00")


def reject_null_bytes(value: str) -> str:
    """Strip null bytes from input. Raises ValueError if null bytes found."""
    if NULL_BYTE_PATTERN.search(value):
        raise ValueError("Input contains null bytes")
    return value


def sanitize_html(value: str) -> str:
    """Sanitize HTML using bleach with allowed tags only."""
    return bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
    )


def sanitize_string(value: str) -> str:
    """Strip whitespace and reject null bytes."""
    value = value.strip()
    return reject_null_bytes(value)
