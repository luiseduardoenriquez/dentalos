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
from app.models.tenant.intake_form import IntakeFormTemplate, IntakeSubmission
from app.models.tenant.inventory import (
    InventoryItem,
    InventoryQuantityHistory,
    SterilizationRecord,
    SterilizationRecordInstrument,
    ImplantPlacement,
)
from app.models.tenant.membership import (
    MembershipPlan,
    MembershipSubscription,
    MembershipUsageLog,
)
from app.models.tenant.eps_verification import EPSVerification
from app.models.tenant.postop_template import PostopTemplate
from app.models.tenant.recall_campaign import RecallCampaign, RecallCampaignRecipient

from app.models.tenant.patient_referral_program import ReferralCode, ReferralReward

# Sprint 23-24: GAP-02 Cash Register + GAP-03 Expenses
from app.models.tenant.cash_register import CashMovement, CashRegister
from app.models.tenant.expense import Expense, ExpenseCategory

# Sprint 23-24: GAP-05 + GAP-06 Staff Tasks (delinquency + acceptance)
from app.models.tenant.staff_task import StaffTask

# Sprint 27-28: AI Treatment Advisor (VP-13)
from app.models.tenant.ai_treatment import AITreatmentSuggestion

# Sprint 25-26: Reputation, Loyalty, Periodontal, Convenios, Families
from app.models.tenant.satisfaction_survey import SatisfactionSurvey
from app.models.tenant.loyalty import LoyaltyPoints, LoyaltyTransaction
from app.models.tenant.periodontal import PeriodontalMeasurement, PeriodontalRecord
from app.models.tenant.convenio import Convenio, ConvenioPatient
from app.models.tenant.family import FamilyGroup, FamilyMember

# Sprint 27-28: VP-12 WhatsApp Bidirectional Chat
from app.models.tenant.whatsapp import (
    WhatsAppConversation,
    WhatsAppMessage,
    WhatsAppQuickReply,
)

# Sprint 27-28: VP-17 Email Marketing Campaigns
from app.models.tenant.email_campaign import EmailCampaign, EmailCampaignRecipient

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
    "InventoryItem",
    "InventoryQuantityHistory",
    "SterilizationRecord",
    "SterilizationRecordInstrument",
    "ImplantPlacement",
    "IntakeFormTemplate",
    "IntakeSubmission",
    "MembershipPlan",
    "MembershipSubscription",
    "MembershipUsageLog",
    "EPSVerification",
    "PostopTemplate",
    "RecallCampaign",
    "RecallCampaignRecipient",
    # Sprint 23-24: VP-08 Patient Referral Program
    "ReferralCode",
    "ReferralReward",
    # Sprint 23-24: GAP-02 + GAP-03
    "CashRegister",
    "CashMovement",
    "ExpenseCategory",
    "Expense",
    # Sprint 23-24: GAP-05 + GAP-06
    "StaffTask",
    # Sprint 27-28: VP-13
    "AITreatmentSuggestion",
    # Sprint 25-26
    "SatisfactionSurvey",
    "LoyaltyPoints",
    "LoyaltyTransaction",
    "PeriodontalRecord",
    "PeriodontalMeasurement",
    "Convenio",
    "ConvenioPatient",
    "FamilyGroup",
    "FamilyMember",
    # Sprint 27-28: VP-12 WhatsApp Chat
    "WhatsAppConversation",
    "WhatsAppMessage",
    "WhatsAppQuickReply",
    # Sprint 27-28: VP-17 Email Marketing
    "EmailCampaign",
    "EmailCampaignRecipient",
]
