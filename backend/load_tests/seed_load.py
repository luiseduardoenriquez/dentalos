"""Seed load test data — 10 tenants, 2500 patients, 50 users.

Creates tenants with the Enterprise plan, provisions schemas, seeds users and
patients, pre-mints JWT access tokens, and writes a manifest JSON file for the
Locust scenarios to consume.

Usage:
    cd backend
    uv run python -m load_tests.seed_load

Manifest output: load_tests/fixtures/seed_manifest.json
"""

import asyncio
import json
import os
import subprocess
import sys
import uuid
from datetime import date

from faker import Faker

# Add backend/ to the Python path so `app` is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.core.security import create_access_token, hash_password
from load_tests.config import (
    DOCTORS_PER_TENANT,
    LOAD_PASSWORD,
    MANIFEST_PATH,
    NUM_TENANTS,
    PATIENTS_PER_TENANT,
    TOKEN_TTL_HOURS,
)

fake = Faker("es_CO")


# ─── Helpers ────────────────────────────────────────────


def _print_section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def _print_ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def _print_skip(msg: str) -> None:
    print(f"  [--] {msg} (already exists, skipped)")


# ─── Define Users Per Tenant ────────────────────────────

ROLES = [
    {"role": "clinic_owner", "prefix": "owner"},
    {"role": "doctor", "prefix": "doctor1"},
    {"role": "doctor", "prefix": "doctor2"},
    {"role": "doctor", "prefix": "doctor3"},
    {"role": "receptionist", "prefix": "recep"},
]

# Permission sets by role
ROLE_PERMISSIONS = {
    "clinic_owner": [
        "patients:read", "patients:write", "patients:delete",
        "odontogram:read", "odontogram:write",
        "appointments:read", "appointments:write", "appointments:delete",
        "billing:read", "billing:write",
        "clinical_records:read", "clinical_records:write",
        "users:read", "users:write",
        "settings:read", "settings:write",
    ],
    "doctor": [
        "patients:read", "patients:write",
        "odontogram:read", "odontogram:write",
        "appointments:read", "appointments:write",
        "clinical_records:read", "clinical_records:write",
        "billing:read",
    ],
    "receptionist": [
        "patients:read", "patients:write",
        "appointments:read", "appointments:write",
        "billing:read",
    ],
}


# ─── Seed Steps ─────────────────────────────────────────


async def ensure_enterprise_plan(db: AsyncSession) -> uuid.UUID:
    """Ensure Enterprise plan exists. Returns plan ID."""
    from app.models.public.plan import Plan

    _print_section("Enterprise Plan")
    stmt = select(Plan).where(Plan.slug == "enterprise")
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if existing:
        _print_skip(f"Plan '{existing.name}'")
        return existing.id

    plan = Plan(
        name="Enterprise",
        slug="enterprise",
        description="Load test enterprise plan — no limits.",
        max_patients=999999,
        max_doctors=999,
        max_users=999,
        max_storage_mb=102400,
        features={
            "odontogram": True,
            "appointments": True,
            "clinical_records": True,
            "billing": True,
            "portal": True,
            "analytics": True,
            "ai_voice": True,
            "ai_radiograph": True,
        },
        price_cents=0,
        currency="USD",
        billing_period="monthly",
        pricing_model="custom",
        included_doctors=999,
        additional_doctor_price_cents=0,
        is_active=True,
        sort_order=99,
    )
    db.add(plan)
    await db.flush()
    _print_ok(f"Created plan '{plan.name}' (id={plan.id})")
    await db.commit()
    return plan.id


async def create_tenant(
    db: AsyncSession, index: int, plan_id: uuid.UUID
) -> dict:
    """Create a load test tenant. Returns tenant info dict."""
    from app.models.public.tenant import Tenant

    slug = f"load-test-{index:02d}"
    schema_name = f"tn_load_{index:02d}"

    stmt = select(Tenant).where(Tenant.slug == slug)
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if existing:
        _print_skip(f"Tenant '{existing.name}' (schema={schema_name})")
        return {
            "tenant_id": str(existing.id),
            "schema_name": schema_name,
            "slug": slug,
        }

    tenant = Tenant(
        slug=slug,
        schema_name=schema_name,
        name=f"Clínica Load Test {index:02d}",
        country_code="CO",
        timezone="America/Bogota",
        currency_code="COP",
        locale="es-CO",
        plan_id=plan_id,
        owner_email=f"owner.load{index:02d}@test.dentalos.co",
        phone=f"+5716{100000 + index:06d}",
        address=f"Cra {10 + index} # {20 + index}-{30 + index}, Bogotá",
        status="active",
        onboarding_step=5,
        settings={
            "invoice_prefix": f"LT{index:02d}",
            "whatsapp_enabled": False,
            "default_appointment_duration_minutes": 30,
        },
    )
    db.add(tenant)
    await db.flush()
    _print_ok(f"Created tenant '{tenant.name}' (id={tenant.id})")
    await db.commit()
    return {
        "tenant_id": str(tenant.id),
        "schema_name": schema_name,
        "slug": slug,
    }


async def provision_schema(schema_name: str, db: AsyncSession) -> None:
    """Create PostgreSQL schema and run Alembic tenant migrations."""
    result = await db.execute(
        text(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name = :schema"
        ),
        {"schema": schema_name},
    )
    if result.scalar_one_or_none():
        _print_skip(f"Schema '{schema_name}'")
        return

    await db.execute(text(f"CREATE SCHEMA {schema_name}"))
    await db.commit()

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result_proc = subprocess.run(
        [
            sys.executable, "-m", "alembic",
            "-c", "alembic_tenant/alembic.ini",
            "-x", f"schema={schema_name}",
            "upgrade", "head",
        ],
        capture_output=True,
        text=True,
        cwd=backend_dir,
    )

    if result_proc.returncode != 0:
        await db.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
        await db.commit()
        print(f"\n  [ERROR] Alembic failed for '{schema_name}':\n{result_proc.stderr}")
        raise RuntimeError(f"Failed to provision schema '{schema_name}'")

    _print_ok(f"Provisioned schema '{schema_name}'")


async def seed_users(
    schema_name: str, tenant_id: str, index: int,
    password_hash: str, db: AsyncSession,
) -> list[dict]:
    """Create users in the tenant schema. Returns list of user info dicts."""
    from app.models.tenant.user import User

    await db.execute(text(f"SET search_path TO {schema_name}, public"))

    users = []
    for role_def in ROLES:
        email = f"{role_def['prefix']}.load{index:02d}@test.dentalos.co"

        stmt = select(User).where(User.email == email)
        existing = (await db.execute(stmt)).scalar_one_or_none()

        if existing:
            user_id = str(existing.id)
            _print_skip(f"User '{email}'")
        else:
            user = User(
                email=email,
                password_hash=password_hash,
                name=fake.name(),
                phone=f"+573{fake.msisdn()[:9]}",
                role=role_def["role"],
                professional_license=f"TP-LT{index:02d}-{role_def['prefix']}" if role_def["role"] == "doctor" else None,
                specialties=["Odontología General"] if role_def["role"] == "doctor" else None,
                is_active=True,
                email_verified=True,
                failed_login_attempts=0,
                token_version=0,
            )
            db.add(user)
            await db.flush()
            user_id = str(user.id)
            _print_ok(f"Created user '{email}' [{role_def['role']}]")

        # Pre-mint JWT with extended TTL
        token = create_access_token(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role_def["role"],
            permissions=ROLE_PERMISSIONS.get(role_def["role"], []),
            email=email,
            name=f"Load User {index:02d}",
        )

        users.append({
            "user_id": user_id,
            "email": email,
            "role": role_def["role"],
            "token": token,
        })

    await db.commit()

    # Create memberships in public schema
    await db.execute(text("SET search_path TO public"))
    from app.models.public.user_tenant_membership import UserTenantMembership

    for user_info in users:
        stmt = select(UserTenantMembership).where(
            UserTenantMembership.user_id == uuid.UUID(user_info["user_id"]),
            UserTenantMembership.tenant_id == uuid.UUID(tenant_id),
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if not existing:
            membership = UserTenantMembership(
                user_id=uuid.UUID(user_info["user_id"]),
                tenant_id=uuid.UUID(tenant_id),
                role=user_info["role"],
                status="active",
                is_primary=(user_info["role"] == "clinic_owner"),
            )
            db.add(membership)

    await db.commit()
    return users


async def seed_patients(
    schema_name: str, db: AsyncSession
) -> list[str]:
    """Insert patients into tenant schema using raw SQL. Returns patient IDs."""
    await db.execute(text(f"SET search_path TO {schema_name}, public"))

    # Check if patients table exists
    table_check = await db.execute(
        text("SELECT to_regclass(:name)"),
        {"name": f"{schema_name}.patients"},
    )
    if table_check.scalar_one_or_none() is None:
        print(f"  [SKIP] 'patients' table not found in {schema_name}")
        await db.execute(text("SET search_path TO public"))
        await db.commit()
        return []

    patient_ids = []

    # Check existing count
    count_result = await db.execute(text("SELECT COUNT(*) FROM patients"))
    existing_count = count_result.scalar()
    if existing_count >= PATIENTS_PER_TENANT:
        # Load existing IDs
        ids_result = await db.execute(
            text(f"SELECT id::text FROM patients LIMIT {PATIENTS_PER_TENANT}")
        )
        patient_ids = [row[0] for row in ids_result.fetchall()]
        _print_skip(f"{existing_count} patients in {schema_name}")
        await db.execute(text("SET search_path TO public"))
        await db.commit()
        return patient_ids

    to_create = PATIENTS_PER_TENANT - existing_count
    for i in range(to_create):
        pid = str(uuid.uuid4())
        doc_number = f"{fake.random_int(min=10000000, max=9999999999)}"
        first_name = fake.first_name()
        last_name = f"{fake.last_name()} {fake.last_name()}"

        await db.execute(
            text("""
                INSERT INTO patients (
                    id, first_name, last_name,
                    document_type, document_number,
                    birthdate, gender, phone, email, address,
                    blood_type, is_active, no_show_count, portal_access,
                    created_at, updated_at
                ) VALUES (
                    :id, :first_name, :last_name,
                    'CC', :document_number,
                    :birthdate, :gender, :phone, :email, :address,
                    :blood_type, true, 0, false,
                    now(), now()
                )
            """),
            {
                "id": pid,
                "first_name": first_name,
                "last_name": last_name,
                "document_number": doc_number,
                "birthdate": date(
                    fake.random_int(min=1960, max=2005),
                    fake.random_int(min=1, max=12),
                    fake.random_int(min=1, max=28),
                ),
                "gender": fake.random_element(["male", "female"]),
                "phone": f"+573{fake.msisdn()[:9]}",
                "email": f"patient_{uuid.uuid4().hex[:8]}@test.dentalos.co",
                "address": fake.address()[:100],
                "blood_type": fake.random_element(
                    ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]
                ),
            },
        )
        patient_ids.append(pid)

    await db.commit()

    # Load all patient IDs (including pre-existing)
    ids_result = await db.execute(
        text(f"SELECT id::text FROM patients LIMIT {PATIENTS_PER_TENANT}")
    )
    patient_ids = [row[0] for row in ids_result.fetchall()]

    _print_ok(f"Seeded {to_create} new patients in {schema_name} ({len(patient_ids)} total)")

    await db.execute(text("SET search_path TO public"))
    await db.commit()
    return patient_ids


async def write_manifest(manifest: dict) -> None:
    """Write the seed manifest to JSON."""
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    _print_ok(f"Wrote manifest to {MANIFEST_PATH}")


# ─── Main ───────────────────────────────────────────────


async def main() -> None:
    print("\nDentalOS — Load Test Seed Script")
    print("─" * 40)
    print(f"  Tenants: {NUM_TENANTS}")
    print(f"  Patients/tenant: {PATIENTS_PER_TENANT}")
    print(f"  Users/tenant: {len(ROLES)}")
    print(f"  Token TTL: {TOKEN_TTL_HOURS}h")
    print()

    # Temporarily override access_token_expire_minutes for long-lived tokens
    original_ttl = settings.access_token_expire_minutes
    settings.access_token_expire_minutes = TOKEN_TTL_HOURS * 60

    # Hash password once — reused for all 50 users
    _print_section("Password Hash")
    password_hash = hash_password(LOAD_PASSWORD)
    _print_ok(f"Hashed password once (bcrypt rounds={settings.password_bcrypt_rounds})")

    manifest = {
        "password": LOAD_PASSWORD,
        "tenants": [],
    }

    async with AsyncSessionLocal() as db:
        # Ensure Enterprise plan
        plan_id = await ensure_enterprise_plan(db)

        for i in range(NUM_TENANTS):
            _print_section(f"Tenant {i:02d}")

            # Create tenant record
            tenant_info = await create_tenant(db, i, plan_id)

            # Provision schema
            await provision_schema(tenant_info["schema_name"], db)

            # Seed users
            users = await seed_users(
                tenant_info["schema_name"],
                tenant_info["tenant_id"],
                i,
                password_hash,
                db,
            )

            # Seed patients
            patient_ids = await seed_patients(tenant_info["schema_name"], db)

            # Extract doctor IDs
            doctor_ids = [u["user_id"] for u in users if u["role"] == "doctor"]

            manifest["tenants"].append({
                "tenant_id": tenant_info["tenant_id"],
                "schema_name": tenant_info["schema_name"],
                "slug": tenant_info["slug"],
                "patient_ids": patient_ids,
                "doctor_ids": doctor_ids,
                "users": users,
            })

    await write_manifest(manifest)

    # Restore original TTL
    settings.access_token_expire_minutes = original_ttl

    _print_section("Seed Complete")
    total_patients = sum(len(t["patient_ids"]) for t in manifest["tenants"])
    total_users = sum(len(t["users"]) for t in manifest["tenants"])
    print(f"  Tenants:  {len(manifest['tenants'])}")
    print(f"  Users:    {total_users}")
    print(f"  Patients: {total_patients}")
    print(f"  Manifest: {MANIFEST_PATH}")
    print()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
