from fastapi import APIRouter

from app.api.v1.auth.router import router as auth_router
from app.api.v1.billing.router import router as billing_router
from app.api.v1.catalog.router import router as catalog_router
from app.api.v1.clinical_records.router import router as clinical_records_router
from app.api.v1.consent_templates.router import router as consent_templates_router
from app.api.v1.consents.router import router as consents_router
from app.api.v1.diagnoses.router import router as diagnoses_router
from app.api.v1.evolution_templates.router import router as evolution_templates_router
from app.api.v1.health import router as health_router
from app.api.v1.odontogram.router import router as odontogram_router
from app.api.v1.onboarding.router import router as onboarding_router
from app.api.v1.patients.router import router as patients_router
from app.api.v1.prescriptions.router import router as prescriptions_router
from app.api.v1.procedures.router import router as procedures_router
from app.api.v1.quotations.router import router as quotations_router
from app.api.v1.settings.router import router as settings_router
from app.api.v1.signatures.router import router as signatures_router
from app.api.v1.tenants.router import router as tenants_router
from app.api.v1.tooth_photos.router import router as tooth_photos_router
from app.api.v1.treatment_plans.router import router as treatment_plans_router
from app.api.v1.users.router import router as users_router

api_v1_router = APIRouter(prefix="/api/v1")

# Sprint 15-16: Admin — included early to take priority over the legacy
# tenants_router whose prefix="/admin/tenants" overlaps with the admin
# router's GET /admin/tenants endpoint.
from app.api.v1.admin.router import router as admin_router

api_v1_router.include_router(admin_router)

api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(tenants_router)
api_v1_router.include_router(settings_router)
api_v1_router.include_router(onboarding_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(patients_router)

# Sprint 5-6: Clinical core
api_v1_router.include_router(odontogram_router)
api_v1_router.include_router(catalog_router)
api_v1_router.include_router(clinical_records_router)
api_v1_router.include_router(evolution_templates_router)
api_v1_router.include_router(billing_router)

# Sprint 7-8: Clinical core 2
api_v1_router.include_router(signatures_router)
api_v1_router.include_router(diagnoses_router)
api_v1_router.include_router(procedures_router)
api_v1_router.include_router(tooth_photos_router)
api_v1_router.include_router(treatment_plans_router)
api_v1_router.include_router(quotations_router)
api_v1_router.include_router(consent_templates_router)
api_v1_router.include_router(consents_router)
api_v1_router.include_router(prescriptions_router)

# Sprint 9-10: Agenda + Voice
from app.api.v1.appointments.router import router as appointments_router
from app.api.v1.appointments.public_router import router as public_booking_router
from app.api.v1.appointments.waitlist_router import router as waitlist_router
from app.api.v1.voice.router import router as voice_router

api_v1_router.include_router(appointments_router)
api_v1_router.include_router(waitlist_router)
api_v1_router.include_router(public_booking_router)
api_v1_router.include_router(voice_router)

# Sprint 11-12: Billing
from app.api.v1.billing.summary_router import router as billing_summary_router
from app.api.v1.invoices.router import router as invoices_router
from app.api.v1.payments.router import router as payments_router

api_v1_router.include_router(invoices_router)
api_v1_router.include_router(payments_router)
api_v1_router.include_router(billing_summary_router)

# Sprint 23-24: QR Payments (Nequi/Daviplata)
from app.api.v1.billing.payment_qr_router import router as payment_qr_router

api_v1_router.include_router(payment_qr_router)

# Sprint 11-12: Notifications
from app.api.v1.notifications.router import router as notifications_router

api_v1_router.include_router(notifications_router)

# Sprint 11-12: Patient Portal
from app.api.v1.portal.auth_router import router as portal_auth_router
from app.api.v1.portal.access_router import router as portal_access_router
from app.api.v1.portal.data_router import router as portal_data_router
from app.api.v1.portal.action_router import router as portal_action_router

api_v1_router.include_router(portal_auth_router)
api_v1_router.include_router(portal_access_router)
api_v1_router.include_router(portal_data_router)
api_v1_router.include_router(portal_action_router)

# Sprint 11-12: Messaging + Referrals
from app.api.v1.messages.router import router as messages_router
from app.api.v1.referrals.router import router as referrals_router

api_v1_router.include_router(messages_router)
api_v1_router.include_router(referrals_router)

# Sprint 13-14: Compliance
from app.api.v1.compliance.router import router as compliance_router

api_v1_router.include_router(compliance_router)

# Sprint 15-16: Inventory
from app.api.v1.inventory.router import router as inventory_router

api_v1_router.include_router(inventory_router)

# Sprint 15-16: Analytics
from app.api.v1.analytics.router import router as analytics_router

api_v1_router.include_router(analytics_router)

# Sprint 21-22: Patient Engagement & Revenue Acceleration
from app.api.v1.memberships.router import router as memberships_router
from app.api.v1.intake.router import router as intake_router
from app.api.v1.intake.public_router import router as public_intake_router
from app.api.v1.recall.router import router as recall_router

api_v1_router.include_router(memberships_router)
api_v1_router.include_router(intake_router)
api_v1_router.include_router(public_intake_router)
api_v1_router.include_router(recall_router)

# Sprint 23-24: Verification Platform (VP-06 EPS, VP-07 RETHUS)
from app.api.v1.patients.eps_router import router as eps_router
from app.api.v1.users.rethus_router import router as rethus_router

api_v1_router.include_router(eps_router)
api_v1_router.include_router(rethus_router)

# Sprint 23-24: Post-Op Instructions (VP-20)
from app.api.v1.postop.router import router as postop_router

api_v1_router.include_router(postop_router)

# Sprint 17+: Webhooks (provider-authenticated, not JWT)
from app.integrations.whatsapp.webhook_router import router as whatsapp_webhook_router

api_v1_router.include_router(whatsapp_webhook_router)

from app.integrations.sms.webhook_router import router as twilio_webhook_router

api_v1_router.include_router(twilio_webhook_router)

# Sprint 25-26: Nequi + Daviplata QR payment webhooks (GAP-01)
from app.integrations.nequi.webhook_router import router as nequi_webhook_router
from app.integrations.daviplata.webhook_router import router as daviplata_webhook_router

api_v1_router.include_router(nequi_webhook_router)
api_v1_router.include_router(daviplata_webhook_router)

# Sprint 29-30: Mercado Pago IPN webhook (INT-07)
from app.integrations.payments.mercadopago_webhook import router as mercadopago_webhook_router

api_v1_router.include_router(mercadopago_webhook_router)

# Sprint 23-24: GAP-02 Cash Register + GAP-03 Expenses
from app.api.v1.cash_registers.router import router as cash_registers_router
from app.api.v1.expenses.router import router as expenses_router

api_v1_router.include_router(cash_registers_router)
api_v1_router.include_router(expenses_router)

# Sprint 23-24: VP-08 Patient Referral Program
from app.api.v1.referral_program.router import router as referral_program_router
from app.api.v1.portal.referral_router import router as portal_referral_router

api_v1_router.include_router(referral_program_router)
api_v1_router.include_router(portal_referral_router)

# Sprint 23-24: GAP-05 + GAP-06 Staff Tasks (delinquency + acceptance follow-up)
from app.api.v1.tasks.router import router as tasks_router

api_v1_router.include_router(tasks_router)

# Sprint 25-26: Reputation, Schedule Intelligence, Multi-Currency, Loyalty,
# Periodontal, Convenios, Families
from app.api.v1.reputation.router import router as reputation_router
from app.api.v1.reputation.public_router import router as public_survey_router
from app.api.v1.analytics.schedule_intelligence_router import router as schedule_intelligence_router
from app.api.v1.billing.exchange_rate_router import router as exchange_rate_router
from app.api.v1.loyalty.router import router as loyalty_router
from app.api.v1.portal.loyalty_router import router as portal_loyalty_router
from app.api.v1.periodontal.router import router as periodontal_router
from app.api.v1.convenios.router import router as convenios_router
from app.api.v1.families.router import router as families_router

api_v1_router.include_router(reputation_router)
api_v1_router.include_router(public_survey_router)
api_v1_router.include_router(schedule_intelligence_router)
api_v1_router.include_router(exchange_rate_router)
api_v1_router.include_router(loyalty_router)
api_v1_router.include_router(portal_loyalty_router)
api_v1_router.include_router(periodontal_router)
api_v1_router.include_router(convenios_router)
api_v1_router.include_router(families_router)

# Sprint 27-28: AI Treatment Advisor (VP-13)
from app.api.v1.treatment_plans.ai_router import router as ai_treatment_router

api_v1_router.include_router(ai_treatment_router)

# Sprint 27-28: VP-17 Email Marketing Campaigns
from app.api.v1.marketing.router import router as marketing_router
from app.api.v1.marketing.tracking_router import router as email_tracking_router

api_v1_router.include_router(marketing_router)
api_v1_router.include_router(email_tracking_router)

# Sprint 27-28: GAP-14 AI Natural Language Reports
from app.api.v1.analytics.ai_router import router as ai_report_router

api_v1_router.include_router(ai_report_router)

# Sprint 27-28: VP-12 WhatsApp Bidirectional Chat
from app.api.v1.whatsapp.router import router as whatsapp_chat_router

api_v1_router.include_router(whatsapp_chat_router)

# Sprint 29-30: VP-21 NPS/CSAT Surveys
from app.api.v1.surveys.router import router as nps_surveys_router
from app.api.v1.surveys.public_router import router as public_nps_surveys_router

api_v1_router.include_router(nps_surveys_router)
api_v1_router.include_router(public_nps_surveys_router)

# Sprint 29-30: VP-16 AI Virtual Receptionist (Chatbot)
from app.api.v1.chatbot.router import router as chatbot_router
from app.api.v1.chatbot.widget_router import router as chatbot_widget_router

api_v1_router.include_router(chatbot_router)
api_v1_router.include_router(chatbot_widget_router)

# Sprint 29-30: VP-11 Patient Financing (Addi + Sistecrédito)
from app.api.v1.financing.router import router as financing_router
from app.integrations.financing.webhook_router import router as financing_webhook_router

api_v1_router.include_router(financing_router)
api_v1_router.include_router(financing_webhook_router)

# Sprint 29-30: GAP-09 Telemedicine (Daily.co video sessions)
from app.api.v1.telemedicine.router import router as telemedicine_router

api_v1_router.include_router(telemedicine_router)

# Sprint 31-32: VP-18 VoIP Screen Pop
from app.api.v1.calls.router import router as calls_router
from app.integrations.twilio_voice.webhook_router import router as twilio_voice_webhook_router

api_v1_router.include_router(calls_router)
api_v1_router.include_router(twilio_voice_webhook_router)

# Sprint 31-32: VP-19 EPS Claims
from app.api.v1.billing.eps_claims_router import router as eps_claims_router

api_v1_router.include_router(eps_claims_router)

# Sprint 31-32: VP-22 Lab Orders
from app.api.v1.lab_orders.router import router as lab_orders_router

api_v1_router.include_router(lab_orders_router)

# Sprint 33: GAP-07 Orthodontics
from app.api.v1.ortho.router import router as ortho_router

api_v1_router.include_router(ortho_router)

# Sprint 15-16: Admin (included at top of file for route priority)
