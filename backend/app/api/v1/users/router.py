"""User management API routes — own profile and team management.

Endpoint map:
  GET  /users/me              — Any authenticated user: read own profile
  PUT  /users/me              — Any authenticated user: update own profile
  GET  /users/                — clinic_owner only: list all team members
  GET  /users/{user_id}       — clinic_owner only: get a specific team member
  PUT  /users/{user_id}       — clinic_owner only: update role or status
  POST /users/{user_id}/deactivate — clinic_owner only: soft-deactivate a member
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_role
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.schemas.user import (
    UserListResponse,
    UserProfileResponse,
    UserProfileUpdate,
    UserTeamMemberResponse,
    UserTeamMemberUpdate,
)
from app.services.user_service import user_service

router = APIRouter(prefix="/users", tags=["users"])


# ─── Own Profile Endpoints ───────────────────────────────────────────────


@router.get("/me", response_model=UserProfileResponse)
async def get_own_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> UserProfileResponse:
    """Return the authenticated user's own profile.

    Available to all authenticated roles. The profile includes all personal
    and professional fields stored in the tenant schema.
    """
    result = await user_service.get_own_profile(
        user_id=current_user.user_id,
        tenant_schema=current_user.tenant.schema_name,
        db=db,
    )
    return UserProfileResponse(**result)


@router.put("/me", response_model=UserProfileResponse)
async def update_own_profile(
    body: UserProfileUpdate,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> UserProfileResponse:
    """Update the authenticated user's own profile.

    All fields are optional. professional_license and specialties are
    silently ignored for non-doctor roles (no error is raised; the schema
    deliberately accepts them to keep the client contract clean).
    """
    result = await user_service.update_own_profile(
        user_id=current_user.user_id,
        tenant_id=current_user.tenant.tenant_id,
        tenant_schema=current_user.tenant.schema_name,
        db=db,
        name=body.name,
        phone=body.phone,
        avatar_url=body.avatar_url,
        professional_license=body.professional_license,
        specialties=body.specialties,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="update",
        resource_type="user_profile",
        resource_id=current_user.user_id,
        changes=body.model_dump(exclude_none=True),
    )

    return UserProfileResponse(**result)


# ─── Team Management Endpoints (clinic_owner only) ───────────────────────


@router.get("/", response_model=UserListResponse)
async def list_team_members(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(require_role(["clinic_owner"])),
    db: AsyncSession = Depends(get_tenant_db),
) -> UserListResponse:
    """Return a paginated list of all active team members in the clinic.

    Ordered alphabetically by name. Only active users are returned.
    Restricted to clinic_owner role.
    """
    result = await user_service.list_team_members(
        tenant_schema=current_user.tenant.schema_name,
        db=db,
        page=page,
        page_size=page_size,
    )
    return UserListResponse(
        items=[UserTeamMemberResponse(**u) for u in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get("/{user_id}", response_model=UserTeamMemberResponse)
async def get_team_member(
    user_id: str,
    current_user: AuthenticatedUser = Depends(require_role(["clinic_owner"])),
    db: AsyncSession = Depends(get_tenant_db),
) -> UserTeamMemberResponse:
    """Return a single active team member's profile.

    Returns 404 if the user does not exist or is inactive in this tenant.
    Restricted to clinic_owner role.
    """
    result = await user_service.get_team_member(
        member_id=user_id,
        tenant_schema=current_user.tenant.schema_name,
        db=db,
    )
    return UserTeamMemberResponse(**result)


@router.put("/{user_id}", response_model=UserTeamMemberResponse)
async def update_team_member(
    user_id: str,
    body: UserTeamMemberUpdate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_role(["clinic_owner"])),
    db: AsyncSession = Depends(get_tenant_db),
) -> UserTeamMemberResponse:
    """Update a team member's role or active status.

    The clinic_owner role cannot be assigned through this endpoint.
    Actors cannot update themselves (use /users/me instead).
    Restricted to clinic_owner role.
    """
    result = await user_service.update_team_member(
        actor_user_id=current_user.user_id,
        member_id=user_id,
        tenant_id=current_user.tenant.tenant_id,
        tenant_schema=current_user.tenant.schema_name,
        db=db,
        role=body.role,
        is_active=body.is_active,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="update",
        resource_type="team_member",
        resource_id=user_id,
        changes=body.model_dump(exclude_none=True),
    )

    return UserTeamMemberResponse(**result)


@router.post("/{user_id}/deactivate", response_model=UserTeamMemberResponse)
async def deactivate_team_member(
    user_id: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_role(["clinic_owner"])),
    db: AsyncSession = Depends(get_tenant_db),
) -> UserTeamMemberResponse:
    """Soft-deactivate a team member.

    The user record is preserved for audit and compliance purposes (clinical
    data regulations prohibit hard deletion). The member loses API access on
    their next token refresh (within the 15-minute JWT lifetime).

    Safety constraints enforced:
      - Actors cannot deactivate themselves.
      - The sole clinic_owner of a tenant cannot be deactivated.

    Restricted to clinic_owner role.
    """
    result = await user_service.deactivate_team_member(
        actor_user_id=current_user.user_id,
        member_id=user_id,
        tenant_id=current_user.tenant.tenant_id,
        tenant_schema=current_user.tenant.schema_name,
        db=db,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="deactivate",
        resource_type="team_member",
        resource_id=user_id,
    )

    return UserTeamMemberResponse(**result)
