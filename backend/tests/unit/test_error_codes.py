"""Unit tests for the centralized error codes registry.

Verifies that all error codes are unique, follow the DOMAIN_error_name convention,
and that every domain class contributes at least one code.
"""
import re

import pytest

from app.core.error_codes import (
    AppointmentErrors,
    AuthErrors,
    BillingErrors,
    ClinicalErrors,
    ConsentErrors,
    OdontogramErrors,
    PatientErrors,
    SystemErrors,
    TenantErrors,
    ValidationErrors,
)

# Every domain class under test
_ALL_DOMAIN_CLASSES = [
    AuthErrors,
    TenantErrors,
    PatientErrors,
    OdontogramErrors,
    ClinicalErrors,
    AppointmentErrors,
    BillingErrors,
    ConsentErrors,
    ValidationErrors,
    SystemErrors,
]

# Expected prefix for each class (used in pattern check)
_DOMAIN_PREFIX = {
    AuthErrors: "AUTH_",
    TenantErrors: "TENANT_",
    PatientErrors: "PATIENT_",
    OdontogramErrors: "ODONTOGRAM_",
    ClinicalErrors: "CLINICAL_",
    AppointmentErrors: "APPOINTMENT_",
    BillingErrors: "BILLING_",
    ConsentErrors: "CONSENT_",
    ValidationErrors: "VALIDATION_",
    SystemErrors: "SYSTEM_",
}

# Pattern: uppercase domain, underscore, then lowercase_snake_case identifier
_CODE_PATTERN = re.compile(r"^[A-Z]+_[a-z][a-z0-9_]*$")


def _collect_codes(cls) -> list[str]:
    """Return all public string attributes of a domain error class."""
    return [
        value
        for name, value in vars(cls).items()
        if not name.startswith("_") and isinstance(value, str)
    ]


@pytest.mark.unit
class TestErrorCodeUniqueness:
    def test_all_codes_are_unique_across_all_domains(self):
        """No two domain classes may share the same error code string."""
        all_codes: list[str] = []
        for cls in _ALL_DOMAIN_CLASSES:
            all_codes.extend(_collect_codes(cls))

        seen: set[str] = set()
        duplicates: list[str] = []
        for code in all_codes:
            if code in seen:
                duplicates.append(code)
            seen.add(code)

        assert not duplicates, f"Duplicate error codes found: {duplicates}"

    def test_each_domain_has_at_least_one_code(self):
        """Every domain error class must define at least one error code."""
        for cls in _ALL_DOMAIN_CLASSES:
            codes = _collect_codes(cls)
            assert len(codes) >= 1, f"{cls.__name__} defines no error codes"


@pytest.mark.unit
class TestErrorCodeFormat:
    def test_codes_match_domain_underscore_name_pattern(self):
        """All error codes must match the pattern DOMAIN_error_name."""
        bad: list[str] = []
        for cls in _ALL_DOMAIN_CLASSES:
            for code in _collect_codes(cls):
                if not _CODE_PATTERN.match(code):
                    bad.append(f"{cls.__name__}: {code!r}")

        assert not bad, f"Error codes violating DOMAIN_error_name pattern:\n" + "\n".join(bad)

    def test_codes_carry_correct_domain_prefix(self):
        """Each code in a domain class must start with that domain's prefix."""
        bad: list[str] = []
        for cls, prefix in _DOMAIN_PREFIX.items():
            for code in _collect_codes(cls):
                if not code.startswith(prefix):
                    bad.append(f"{cls.__name__}: {code!r} (expected prefix {prefix!r})")

        assert not bad, f"Error codes with wrong domain prefix:\n" + "\n".join(bad)

    def test_auth_error_known_codes_exist(self):
        """Spot-check that critical AUTH codes are present and correctly spelled."""
        assert AuthErrors.INVALID_CREDENTIALS == "AUTH_invalid_credentials"
        assert AuthErrors.TOKEN_EXPIRED == "AUTH_token_expired"
        assert AuthErrors.INSUFFICIENT_PERMISSIONS == "AUTH_insufficient_permissions"
        assert AuthErrors.MISSING_REFRESH_TOKEN == "AUTH_missing_refresh_token"

    def test_tenant_error_known_codes_exist(self):
        assert TenantErrors.NOT_FOUND == "TENANT_not_found"
        assert TenantErrors.PLAN_LIMIT_REACHED == "TENANT_plan_limit_reached"
        assert TenantErrors.SUSPENDED == "TENANT_suspended"

    def test_system_error_known_codes_exist(self):
        assert SystemErrors.INTERNAL_ERROR == "SYSTEM_internal_error"
        assert SystemErrors.RATE_LIMIT_EXCEEDED == "SYSTEM_rate_limit_exceeded"
        assert SystemErrors.NOT_FOUND == "SYSTEM_not_found"
