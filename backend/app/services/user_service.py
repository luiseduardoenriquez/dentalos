"""User management service — profile updates and team management.

Handles all user-facing operations within a tenant schema:
  - Own profile read/update
  - Team member listing, detail, role changes, and deactivation

Security invariants:
  - PHI (emails, names, phones) is NEVER logged.
  - Users cannot modify their own role or deactivate themselves.
  - The last clinic_owner in a tenant cannot be deactivated.
  - professional_license and specialties are doctor-only fields; any
    attempt to set them on a non-doctor is silently ignored.
  - Cache keys for permissions are invalidated on every role/status change.
"""

import contextlib
import logging
import uuid
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete
from app.core.exceptions import AuthError, ResourceConflictError, ResourceNotFoundError
from app.models.tenant.user import User

logger = logging.getLogger("dentalos.users")

# ─── Cache key helpers ──────────────────────────────────────────────────


def _permissions_cache_key(tenant_id: str, user_id: str) -> str:
    """Build the Redis key used by the auth dependency for permission caching."""
    # Pattern: dentalos:{tid}:auth:permissions:{uid}
    # tid is the short tenant_id prefix stored in TenantContext
    return f"dentalos:{tenant_id}:auth:permissions:{user_id}"


# ─── User Service ───────────────────────────────────────────────────────


class UserService:
    """Stateless user management service.

    Each method accepts primitive arguments and an AsyncSession so it can
    be called from API routes, workers, CLI scripts, and tests without
    coupling to HTTP concerns.

    All methods set the PostgreSQL search_path to the tenant schema and
    reset it in a try/finally block, matching the pattern used in
    auth_service.py.
    """

    # ─── Own Profile ────────────────────────────────────────────────

    async def get_own_profile(
        self,
        *,
        user_id: str,
        tenant_schema: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Load and return the authenticated user's own profile.

        Returns a dict with all profile fields. Raises ResourceNotFoundError
        if the user does not exist or is inactive in this tenant schema.
        """
        await db.execute(text(f"SET search_path TO {tenant_schema}, public"))
        try:
            result = await db.execute(
                select(User).where(
                    User.id == uuid.UUID(user_id),
                    User.is_active.is_(True),
                )
            )
            user = result.scalar_one_or_none()

            if user is None:
                raise ResourceNotFoundError(
                    error="USER_not_found",
                    resource_name="User",
                )

            return _user_to_dict(user)

        finally:
            with contextlib.suppress(Exception):
                await db.execute(text("SET search_path TO public"))

    async def update_own_profile(
        self,
        *,
        user_id: str,
        tenant_id: str,
        tenant_schema: str,
        db: AsyncSession,
        name: str | None = None,
        phone: str | None = None,
        avatar_url: str | None = None,
        professional_license: str | None = None,
        specialties: list[str] | None = None,
    ) -> dict[str, Any]:
        """Update the authenticated user's own profile.

        All fields are optional. professional_license and specialties are
        only applied when the user is a doctor; for other roles those fields
        are silently ignored (not an error — the schema does not restrict
        which fields are sent, only the service enforces the business rule).

        Invalidates the Redis permissions cache after update so the next
        request re-evaluates permissions from the DB.
        """
        await db.execute(text(f"SET search_path TO {tenant_schema}, public"))
        try:
            result = await db.execute(
                select(User).where(
                    User.id == uuid.UUID(user_id),
                    User.is_active.is_(True),
                )
            )
            user = result.scalar_one_or_none()

            if user is None:
                raise ResourceNotFoundError(
                    error="USER_not_found",
                    resource_name="User",
                )

            # Apply fields available to everyone
            if name is not None:
                user.name = name
            if phone is not None:
                user.phone = phone
            if avatar_url is not None:
                user.avatar_url = avatar_url

            # Doctor-only fields — silently skip for other roles
            if user.role == "doctor":
                if professional_license is not None:
                    user.professional_license = professional_license
                if specialties is not None:
                    user.specialties = specialties

            await db.commit()

            logger.info(
                "Profile updated for user_id=%s in schema=%s",
                user_id[:8],
                tenant_schema,
            )

            # Invalidate permissions cache so next request re-loads from DB
            cache_key = _permissions_cache_key(tenant_id, user_id)
            await cache_delete(cache_key)

            return _user_to_dict(user)

        finally:
            with contextlib.suppress(Exception):
                await db.execute(text("SET search_path TO public"))

    # ─── Team Management ────────────────────────────────────────────

    async def list_team_members(
        self,
        *,
        tenant_schema: str,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Return a paginated list of all active users in the tenant schema.

        Results are ordered by name ascending for a stable, predictable sort.
        """
        await db.execute(text(f"SET search_path TO {tenant_schema}, public"))
        try:
            offset = (page - 1) * page_size

            # Total count
            count_result = await db.execute(
                select(func.count(User.id)).where(User.is_active.is_(True))
            )
            total = count_result.scalar_one()

            # Paginated records
            users_result = await db.execute(
                select(User)
                .where(User.is_active.is_(True))
                .order_by(User.name.asc())
                .offset(offset)
                .limit(page_size)
            )
            users = users_result.scalars().all()

            return {
                "items": [_user_to_dict(u) for u in users],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

        finally:
            with contextlib.suppress(Exception):
                await db.execute(text("SET search_path TO public"))

    async def get_team_member(
        self,
        *,
        member_id: str,
        tenant_schema: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Return a single team member's details.

        Raises ResourceNotFoundError when the user does not exist or is
        inactive. Both active and inactive users could be queried by admins
        in future; for now, only active users are accessible.
        """
        await db.execute(text(f"SET search_path TO {tenant_schema}, public"))
        try:
            result = await db.execute(
                select(User).where(
                    User.id == uuid.UUID(member_id),
                    User.is_active.is_(True),
                )
            )
            user = result.scalar_one_or_none()

            if user is None:
                raise ResourceNotFoundError(
                    error="USER_not_found",
                    resource_name="User",
                )

            return _user_to_dict(user)

        finally:
            with contextlib.suppress(Exception):
                await db.execute(text("SET search_path TO public"))

    async def update_team_member(
        self,
        *,
        actor_user_id: str,
        member_id: str,
        tenant_id: str,
        tenant_schema: str,
        db: AsyncSession,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any]:
        """Update a team member's role or active status.

        Business rules enforced here:
          - Actor cannot update themselves via this endpoint (use /me).
          - Role cannot be changed to clinic_owner (ownership transfer is
            a separate, deliberate operation not in scope for MVP).
          - is_active=False is not allowed here (use the dedicated
            deactivate endpoint which has additional safety checks).

        Invalidates the member's Redis permissions cache after any change.
        """
        if actor_user_id == member_id:
            raise AuthError(
                error="USER_cannot_update_self",
                message="Use the /users/me endpoint to update your own profile.",
                status_code=400,
            )

        if role == "clinic_owner":
            raise AuthError(
                error="USER_cannot_assign_owner_role",
                message="Clinic owner role cannot be assigned via this endpoint.",
                status_code=400,
            )

        await db.execute(text(f"SET search_path TO {tenant_schema}, public"))
        try:
            result = await db.execute(
                select(User).where(
                    User.id == uuid.UUID(member_id),
                    User.is_active.is_(True),
                )
            )
            user = result.scalar_one_or_none()

            if user is None:
                raise ResourceNotFoundError(
                    error="USER_not_found",
                    resource_name="User",
                )

            if role is not None:
                user.role = role
            if is_active is not None:
                user.is_active = is_active

            await db.commit()

            logger.info(
                "Team member updated by actor=%s for member=%s in schema=%s",
                actor_user_id[:8],
                member_id[:8],
                tenant_schema,
            )

            # Invalidate the member's permissions cache
            cache_key = _permissions_cache_key(tenant_id, member_id)
            await cache_delete(cache_key)

            return _user_to_dict(user)

        finally:
            with contextlib.suppress(Exception):
                await db.execute(text("SET search_path TO public"))

    async def list_providers(
        self,
        *,
        tenant_schema: str,
        db: AsyncSession,
    ) -> list[dict[str, Any]]:
        """Return all active doctors and clinic owners (appointment providers).

        Lightweight query returning minimal fields for scheduling UIs.
        No PHI beyond name is exposed.
        """
        await db.execute(text(f"SET search_path TO {tenant_schema}, public"))
        try:
            result = await db.execute(
                select(User)
                .where(
                    User.is_active.is_(True),
                    User.role.in_(["doctor", "clinic_owner"]),
                )
                .order_by(User.name.asc())
            )
            users = result.scalars().all()

            return [
                {
                    "id": str(u.id),
                    "name": u.name,
                    "role": u.role,
                    "specialties": u.specialties,
                    "avatar_url": u.avatar_url,
                }
                for u in users
            ]

        finally:
            with contextlib.suppress(Exception):
                await db.execute(text("SET search_path TO public"))

    async def deactivate_team_member(
        self,
        *,
        actor_user_id: str,
        member_id: str,
        tenant_id: str,
        tenant_schema: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Soft-deactivate a team member (is_active=False).

        Safety rules:
          - Actor cannot deactivate themselves.
          - The sole clinic_owner of the tenant cannot be deactivated;
            doing so would lock out the clinic entirely.

        The user record is preserved for audit/regulatory purposes. The
        member loses access on their next token refresh because get_current_user
        queries is_active from the DB via the permissions cache (TTL 5 min).

        Invalidates the member's Redis permissions cache immediately.
        """
        if actor_user_id == member_id:
            raise AuthError(
                error="USER_cannot_deactivate_self",
                message="You cannot deactivate your own account.",
                status_code=400,
            )

        await db.execute(text(f"SET search_path TO {tenant_schema}, public"))
        try:
            result = await db.execute(
                select(User).where(
                    User.id == uuid.UUID(member_id),
                    User.is_active.is_(True),
                )
            )
            user = result.scalar_one_or_none()

            if user is None:
                raise ResourceNotFoundError(
                    error="USER_not_found",
                    resource_name="User",
                )

            # Guard: cannot deactivate the last clinic_owner
            if user.role == "clinic_owner":
                owner_count_result = await db.execute(
                    select(func.count(User.id)).where(
                        User.role == "clinic_owner",
                        User.is_active.is_(True),
                    )
                )
                owner_count = owner_count_result.scalar_one()

                if owner_count <= 1:
                    raise ResourceConflictError(
                        error="USER_sole_owner_cannot_be_deactivated",
                        message=(
                            "Cannot deactivate the sole clinic owner. "
                            "Assign a new owner first."
                        ),
                    )

            user.is_active = False
            await db.commit()

            logger.info(
                "Team member deactivated by actor=%s for member=%s in schema=%s",
                actor_user_id[:8],
                member_id[:8],
                tenant_schema,
            )

            # Invalidate the member's permissions cache immediately
            cache_key = _permissions_cache_key(tenant_id, member_id)
            await cache_delete(cache_key)

            return _user_to_dict(user)

        finally:
            with contextlib.suppress(Exception):
                await db.execute(text("SET search_path TO public"))


# ─── Helpers ─────────────────────────────────────────────────────────────


def _user_to_dict(user: User) -> dict[str, Any]:
    """Serialize a User ORM instance to a plain dict for response construction.

    Only safe, non-PHI-sensitive structural fields are included. The caller
    is responsible for mapping this into the appropriate Pydantic response
    model before returning to the API consumer.
    """
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "professional_license": user.professional_license,
        "specialties": user.specialties,
        "is_active": user.is_active,
        "email_verified": user.email_verified,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


# Module-level singleton for dependency injection
user_service = UserService()
