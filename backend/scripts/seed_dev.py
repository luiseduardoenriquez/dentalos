"""Seed development database with demo data.

Creates:
  - Plans: free, starter, enterprise
  - Tenant: Clínica Demo Dental (Colombia)
  - Users: clinic_owner, doctor, assistant, receptionist
  - UserTenantMemberships for each user
  - 5 sample patients with realistic Colombian data
  - 5 sample inventory items (materials, instruments, medications)
  - 1 superadmin account for platform administration

Usage:
    cd backend
    python scripts/seed_dev.py

Demo credentials (password: DemoPass1):
    owner@demo.dentalos.co       — clinic_owner
    doctor@demo.dentalos.co      — doctor
    assistant@demo.dentalos.co   — assistant
    receptionist@demo.dentalos.co — receptionist

Superadmin credentials (password: AdminPass1):
    admin@dentalos.app           — superadmin
"""

import asyncio
import os
import sys

# Add backend/ to the Python path so `app` is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from datetime import date

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, engine
from app.core.security import hash_password
from app.models.base import TenantBase
from app.models.public.plan import Plan
from app.models.public.superadmin import Superadmin
from app.models.public.tenant import Tenant
from app.models.public.user_tenant_membership import UserTenantMembership
from app.models.tenant.user import User

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEMO_PASSWORD = "DemoPass1"
DEMO_TENANT_SLUG = "clinica-demo-dental"
DEMO_SCHEMA_NAME = "tn_demodent"  # Fixed name for repeatability in dev

# ---------------------------------------------------------------------------
# Plan definitions
# ---------------------------------------------------------------------------

PLANS: list[dict] = [
    {
        "name": "Free",
        "slug": "free",
        "description": "Plan gratuito para clínicas pequeñas.",
        "max_patients": 50,
        "max_doctors": 1,
        "max_users": 2,
        "max_storage_mb": 500,
        "features": {
            "odontogram": True,
            "appointments": True,
            "clinical_records": False,
            "billing": False,
            "portal": False,
            "analytics": False,
            "ai_voice": False,
            "ai_radiograph": False,
        },
        "price_cents": 0,
        "currency": "USD",
        "billing_period": "monthly",
        "pricing_model": "flat",
        "included_doctors": 1,
        "additional_doctor_price_cents": 0,
        "is_active": True,
        "sort_order": 0,
    },
    {
        "name": "Starter",
        "slug": "starter",
        "description": "Plan para clínicas en crecimiento.",
        "max_patients": 500,
        "max_doctors": 3,
        "max_users": 10,
        "max_storage_mb": 5120,
        "features": {
            "odontogram": True,
            "appointments": True,
            "clinical_records": True,
            "billing": True,
            "portal": True,
            "analytics": False,
            "ai_voice": False,
            "ai_radiograph": False,
        },
        "price_cents": 1900,
        "currency": "USD",
        "billing_period": "monthly",
        "pricing_model": "per_doctor",
        "included_doctors": 1,
        "additional_doctor_price_cents": 1900,
        "is_active": True,
        "sort_order": 1,
    },
    {
        "name": "Enterprise",
        "slug": "enterprise",
        "description": "Plan empresarial sin límites — todas las funcionalidades habilitadas.",
        "max_patients": 999999,
        "max_doctors": 999,
        "max_users": 999,
        "max_storage_mb": 102400,
        "features": {
            "odontogram": True,
            "appointments": True,
            "clinical_records": True,
            "billing": True,
            "portal": True,
            "analytics": True,
            "ai_voice": True,
            "ai_radiograph": True,
        },
        "price_cents": 0,
        "currency": "USD",
        "billing_period": "monthly",
        "pricing_model": "custom",
        "included_doctors": 999,
        "additional_doctor_price_cents": 0,
        "is_active": True,
        "sort_order": 4,
    },
]

# ---------------------------------------------------------------------------
# Demo users (tenant schema)
# ---------------------------------------------------------------------------

DEMO_USERS: list[dict] = [
    {
        "email": "owner@demo.dentalos.co",
        "name": "Catalina Morales Herrera",
        "phone": "+573001234567",
        "role": "clinic_owner",
        "professional_license": None,
        "specialties": None,
        "is_primary": True,
    },
    {
        "email": "doctor@demo.dentalos.co",
        "name": "Andrés Felipe Ramírez Gómez",
        "phone": "+573109876543",
        "role": "doctor",
        "professional_license": "TP-12345-CO",
        "specialties": ["Odontología General", "Ortodoncia"],
        "is_primary": False,
    },
    {
        "email": "assistant@demo.dentalos.co",
        "name": "Valentina Torres Ospina",
        "phone": "+573205551234",
        "role": "assistant",
        "professional_license": None,
        "specialties": None,
        "is_primary": False,
    },
    {
        "email": "receptionist@demo.dentalos.co",
        "name": "Juan Sebastián Vargas Díaz",
        "phone": "+573006667890",
        "role": "receptionist",
        "professional_license": None,
        "specialties": None,
        "is_primary": False,
    },
]

# ---------------------------------------------------------------------------
# Sample patients (tenant schema)
# Colombian data: cedula format (6-12 digits), Bogotá phone prefix (+5716…)
# Patients are plain dicts — we build raw INSERT statements because the
# Patient model doesn't exist yet (M3 sprint). We use text() SQL to stay
# flexible and avoid import errors.
# ---------------------------------------------------------------------------

SAMPLE_PATIENTS: list[dict] = [
    {
        "first_name": "María",
        "last_name": "González Rodríguez",
        "document_type": "CC",
        "document_number": "52814763",
        "birthdate": date(1985, 3, 12),
        "gender": "female",
        "phone": "+5716234567",
        "email": "maria.gonzalez@gmail.com",
        "address": "Cra 7 # 45-12, Bogotá, Colombia",
        "blood_type": "O+",
    },
    {
        "first_name": "Carlos",
        "last_name": "Martínez López",
        "document_type": "CC",
        "document_number": "80295143",
        "birthdate": date(1979, 7, 28),
        "gender": "male",
        "phone": "+5716891234",
        "email": "carlos.martinez@hotmail.com",
        "address": "Cll 100 # 15-30 Apto 401, Bogotá, Colombia",
        "blood_type": "A+",
    },
    {
        "first_name": "Sofía",
        "last_name": "Hernández Castro",
        "document_type": "CC",
        "document_number": "1020345678",
        "birthdate": date(1998, 11, 5),
        "gender": "female",
        "phone": "+5716452890",
        "email": "sofia.hernandez@outlook.com",
        "address": "Av El Dorado # 68C-61, Bogotá, Colombia",
        "blood_type": "B+",
    },
    {
        "first_name": "Luis",
        "last_name": "Jiménez Reyes",
        "document_type": "CC",
        "document_number": "71634892",
        "birthdate": date(1972, 2, 18),
        "gender": "male",
        "phone": "+5716789012",
        "email": "luis.jimenez@gmail.com",
        "address": "Cll 63 # 24-55, Bogotá, Colombia",
        "blood_type": "AB-",
    },
    {
        "first_name": "Isabela",
        "last_name": "Sánchez Peña",
        "document_type": "CC",
        "document_number": "1013598427",
        "birthdate": date(2001, 9, 22),
        "gender": "female",
        "phone": "+5716123456",
        "email": "isabela.sanchez@gmail.com",
        "address": "Cra 50 # 127-08, Bogotá, Colombia",
        "blood_type": "O-",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _print_section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def _print_ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def _print_skip(msg: str) -> None:
    print(f"  [--] {msg} (already exists, skipped)")


# ---------------------------------------------------------------------------
# Seed steps
# ---------------------------------------------------------------------------


async def seed_plans(db: AsyncSession) -> dict[str, Plan]:
    """Create Free and Starter plans if they don't exist. Returns slug -> Plan."""
    _print_section("Plans")
    result: dict[str, Plan] = {}

    for plan_data in PLANS:
        slug = plan_data["slug"]
        stmt = select(Plan).where(Plan.slug == slug)
        existing = (await db.execute(stmt)).scalar_one_or_none()

        if existing:
            _print_skip(f"Plan '{existing.name}' (slug={slug})")
            result[slug] = existing
            continue

        plan = Plan(**plan_data)
        db.add(plan)
        await db.flush()  # Populate server-side ID before referencing
        _print_ok(f"Created plan '{plan.name}' (id={plan.id}, slug={slug})")
        result[slug] = plan

    await db.commit()
    return result


async def seed_tenant(db: AsyncSession, plan: Plan) -> Tenant:
    """Create the demo tenant (Clínica Demo Dental) if it doesn't exist."""
    _print_section("Tenant")

    stmt = select(Tenant).where(Tenant.slug == DEMO_TENANT_SLUG)
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if existing:
        if existing.plan_id != plan.id:
            existing.plan_id = plan.id
            await db.commit()
            _print_ok(f"Tenant '{existing.name}' plan updated to '{plan.name}'")
        else:
            _print_skip(f"Tenant '{existing.name}' (slug={DEMO_TENANT_SLUG})")
        return existing

    tenant = Tenant(
        slug=DEMO_TENANT_SLUG,
        schema_name=DEMO_SCHEMA_NAME,
        name="Clínica Demo Dental",
        country_code="CO",
        timezone="America/Bogota",
        currency_code="COP",
        locale="es-CO",
        plan_id=plan.id,
        owner_email="owner@demo.dentalos.co",
        owner_user_id=None,  # Updated after user creation
        phone="+5716001234",
        address="Cra 13 # 32-76, Bogotá, Colombia",
        status="active",
        onboarding_step=5,
        settings={
            "invoice_prefix": "DEMO",
            "whatsapp_enabled": False,
            "default_appointment_duration_minutes": 30,
        },
    )
    db.add(tenant)
    await db.commit()
    _print_ok(f"Created tenant '{tenant.name}' (id={tenant.id}, schema={DEMO_SCHEMA_NAME})")
    return tenant


async def provision_schema(schema_name: str, db: AsyncSession) -> bool:
    """Create the PostgreSQL schema and run tenant Alembic migrations.

    Returns True if schema was freshly created, False if it already existed.
    """
    _print_section("Schema Provisioning")

    # Check whether schema already exists
    result = await db.execute(
        text(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name = :schema"
        ),
        {"schema": schema_name},
    )
    if result.scalar_one_or_none():
        _print_skip(f"Schema '{schema_name}' already exists")
        return False

    # Create schema
    await db.execute(text(f"CREATE SCHEMA {schema_name}"))
    await db.commit()
    _print_ok(f"Created PostgreSQL schema '{schema_name}'")

    # Run Alembic tenant migrations (replicates tenant_service.provision_tenant_schema)
    import subprocess

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result_proc = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "alembic_tenant/alembic.ini",
            "-x",
            f"schema={schema_name}",
            "upgrade",
            "head",
        ],
        capture_output=True,
        text=True,
        cwd=backend_dir,
    )

    if result_proc.returncode != 0:
        # Rollback: drop schema so the next run can retry
        await db.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
        await db.commit()
        print(f"\n  [ERROR] Alembic migrations failed:\n{result_proc.stderr}")
        raise RuntimeError(f"Failed to provision tenant schema '{schema_name}'.")

    _print_ok(f"Alembic tenant migrations applied to '{schema_name}'")
    return True


async def seed_users(
    schema_name: str, tenant: Tenant, db: AsyncSession
) -> dict[str, uuid.UUID]:
    """Create demo users in the tenant schema. Returns email -> user_id."""
    _print_section("Users")

    # Switch search_path to the tenant schema for this session
    await db.execute(text(f"SET search_path TO {schema_name}, public"))

    password_hash = hash_password(DEMO_PASSWORD)
    created: dict[str, uuid.UUID] = {}

    for user_data in DEMO_USERS:
        email = user_data["email"]

        # Check if user already exists (case-insensitive per idx_users_email_lower)
        stmt = select(User).where(User.email == email)
        existing = (await db.execute(stmt)).scalar_one_or_none()

        if existing:
            _print_skip(f"User '{existing.name}' ({email})")
            created[email] = existing.id
            continue

        user = User(
            email=email,
            password_hash=password_hash,
            name=user_data["name"],
            phone=user_data["phone"],
            role=user_data["role"],
            professional_license=user_data.get("professional_license"),
            specialties=user_data.get("specialties"),
            is_active=True,
            email_verified=True,
            failed_login_attempts=0,
            token_version=0,
        )
        db.add(user)
        await db.flush()
        _print_ok(f"Created user '{user.name}' ({email}) [{user.role}] (id={user.id})")
        created[email] = user.id

    await db.commit()

    # Reset search_path back to public
    await db.execute(text("SET search_path TO public"))
    await db.commit()

    return created


async def update_tenant_owner(
    tenant: Tenant, owner_id: uuid.UUID, db: AsyncSession
) -> None:
    """Backfill owner_user_id on the tenant record."""
    if tenant.owner_user_id is not None:
        return
    tenant.owner_user_id = owner_id
    db.add(tenant)
    await db.commit()
    _print_ok(f"Set tenant.owner_user_id = {owner_id}")


async def seed_memberships(
    tenant: Tenant,
    user_ids: dict[str, uuid.UUID],
    db: AsyncSession,
) -> None:
    """Create UserTenantMembership records in the public schema."""
    _print_section("Memberships")

    for user_data in DEMO_USERS:
        email = user_data["email"]
        user_id = user_ids.get(email)
        if not user_id:
            continue

        # Check for existing membership
        stmt = select(UserTenantMembership).where(
            UserTenantMembership.user_id == user_id,
            UserTenantMembership.tenant_id == tenant.id,
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()

        if existing:
            _print_skip(f"Membership for {email} in tenant {tenant.slug}")
            continue

        membership = UserTenantMembership(
            user_id=user_id,
            tenant_id=tenant.id,
            role=user_data["role"],
            status="active",
            is_primary=user_data["is_primary"],
        )
        db.add(membership)
        _print_ok(
            f"Created membership: {email} -> {tenant.slug} [{user_data['role']}]"
        )

    await db.commit()


async def seed_patients(schema_name: str, db: AsyncSession) -> None:
    """Insert sample patients using raw SQL (Patient model not yet implemented).

    This is future-proof: when the Patient model lands in M3, this block can
    be replaced with ORM inserts. The columns below match the spec in
    specs/patients/patients-model.md.
    """
    _print_section("Sample Patients")

    await db.execute(text(f"SET search_path TO {schema_name}, public"))

    # Check if patients table exists before attempting inserts
    table_check = await db.execute(
        text(
            "SELECT to_regclass(:qualified_name)"
        ),
        {"qualified_name": f"{schema_name}.patients"},
    )
    if table_check.scalar_one_or_none() is None:
        print(
            "  [SKIP] 'patients' table not found in tenant schema — "
            "will be available after M3 migrations."
        )
        await db.execute(text("SET search_path TO public"))
        await db.commit()
        return

    for patient in SAMPLE_PATIENTS:
        # Idempotency: skip if document_number already exists
        dup_check = await db.execute(
            text(
                "SELECT id FROM patients WHERE document_number = :doc"
            ),
            {"doc": patient["document_number"]},
        )
        if dup_check.scalar_one_or_none():
            _print_skip(
                f"Patient {patient['first_name']} {patient['last_name']} "
                f"(doc={patient['document_number']})"
            )
            continue

        await db.execute(
            text(
                """
                INSERT INTO patients (
                    id,
                    first_name, last_name,
                    document_type, document_number,
                    birthdate, gender,
                    phone, email, address,
                    blood_type,
                    is_active, no_show_count, portal_access,
                    created_at, updated_at
                ) VALUES (
                    gen_random_uuid(),
                    :first_name, :last_name,
                    :document_type, :document_number,
                    :birthdate, :gender,
                    :phone, :email, :address,
                    :blood_type,
                    true, 0, false,
                    now(), now()
                )
                """
            ),
            patient,
        )
        _print_ok(
            f"Created patient {patient['first_name']} {patient['last_name']} "
            f"(doc={patient['document_number']})"
        )

    await db.commit()

    await db.execute(text("SET search_path TO public"))
    await db.commit()


async def seed_inventory(schema_name: str, db: AsyncSession) -> None:
    """Insert sample inventory items using raw SQL.

    Items are chosen to exercise the semaphore status logic:
    - Green (ok): Resina compuesta A2, Espejo dental #5, Implante Nobel Biocare
    - Yellow / warning zone: Lidocaína 2% (expiry 2026-08-01)
    - Red / critical zone: Guantes nitrilo M (expiry 2026-04-15, low stock)

    Columns match the spec in specs/inventory/inventory-model.md.
    """
    _print_section("Inventory Items")

    await db.execute(text(f"SET search_path TO {schema_name}, public"))

    # Gracefully skip if the inventory_items table has not been migrated yet.
    table_check = await db.execute(
        text("SELECT to_regclass(:qualified_name)"),
        {"qualified_name": f"{schema_name}.inventory_items"},
    )
    if table_check.scalar_one_or_none() is None:
        print(
            "  [SKIP] 'inventory_items' table not found in tenant schema — "
            "will be available after inventory migrations."
        )
        await db.execute(text("SET search_path TO public"))
        await db.commit()
        return

    sample_items: list[dict] = [
        {
            "name": "Resina compuesta A2",
            "category": "material",
            "quantity": 50,
            "unit": "unidades",
            "lot_number": "RC-2024-001",
            "expiry_date": date(2027, 6, 15),
            "manufacturer": "3M ESPE",
            "cost_per_unit": 15000,  # COP cents
            "minimum_stock": 10,
            "location": "Armario A — Estante 2",
        },
        {
            "name": "Espejo dental #5",
            "category": "instrument",
            "quantity": 20,
            "unit": "unidades",
            "lot_number": "ED-2023-042",
            "expiry_date": None,
            "manufacturer": "Hu-Friedy",
            "cost_per_unit": 8000,
            "minimum_stock": 5,
            "location": "Cajón de instrumentos — B1",
        },
        {
            "name": "Implante Nobel Biocare",
            "category": "implant",
            "quantity": 5,
            "unit": "unidades",
            "lot_number": "NB-2025-0817",
            "expiry_date": date(2028, 1, 1),
            "manufacturer": "Nobel Biocare",
            "cost_per_unit": 1500000,
            "minimum_stock": 2,
            "location": "Refrigerador — Bandeja implantes",
        },
        {
            "name": "Lidocaína 2%",
            "category": "medication",
            "quantity": 30,
            "unit": "ml",
            "lot_number": "LIDO-2024-999",
            "expiry_date": date(2026, 8, 1),
            "manufacturer": "Laboratorios Rymco",
            "cost_per_unit": 3500,
            "minimum_stock": 10,
            "location": "Cajón medicamentos — C3",
        },
        {
            "name": "Guantes nitrilo M",
            "category": "material",
            "quantity": 10,
            "unit": "cajas",
            "lot_number": "GN-2025-077",
            "expiry_date": date(2026, 4, 15),
            "manufacturer": "Ansell",
            "cost_per_unit": 25000,
            "minimum_stock": 5,
            "location": "Armario A — Estante 1",
        },
    ]

    for item in sample_items:
        # Idempotency: skip if item with same name already exists.
        dup_check = await db.execute(
            text("SELECT id FROM inventory_items WHERE name = :name"),
            {"name": item["name"]},
        )
        if dup_check.scalar_one_or_none():
            _print_skip(f"Inventory item '{item['name']}'")
            continue

        await db.execute(
            text(
                """
                INSERT INTO inventory_items (
                    id,
                    name, category, quantity, unit,
                    lot_number, expiry_date, manufacturer,
                    cost_per_unit, minimum_stock, location,
                    created_by,
                    is_active, created_at, updated_at
                ) VALUES (
                    gen_random_uuid(),
                    :name, :category, :quantity, :unit,
                    :lot_number, :expiry_date, :manufacturer,
                    :cost_per_unit, :minimum_stock, :location,
                    NULL,
                    true, now(), now()
                )
                """
            ),
            item,
        )
        _print_ok(f"Created inventory item '{item['name']}' (category={item['category']})")

    await db.commit()

    await db.execute(text("SET search_path TO public"))
    await db.commit()


async def seed_superadmin(db: AsyncSession) -> None:
    """Create a superadmin account in the public schema for dev/testing.

    Uses ORM (not raw SQL) since this targets the public schema directly.
    Idempotent: skips creation if admin@dentalos.app already exists.
    """
    _print_section("Superadmin")

    stmt = select(Superadmin).where(Superadmin.email == "admin@dentalos.app")
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if existing:
        _print_skip("Superadmin admin@dentalos.app")
        return

    superadmin = Superadmin(
        email="admin@dentalos.app",
        name="Superadmin Dev",
        password_hash=hash_password("AdminPass1"),
        totp_enabled=False,
        is_active=True,
    )
    db.add(superadmin)
    await db.commit()
    _print_ok(f"Created superadmin admin@dentalos.app (id={superadmin.id})")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def print_summary(tenant: Tenant, user_ids: dict[str, uuid.UUID]) -> None:
    _print_section("Seed Complete — Demo Credentials")
    print(f"  Tenant  : {tenant.name}")
    print(f"  Slug    : {tenant.slug}")
    print(f"  Schema  : {tenant.schema_name}")
    print(f"  Tenant ID: {tenant.id}")
    print()
    print(f"  Password for all users: {DEMO_PASSWORD}")
    print()
    print(f"  {'Email':<40} {'Role':<20} {'User ID'}")
    print(f"  {'-' * 40} {'-' * 20} {'-' * 36}")
    for user_data in DEMO_USERS:
        email = user_data["email"]
        role = user_data["role"]
        uid = user_ids.get(email, "n/a")
        print(f"  {email:<40} {role:<20} {uid}")
    print()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


async def main() -> None:
    print("\nDentalOS — Development Seed Script")
    print("-----------------------------------")

    async with AsyncSessionLocal() as db:
        # 1. Plans
        plans = await seed_plans(db)
        enterprise_plan = plans["enterprise"]

        # 2. Tenant
        tenant = await seed_tenant(db, enterprise_plan)

        # 3. Schema provisioning (CREATE SCHEMA + Alembic migrations)
        await provision_schema(DEMO_SCHEMA_NAME, db)

        # 4. Users (in tenant schema)
        user_ids = await seed_users(DEMO_SCHEMA_NAME, tenant, db)

        # 5. Backfill owner_user_id on tenant
        owner_id = user_ids.get("owner@demo.dentalos.co")
        if owner_id:
            await update_tenant_owner(tenant, owner_id, db)

        # 6. Memberships (in public schema)
        await seed_memberships(tenant, user_ids, db)

        # 7. Sample patients (graceful skip if table doesn't exist yet)
        await seed_patients(DEMO_SCHEMA_NAME, db)

        # 8. Inventory items (graceful skip if table doesn't exist yet)
        await seed_inventory(DEMO_SCHEMA_NAME, db)

        # 9. Superadmin
        await seed_superadmin(db)

    print_summary(tenant, user_ids)

    # Dispose engine so the process exits cleanly
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
