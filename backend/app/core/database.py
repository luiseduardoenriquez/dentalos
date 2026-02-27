import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

logger = logging.getLogger("dentalos.database")

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=settings.database_echo,
)


@event.listens_for(engine.sync_engine, "checkin")
def _reset_search_path_on_checkin(dbapi_connection, connection_record):
    """Reset search_path when a connection returns to the pool.

    This guarantees no tenant schema leaks between requests, even if the
    request handler crashes before the finally block runs.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("SET search_path TO public")
    cursor.close()


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def _set_search_path(session: AsyncSession, schema: str) -> None:
    """Set search_path using a raw connection to avoid transaction conflicts.

    Uses the underlying connection's exec_driver_sql which bypasses
    SQLAlchemy's transaction management. SET search_path is not
    transactional in PostgreSQL — it takes effect immediately regardless
    of transaction state.
    """
    conn = await session.connection()
    await conn.exec_driver_sql(f"SET search_path TO {schema}, public")


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
    Accepts either a schema name (e.g. "tn_demodent") or a raw tenant UUID.
    When a UUID is provided, looks up the actual schema_name from public.tenants.
    """
    from app.core.tenant import validate_schema_name

    if tenant_id.startswith("tn_") and validate_schema_name(tenant_id):
        schema = tenant_id
    else:
        # Look up schema_name from public.tenants by UUID
        async with AsyncSessionLocal() as lookup_session:
            result = await lookup_session.execute(
                text("SELECT schema_name FROM public.tenants WHERE id = :tid"),
                {"tid": tenant_id},
            )
            row = result.scalar_one_or_none()
            if row is None:
                raise ValueError(f"Tenant not found: {tenant_id}")
            schema = row

    if not validate_schema_name(schema):
        raise ValueError(f"Invalid tenant schema: {schema}")

    async with AsyncSessionLocal() as session:
        try:
            await _set_search_path(session, schema)
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        # No finally block needed — the pool checkin listener resets search_path


async def get_tenant_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a tenant-scoped database session.

    Reads TenantContext from ContextVar, validates schema name,
    sets search_path to the tenant schema, and resets on exit.

    The search_path is reset automatically when the connection returns
    to the pool via the checkin event listener — no finally block needed.
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
            await _set_search_path(session, schema)
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        # No finally block needed — the pool checkin listener resets search_path
