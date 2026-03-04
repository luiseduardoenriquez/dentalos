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
    PAST_START_TIME = "APPOINTMENT_past_start_time"
    SCHEDULE_CONFLICT = "APPOINTMENT_schedule_conflict"
    DURING_BREAK = "APPOINTMENT_during_break"
    CANNOT_COMPLETE = "APPOINTMENT_cannot_complete"
    CANNOT_NO_SHOW = "APPOINTMENT_cannot_no_show"
    MIN_CANCEL_NOTICE = "APPOINTMENT_min_cancel_notice"


class ScheduleErrors:
    """SCHEDULE domain — doctor schedule and availability error codes."""

    NOT_FOUND = "SCHEDULE_not_found"
    INVALID_DAY = "SCHEDULE_invalid_day"
    OVERLAP = "SCHEDULE_overlap"
    BLOCK_CONFLICT = "SCHEDULE_block_conflict"
    INVALID_TIME_RANGE = "SCHEDULE_invalid_time_range"
    BLOCK_IN_PAST = "SCHEDULE_block_in_past"
    MISSING_WORKING_HOURS = "SCHEDULE_missing_working_hours"
    BREAK_OUTSIDE_HOURS = "SCHEDULE_break_outside_hours"


class WaitlistErrors:
    """WAITLIST domain — appointment waitlist error codes."""

    NOT_FOUND = "WAITLIST_not_found"
    ALREADY_EXISTS = "WAITLIST_already_exists"
    ALREADY_NOTIFIED = "WAITLIST_already_notified"
    EXPIRED = "WAITLIST_expired"
    PATIENT_NOT_FOUND = "WAITLIST_patient_not_found"


class VoiceErrors:
    """VOICE domain — voice-to-odontogram pipeline error codes."""

    SESSION_NOT_FOUND = "VOICE_session_not_found"
    SESSION_EXPIRED = "VOICE_session_expired"
    ADDON_REQUIRED = "VOICE_addon_required"
    RATE_LIMIT_EXCEEDED = "VOICE_rate_limit_exceeded"
    UPLOAD_FAILED = "VOICE_upload_failed"
    TRANSCRIPTION_FAILED = "VOICE_transcription_failed"
    PARSE_FAILED = "VOICE_parse_failed"
    APPLY_FAILED = "VOICE_apply_failed"


class BillingErrors:
    """BILLING domain — invoicing, payments, and quotation error codes."""

    INVOICE_NOT_FOUND = "BILLING_invoice_not_found"
    QUOTATION_NOT_FOUND = "BILLING_quotation_not_found"
    INVOICE_ALREADY_PAID = "BILLING_invoice_already_paid"
    INVOICE_ALREADY_CANCELLED = "BILLING_invoice_already_cancelled"
    INVALID_AMOUNT = "BILLING_invalid_amount"
    DIAN_SUBMISSION_FAILED = "BILLING_dian_submission_failed"
    PAYMENT_METHOD_NOT_SUPPORTED = "BILLING_payment_method_not_supported"
    PAYMENT_EXCEEDS_BALANCE = "BILLING_payment_exceeds_balance"
    INVOICE_NOT_PAYABLE = "BILLING_invoice_not_payable"
    PLAN_ALREADY_EXISTS = "BILLING_plan_already_exists"
    INSTALLMENT_NOT_FOUND = "BILLING_installment_not_found"


class ConsentErrors:
    """CONSENT domain — informed consent document error codes."""

    NOT_FOUND = "CONSENT_not_found"
    ALREADY_SIGNED = "CONSENT_already_signed"
    ALREADY_REVOKED = "CONSENT_already_revoked"
    SIGNATURE_REQUIRED = "CONSENT_signature_required"
    TEMPLATE_NOT_FOUND = "CONSENT_template_not_found"


class TreatmentPlanErrors:
    """TREATMENT_PLAN domain — treatment plan error codes."""

    NOT_FOUND = "TREATMENT_PLAN_not_found"
    ITEM_NOT_FOUND = "TREATMENT_PLAN_item_not_found"
    ALREADY_APPROVED = "TREATMENT_PLAN_already_approved"
    ALREADY_COMPLETED = "TREATMENT_PLAN_already_completed"
    ALREADY_CANCELLED = "TREATMENT_PLAN_already_cancelled"
    INVALID_STATUS_TRANSITION = "TREATMENT_PLAN_invalid_status_transition"
    ITEM_ALREADY_COMPLETED = "TREATMENT_PLAN_item_already_completed"
    APPROVAL_REQUIRED = "TREATMENT_PLAN_approval_required"


class QuotationErrors:
    """QUOTATION domain — quotation error codes."""

    NOT_FOUND = "QUOTATION_not_found"
    ALREADY_APPROVED = "QUOTATION_already_approved"
    ALREADY_EXPIRED = "QUOTATION_already_expired"
    DUPLICATE_FOR_PLAN = "QUOTATION_duplicate_for_plan"
    INVALID_STATUS_TRANSITION = "QUOTATION_invalid_status_transition"


class DiagnosisErrors:
    """DIAGNOSIS domain — diagnosis error codes."""

    NOT_FOUND = "DIAGNOSIS_not_found"
    INVALID_CIE10_CODE = "DIAGNOSIS_invalid_cie10_code"
    ALREADY_RESOLVED = "DIAGNOSIS_already_resolved"


class ProcedureErrors:
    """PROCEDURE domain — procedure error codes."""

    NOT_FOUND = "PROCEDURE_not_found"
    INVALID_CUPS_CODE = "PROCEDURE_invalid_cups_code"
    ALREADY_LINKED = "PROCEDURE_already_linked"


class SignatureErrors:
    """SIGNATURE domain — digital signature error codes."""

    NOT_FOUND = "SIGNATURE_not_found"
    BLANK_SIGNATURE = "SIGNATURE_blank_signature"
    INVALID_IMAGE = "SIGNATURE_invalid_image"
    ALREADY_SIGNED = "SIGNATURE_already_signed"
    VERIFICATION_FAILED = "SIGNATURE_verification_failed"
    DOCUMENT_NOT_FOUND = "SIGNATURE_document_not_found"


class PrescriptionErrors:
    """PRESCRIPTION domain — prescription error codes."""

    NOT_FOUND = "PRESCRIPTION_not_found"


class ValidationErrors:
    """VALIDATION domain — input and business rule validation error codes."""

    FAILED = "VALIDATION_failed"
    INVALID_FIELD = "VALIDATION_invalid_field"
    REQUIRED_FIELD_MISSING = "VALIDATION_required_field_missing"


class MembershipErrors:
    """MEMBERSHIP domain — membership plan and subscription error codes."""

    PLAN_NOT_FOUND = "MEMBERSHIP_plan_not_found"
    ALREADY_SUBSCRIBED = "MEMBERSHIP_already_subscribed"
    CANNOT_CANCEL = "MEMBERSHIP_cannot_cancel"
    CANNOT_PAUSE = "MEMBERSHIP_cannot_pause"
    SUBSCRIPTION_NOT_FOUND = "MEMBERSHIP_subscription_not_found"


class IntakeErrors:
    """INTAKE domain — intake form template and submission error codes."""

    TEMPLATE_NOT_FOUND = "INTAKE_template_not_found"
    SUBMISSION_NOT_FOUND = "INTAKE_submission_not_found"
    ALREADY_APPROVED = "INTAKE_already_approved"
    INVALID_SLUG = "INTAKE_invalid_slug"


class RecallErrors:
    """RECALL domain — recall campaign error codes."""

    CAMPAIGN_NOT_FOUND = "RECALL_campaign_not_found"
    ALREADY_ACTIVE = "RECALL_already_active"
    ALREADY_PAUSED = "RECALL_already_paused"
    CANNOT_ACTIVATE = "RECALL_cannot_activate"


class EPSErrors:
    """EPS domain — EPS insurance verification error codes."""

    VERIFICATION_FAILED = "EPS_verification_failed"
    NOT_FOUND = "EPS_not_found"
    SERVICE_UNAVAILABLE = "EPS_service_unavailable"


class RETHUSErrors:
    """RETHUS domain — professional registry verification error codes."""

    VERIFICATION_FAILED = "RETHUS_verification_failed"
    NOT_FOUND = "RETHUS_not_found"
    SERVICE_UNAVAILABLE = "RETHUS_service_unavailable"
    ALREADY_VERIFIED = "RETHUS_already_verified"


class ReferralProgramErrors:
    """REFERRAL_PROGRAM domain — patient referral program error codes."""

    CODE_NOT_FOUND = "REFERRAL_PROGRAM_code_not_found"
    CODE_EXPIRED = "REFERRAL_PROGRAM_code_expired"
    CODE_MAX_USES = "REFERRAL_PROGRAM_code_max_uses"
    SELF_REFERRAL = "REFERRAL_PROGRAM_self_referral"
    ALREADY_REFERRED = "REFERRAL_PROGRAM_already_referred"


class CashRegisterErrors:
    """CASH_REGISTER domain — cash register operation error codes."""

    NOT_FOUND = "CASH_REGISTER_not_found"
    ALREADY_OPEN = "CASH_REGISTER_already_open"
    ALREADY_CLOSED = "CASH_REGISTER_already_closed"
    NO_OPEN_REGISTER = "CASH_REGISTER_no_open_register"


class ExpenseErrors:
    """EXPENSE domain — expense tracking error codes."""

    NOT_FOUND = "EXPENSE_not_found"
    CATEGORY_NOT_FOUND = "EXPENSE_category_not_found"
    ALREADY_DELETED = "EXPENSE_already_deleted"


class TaskErrors:
    """TASK domain — staff task error codes."""

    NOT_FOUND = "TASK_not_found"
    INVALID_STATUS_TRANSITION = "TASK_invalid_status_transition"
    ALREADY_COMPLETED = "TASK_already_completed"


class PostopErrors:
    """POSTOP domain — post-operative instruction error codes."""

    TEMPLATE_NOT_FOUND = "POSTOP_template_not_found"
    SEND_FAILED = "POSTOP_send_failed"


class ReputationErrors:
    """REPUTATION domain — satisfaction survey and reputation management error codes."""

    SURVEY_NOT_FOUND = "REPUTATION_survey_not_found"
    SURVEY_ALREADY_RESPONDED = "REPUTATION_survey_already_responded"
    SURVEY_EXPIRED = "REPUTATION_survey_expired"
    INVALID_TOKEN = "REPUTATION_invalid_token"
    SEND_FAILED = "REPUTATION_send_failed"


class LoyaltyErrors:
    """LOYALTY domain — loyalty points program error codes."""

    INSUFFICIENT_POINTS = "LOYALTY_insufficient_points"
    PROGRAM_DISABLED = "LOYALTY_program_disabled"
    PATIENT_NOT_ENROLLED = "LOYALTY_patient_not_enrolled"
    INVALID_REDEMPTION = "LOYALTY_invalid_redemption"


class PeriodontalErrors:
    """PERIODONTAL domain — periodontal charting error codes."""

    RECORD_NOT_FOUND = "PERIODONTAL_record_not_found"
    INVALID_TOOTH_NUMBER = "PERIODONTAL_invalid_tooth_number"
    INVALID_SITE = "PERIODONTAL_invalid_site"
    INVALID_MEASUREMENT = "PERIODONTAL_invalid_measurement"
    COMPARISON_REQUIRES_TWO = "PERIODONTAL_comparison_requires_two"


class ConvenioErrors:
    """CONVENIO domain — corporate agreement error codes."""

    NOT_FOUND = "CONVENIO_not_found"
    PATIENT_ALREADY_LINKED = "CONVENIO_patient_already_linked"
    EXPIRED = "CONVENIO_expired"
    INACTIVE = "CONVENIO_inactive"


class FamilyErrors:
    """FAMILY domain — family group error codes."""

    NOT_FOUND = "FAMILY_not_found"
    ALREADY_IN_FAMILY = "FAMILY_already_in_family"
    PRIMARY_CONTACT_REQUIRED = "FAMILY_primary_contact_required"
    MEMBER_NOT_FOUND = "FAMILY_member_not_found"


class ExchangeRateErrors:
    """EXCHANGE_RATE domain — currency exchange rate error codes."""

    RATE_NOT_AVAILABLE = "EXCHANGE_RATE_not_available"
    UNSUPPORTED_CURRENCY = "EXCHANGE_RATE_unsupported_currency"
    SERVICE_UNAVAILABLE = "EXCHANGE_RATE_service_unavailable"


class WhatsAppChatErrors:
    """WHATSAPP_CHAT domain — bidirectional WhatsApp chat error codes."""

    CONVERSATION_NOT_FOUND = "WHATSAPP_CHAT_conversation_not_found"
    MESSAGE_SEND_FAILED = "WHATSAPP_CHAT_message_send_failed"
    OUTSIDE_24H_WINDOW = "WHATSAPP_CHAT_outside_24h_window"
    NOT_CONFIGURED = "WHATSAPP_CHAT_not_configured"
    INVALID_PHONE = "WHATSAPP_CHAT_invalid_phone"


class AITreatmentErrors:
    """AI_TREATMENT domain — AI treatment advisor error codes."""

    ADDON_REQUIRED = "AI_TREATMENT_addon_required"
    GENERATION_FAILED = "AI_TREATMENT_generation_failed"
    SUGGESTION_NOT_FOUND = "AI_TREATMENT_suggestion_not_found"
    ALREADY_REVIEWED = "AI_TREATMENT_already_reviewed"
    PLAN_CREATION_FAILED = "AI_TREATMENT_plan_creation_failed"
    NO_ACTIVE_CONDITIONS = "AI_TREATMENT_no_active_conditions"


class MarketingErrors:
    """MARKETING domain — email marketing campaign error codes."""

    CAMPAIGN_NOT_FOUND = "MARKETING_campaign_not_found"
    NOT_DRAFT = "MARKETING_not_draft"
    NO_RECIPIENTS = "MARKETING_no_recipients"
    ALREADY_SENT = "MARKETING_already_sent"
    ALREADY_CANCELLED = "MARKETING_already_cancelled"
    TEMPLATE_NOT_FOUND = "MARKETING_template_not_found"
    ADDON_REQUIRED = "MARKETING_addon_required"
    RECIPIENT_NOT_FOUND = "MARKETING_recipient_not_found"


class AIReportErrors:
    """AI_REPORT domain — natural language analytics report error codes."""

    QUERY_FAILED = "AI_REPORT_query_failed"
    UNKNOWN_QUERY_TYPE = "AI_REPORT_unknown_query_type"
    INVALID_PARAMETERS = "AI_REPORT_invalid_parameters"
    GENERATION_FAILED = "AI_REPORT_generation_failed"


class FinancingErrors:
    """FINANCING domain — patient financing error codes."""

    NOT_ELIGIBLE = "FINANCING_not_eligible"
    PROVIDER_UNAVAILABLE = "FINANCING_provider_unavailable"
    APPLICATION_NOT_FOUND = "FINANCING_application_not_found"
    ALREADY_FINANCED = "FINANCING_already_financed"
    AMOUNT_OUT_OF_RANGE = "FINANCING_amount_out_of_range"


class ChatbotErrors:
    """CHATBOT domain — AI virtual receptionist error codes."""

    CONVERSATION_NOT_FOUND = "CHATBOT_conversation_not_found"
    INTENT_UNCLEAR = "CHATBOT_intent_unclear"
    ESCALATION_FAILED = "CHATBOT_escalation_failed"
    RATE_LIMITED = "CHATBOT_rate_limited"


class SurveyErrors:
    """SURVEY domain — NPS/CSAT survey error codes."""

    ALREADY_RESPONDED = "SURVEY_already_responded"
    TOKEN_EXPIRED = "SURVEY_token_expired"
    INVALID_SCORE = "SURVEY_invalid_score"


class TelemedicineErrors:
    """TELEMEDICINE domain — video consultation error codes."""

    SESSION_NOT_FOUND = "TELEMEDICINE_session_not_found"
    PROVIDER_ERROR = "TELEMEDICINE_provider_error"
    SESSION_ALREADY_ACTIVE = "TELEMEDICINE_session_already_active"
    ADD_ON_REQUIRED = "TELEMEDICINE_add_on_required"


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
