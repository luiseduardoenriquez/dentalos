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
from app.models.tenant.odontogram import (
    OdontogramCondition,
    OdontogramHistory,
    OdontogramSnapshot,
    OdontogramState,
)
from app.models.tenant.patient import Patient
from app.models.tenant.patient_document import PatientDocument
from app.models.tenant.prescription import Prescription
from app.models.tenant.procedure import Procedure
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
    "DoctorSchedule",
    "EvolutionTemplate",
    "EvolutionTemplateStep",
    "EvolutionTemplateVariable",
    "OdontogramCondition",
    "OdontogramHistory",
    "OdontogramSnapshot",
    "OdontogramState",
    "Patient",
    "PatientDocument",
    "Prescription",
    "Procedure",
    "Quotation",
    "QuotationItem",
    "ReminderConfig",
    "ServiceCatalog",
    "SignatureVerification",
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
