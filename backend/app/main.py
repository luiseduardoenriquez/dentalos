import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.database import engine
from app.core.exception_handlers import register_exception_handlers
from app.core.logging_config import setup_logging
from app.core.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from app.core.pdf import shutdown_pdf_engine
from app.core.queue import close_rabbitmq, connect_rabbitmq
from app.core.redis import redis_client

logger = logging.getLogger("dentalos")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown events."""
    setup_logging(settings.log_level)
    logger.info(
        "Starting %s v%s (env=%s)",
        settings.app_name,
        settings.app_version,
        settings.environment,
    )
    await connect_rabbitmq()
    yield
    logger.info("Shutting down %s", settings.app_name)
    await engine.dispose()
    await redis_client.aclose()
    await close_rabbitmq()
    await shutdown_pdf_engine()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Middleware stack (order matters: outermost runs first on request, last on response)
# Added in reverse order: last add_middleware = outermost
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "Accept",
    ],
    expose_headers=["X-Request-ID"],
    max_age=600,
)

register_exception_handlers(app)
app.include_router(api_v1_router)
