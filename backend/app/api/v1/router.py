from fastapi import APIRouter

from app.api.v1.auth.router import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.onboarding.router import router as onboarding_router
from app.api.v1.settings.router import router as settings_router
from app.api.v1.tenants.router import router as tenants_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(tenants_router)
api_v1_router.include_router(settings_router)
api_v1_router.include_router(onboarding_router)
