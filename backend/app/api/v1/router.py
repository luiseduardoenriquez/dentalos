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

# Sprint 15-16: Admin
from app.api.v1.admin.router import router as admin_router

api_v1_router.include_router(admin_router)
