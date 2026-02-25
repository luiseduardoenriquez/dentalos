import pytest

from app.auth.permissions import (
    ROLE_PERMISSIONS,
    SUPERADMIN_PERMISSIONS,
    get_permissions_for_role,
    has_permission,
)


@pytest.mark.unit
class TestPermissions:
    def test_all_roles_defined(self):
        expected = {"clinic_owner", "doctor", "assistant", "receptionist", "patient"}
        assert set(ROLE_PERMISSIONS.keys()) == expected

    def test_clinic_owner_has_all_standard(self):
        perms = get_permissions_for_role("clinic_owner")
        assert "users:manage" in perms
        assert "patients:delete" in perms
        assert "billing:manage" in perms
        assert "settings:write" in perms

    def test_doctor_has_clinical(self):
        perms = get_permissions_for_role("doctor")
        assert "odontogram:write" in perms
        assert "clinical_records:write" in perms
        assert "prescriptions:write" in perms

    def test_doctor_lacks_admin(self):
        perms = get_permissions_for_role("doctor")
        assert "users:manage" not in perms
        assert "settings:write" not in perms
        assert "billing:manage" not in perms

    def test_receptionist_lacks_clinical_write(self):
        perms = get_permissions_for_role("receptionist")
        assert "odontogram:write" not in perms
        assert "clinical_records:write" not in perms
        assert "treatment_plans:write" not in perms

    def test_patient_minimal(self):
        perms = get_permissions_for_role("patient")
        assert "patients:write" not in perms
        assert "odontogram:write" not in perms
        assert "patients:read" in perms

    def test_superadmin(self):
        perms = get_permissions_for_role("superadmin")
        assert perms is SUPERADMIN_PERMISSIONS
        assert "tenants:manage" in perms

    def test_unknown_role(self):
        perms = get_permissions_for_role("unknown")
        assert perms == frozenset()

    def test_has_permission(self):
        assert has_permission("doctor", "patients:read")
        assert not has_permission("patient", "patients:write")
