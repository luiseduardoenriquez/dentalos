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
        # Schedules
        "schedule:read", "schedule:write",
        # Waitlist
        "waitlist:read", "waitlist:write",
        # Voice
        "voice:read", "voice:write",
        # Reminders
        "reminders:read", "reminders:write",
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
        # Diagnoses
        "diagnoses:read", "diagnoses:write",
        # Procedures
        "procedures:read", "procedures:write",
        # Quotations
        "quotations:read", "quotations:write", "quotations:delete",
        # Signatures
        "signatures:read", "signatures:write",
        # Photos
        "photos:read", "photos:write",
        # Inventory
        "inventory:read", "inventory:write", "inventory:delete",
        # Compliance
        "compliance:read", "compliance:write",
        # Messages
        "messages:read", "messages:write",
        # Notifications
        "notifications:read", "notifications:write",
        # Sprint 21-22: Memberships, Intake, Recall
        "memberships:read", "memberships:write",
        "intake:read", "intake:write",
        "recall:read", "recall:write",
        # Sprint 23-24
        "cash_register:read", "cash_register:write",
        "expenses:read", "expenses:write",
        "tasks:read", "tasks:write",
        "postop:read", "postop:write",
        "referral_program:read",
    }),
    "doctor": frozenset({
        "patients:read", "patients:write",
        "odontogram:read", "odontogram:write",
        "clinical_records:read", "clinical_records:write",
        "treatment_plans:read", "treatment_plans:write",
        "appointments:read", "appointments:write",
        "schedule:read", "schedule:write",
        "waitlist:read",
        "voice:read", "voice:write",
        "reminders:read",
        "billing:read",
        "consents:read", "consents:write",
        "prescriptions:read", "prescriptions:write",
        "diagnoses:read", "diagnoses:write",
        "procedures:read", "procedures:write",
        "quotations:read", "quotations:write",
        "signatures:read", "signatures:write",
        "photos:read", "photos:write",
        "analytics:read",
        "messages:read", "messages:write",
        # Notifications
        "notifications:read", "notifications:write",
        "inventory:read",
        # Sprint 21-22
        "memberships:read", "intake:read",
        # Sprint 23-24
        "postop:read", "postop:write",
        "tasks:read",
    }),
    "assistant": frozenset({
        "patients:read", "patients:write",
        "odontogram:read", "odontogram:write",
        "clinical_records:read", "clinical_records:write",
        "treatment_plans:read",
        "appointments:read", "appointments:write",
        "waitlist:read", "waitlist:write",
        "voice:read", "voice:write",
        "billing:read",
        "consents:read",
        "prescriptions:read",
        "diagnoses:read",
        "procedures:read",
        "quotations:read",
        "signatures:read",
        "photos:read", "photos:write",
        "messages:read", "messages:write",
        # Notifications
        "notifications:read", "notifications:write",
        "inventory:read", "inventory:write",
        # Sprint 21-22
        "memberships:read", "intake:read",
        # Sprint 23-24
        "postop:read", "postop:write",
        "tasks:read",
    }),
    "receptionist": frozenset({
        "patients:read", "patients:write",
        "appointments:read", "appointments:write", "appointments:manage",
        "waitlist:read", "waitlist:write",
        "reminders:read",
        "billing:read", "billing:write",
        "quotations:read", "quotations:write",
        "messages:read", "messages:write",
        # Notifications
        "notifications:read", "notifications:write",
        "inventory:read",
        # Sprint 21-22
        "memberships:read", "memberships:write",
        "intake:read", "intake:write",
        "recall:read", "recall:write",
        # Sprint 23-24
        "cash_register:read", "cash_register:write",
        "expenses:read", "expenses:write",
        "tasks:read", "tasks:write",
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
        "diagnoses:read",
        "procedures:read",
        "quotations:read",
        "signatures:read", "signatures:write",
        "photos:read",
        "messages:read", "messages:write",
        # Notifications
        "notifications:read", "notifications:write",
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
