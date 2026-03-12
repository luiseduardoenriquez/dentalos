"""Clinic-facing announcements endpoint.

Exposes active platform announcements so clinic dashboards can display
admin-published banners (e.g., scheduled maintenance, new features).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.schemas.admin import AnnouncementResponse
from app.services.admin_service import admin_service

router = APIRouter(prefix="/announcements", tags=["announcements"])


@router.get("/active", response_model=list[AnnouncementResponse])
async def get_active_announcements(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AnnouncementResponse]:
    """Return active platform announcements for the current tenant context.

    Filters by the tenant's plan and country when applicable.
    """
    # Extract tenant context from user claims for visibility filtering
    tenant_plan = getattr(current_user, "plan_slug", None)
    tenant_country = getattr(current_user, "country_code", None)

    return await admin_service.get_active_announcements_for_tenant(
        db=db,
        tenant_plan=tenant_plan,
        tenant_country=tenant_country,
    )
