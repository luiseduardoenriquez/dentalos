"""Audit logging dependency for FastAPI endpoints."""
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.services.audit_service import write_audit_log


def get_client_ip(request: Request) -> str:
    """Extract the real client IP, honoring X-Forwarded-For from the LB."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def audit_action(
    *,
    request: Request,
    db: AsyncSession,
    current_user: AuthenticatedUser,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    changes: dict | None = None,
) -> None:
    """Log an auditable action from an endpoint.

    Usage in a route handler:
        await audit_action(
            request=request,
            db=db,
            current_user=current_user,
            action="update",
            resource_type="patient",
            resource_id=str(patient.id),
            changes={"first_name": {"old": "Juan", "new": "Juan Carlos"}},
        )
    """
    await write_audit_log(
        db=db,
        tenant_schema=current_user.tenant.schema_name,
        user_id=current_user.user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        changes=changes,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
