"""Centralized error codes registry for DentalOS.

All error codes in the system are defined here as string constants grouped by
domain. Every raised DentalOSError must use a code from this registry so that
error responses are consistent and discoverable.

Error response schema:
    {
        "error": "DOMAIN_error_name",
        "message": "Human-readable description.",
        "details": {}
    }

Usage:
    from app.core.error_codes import AuthErrors, TenantErrors

    raise AuthError(
        error=AuthErrors.INVALID_CREDENTIALS,
        message="Invalid credentials.",
    )
"""


class AuthErrors:
    """AUTH domain — authentication and authorization error codes."""

    # Credentials and login
    INVALID_CREDENTIALS = "AUTH_invalid_credentials"
    ACCOUNT_LOCKED = "AUTH_account_locked"
    EMAIL_ALREADY_REGISTERED = "AUTH_email_already_registered"
    USER_NOT_FOUND = "AUTH_user_not_found"
    USER_ALREADY_EXISTS = "AUTH_user_already_exists"

    # Token lifecycle
    INVALID_TOKEN = "AUTH_invalid_token"
    INVALID_CLAIMS = "AUTH_invalid_claims"
    TOKEN_EXPIRED = "AUTH_token_expired"
    TOKEN_REVOKED = "AUTH_token_revoked"
    TOKEN_REUSE_DETECTED = "AUTH_token_reuse_detected"
    MISSING_TOKEN = "AUTH_missing_token"
    MISSING_REFRESH_TOKEN = "AUTH_missing_refresh_token"

    # Multi-tenant login flow
    INVALID_TENANT = "AUTH_invalid_tenant"
    TENANT_NOT_FOUND = "AUTH_tenant_not_found"

    # Invitations
    INVITE_ALREADY_USED = "AUTH_invite_already_used"
    INVITE_EXPIRED = "AUTH_invite_expired"
    INVITE_ALREADY_PENDING = "AUTH_invite_already_pending"

    # Permissions and roles
    INSUFFICIENT_PERMISSIONS = "AUTH_insufficient_permissions"
    INSUFFICIENT_PERMISSION = "AUTH_insufficient_permission"
    INSUFFICIENT_ROLE = "AUTH_insufficient_role"


class TenantErrors:
    """TENANT domain — tenant resolution, provisioning, and plan limit error codes."""

    NOT_FOUND = "TENANT_not_found"
    NOT_RESOLVED = "TENANT_not_resolved"
    INVALID_SCHEMA = "TENANT_invalid_schema"
    PROVISION_FAILED = "TENANT_provision_failed"
    PLAN_LIMIT_REACHED = "TENANT_plan_limit_reached"
    SUSPENDED = "TENANT_suspended"


class PatientErrors:
    """PATIENT domain — patient record error codes."""

    NOT_FOUND = "PATIENT_not_found"
    DOCUMENT_ALREADY_EXISTS = "PATIENT_document_already_exists"
    INVALID_DOCUMENT_NUMBER = "PATIENT_invalid_document_number"
    INVALID_PHONE = "PATIENT_invalid_phone"
    ALREADY_DELETED = "PATIENT_already_deleted"


class OdontogramErrors:
    """ODONTOGRAM domain — dental chart and tooth notation error codes."""

    NOT_FOUND = "ODONTOGRAM_not_found"
    INVALID_TOOTH_NUMBER = "ODONTOGRAM_invalid_tooth_number"
    INVALID_FDI_CODE = "ODONTOGRAM_invalid_fdi_code"
    CONDITION_NOT_FOUND = "ODONTOGRAM_condition_not_found"
    SNAPSHOT_FAILED = "ODONTOGRAM_snapshot_failed"


class ClinicalErrors:
    """CLINICAL domain — clinical records and evolution notes error codes."""

    RECORD_NOT_FOUND = "CLINICAL_record_not_found"
    RECORD_ALREADY_SIGNED = "CLINICAL_record_already_signed"
    RECORD_LOCKED = "CLINICAL_record_locked"
    INVALID_CIE10_CODE = "CLINICAL_invalid_cie10_code"
    INVALID_CUPS_CODE = "CLINICAL_invalid_cups_code"
    TEMPLATE_NOT_FOUND = "CLINICAL_template_not_found"


class AppointmentErrors:
    """APPOINTMENT domain — scheduling and agenda error codes."""

    NOT_FOUND = "APPOINTMENT_not_found"
    SLOT_UNAVAILABLE = "APPOINTMENT_slot_unavailable"
    INVALID_STATUS_TRANSITION = "APPOINTMENT_invalid_status_transition"
    OUTSIDE_WORKING_HOURS = "APPOINTMENT_outside_working_hours"
    DOCTOR_NOT_AVAILABLE = "APPOINTMENT_doctor_not_available"
    ALREADY_CANCELLED = "APPOINTMENT_already_cancelled"
    ALREADY_CONFIRMED = "APPOINTMENT_already_confirmed"


class BillingErrors:
    """BILLING domain — invoicing, payments, and quotation error codes."""

    INVOICE_NOT_FOUND = "BILLING_invoice_not_found"
    QUOTATION_NOT_FOUND = "BILLING_quotation_not_found"
    INVOICE_ALREADY_PAID = "BILLING_invoice_already_paid"
    INVOICE_ALREADY_CANCELLED = "BILLING_invoice_already_cancelled"
    INVALID_AMOUNT = "BILLING_invalid_amount"
    DIAN_SUBMISSION_FAILED = "BILLING_dian_submission_failed"
    PAYMENT_METHOD_NOT_SUPPORTED = "BILLING_payment_method_not_supported"


class ConsentErrors:
    """CONSENT domain — informed consent document error codes."""

    NOT_FOUND = "CONSENT_not_found"
    ALREADY_SIGNED = "CONSENT_already_signed"
    ALREADY_REVOKED = "CONSENT_already_revoked"
    SIGNATURE_REQUIRED = "CONSENT_signature_required"
    TEMPLATE_NOT_FOUND = "CONSENT_template_not_found"


class ValidationErrors:
    """VALIDATION domain — input and business rule validation error codes."""

    FAILED = "VALIDATION_failed"
    INVALID_FIELD = "VALIDATION_invalid_field"
    REQUIRED_FIELD_MISSING = "VALIDATION_required_field_missing"


class SystemErrors:
    """SYSTEM domain — infrastructure, HTTP, and platform-level error codes."""

    # HTTP-mapped codes (set by exception_handlers.py)
    BAD_REQUEST = "SYSTEM_bad_request"
    NOT_FOUND = "SYSTEM_not_found"
    METHOD_NOT_ALLOWED = "SYSTEM_method_not_allowed"
    RATE_LIMITED = "SYSTEM_rate_limited"
    RATE_LIMIT_EXCEEDED = "SYSTEM_rate_limit_exceeded"
    INTERNAL_ERROR = "SYSTEM_internal_error"

    # Infrastructure and configuration
    CONFIGURATION_ERROR = "SYSTEM_configuration_error"
    SERVICE_UNAVAILABLE = "SYSTEM_service_unavailable"
    UPSTREAM_ERROR = "SYSTEM_upstream_error"

    # File handling
    FILE_TOO_LARGE = "SYSTEM_file_too_large"
    FILE_TYPE_NOT_ALLOWED = "SYSTEM_file_type_not_allowed"
    FILE_UPLOAD_FAILED = "SYSTEM_file_upload_failed"
