"""Initial public schema tables

Revision ID: 001_initial_public
Revises:
Create Date: 2026-02-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "001_initial_public"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Plans table
    op.create_table(
        "plans",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("slug", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("max_patients", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_doctors", sa.Integer, nullable=False, server_default="1"),
        sa.Column("max_users", sa.Integer, nullable=False, server_default="1"),
        sa.Column("max_storage_mb", sa.Integer, nullable=False, server_default="100"),
        sa.Column("features", JSONB, nullable=False, server_default="{}"),
        sa.Column("price_cents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="'USD'"),
        sa.Column("billing_period", sa.String(20), nullable=False, server_default="'monthly'"),
        sa.Column("pricing_model", sa.String(20), nullable=False, server_default="'per_doctor'"),
        sa.Column("included_doctors", sa.Integer, nullable=False, server_default="1"),
        sa.Column("additional_doctor_price_cents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="public",
    )

    # Tenants table
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("schema_name", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False, server_default="'CO'"),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="'America/Bogota'"),
        sa.Column("currency_code", sa.String(3), nullable=False, server_default="'COP'"),
        sa.Column("locale", sa.String(10), nullable=False, server_default="'es-CO'"),
        sa.Column("plan_id", UUID(as_uuid=True), sa.ForeignKey("public.plans.id"), nullable=False),
        sa.Column("owner_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("owner_email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="'pending'"),
        sa.Column("onboarding_step", sa.Integer, nullable=False, server_default="0"),
        sa.Column("settings", JSONB, nullable=False, server_default="{}"),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "status IN ('pending', 'active', 'suspended', 'cancelled')",
            name="chk_tenants_status",
        ),
        schema="public",
    )
    op.create_index("idx_tenants_slug", "tenants", ["slug"], schema="public")

    # User tenant memberships
    op.create_table(
        "user_tenant_memberships",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("public.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="'active'"),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("invited_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "tenant_id", name="uq_user_tenant"),
        sa.CheckConstraint(
            "role IN ('clinic_owner', 'doctor', 'assistant', 'receptionist')",
            name="chk_membership_role",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'suspended')",
            name="chk_membership_status",
        ),
        schema="public",
    )
    op.create_index("idx_memberships_user_id", "user_tenant_memberships", ["user_id"], schema="public")
    op.create_index("idx_memberships_tenant_id", "user_tenant_memberships", ["tenant_id"], schema="public")

    # Seed default plans
    op.execute("""
        INSERT INTO public.plans (name, slug, description, max_patients, max_doctors, max_users, max_storage_mb, features, price_cents, currency, billing_period, pricing_model, included_doctors, additional_doctor_price_cents, is_active, sort_order)
        VALUES
        ('Free', 'free', 'Plan gratuito para probar DentalOS', 50, 1, 2, 100,
         '{"odontogram_classic": true, "odontogram_anatomic": false, "voice_to_odontogram": false, "ai_radiograph": false, "portal": false, "analytics_basic": true, "analytics_advanced": false}',
         0, 'USD', 'monthly', 'flat', 1, 0, true, 0),
        ('Starter', 'starter', 'Para consultorios independientes', 500, 1, 5, 500,
         '{"odontogram_classic": true, "odontogram_anatomic": true, "voice_to_odontogram": false, "ai_radiograph": false, "portal": true, "analytics_basic": true, "analytics_advanced": false}',
         1900, 'USD', 'monthly', 'per_doctor', 1, 1900, true, 1),
        ('Pro', 'pro', 'Para consultorios en crecimiento', 2000, 3, 15, 2000,
         '{"odontogram_classic": true, "odontogram_anatomic": true, "voice_to_odontogram": true, "ai_radiograph": false, "portal": true, "analytics_basic": true, "analytics_advanced": true}',
         3900, 'USD', 'monthly', 'per_doctor', 1, 3900, true, 2),
        ('Clinica', 'clinica', 'Para clinicas con multiples doctores', 10000, 10, 50, 10000,
         '{"odontogram_classic": true, "odontogram_anatomic": true, "voice_to_odontogram": true, "ai_radiograph": true, "portal": true, "analytics_basic": true, "analytics_advanced": true}',
         6900, 'USD', 'monthly', 'per_location', 3, 3900, true, 3),
        ('Enterprise', 'enterprise', 'Para cadenas de clinicas', 0, 0, 0, 0,
         '{"odontogram_classic": true, "odontogram_anatomic": true, "voice_to_odontogram": true, "ai_radiograph": true, "portal": true, "analytics_basic": true, "analytics_advanced": true}',
         0, 'USD', 'monthly', 'custom', 0, 0, true, 4);
    """)


def downgrade() -> None:
    op.drop_table("user_tenant_memberships", schema="public")
    op.drop_table("tenants", schema="public")
    op.drop_table("plans", schema="public")
