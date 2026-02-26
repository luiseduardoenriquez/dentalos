from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=settings.database_echo,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session (public schema only)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_tenant_session(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Standalone async context manager for tenant-scoped DB sessions.

    Used by workers and background tasks that run outside FastAPI request scope.
    Resolves the tenant schema from the tenant_id prefix (e.g., "tn_abc123").
    """
    schema = tenant_id if tenant_id.startswith("tn_") else f"tn_{tenant_id}"

    from app.core.tenant import validate_schema_name

    if not validate_schema_name(schema):
        raise ValueError(f"Invalid tenant schema: {schema}")

    async with AsyncSessionLocal() as session:
        try:
            await session.execute(text(f"SET search_path TO {schema}, public"))
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.execute(text("SET search_path TO public"))
            await session.commit()


async def get_tenant_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a tenant-scoped database session.

    Reads TenantContext from ContextVar, validates schema name,
    sets search_path to the tenant schema, and resets on exit.
    """
    from app.core.exceptions import TenantError
    from app.core.tenant import get_current_tenant_or_raise, validate_schema_name

    tenant = get_current_tenant_or_raise()
    schema = tenant.schema_name

    if not validate_schema_name(schema):
        raise TenantError(
            error="TENANT_invalid_schema",
            message="Invalid tenant schema name.",
            status_code=403,
        )

    async with AsyncSessionLocal() as session:
        try:
            await session.execute(text(f"SET search_path TO {schema}, public"))
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.execute(text("SET search_path TO public"))
            await session.commit()
