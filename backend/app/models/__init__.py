"""DentalOS ORM models."""

from app.models.base import PublicBase, TenantBase, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.public.catalog import CIE10Catalog, CUPSCatalog
from app.models.public.plan import Plan
from app.models.public.tenant import Tenant
from app.models.public.user_tenant_membership import UserTenantMembership
from app.models.tenant.clinical_record import Anamnesis, ClinicalRecord
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
from app.models.tenant.service_catalog import ServiceCatalog
from app.models.tenant.user import User
from app.models.tenant.user_invite import UserInvite
from app.models.tenant.user_session import UserSession

__all__ = [
    # Bases & mixins
    "PublicBase",
    "TenantBase",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    # Public schema
    "CIE10Catalog",
    "CUPSCatalog",
    "Plan",
    "Tenant",
    "UserTenantMembership",
    # Tenant schema — auth & users
    "User",
    "UserInvite",
    "UserSession",
    # Tenant schema — patients
    "Patient",
    # Tenant schema — odontogram
    "OdontogramCondition",
    "OdontogramHistory",
    "OdontogramSnapshot",
    "OdontogramState",
    # Tenant schema — clinical records
    "Anamnesis",
    "ClinicalRecord",
    # Tenant schema — evolution templates
    "EvolutionTemplate",
    "EvolutionTemplateStep",
    "EvolutionTemplateVariable",
    # Tenant schema — service catalog
    "ServiceCatalog",
]
