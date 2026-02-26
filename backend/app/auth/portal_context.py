"""Portal user context for the current request."""
from dataclasses import dataclass

from app.core.tenant import TenantContext


@dataclass(frozen=True)
class PortalUser:
    """Represents the authenticated portal patient for the current request.

    Distinct from AuthenticatedUser (staff) — portal users have patient_id
    instead of user_id, and cannot access staff endpoints.
    """

    patient_id: str
    email: str
    name: str
    tenant: TenantContext
    token_jti: str
