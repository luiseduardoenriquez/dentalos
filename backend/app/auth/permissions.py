"""RBAC permission matrix for all DentalOS roles."""

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "clinic_owner": frozenset({
        # Users
        "users:read", "users:write", "users:delete", "users:manage",
        # Patients
        "patients:read", "patients:write", "patients:delete",
        # Odontogram
        "odontogram:read", "odontogram:write",
        # Clinical records
        "clinical_records:read", "clinical_records:write",
        # Treatment plans
        "treatment_plans:read", "treatment_plans:write", "treatment_plans:delete",
        # Appointments
        "appointments:read", "appointments:write", "appointments:delete",
        "appointments:manage",
        # Billing
        "billing:read", "billing:write", "billing:delete", "billing:manage",
        # Consents
        "consents:read", "consents:write",
        # Settings
        "settings:read", "settings:write",
        # Analytics
        "analytics:read",
        # Invites
        "invites:read", "invites:write", "invites:delete",
        # Prescriptions
        "prescriptions:read", "prescriptions:write",
        # Inventory
        "inventory:read", "inventory:write", "inventory:delete",
        # Compliance
        "compliance:read", "compliance:write",
        # Messages
        "messages:read", "messages:write",
    }),
    "doctor": frozenset({
        "patients:read", "patients:write",
        "odontogram:read", "odontogram:write",
        "clinical_records:read", "clinical_records:write",
        "treatment_plans:read", "treatment_plans:write",
        "appointments:read", "appointments:write",
        "billing:read",
        "consents:read", "consents:write",
        "prescriptions:read", "prescriptions:write",
        "analytics:read",
        "messages:read", "messages:write",
        "inventory:read",
    }),
    "assistant": frozenset({
        "patients:read", "patients:write",
        "odontogram:read", "odontogram:write",
        "clinical_records:read", "clinical_records:write",
        "treatment_plans:read",
        "appointments:read", "appointments:write",
        "billing:read",
        "consents:read",
        "prescriptions:read",
        "messages:read", "messages:write",
        "inventory:read",
    }),
    "receptionist": frozenset({
        "patients:read", "patients:write",
        "appointments:read", "appointments:write", "appointments:manage",
        "billing:read", "billing:write",
        "messages:read", "messages:write",
        "inventory:read",
    }),
    "patient": frozenset({
        "patients:read",
        "odontogram:read",
        "clinical_records:read",
        "treatment_plans:read",
        "appointments:read", "appointments:write",
        "billing:read",
        "consents:read", "consents:write",
        "prescriptions:read",
        "messages:read", "messages:write",
    }),
}

SUPERADMIN_PERMISSIONS: frozenset[str] = frozenset({
    "admin:read", "admin:write", "admin:manage",
    "tenants:read", "tenants:write", "tenants:delete", "tenants:manage",
    "plans:read", "plans:write", "plans:delete",
    "users:read", "users:write", "users:delete", "users:manage",
    "compliance:read", "compliance:write", "compliance:manage",
    "analytics:read", "analytics:manage",
    "system:read", "system:write", "system:manage",
})


def get_permissions_for_role(role: str) -> frozenset[str]:
    """Get the permission set for a given role."""
    if role == "superadmin":
        return SUPERADMIN_PERMISSIONS
    return ROLE_PERMISSIONS.get(role, frozenset())


def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    return permission in get_permissions_for_role(role)
