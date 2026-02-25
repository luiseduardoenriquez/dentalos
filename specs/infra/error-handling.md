# Error Handling Spec

---

## Overview

**Feature:** Global error handling strategy for DentalOS. Defines the standard error response format, HTTP status code selection rules, a complete error code registry organized by domain, FastAPI exception handler implementation, logging discipline, frontend error parsing contract, and security constraints.

**Domain:** infra (cross-cutting)

**Priority:** Critical

**Dependencies:** None

---

## 1. Global Error Response Format

Every error response returned by the DentalOS API MUST conform to this schema, regardless of the HTTP status code.

### Schema

```json
{
  "error": "string (machine-readable error code, snake_case)",
  "message": "string (human-readable description, Spanish or English based on tenant locale)",
  "details": {}
}
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `error` | `string` | Yes | Machine-readable error code from the error registry. Format: `DOMAIN_error_name` (e.g., `AUTH_invalid_credentials`). Always lowercase snake_case after the prefix. |
| `message` | `string` | Yes | Human-readable message safe to display to end users. MUST NOT contain stack traces, internal identifiers, schema names, SQL fragments, or any PHI. |
| `details` | `object` | Yes | Additional structured data about the error. Can be an empty object `{}`. For validation errors, contains field-level errors. For rate limiting, contains retry info. |

### Validation Error Details Format

When `error` is `VALIDATION_failed`, the `details` object contains a map of field names to arrays of error messages:

```json
{
  "error": "VALIDATION_failed",
  "message": "One or more fields failed validation",
  "details": {
    "email": ["Invalid email format"],
    "phone": ["Phone number must include country code"],
    "birthdate": ["Birthdate cannot be in the future"]
  }
}
```

### Rate Limit Error Details Format

```json
{
  "error": "SYSTEM_rate_limit_exceeded",
  "message": "Too many requests. Please try again later.",
  "details": {
    "retry_after_seconds": 60,
    "limit": 100,
    "window": "1m"
  }
}
```

### Plan Limit Error Details Format

```json
{
  "error": "TENANT_plan_limit_reached",
  "message": "Your plan limit has been reached",
  "details": {
    "resource": "patients",
    "current_count": 100,
    "max_allowed": 100,
    "upgrade_url": "/settings/plan"
  }
}
```

---

## 2. HTTP Status Code Selection Rules

### Decision Matrix

| Status Code | Name | When to Use | DentalOS Examples |
|-------------|------|-------------|-------------------|
| **400** | Bad Request | Request is malformed: invalid JSON, missing required headers, wrong Content-Type, unparseable body. The server cannot understand the request. | Malformed JSON body, missing `Authorization` header when required, invalid UUID in URL path. |
| **401** | Unauthorized | Authentication is missing or invalid. The caller has not proven their identity. | Missing JWT, expired access token, invalid token signature, revoked refresh token. |
| **403** | Forbidden | Authentication succeeded but the caller lacks permission for this action. | Receptionist attempting to create a clinical record (doctor-only). User from Tenant A accessing Tenant B data. Suspended tenant accessing any resource. |
| **404** | Not Found | The requested resource does not exist within the caller's authorized scope. Also used when revealing the existence of a resource would be a security risk. | Patient ID not found in tenant schema. Tooth number outside valid range. |
| **409** | Conflict | The request conflicts with the current state of a resource. | Duplicate patient document number. Appointment time slot already booked. Attempting to cancel an already-cancelled appointment. |
| **422** | Unprocessable Entity | The request is well-formed JSON and syntactically correct, but semantically invalid per business rules. Field-level validation failures. | Email format invalid, birthdate in the future, invalid CIE-10 code, tooth zone not applicable to the specified tooth, treatment plan item references a non-existent procedure code. |
| **429** | Too Many Requests | Rate limit exceeded. | Per-user, per-tenant, or per-IP rate limit hit. See `infra/rate-limiting.md`. |
| **500** | Internal Server Error | Unhandled server error. The server encountered an unexpected condition. | Database connection failure, unhandled exception, serialization bug. NEVER expose internals. |
| **502** | Bad Gateway | An upstream dependency returned an invalid response. | RabbitMQ unreachable, Redis connection timeout, external API (WhatsApp, DIAN) returned invalid response. |
| **503** | Service Unavailable | The server is temporarily unable to handle the request. | Database in failover, planned maintenance window, circuit breaker open for a critical dependency. |

### 400 vs 422 Decision Rule

The distinction is structural vs semantic:

- **400**: "I cannot parse your request." The JSON is broken, a required header is missing, a path parameter is not a valid UUID format, the Content-Type is wrong.
- **422**: "I understand your request but it violates business rules." The JSON is valid, all fields are present, but `email` is not a valid email format, `tooth_number` is 99 (non-existent tooth), or `appointment_date` is in the past.

**Practical rule:** If Pydantic can parse the body but a custom validator rejects it, use 422. If Pydantic cannot parse the body at all, use 400.

### 401 vs 403 Decision Rule

- **401**: "Who are you?" -- no valid credentials provided.
- **403**: "I know who you are, but you cannot do this." -- valid credentials, insufficient permissions.

**Never use 403 when the user is not authenticated.** Always use 401 first, then 403.

---

## 3. Error Code Registry

All error codes follow the format: `{DOMAIN}_{descriptive_name}`. Domain prefixes are uppercase; the rest is lowercase snake_case.

### AUTH -- Authentication and Authorization Errors

| Error Code | HTTP Status | Description | Example `message` |
|------------|-------------|-------------|-------------------|
| `AUTH_invalid_credentials` | 401 | Email/password combination is incorrect. | "Invalid email or password." |
| `AUTH_token_expired` | 401 | The access token has expired. | "Your session has expired. Please log in again." |
| `AUTH_token_invalid` | 401 | The token is malformed, has an invalid signature, or has been tampered with. | "Invalid authentication token." |
| `AUTH_refresh_token_expired` | 401 | The refresh token has expired (past 30-day window). | "Your session has expired. Please log in again." |
| `AUTH_refresh_token_revoked` | 401 | The refresh token has been revoked (logout, password change, or replay detection). | "Your session is no longer valid. Please log in again." |
| `AUTH_refresh_token_reused` | 401 | A previously used refresh token was presented again (replay attack). All sessions for this user are revoked. | "Security alert: your session has been terminated. Please log in again." |
| `AUTH_insufficient_role` | 403 | The user's role does not have permission for this action. | "You do not have permission to perform this action." |
| `AUTH_insufficient_permission` | 403 | The user lacks a specific permission required by this endpoint. | "You do not have permission to perform this action." |
| `AUTH_account_locked` | 403 | Too many failed login attempts; account is temporarily locked. | "Your account has been temporarily locked. Try again in 15 minutes." |
| `AUTH_account_inactive` | 403 | The user account has been deactivated by an administrator. | "Your account has been deactivated. Contact your clinic administrator." |
| `AUTH_email_not_verified` | 403 | The user has not verified their email address. | "Please verify your email before logging in." |
| `AUTH_invite_expired` | 400 | The invitation link has expired. | "This invitation has expired. Please request a new one." |
| `AUTH_invite_already_accepted` | 409 | The invitation has already been accepted. | "This invitation has already been accepted." |
| `AUTH_password_too_weak` | 422 | The password does not meet complexity requirements. | "Password must be at least 8 characters with uppercase, lowercase, and a number." |
| `AUTH_email_already_registered` | 409 | The email address is already associated with an account in this tenant. | "An account with this email already exists." |
| `AUTH_current_password_incorrect` | 422 | During password change, the current password is wrong. | "Current password is incorrect." |

### TENANT -- Tenant and Plan Errors

| Error Code | HTTP Status | Description | Example `message` |
|------------|-------------|-------------|-------------------|
| `TENANT_not_found` | 404 | Tenant cannot be resolved from the request context. | "Clinic not found." |
| `TENANT_suspended` | 403 | The tenant account has been suspended by a superadmin. | "Your clinic account has been suspended. Contact support." |
| `TENANT_cancelled` | 403 | The tenant account has been cancelled. | "Your clinic account has been cancelled." |
| `TENANT_plan_limit_reached` | 403 | The tenant has reached a plan limit (patients, doctors, storage). `details` includes the specific resource and counts. | "You have reached the maximum number of patients for your plan." |
| `TENANT_feature_not_available` | 403 | The requested feature is not available on the tenant's current plan. | "This feature is not available on your current plan. Upgrade to access it." |
| `TENANT_provisioning_failed` | 500 | Tenant schema provisioning failed during registration. | "An error occurred while setting up your clinic. Please try again." |
| `TENANT_onboarding_incomplete` | 422 | A required onboarding step has not been completed. | "Please complete the onboarding process first." |
| `TENANT_slug_taken` | 409 | The requested tenant slug is already in use. | "This clinic URL is already taken." |

### PATIENT -- Patient Management Errors

| Error Code | HTTP Status | Description | Example `message` |
|------------|-------------|-------------|-------------------|
| `PATIENT_not_found` | 404 | Patient ID does not exist in the tenant schema. | "Patient not found." |
| `PATIENT_duplicate_document` | 409 | A patient with the same document number already exists in this tenant. | "A patient with this document number already exists." |
| `PATIENT_inactive` | 422 | Operation attempted on a deactivated patient. | "This patient has been deactivated." |
| `PATIENT_has_pending_balance` | 422 | Cannot deactivate a patient with outstanding balance. | "Cannot deactivate patient with pending balance." |
| `PATIENT_import_failed` | 422 | Bulk import failed validation. `details` contains row-level errors. | "Import failed. See details for specific errors." |
| `PATIENT_merge_conflict` | 409 | Patient merge cannot be completed due to conflicting data. | "Cannot merge patients due to data conflicts." |
| `PATIENT_document_not_found` | 404 | Patient document (file) not found. | "Document not found." |
| `PATIENT_portal_already_active` | 409 | Patient already has portal access. | "This patient already has portal access." |

### ODONTOGRAM -- Odontogram Errors

| Error Code | HTTP Status | Description | Example `message` |
|------------|-------------|-------------|-------------------|
| `ODONTOGRAM_tooth_not_found` | 404 | Tooth number is not valid for the patient's current dentition (adult vs pediatric). | "Tooth not found for this patient's dentition type." |
| `ODONTOGRAM_invalid_condition` | 422 | The condition code is not in the allowed condition catalog. | "Invalid dental condition code." |
| `ODONTOGRAM_invalid_zone` | 422 | The specified zone is not applicable to the given tooth. | "Invalid zone for this tooth." |
| `ODONTOGRAM_condition_not_found` | 404 | The condition ID does not exist on the specified tooth. | "Condition not found on this tooth." |
| `ODONTOGRAM_snapshot_not_found` | 404 | The snapshot ID does not exist. | "Odontogram snapshot not found." |
| `ODONTOGRAM_incompatible_dentition` | 422 | Cannot switch dentition type because conditions exist on teeth that would be removed. | "Cannot switch dentition type. Conditions exist on teeth that would be removed." |
| `ODONTOGRAM_bulk_partial_failure` | 422 | One or more items in a bulk update failed validation. `details` contains per-item errors. | "Some updates failed validation. See details." |

### CLINICAL -- Clinical Records Errors

| Error Code | HTTP Status | Description | Example `message` |
|------------|-------------|-------------|-------------------|
| `CLINICAL_record_not_found` | 404 | Clinical record does not exist. | "Clinical record not found." |
| `CLINICAL_record_locked` | 403 | Clinical record is past the edit window (24h) and cannot be modified without clinic_owner override. | "This record can no longer be edited. Contact your clinic administrator." |
| `CLINICAL_invalid_cie10_code` | 422 | The CIE-10 code does not exist in the catalog. | "Invalid CIE-10 diagnosis code." |
| `CLINICAL_invalid_cups_code` | 422 | The CUPS procedure code does not exist in the catalog. | "Invalid CUPS procedure code." |
| `CLINICAL_diagnosis_not_found` | 404 | Diagnosis ID does not exist. | "Diagnosis not found." |
| `CLINICAL_procedure_not_found` | 404 | Procedure ID does not exist. | "Procedure not found." |
| `CLINICAL_anamnesis_not_found` | 404 | Patient has no anamnesis record. | "No anamnesis record found for this patient." |
| `CLINICAL_record_type_invalid` | 422 | The record type is not one of the allowed types. | "Invalid clinical record type." |

### APPOINTMENT -- Appointment and Scheduling Errors

| Error Code | HTTP Status | Description | Example `message` |
|------------|-------------|-------------|-------------------|
| `APPOINTMENT_not_found` | 404 | Appointment does not exist. | "Appointment not found." |
| `APPOINTMENT_slot_unavailable` | 409 | The requested time slot is no longer available. | "This time slot is no longer available." |
| `APPOINTMENT_conflict` | 409 | The appointment conflicts with an existing appointment for the same doctor. | "This time conflicts with an existing appointment." |
| `APPOINTMENT_past_date` | 422 | Cannot create or reschedule an appointment to a past date/time. | "Cannot schedule an appointment in the past." |
| `APPOINTMENT_outside_schedule` | 422 | The requested time is outside the doctor's working hours. | "This time is outside the doctor's working hours." |
| `APPOINTMENT_invalid_duration` | 422 | Appointment duration is invalid (too short or too long). | "Invalid appointment duration." |
| `APPOINTMENT_already_cancelled` | 409 | The appointment has already been cancelled. | "This appointment has already been cancelled." |
| `APPOINTMENT_already_completed` | 409 | The appointment has already been completed. | "This appointment has already been completed." |
| `APPOINTMENT_cancellation_too_late` | 422 | The cancellation is within the minimum notice period. | "Cannot cancel an appointment with less than the required notice." |
| `APPOINTMENT_doctor_unavailable` | 409 | The doctor is blocked/unavailable during this time (vacation, break). | "The doctor is unavailable during this time." |
| `APPOINTMENT_waitlist_not_found` | 404 | Waitlist entry does not exist. | "Waitlist entry not found." |
| `APPOINTMENT_invalid_status_transition` | 422 | Invalid state transition (e.g., scheduled -> completed without confirming). | "Invalid appointment status change." |

### BILLING -- Billing and Payment Errors

| Error Code | HTTP Status | Description | Example `message` |
|------------|-------------|-------------|-------------------|
| `BILLING_invoice_not_found` | 404 | Invoice does not exist. | "Invoice not found." |
| `BILLING_invoice_already_paid` | 409 | The invoice has already been fully paid. | "This invoice has already been paid." |
| `BILLING_invoice_not_editable` | 422 | The invoice is not in draft status and cannot be modified. | "This invoice can no longer be edited." |
| `BILLING_invoice_already_sent` | 409 | The invoice has already been sent to the patient. | "This invoice has already been sent." |
| `BILLING_insufficient_balance` | 422 | Payment amount exceeds the outstanding balance. | "Payment amount exceeds outstanding balance." |
| `BILLING_invalid_payment_method` | 422 | The payment method is not one of the allowed methods. | "Invalid payment method." |
| `BILLING_payment_plan_not_found` | 404 | Payment plan does not exist. | "Payment plan not found." |
| `BILLING_payment_plan_active` | 409 | Patient already has an active payment plan for this invoice. | "An active payment plan already exists for this invoice." |
| `BILLING_service_not_found` | 404 | Service catalog entry does not exist. | "Service not found in catalog." |
| `BILLING_installment_not_due` | 422 | Attempting to pay an installment that is not yet due. | "This installment is not yet due." |
| `BILLING_electronic_invoice_failed` | 502 | Electronic invoice generation failed at the external provider. | "Electronic invoice generation failed. Please try again." |

### CONSENT -- Informed Consent Errors

| Error Code | HTTP Status | Description | Example `message` |
|------------|-------------|-------------|-------------------|
| `CONSENT_template_not_found` | 404 | Consent template does not exist. | "Consent template not found." |
| `CONSENT_not_found` | 404 | Consent record does not exist. | "Consent record not found." |
| `CONSENT_already_signed` | 409 | The consent has already been signed and is immutable. | "This consent has already been signed." |
| `CONSENT_already_voided` | 409 | The consent has already been voided. | "This consent has already been voided." |
| `CONSENT_signature_required` | 422 | Missing signature data in the signing request. | "Signature is required to sign this consent." |

### TREATMENT_PLAN -- Treatment Plan Errors

| Error Code | HTTP Status | Description | Example `message` |
|------------|-------------|-------------|-------------------|
| `TREATMENT_PLAN_not_found` | 404 | Treatment plan does not exist. | "Treatment plan not found." |
| `TREATMENT_PLAN_item_not_found` | 404 | Treatment plan item does not exist. | "Treatment plan item not found." |
| `TREATMENT_PLAN_not_editable` | 422 | Plan is not in a status that allows editing (e.g., already completed). | "This treatment plan can no longer be edited." |
| `TREATMENT_PLAN_invalid_status_transition` | 422 | Invalid state transition (e.g., draft -> completed without activation). | "Invalid treatment plan status change." |
| `TREATMENT_PLAN_already_approved` | 409 | The plan has already been approved by the patient. | "This treatment plan has already been approved." |

### PRESCRIPTION -- Prescription Errors

| Error Code | HTTP Status | Description | Example `message` |
|------------|-------------|-------------|-------------------|
| `PRESCRIPTION_not_found` | 404 | Prescription does not exist. | "Prescription not found." |
| `PRESCRIPTION_medication_not_found` | 404 | Medication not found in the catalog. | "Medication not found in catalog." |
| `PRESCRIPTION_not_editable` | 422 | Prescription has already been finalized. | "This prescription can no longer be edited." |

### MESSAGE -- Messaging Errors

| Error Code | HTTP Status | Description | Example `message` |
|------------|-------------|-------------|-------------------|
| `MESSAGE_thread_not_found` | 404 | Message thread does not exist. | "Message thread not found." |
| `MESSAGE_not_found` | 404 | Message does not exist. | "Message not found." |
| `MESSAGE_thread_closed` | 422 | The message thread has been closed. | "This conversation has been closed." |

### VALIDATION -- Generic Validation Errors

| Error Code | HTTP Status | Description | Example `message` |
|------------|-------------|-------------|-------------------|
| `VALIDATION_failed` | 422 | One or more fields failed validation. `details` contains field-level errors. | "Validation errors occurred." |
| `VALIDATION_missing_required_field` | 422 | A required field is missing. | "Required field is missing." |
| `VALIDATION_invalid_format` | 422 | A field value has an invalid format. | "Invalid format." |
| `VALIDATION_value_out_of_range` | 422 | A numeric value is outside the allowed range. | "Value is out of allowed range." |
| `VALIDATION_invalid_enum_value` | 422 | A field value is not one of the allowed enum values. | "Invalid value. Allowed values: ..." |
| `VALIDATION_string_too_long` | 422 | A string field exceeds the maximum allowed length. | "Value exceeds maximum length." |
| `VALIDATION_invalid_uuid` | 400 | A UUID parameter or field is not a valid UUID format. | "Invalid identifier format." |

### FILE -- File Upload/Storage Errors

| Error Code | HTTP Status | Description | Example `message` |
|------------|-------------|-------------|-------------------|
| `FILE_too_large` | 422 | The uploaded file exceeds the maximum allowed size. | "File size exceeds the maximum allowed limit." |
| `FILE_invalid_type` | 422 | The uploaded file MIME type is not allowed. | "File type is not allowed." |
| `FILE_storage_limit_reached` | 403 | The tenant has reached their storage quota. | "Storage limit reached. Upgrade your plan for more storage." |
| `FILE_upload_failed` | 500 | File upload to object storage failed. | "File upload failed. Please try again." |
| `FILE_not_found` | 404 | The requested file does not exist. | "File not found." |

### SYSTEM -- Internal and Infrastructure Errors

| Error Code | HTTP Status | Description | Example `message` |
|------------|-------------|-------------|-------------------|
| `SYSTEM_internal_error` | 500 | An unhandled internal error occurred. Generic fallback. | "An unexpected error occurred. Please try again later." |
| `SYSTEM_database_error` | 500 | A database operation failed unexpectedly. | "An unexpected error occurred. Please try again later." |
| `SYSTEM_cache_error` | 500 | Redis cache operation failed. Non-fatal; operation may succeed without cache. | "An unexpected error occurred. Please try again later." |
| `SYSTEM_queue_error` | 500 | RabbitMQ message publishing failed. | "An unexpected error occurred. Please try again later." |
| `SYSTEM_external_service_error` | 502 | An external service (WhatsApp API, DIAN, etc.) returned an error. | "An external service is temporarily unavailable. Please try again." |
| `SYSTEM_service_unavailable` | 503 | The service is temporarily unavailable (maintenance, overload). | "The service is temporarily unavailable. Please try again shortly." |
| `SYSTEM_rate_limit_exceeded` | 429 | Rate limit exceeded. `details` includes `retry_after_seconds`. | "Too many requests. Please try again later." |
| `SYSTEM_maintenance_mode` | 503 | The system is in planned maintenance mode. | "The system is under maintenance. Please try again shortly." |

---

## 4. FastAPI Exception Handlers

### 4.1 Custom Exception Classes

```python
# app/core/exceptions.py

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
    pass


class InvalidCredentialsError(AuthError):
    def __init__(self) -> None:
        super().__init__(
            error="AUTH_invalid_credentials",
            message="Invalid email or password.",
            status_code=401,
        )


class TokenExpiredError(AuthError):
    def __init__(self) -> None:
        super().__init__(
            error="AUTH_token_expired",
            message="Your session has expired. Please log in again.",
            status_code=401,
        )


class TokenInvalidError(AuthError):
    def __init__(self) -> None:
        super().__init__(
            error="AUTH_token_invalid",
            message="Invalid authentication token.",
            status_code=401,
        )


class InsufficientRoleError(AuthError):
    def __init__(self) -> None:
        super().__init__(
            error="AUTH_insufficient_role",
            message="You do not have permission to perform this action.",
            status_code=403,
        )


class AccountLockedError(AuthError):
    def __init__(self, retry_after_minutes: int = 15) -> None:
        super().__init__(
            error="AUTH_account_locked",
            message=f"Your account has been temporarily locked. Try again in {retry_after_minutes} minutes.",
            status_code=403,
            details={"retry_after_minutes": retry_after_minutes},
        )


# --- Tenant Errors ---

class TenantError(DentalOSError):
    """Base class for tenant-related errors."""
    pass


class TenantSuspendedError(TenantError):
    def __init__(self) -> None:
        super().__init__(
            error="TENANT_suspended",
            message="Your clinic account has been suspended. Contact support.",
            status_code=403,
        )


class PlanLimitReachedError(TenantError):
    def __init__(
        self, resource: str, current_count: int, max_allowed: int
    ) -> None:
        super().__init__(
            error="TENANT_plan_limit_reached",
            message=f"You have reached the maximum number of {resource} for your plan.",
            status_code=403,
            details={
                "resource": resource,
                "current_count": current_count,
                "max_allowed": max_allowed,
                "upgrade_url": "/settings/plan",
            },
        )


# --- Resource Errors (Generic pattern for domain entities) ---

class ResourceNotFoundError(DentalOSError):
    """Generic resource not found. Subclass per domain for specific error codes."""

    def __init__(self, error: str, resource_name: str) -> None:
        super().__init__(
            error=error,
            message=f"{resource_name} not found.",
            status_code=404,
        )


class PatientNotFoundError(ResourceNotFoundError):
    def __init__(self) -> None:
        super().__init__(error="PATIENT_not_found", resource_name="Patient")


class AppointmentNotFoundError(ResourceNotFoundError):
    def __init__(self) -> None:
        super().__init__(error="APPOINTMENT_not_found", resource_name="Appointment")


# --- Conflict Errors ---

class ResourceConflictError(DentalOSError):
    """Generic conflict error for duplicate resources or state conflicts."""

    def __init__(self, error: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            error=error,
            message=message,
            status_code=409,
            details=details or {},
        )


class DuplicatePatientDocumentError(ResourceConflictError):
    def __init__(self) -> None:
        super().__init__(
            error="PATIENT_duplicate_document",
            message="A patient with this document number already exists.",
        )


class AppointmentSlotUnavailableError(ResourceConflictError):
    def __init__(self) -> None:
        super().__init__(
            error="APPOINTMENT_slot_unavailable",
            message="This time slot is no longer available.",
        )


# --- Odontogram Errors ---

class OdontogramError(DentalOSError):
    """Base class for odontogram errors."""
    pass


class ToothNotFoundError(OdontogramError):
    def __init__(self, tooth_number: int) -> None:
        super().__init__(
            error="ODONTOGRAM_tooth_not_found",
            message="Tooth not found for this patient's dentition type.",
            status_code=404,
            details={"tooth_number": tooth_number},
        )


class InvalidConditionError(OdontogramError):
    def __init__(self, condition_code: str) -> None:
        super().__init__(
            error="ODONTOGRAM_invalid_condition",
            message="Invalid dental condition code.",
            status_code=422,
            details={"condition_code": condition_code},
        )


class InvalidZoneError(OdontogramError):
    def __init__(self, zone: str, tooth_number: int) -> None:
        super().__init__(
            error="ODONTOGRAM_invalid_zone",
            message="Invalid zone for this tooth.",
            status_code=422,
            details={"zone": zone, "tooth_number": tooth_number},
        )


# --- Billing Errors ---

class BillingError(DentalOSError):
    """Base class for billing errors."""
    pass


class InvoiceAlreadyPaidError(BillingError):
    def __init__(self) -> None:
        super().__init__(
            error="BILLING_invoice_already_paid",
            message="This invoice has already been paid.",
            status_code=409,
        )


class InsufficientBalanceError(BillingError):
    def __init__(self) -> None:
        super().__init__(
            error="BILLING_insufficient_balance",
            message="Payment amount exceeds outstanding balance.",
            status_code=422,
        )


# --- Validation Error (wraps Pydantic) ---

class BusinessValidationError(DentalOSError):
    """For business rule validation failures (not Pydantic schema validation)."""

    def __init__(self, message: str, field_errors: dict[str, list[str]] | None = None) -> None:
        super().__init__(
            error="VALIDATION_failed",
            message=message,
            status_code=422,
            details=field_errors or {},
        )
```

### 4.2 Exception Handler Registration

```python
# app/core/exception_handlers.py

import logging
import traceback
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import DentalOSError

logger = logging.getLogger("dentalos.errors")


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI application."""

    @app.exception_handler(DentalOSError)
    async def dentalos_error_handler(request: Request, exc: DentalOSError):
        """Handle all DentalOS application errors."""
        # Log at appropriate level based on status code
        log_context = _build_log_context(request, exc)

        if exc.status_code >= 500:
            logger.error(
                "Server error: %s (code=%s, status=%d, trace_id=%s)",
                exc.message,
                exc.error,
                exc.status_code,
                log_context["trace_id"],
                extra=log_context,
            )
        elif exc.status_code >= 400:
            logger.warning(
                "Client error: %s (code=%s, status=%d)",
                exc.error,
                exc.message,
                exc.status_code,
                extra=log_context,
            )

        return _build_error_response(exc.status_code, exc.error, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """Convert Pydantic validation errors to standard error format."""
        field_errors: dict[str, list[str]] = {}
        for error in exc.errors():
            # Build field path from error location, excluding "body" prefix
            loc = error.get("loc", ())
            field_path = ".".join(str(part) for part in loc if part != "body")
            if not field_path:
                field_path = "__root__"
            field_errors.setdefault(field_path, []).append(error.get("msg", "Invalid value"))

        return _build_error_response(
            status_code=422,
            error="VALIDATION_failed",
            message="Validation errors occurred.",
            details=field_errors,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Convert Starlette HTTP exceptions to standard error format."""
        error_map = {
            400: "SYSTEM_bad_request",
            404: "SYSTEM_not_found",
            405: "SYSTEM_method_not_allowed",
            429: "SYSTEM_rate_limit_exceeded",
            500: "SYSTEM_internal_error",
        }
        error_code = error_map.get(exc.status_code, f"SYSTEM_http_{exc.status_code}")

        return _build_error_response(
            status_code=exc.status_code,
            error=error_code,
            message=str(exc.detail) if exc.detail else "An error occurred.",
            details={},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Catch-all for unhandled exceptions. NEVER expose internals."""
        trace_id = str(uuid4())

        # Log the FULL exception with stack trace for debugging
        logger.critical(
            "Unhandled exception (trace_id=%s): %s",
            trace_id,
            str(exc),
            extra={
                "trace_id": trace_id,
                "path": request.url.path,
                "method": request.method,
                "exception_type": type(exc).__name__,
                "traceback": traceback.format_exc(),
            },
            exc_info=True,
        )

        # Return generic error to client -- NO stack trace, NO exception details
        return _build_error_response(
            status_code=500,
            error="SYSTEM_internal_error",
            message="An unexpected error occurred. Please try again later.",
            details={"trace_id": trace_id},
        )


def _build_error_response(
    status_code: int, error: str, message: str, details: dict
):
    """Build standardized JSON error response."""
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=status_code,
        content={
            "error": error,
            "message": message,
            "details": details,
        },
    )


def _build_log_context(request: Request, exc: DentalOSError) -> dict:
    """Build structured log context. NEVER include PHI."""
    return {
        "trace_id": str(uuid4()),
        "error_code": exc.error,
        "status_code": exc.status_code,
        "path": request.url.path,
        "method": request.method,
        # Tenant ID is safe to log; it is not PHI
        "tenant_id": getattr(request.state, "tenant_id", None),
        "user_id": getattr(request.state, "user_id", None),
    }
```

### 4.3 Usage in Route Handlers

```python
# Example: patient creation endpoint
from app.core.exceptions import (
    DuplicatePatientDocumentError,
    PatientNotFoundError,
    PlanLimitReachedError,
)


@router.post("/patients", status_code=201)
async def create_patient(
    body: PatientCreateSchema,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(require_role(["clinic_owner", "doctor", "assistant", "receptionist"])),
    db: AsyncSession = Depends(get_tenant_session),
):
    # Check plan limits
    patient_count = await patient_repo.count(db)
    if patient_count >= tenant.plan.max_patients:
        raise PlanLimitReachedError(
            resource="patients",
            current_count=patient_count,
            max_allowed=tenant.plan.max_patients,
        )

    # Check for duplicate document
    existing = await patient_repo.find_by_document(db, body.document_number)
    if existing:
        raise DuplicatePatientDocumentError()

    patient = await patient_repo.create(db, body)
    return patient
```

---

## 5. Logging Strategy

### 5.1 What to Log

All logs MUST be structured JSON and include the following base fields:

| Field | Source | Always Present | Description |
|-------|--------|----------------|-------------|
| `timestamp` | auto | Yes | ISO 8601 timestamp with timezone. |
| `level` | auto | Yes | Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL. |
| `logger` | auto | Yes | Logger name (e.g., `dentalos.auth`, `dentalos.patients`). |
| `message` | developer | Yes | Human-readable log message. |
| `tenant_id` | request | When available | Tenant UUID. Safe to log. |
| `user_id` | request | When available | User UUID. Safe to log. |
| `request_id` | middleware | Yes (in request context) | Unique request identifier for tracing. |
| `path` | request | Yes (in request context) | API path (e.g., `/api/v1/patients`). |
| `method` | request | Yes (in request context) | HTTP method. |
| `status_code` | response | On response | HTTP status code returned. |
| `duration_ms` | middleware | On response | Request processing time. |
| `error_code` | exception | On error | DentalOS error code. |
| `trace_id` | exception | On 5xx errors | Unique trace ID returned to client. |

### 5.2 Log Levels

| Level | When to Use |
|-------|------------|
| `DEBUG` | Detailed diagnostic info. Database query plans, cache hit/miss, dependency injection resolution. Never in production unless temporarily enabled. |
| `INFO` | Normal operations. Request received, request completed, user logged in, appointment created, tenant provisioned. |
| `WARNING` | Abnormal but handled situations. Rate limit approaching, cache miss on expected key, deprecated endpoint called, failed login attempt. |
| `ERROR` | Failures that impact the current request. Database query failed, external service timeout, unhandled business logic error. |
| `CRITICAL` | System-level failures. Database connection pool exhausted, Redis unreachable, RabbitMQ connection lost, unhandled exception (catch-all handler). |

### 5.3 What NEVER to Log

**PHI (Protected Health Information) MUST NEVER appear in logs.** This is a non-negotiable rule enforced by healthcare regulations.

| Category | Examples of Forbidden Log Content |
|----------|-----------------------------------|
| Patient identity | Patient name, document number (cedula/CURP/RUT), email, phone, address. |
| Clinical data | Diagnoses, procedures, odontogram conditions, prescriptions, anamnesis, clinical notes. |
| Financial data | Invoice amounts, payment details, insurance information, card numbers. |
| Authentication secrets | Passwords (hashed or otherwise), JWT token values, refresh tokens, API keys. |
| Internal architecture | Database schema names (`tenant_tn_abc123`), internal table names in error messages, SQL queries with data, stack traces in responses. |

**What IS safe to log:** UUIDs (tenant_id, user_id, patient_id, appointment_id), error codes, HTTP paths, status codes, durations, counts, boolean flags.

### 5.4 Logging Configuration

```python
# app/core/logging_config.py

import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S%z",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "dentalos": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "sqlalchemy.engine": {
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": False,
        },
    },
    "root": {
        "level": "WARNING",
        "handlers": ["console"],
    },
}
```

---

## 6. Frontend Error Handling Contract

### 6.1 Error Response Parsing

The frontend (React/Next.js with React Query / TanStack Query) MUST parse errors using the following contract.

**Every API error response is guaranteed to have this shape:**

```typescript
// types/api-error.ts

interface ApiError {
  error: string;       // machine-readable error code
  message: string;     // human-readable, safe to display
  details: Record<string, unknown>;  // additional data, varies by error type
}

interface ValidationErrorDetails {
  [fieldName: string]: string[];  // field name -> array of error messages
}

interface RateLimitErrorDetails {
  retry_after_seconds: number;
  limit: number;
  window: string;
}

interface PlanLimitErrorDetails {
  resource: string;
  current_count: number;
  max_allowed: number;
  upgrade_url: string;
}
```

### 6.2 Error Handling Strategy by Status Code

| Status Code | Frontend Behavior |
|-------------|-------------------|
| **401** | Redirect to login page. Clear local auth state. If on a refresh token call, the session has fully expired. |
| **403** with `TENANT_suspended` | Show full-screen suspension notice with support contact. |
| **403** with `TENANT_plan_limit_reached` | Show upgrade prompt modal with plan comparison. |
| **403** with `AUTH_insufficient_role` | Show "access denied" toast notification. Do NOT redirect. |
| **404** | Show "not found" state in the component. Navigate back or show empty state. |
| **409** | Show conflict message in a toast. Suggest refreshing the data. |
| **422** with `VALIDATION_failed` | Map `details` fields to form field errors. Highlight invalid fields. |
| **429** | Show "too many requests" toast. Disable retry button for `retry_after_seconds`. |
| **500** | Show generic "something went wrong" message. Include `trace_id` from `details` if present for support tickets. |
| **502, 503** | Show "service temporarily unavailable" banner. Auto-retry with exponential backoff (max 3 retries). |

### 6.3 Global Error Interceptor

```typescript
// lib/api-client.ts

import axios, { AxiosError } from "axios";

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    const apiError = error.response?.data;
    const status = error.response?.status;

    // Handle 401: redirect to login
    if (status === 401) {
      // Clear tokens from local storage
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      window.location.href = "/login";
      return Promise.reject(error);
    }

    // Handle tenant suspension: show blocking modal
    if (status === 403 && apiError?.error === "TENANT_suspended") {
      window.dispatchEvent(new CustomEvent("tenant:suspended"));
      return Promise.reject(error);
    }

    // Handle plan limits: show upgrade modal
    if (status === 403 && apiError?.error === "TENANT_plan_limit_reached") {
      window.dispatchEvent(
        new CustomEvent("plan:limit-reached", { detail: apiError.details })
      );
      return Promise.reject(error);
    }

    return Promise.reject(error);
  }
);
```

### 6.4 Form Validation Error Mapping

```typescript
// hooks/use-form-errors.ts

function mapApiErrorsToForm(
  apiError: ApiError,
  setError: UseFormSetError<any>
) {
  if (apiError.error === "VALIDATION_failed" && apiError.details) {
    for (const [field, messages] of Object.entries(apiError.details)) {
      if (Array.isArray(messages) && messages.length > 0) {
        setError(field, { type: "server", message: messages[0] });
      }
    }
  }
}
```

---

## 7. Security Constraints

### 7.1 Rules

1. **NEVER expose stack traces** in any error response, regardless of environment. Stack traces are logged server-side only.
2. **NEVER include internal identifiers** such as database schema names, internal table names, or SQL fragments in error messages.
3. **NEVER reveal resource existence** to unauthorized users. If a user requests a resource from another tenant, return 404 (not 403) to avoid confirming the resource exists.
4. **NEVER include PHI** in error messages or details. If a validation error references a patient field, use the field name only, not the field value.
5. **NEVER return different error messages** for "user not found" vs "wrong password" during authentication. Always return `AUTH_invalid_credentials` for both cases.
6. **Rate limit all authentication endpoints** to prevent brute-force attacks. See `infra/rate-limiting.md`.
7. **Include `trace_id`** in 5xx error responses so users can reference it in support tickets. The trace_id maps to the full error context in server logs.
8. **Sanitize all user input** before including it in error messages. Never reflect raw user input in error responses (prevents reflected XSS in API consumers that render error messages as HTML).

### 7.2 Error Message Localization

Error messages are returned in the locale configured for the tenant (default: `es` for Spanish, `en` for English). The error code (`error` field) is always in English and machine-readable. Localization applies only to the `message` field.

The `message` field serves as a sensible default. The frontend MAY override error messages using the `error` code to look up locale-specific translations in its own translation files.

---

## 8. Out of Scope

This spec explicitly does NOT cover:

- Retry logic for outgoing requests to external services (covered in `infra/background-processing.md`).
- Rate limiting implementation details (covered in `infra/rate-limiting.md`).
- Audit log entry format and storage (covered in `infra/audit-logging.md`).
- WebSocket error handling (will be defined if/when real-time features are added).
- Error tracking service configuration (Sentry setup is in `infra/monitoring-observability.md`).
- Offline error handling and sync conflict resolution (covered in `infra/offline-sync-strategy.md`).
- Error message translation files (will be managed as part of the frontend i18n system).

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec. Complete error code registry, exception handler implementation, logging strategy, frontend contract, security constraints. |
