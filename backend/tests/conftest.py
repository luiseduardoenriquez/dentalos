import uuid
from collections.abc import AsyncGenerator

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.permissions import get_permissions_for_role
from app.core.config import settings
from app.core.security import clear_keys, create_access_token, hash_password, set_keys
from app.main import app
from app.models.base import PublicBase, TenantBase

# ─── Engine ──────────────────────────────────────────
test_engine = create_async_engine(settings.database_url, echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)


# ─── RS256 Keys ──────────────────────────────────────
@pytest.fixture(scope="session", autouse=True)
def ephemeral_keys():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = (
        key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    set_keys(private_key=private_pem, public_key=public_pem)
    yield
    clear_keys()


# ─── Client ──────────────────────────────────────────
@pytest.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """httpx AsyncClient configured for FastAPI test server."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# ─── DB Fixtures ─────────────────────────────────────
@pytest.fixture(scope="session")
async def setup_public_schema():
    """Create all public schema tables once per test session."""
    async with test_engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS public"))
        await conn.run_sync(PublicBase.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(PublicBase.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def db_session(setup_public_schema) -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean DB session for each test with rollback."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def test_tenant_schema(db_session: AsyncSession):
    """Create a random tenant schema for this test, drop after."""
    schema = f"tn_{uuid.uuid4().hex[:8]}"
    await db_session.execute(text(f"CREATE SCHEMA {schema}"))
    await db_session.execute(text(f"SET search_path TO {schema}, public"))
    await db_session.run_sync(TenantBase.metadata.create_all)
    await db_session.execute(text("SET search_path TO public"))
    await db_session.commit()
    yield schema
    await db_session.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
    await db_session.commit()


@pytest.fixture
async def test_plan(db_session: AsyncSession, setup_public_schema):
    from app.models.public.plan import Plan

    plan = Plan(
        name=f"Test Free {uuid.uuid4().hex[:6]}",
        slug=f"test-free-{uuid.uuid4().hex[:6]}",
        max_patients=50,
        max_doctors=1,
        max_users=2,
        max_storage_mb=100,
        features={"odontogram_classic": True},
        price_cents=0,
        currency="USD",
        billing_period="monthly",
        pricing_model="flat",
        included_doctors=1,
        additional_doctor_price_cents=0,
    )
    db_session.add(plan)
    await db_session.flush()
    return plan


@pytest.fixture
async def test_tenant(db_session: AsyncSession, test_plan, test_tenant_schema):
    from app.models.public.tenant import Tenant

    tenant = Tenant(
        slug=f"test-clinic-{uuid.uuid4().hex[:4]}",
        schema_name=test_tenant_schema,
        name="Test Clinic",
        country_code="CO",
        timezone="America/Bogota",
        currency_code="COP",
        locale="es-CO",
        plan_id=test_plan.id,
        owner_email="owner@test.co",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest.fixture
async def test_user(db_session: AsyncSession, test_tenant_schema):
    from app.models.tenant.user import User

    await db_session.execute(text(f"SET search_path TO {test_tenant_schema}, public"))
    user = User(
        email="owner@test.co",
        password_hash=hash_password("TestPass1"),
        name="Dr. Test",
        role="clinic_owner",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.execute(text("SET search_path TO public"))
    return user


@pytest.fixture
async def test_membership(db_session: AsyncSession, test_user, test_tenant):
    from app.models.public.user_tenant_membership import UserTenantMembership

    membership = UserTenantMembership(
        user_id=test_user.id,
        tenant_id=test_tenant.id,
        role="clinic_owner",
        is_primary=True,
    )
    db_session.add(membership)
    await db_session.flush()
    return membership


@pytest.fixture
async def authenticated_client(
    async_client: httpx.AsyncClient,
    test_user,
    test_tenant,
) -> httpx.AsyncClient:
    permissions = get_permissions_for_role("clinic_owner")
    token = create_access_token(
        user_id=str(test_user.id),
        tenant_id=str(test_tenant.id),
        role="clinic_owner",
        permissions=list(permissions),
        email=test_user.email,
        name=test_user.name,
    )
    async_client.headers["Authorization"] = f"Bearer {token}"
    return async_client


@pytest.fixture
async def doctor_client(
    async_client: httpx.AsyncClient,
    test_user,
    test_tenant,
) -> httpx.AsyncClient:
    permissions = get_permissions_for_role("doctor")
    token = create_access_token(
        user_id=str(test_user.id),
        tenant_id=str(test_tenant.id),
        role="doctor",
        permissions=list(permissions),
        email=test_user.email,
        name=test_user.name,
    )
    async_client.headers["Authorization"] = f"Bearer {token}"
    return async_client
