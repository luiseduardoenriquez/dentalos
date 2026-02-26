"""Colombia-specific field validators for RIPS and compliance.

Provides regex-based validation for Colombian regulatory field formats:
NIT, CUPS codes, CIE-10 codes, document numbers (cedula), and DANE
municipality codes.
"""

import re

# NIT: 6-12 digits, optional dash + single check digit
_NIT_PATTERN = re.compile(r"^[0-9]{6,12}(-[0-9])?$")

# CUPS: exactly 6 digits
_CUPS_PATTERN = re.compile(r"^[0-9]{6}$")

# CIE-10: letter + 2 digits, optional dot + 1-4 digits
_CIE10_PATTERN = re.compile(r"^[A-Z][0-9]{2}(\.[0-9]{1,4})?$")

# Colombian document number: 6-12 digits
_DOCUMENT_NUMBER_PATTERN = re.compile(r"^[0-9]{6,12}$")

# DANE municipality code: 5 digits
_DANE_CODE_PATTERN = re.compile(r"^[0-9]{5}$")


def validate_nit(nit: str) -> bool:
    """Validate Colombian NIT (Numero de Identificacion Tributaria).

    Format: 6-12 digits, optionally followed by a dash and a single
    check digit (e.g. ``900123456-7``).
    """
    return bool(_NIT_PATTERN.match(nit))


def validate_cups_code(code: str) -> bool:
    """Validate CUPS code format (exactly 6 digits)."""
    return bool(_CUPS_PATTERN.match(code))


def validate_cie10_code(code: str) -> bool:
    """Validate CIE-10 diagnosis code format.

    Format: uppercase letter + 2 digits, optional dot + 1-4 digits
    (e.g. ``K02``, ``K02.1``).  The input is uppercased before matching.
    """
    return bool(_CIE10_PATTERN.match(code.upper()))


def validate_document_number(doc_number: str) -> bool:
    """Validate Colombian document number (cedula, TI, etc.).

    Format: 6-12 digits.
    """
    return bool(_DOCUMENT_NUMBER_PATTERN.match(doc_number))


def validate_dane_code(code: str) -> bool:
    """Validate DANE municipality code (exactly 5 digits)."""
    return bool(_DANE_CODE_PATTERN.match(code))
