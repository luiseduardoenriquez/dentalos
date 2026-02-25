"""Authenticated user context for the current request."""
from dataclasses import dataclass

from app.core.tenant import TenantContext


@dataclass(frozen=True)
class AuthenticatedUser:
    """Represents the fully authenticated user for the current request."""

    user_id: str
    email: str
    name: str
    role: str
    permissions: frozenset[str]
    tenant: TenantContext
    token_jti: str
    token_version: int = 0
