"""User management API routes — own profile and team management.

Endpoint map:
  GET  /users/me              — Any authenticated user: read own profile
  PUT  /users/me              — Any authenticated user: update own profile
  GET  /users/                — clinic_owner only: list all team members
  GET  /users/{user_id}       — clinic_owner only: get a specific team member
  PUT  /users/{user_id}       — clinic_owner only: update role or status
  POST /users/{user_id}/deactivate         — clinic_owner only: soft-deactivate a member
  GET  /users/{user_id}/schedule           — U-07: Get doctor weekly schedule
  PUT  /users/{user_id}/schedule           — U-08: Update doctor weekly schedule
  GET  /users/{user_id}/availability-blocks       — List doctor availability blocks
  POST /users/{user_id}/availability-blocks       — Create availability block
  DELETE /users/{user_id}/availability-blocks/{block_id} — Delete availability block
  GET  /users/{user_id}/available-slots    — Get available appointment slots
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_permission, require_role
from app.core.audit import audit_action
from app.core.database import get_tenant_db
from app.schemas.schedule import (
    AvailabilityBlockCreate,
    AvailabilityBlockResponse,
    AvailabilityResponse,
    DoctorScheduleResponse,
    DoctorScheduleUpdate,
)
from app.schemas.user import (
    UserListResponse,
    UserProfileResponse,
    UserProfileUpdate,
    UserTeamMemberResponse,
    UserTeamMemberUpdate,
)
from app.services.schedule_service import schedule_service
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


# ─── Doctor Schedule Endpoints ────────────────────────────────────────────────


@router.get("/{user_id}/schedule", response_model=DoctorScheduleResponse)
async def get_doctor_schedule(
    user_id: str,
    current_user: AuthenticatedUser = Depends(require_permission("schedule:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> DoctorScheduleResponse:
    """Return a doctor's weekly working schedule (U-07).

    If no schedule has been configured for the doctor, a sensible default
    (Mon-Fri 08:00-18:00 with a lunch break) is returned without persisting it.
    """
    result = await schedule_service.get_schedule(db=db, doctor_id=user_id)
    return DoctorScheduleResponse(**result)


@router.put("/{user_id}/schedule", response_model=DoctorScheduleResponse)
async def update_doctor_schedule(
    user_id: str,
    body: DoctorScheduleUpdate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("schedule:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> DoctorScheduleResponse:
    """Replace a doctor's full weekly schedule (U-08).

    The entire schedule is replaced atomically. Each day entry controls
    working hours, breaks, and default appointment duration per type.
    """
    result = await schedule_service.set_schedule(
        db=db,
        doctor_id=user_id,
        schedule=[day.model_dump() for day in body.schedule],
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="update",
        resource_type="doctor_schedule",
        resource_id=user_id,
    )

    return DoctorScheduleResponse(**result)


# ─── Availability Block Endpoints ─────────────────────────────────────────────


@router.get("/{user_id}/availability-blocks", response_model=list[AvailabilityBlockResponse])
async def list_availability_blocks(
    user_id: str,
    date_from: str | None = Query(default=None, description="ISO date string (YYYY-MM-DD)"),
    date_to: str | None = Query(default=None, description="ISO date string (YYYY-MM-DD)"),
    current_user: AuthenticatedUser = Depends(require_permission("schedule:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> list[AvailabilityBlockResponse]:
    """List a doctor's availability blocks (vacations, conferences, etc.).

    Optionally filtered by date range. Returns all active blocks when no
    date range is provided.
    """
    from datetime import date as date_type

    df = date_type.fromisoformat(date_from) if date_from else None
    dt = date_type.fromisoformat(date_to) if date_to else None

    blocks = await schedule_service.list_blocks(
        db=db,
        doctor_id=user_id,
        date_from=df,
        date_to=dt,
    )

    return [AvailabilityBlockResponse(**b) for b in blocks]


@router.post("/{user_id}/availability-blocks", response_model=AvailabilityBlockResponse, status_code=201)
async def create_availability_block(
    user_id: str,
    body: AvailabilityBlockCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("schedule:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> AvailabilityBlockResponse:
    """Create an availability block for a doctor.

    Blocks mark periods when the doctor is unavailable (vacation, conference,
    personal, sick leave, training, or other). Recurring blocks extend until
    recurring_until, inclusive.
    """
    result = await schedule_service.create_block(
        db=db,
        doctor_id=user_id,
        start_time=body.start_time,
        end_time=body.end_time,
        reason=body.reason,
        description=body.description,
        is_recurring=body.is_recurring,
        recurring_until=body.recurring_until,
    )

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="create",
        resource_type="availability_block",
        resource_id=result["id"],
    )

    return AvailabilityBlockResponse(**result)


@router.delete("/{user_id}/availability-blocks/{block_id}")
async def delete_availability_block(
    user_id: str,
    block_id: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_permission("schedule:write")),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """Soft-delete an availability block.

    The block record is preserved for audit purposes. It no longer affects
    slot availability queries after deletion.
    """
    result = await schedule_service.delete_block(db=db, block_id=block_id)

    await audit_action(
        request=request,
        db=db,
        current_user=current_user,
        action="delete",
        resource_type="availability_block",
        resource_id=block_id,
    )

    return result


# ─── Available Slots Endpoint ─────────────────────────────────────────────────


@router.get("/{user_id}/available-slots", response_model=AvailabilityResponse)
async def get_available_slots(
    user_id: str,
    date_from: str = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., description="End date (YYYY-MM-DD)"),
    slot_duration_minutes: int = Query(default=30, ge=10, le=120),
    appointment_type: str | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> AvailabilityResponse:
    """Return available appointment slots for a doctor over a date range.

    Uses the doctor's configured weekly schedule and existing appointments to
    compute a date-keyed grid of free and taken slots. Useful for the booking
    calendar to highlight available times.
    """
    from datetime import date as date_type

    result = await schedule_service.get_available_slots(
        db=db,
        doctor_id=user_id,
        date_from=date_type.fromisoformat(date_from),
        date_to=date_type.fromisoformat(date_to),
        slot_duration_minutes=slot_duration_minutes,
        appointment_type=appointment_type,
    )

    return AvailabilityResponse(**result)
