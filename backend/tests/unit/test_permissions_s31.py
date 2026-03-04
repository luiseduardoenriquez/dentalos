"""Unit tests for Sprint 31-32 RBAC permission matrix.

Tests cover that:
  - clinic_owner has calls:read, calls:write, eps_claims:*, lab_orders:*
  - doctor has calls:read (only), eps_claims:read (only), lab_orders:read+write
  - receptionist has calls:read+write, eps_claims:read+write, lab_orders:read (only)
  - assistant has calls:read (only), lab_orders:read (only)
  - patient has NONE of the new Sprint 31-32 permissions
"""

import pytest

from app.auth.permissions import get_permissions_for_role


# ── Helper ────────────────────────────────────────────────────────────────────


def _perms(role: str) -> frozenset[str]:
    return get_permissions_for_role(role)


# ── TestClinicOwnerS31Permissions ─────────────────────────────────────────────


@pytest.mark.unit
class TestClinicOwnerS31Permissions:
    """clinic_owner has full calls, eps_claims, and lab_orders access."""

    def test_clinic_owner_has_calls_read_write(self):
        """clinic_owner has both calls:read and calls:write."""
        perms = _perms("clinic_owner")
        assert "calls:read" in perms
        assert "calls:write" in perms

    def test_clinic_owner_has_eps_claims_permissions(self):
        """clinic_owner has eps_claims:read and eps_claims:write."""
        perms = _perms("clinic_owner")
        assert "eps_claims:read" in perms
        assert "eps_claims:write" in perms

    def test_clinic_owner_has_lab_orders_permissions(self):
        """clinic_owner has lab_orders:read and lab_orders:write."""
        perms = _perms("clinic_owner")
        assert "lab_orders:read" in perms
        assert "lab_orders:write" in perms


# ── TestDoctorS31Permissions ──────────────────────────────────────────────────


@pytest.mark.unit
class TestDoctorS31Permissions:
    """doctor has read-only on calls/eps_claims; full on lab_orders."""

    def test_doctor_has_calls_read(self):
        """doctor has calls:read."""
        perms = _perms("doctor")
        assert "calls:read" in perms

    def test_doctor_does_not_have_calls_write(self):
        """doctor does NOT have calls:write."""
        perms = _perms("doctor")
        assert "calls:write" not in perms

    def test_doctor_has_eps_claims_read_only(self):
        """doctor has eps_claims:read but NOT eps_claims:write."""
        perms = _perms("doctor")
        assert "eps_claims:read" in perms
        assert "eps_claims:write" not in perms

    def test_doctor_has_lab_orders_read_write(self):
        """doctor has both lab_orders:read and lab_orders:write."""
        perms = _perms("doctor")
        assert "lab_orders:read" in perms
        assert "lab_orders:write" in perms


# ── TestReceptionistS31Permissions ────────────────────────────────────────────


@pytest.mark.unit
class TestReceptionistS31Permissions:
    """receptionist has calls:read+write, eps_claims:read+write, lab_orders:read."""

    def test_receptionist_has_calls_read_write(self):
        """receptionist has calls:read and calls:write."""
        perms = _perms("receptionist")
        assert "calls:read" in perms
        assert "calls:write" in perms

    def test_receptionist_has_eps_claims_permissions(self):
        """receptionist has eps_claims:read and eps_claims:write."""
        perms = _perms("receptionist")
        assert "eps_claims:read" in perms
        assert "eps_claims:write" in perms

    def test_receptionist_has_lab_orders_read_only(self):
        """receptionist has lab_orders:read but NOT lab_orders:write."""
        perms = _perms("receptionist")
        assert "lab_orders:read" in perms
        assert "lab_orders:write" not in perms


# ── TestAssistantS31Permissions ───────────────────────────────────────────────


@pytest.mark.unit
class TestAssistantS31Permissions:
    """assistant has calls:read and lab_orders:read only."""

    def test_assistant_has_calls_read(self):
        """assistant has calls:read."""
        perms = _perms("assistant")
        assert "calls:read" in perms

    def test_assistant_does_not_have_calls_write(self):
        """assistant does NOT have calls:write."""
        perms = _perms("assistant")
        assert "calls:write" not in perms

    def test_assistant_has_lab_orders_read(self):
        """assistant has lab_orders:read."""
        perms = _perms("assistant")
        assert "lab_orders:read" in perms

    def test_assistant_does_not_have_lab_orders_write(self):
        """assistant does NOT have lab_orders:write."""
        perms = _perms("assistant")
        assert "lab_orders:write" not in perms

    def test_assistant_does_not_have_eps_claims(self):
        """assistant does NOT have eps_claims:read or eps_claims:write."""
        perms = _perms("assistant")
        assert "eps_claims:read" not in perms
        assert "eps_claims:write" not in perms


# ── TestPatientNoNewPermissions ───────────────────────────────────────────────


@pytest.mark.unit
class TestPatientNoNewPermissions:
    """patient role does NOT have any Sprint 31-32 permissions."""

    def test_patient_no_calls_permissions(self):
        """patient does NOT have calls:read or calls:write."""
        perms = _perms("patient")
        assert "calls:read" not in perms
        assert "calls:write" not in perms

    def test_patient_no_eps_claims_permissions(self):
        """patient does NOT have eps_claims:read or eps_claims:write."""
        perms = _perms("patient")
        assert "eps_claims:read" not in perms
        assert "eps_claims:write" not in perms

    def test_patient_no_lab_orders_permissions(self):
        """patient does NOT have lab_orders:read or lab_orders:write."""
        perms = _perms("patient")
        assert "lab_orders:read" not in perms
        assert "lab_orders:write" not in perms
