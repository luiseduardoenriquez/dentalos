from typing import Any


class DentalOSError(Exception):
    """Base exception for all DentalOS application errors."""

    def __init__(
        self,
        error: str,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.error = error
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


# --- Auth Errors ---


class AuthError(DentalOSError):
    """Base class for authentication/authorization errors."""

    def __init__(
        self,
        error: str = "AUTH_error",
        message: str = "Authentication error.",
        status_code: int = 401,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(error=error, message=message, status_code=status_code, details=details)


# --- Tenant Errors ---


class TenantError(DentalOSError):
    """Base class for tenant-related errors."""

    def __init__(
        self,
        error: str = "TENANT_error",
        message: str = "Tenant error.",
        status_code: int = 403,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(error=error, message=message, status_code=status_code, details=details)


# --- Rate Limit Errors ---


class RateLimitError(DentalOSError):
    """Rate limit exceeded error."""

    def __init__(
        self,
        message: str = "Too many requests. Please try again later.",
        retry_after: int = 60,
    ) -> None:
        super().__init__(
            error="SYSTEM_rate_limited",
            message=message,
            status_code=429,
            details={"retry_after": retry_after},
        )


# --- Resource Errors ---


class ResourceNotFoundError(DentalOSError):
    """Generic resource not found."""

    def __init__(self, error: str, resource_name: str) -> None:
        super().__init__(
            error=error,
            message=f"{resource_name} not found.",
            status_code=404,
        )


class ResourceConflictError(DentalOSError):
    """Generic conflict error for duplicate resources or state conflicts."""

    def __init__(self, error: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            error=error,
            message=message,
            status_code=409,
            details=details or {},
        )


class BusinessValidationError(DentalOSError):
    """For business rule validation failures (not Pydantic schema validation)."""

    def __init__(self, message: str, field_errors: dict[str, list[str]] | None = None) -> None:
        super().__init__(
            error="VALIDATION_failed",
            message=message,
            status_code=422,
            details=field_errors or {},
        )


# --- Domain-Specific Base Errors ---


class OdontogramError(DentalOSError):
    """Base class for odontogram errors."""

    pass


class BillingError(DentalOSError):
    """Base class for billing errors."""

    pass


class FileError(DentalOSError):
    """Base class for file upload/storage errors."""

    pass


class ClinicalError(DentalOSError):
    """Base class for clinical domain errors (diagnoses, procedures)."""

    pass


class TreatmentPlanError(DentalOSError):
    """Base class for treatment plan errors."""

    pass


class QuotationError(DentalOSError):
    """Base class for quotation errors."""

    pass


class ConsentError(DentalOSError):
    """Base class for consent errors."""

    pass


class SignatureError(DentalOSError):
    """Base class for digital signature errors."""

    pass


class PrescriptionError(DentalOSError):
    """Base class for prescription errors."""

    pass


class AppointmentError(DentalOSError):
    """Base class for appointment/agenda errors."""

    pass


class ScheduleError(DentalOSError):
    """Base class for doctor schedule errors."""

    pass


class VoiceError(DentalOSError):
    """Base class for voice-to-odontogram errors."""

    pass
