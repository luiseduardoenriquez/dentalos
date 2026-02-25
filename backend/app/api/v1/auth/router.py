"""Auth API routes — registration, login, token lifecycle, team invites."""
from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import get_current_user, require_role
from app.core.config import settings
from app.core.database import get_db
from app.schemas.auth import (
    AcceptInviteRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    InviteRequest,
    LoginMultiTenantResponse,
    LoginRequest,
    LoginSuccessResponse,
    MeResponse,
    MessageResponse,
    PlanLimits,
    RegisterRequest,
    ResetPasswordRequest,
    SelectTenantRequest,
    TenantResponse,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Set the refresh token as an HttpOnly cookie."""
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.environment != "development",
        samesite="strict",
        path="/api/v1/auth",
        max_age=settings.refresh_token_expire_days * 86400,
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Clear the refresh token cookie."""
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
    )


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ─── Endpoints ───────────────────────────────────────


@router.post("/register", status_code=201, response_model=LoginSuccessResponse)
async def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginSuccessResponse:
    """Register a new clinic and owner account."""
    result = await auth_service.register(
        email=body.email,
        password=body.password,
        name=body.name,
        clinic_name=body.clinic_name,
        country=body.country,
        phone=body.phone,
        ip_address=_get_client_ip(request),
        db=db,
    )

    _set_refresh_cookie(response, result["refresh_token"])

    return LoginSuccessResponse(
        access_token=result["access_token"],
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse(**result["user"]),
        tenant=TenantResponse(**result["tenant"]),
    )


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginSuccessResponse | LoginMultiTenantResponse:
    """Authenticate user. Returns tokens or tenant selection list."""
    result = await auth_service.login(
        email=body.email,
        password=body.password,
        ip_address=_get_client_ip(request),
        db=db,
    )

    if result.get("requires_tenant_selection"):
        return LoginMultiTenantResponse(
            pre_auth_token=result["pre_auth_token"],
            tenants=result["tenants"],
        )

    _set_refresh_cookie(response, result["refresh_token"])

    return LoginSuccessResponse(
        access_token=result["access_token"],
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse(**result["user"]),
        tenant=TenantResponse(**result["tenant"]),
    )


@router.post("/select-tenant", response_model=LoginSuccessResponse)
async def select_tenant(
    body: SelectTenantRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginSuccessResponse:
    """Complete multi-tenant login by selecting a clinic."""
    result = await auth_service.select_tenant(
        pre_auth_token=body.pre_auth_token,
        tenant_id=body.tenant_id,
        ip_address=_get_client_ip(request),
        db=db,
    )

    _set_refresh_cookie(response, result["refresh_token"])

    return LoginSuccessResponse(
        access_token=result["access_token"],
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse(**result["user"]),
        tenant=TenantResponse(**result["tenant"]),
    )


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias="refresh_token"),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Refresh access token using the refresh token cookie."""
    if not refresh_token:
        from app.core.exceptions import AuthError

        raise AuthError(
            error="AUTH_missing_refresh_token",
            message="Refresh token required.",
            status_code=401,
        )

    result = await auth_service.refresh_token(
        raw_refresh_token=refresh_token,
        ip_address=_get_client_ip(request),
        db=db,
    )

    _set_refresh_cookie(response, result["refresh_token"])

    return TokenResponse(
        access_token=result["access_token"],
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    current_user: AuthenticatedUser = Depends(get_current_user),
    refresh_token: str | None = Cookie(default=None, alias="refresh_token"),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Logout — blacklist access token and revoke refresh token."""
    await auth_service.logout(
        jti=current_user.token_jti,
        user_id=current_user.user_id,
        raw_refresh_token=refresh_token,
        tenant_schema=current_user.tenant.schema_name,
        db=db,
    )
    _clear_refresh_cookie(response)


@router.get("/me", response_model=MeResponse)
async def get_me(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    """Get current user profile with tenant and permissions."""
    result = await auth_service.get_me(
        user_id=current_user.user_id,
        tenant_id=current_user.tenant.tenant_id,
        tenant_schema=current_user.tenant.schema_name,
        db=db,
    )

    return MeResponse(
        user=UserResponse(**result["user"]),
        tenant=TenantResponse(**result["tenant"]),
        permissions=list(result["permissions"]),
        feature_flags=result["feature_flags"],
        plan_limits=PlanLimits(**result["plan_limits"]),
    )


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Request a password reset email."""
    await auth_service.forgot_password(
        email=body.email,
        ip_address=_get_client_ip(request),
        db=db,
    )
    return MessageResponse(
        message="If an account with that email exists, a reset link has been sent."
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Reset password with token from email."""
    await auth_service.reset_password(
        token=body.token,
        new_password=body.new_password,
        db=db,
    )
    return MessageResponse(message="Password has been reset successfully.")


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Change password for the authenticated user."""
    await auth_service.change_password(
        user_id=current_user.user_id,
        current_password=body.current_password,
        new_password=body.new_password,
        current_session_token_hash=None,
        tenant_schema=current_user.tenant.schema_name,
        db=db,
    )
    return MessageResponse(message="Password changed successfully.")


@router.post("/invite", status_code=201, response_model=MessageResponse)
async def invite_user(
    body: InviteRequest,
    current_user: AuthenticatedUser = Depends(
        require_role(["clinic_owner"])
    ),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Invite a team member to the clinic."""
    await auth_service.invite_user(
        inviter_user_id=current_user.user_id,
        email=body.email,
        role=body.role,
        tenant_id=current_user.tenant.tenant_id,
        tenant_schema=current_user.tenant.schema_name,
        db=db,
    )
    return MessageResponse(message="Invitation sent successfully.")


@router.post("/accept-invite", response_model=LoginSuccessResponse)
async def accept_invite(
    body: AcceptInviteRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginSuccessResponse:
    """Accept a team invitation and create account."""
    result = await auth_service.accept_invite(
        token=body.token,
        password=body.password,
        name=body.name,
        phone=body.phone,
        ip_address=_get_client_ip(request),
        db=db,
    )

    _set_refresh_cookie(response, result["refresh_token"])

    return LoginSuccessResponse(
        access_token=result["access_token"],
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse(**result["user"]),
        tenant=TenantResponse(**result["tenant"]),
    )


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    body: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Verify email address with token."""
    await auth_service.verify_email(
        token=body.token,
        db=db,
    )
    return MessageResponse(message="Email verified successfully.")
