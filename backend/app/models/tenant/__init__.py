"""Tenant schema models — scoped per clinic."""

from app.models.audit import AuditLog
from app.models.tenant.appointment import Appointment
from app.models.tenant.clinical_record import Anamnesis, ClinicalRecord
from app.models.tenant.consent import Consent, ConsentTemplate
from app.models.tenant.diagnosis import Diagnosis
from app.models.tenant.digital_signature import DigitalSignature, SignatureVerification
from app.models.tenant.doctor_schedule import AvailabilityBlock, DoctorSchedule
from app.models.tenant.evolution_template import (
    EvolutionTemplate,
    EvolutionTemplateStep,
    EvolutionTemplateVariable,
)
from app.models.tenant.e_invoice import EInvoice, TenantEInvoiceConfig
from app.models.tenant.invoice import Invoice, InvoiceItem
from app.models.tenant.messaging import Message, MessageThread, ThreadParticipant
from app.models.tenant.notification import (
    Notification,
    NotificationDeliveryLog,
    NotificationPreference,
)
from app.models.tenant.odontogram import (
    OdontogramCondition,
    OdontogramHistory,
    OdontogramSnapshot,
    OdontogramState,
)
from app.models.tenant.patient import Patient
from app.models.tenant.patient_document import PatientDocument
from app.models.tenant.portal import PortalCredentials, PortalInvitation
from app.models.tenant.payment import Payment
from app.models.tenant.payment_plan import PaymentPlan, PaymentPlanInstallment
from app.models.tenant.prescription import Prescription
from app.models.tenant.procedure import Procedure
from app.models.tenant.referral import PatientReferral
from app.models.tenant.rips import RIPSBatch, RIPSBatchError, RIPSBatchFile
from app.models.tenant.quotation import Quotation, QuotationItem
from app.models.tenant.reminder_config import ReminderConfig
from app.models.tenant.service_catalog import ServiceCatalog
from app.models.tenant.tooth_photo import ToothPhoto
from app.models.tenant.treatment_plan import TreatmentPlan, TreatmentPlanItem
from app.models.tenant.user import User
from app.models.tenant.user_invite import UserInvite
from app.models.tenant.user_session import UserSession
from app.models.tenant.voice_session import VoiceParse, VoiceSession, VoiceTranscription
from app.models.tenant.waitlist_entry import WaitlistEntry

__all__ = [
    "AuditLog",
    "Anamnesis",
    "Appointment",
    "AvailabilityBlock",
    "ClinicalRecord",
    "Consent",
    "ConsentTemplate",
    "Diagnosis",
    "DigitalSignature",
    "EInvoice",
    "DoctorSchedule",
    "EvolutionTemplate",
    "EvolutionTemplateStep",
    "EvolutionTemplateVariable",
    "Invoice",
    "InvoiceItem",
    "Message",
    "MessageThread",
    "Notification",
    "NotificationDeliveryLog",
    "NotificationPreference",
    "OdontogramCondition",
    "OdontogramHistory",
    "OdontogramSnapshot",
    "OdontogramState",
    "Patient",
    "PatientDocument",
    "PortalCredentials",
    "PortalInvitation",
    "Payment",
    "PaymentPlan",
    "PaymentPlanInstallment",
    "PatientReferral",
    "Prescription",
    "Procedure",
    "Quotation",
    "QuotationItem",
    "ReminderConfig",
    "RIPSBatch",
    "RIPSBatchError",
    "RIPSBatchFile",
    "ServiceCatalog",
    "SignatureVerification",
    "TenantEInvoiceConfig",
    "ThreadParticipant",
    "ToothPhoto",
    "TreatmentPlan",
    "TreatmentPlanItem",
    "User",
    "UserInvite",
    "UserSession",
    "VoiceParse",
    "VoiceSession",
    "VoiceTranscription",
    "WaitlistEntry",
]
