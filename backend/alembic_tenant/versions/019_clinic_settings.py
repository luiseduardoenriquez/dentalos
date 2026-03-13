"""Create clinic_settings table.

Revision ID: 019_clinic_settings
Revises: 018_postop_instructions
Create Date: 2026-03-12

Creates:
  - clinic_settings — singleton table per tenant for JSONB-based feature
    configuration (chatbot, telemedicine, production goals, intake templates).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "019_clinic_settings"
down_revision = "018_postop_instructions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Guard: skip if already exists (some tenants may have been provisioned
    # with this table via seed scripts).
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = current_schema() "
            "AND table_name = 'clinic_settings'"
        )
    )
    if result.scalar():
        return

    op.create_table(
        "clinic_settings",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "settings",
            JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Seed a singleton row with sensible defaults
    op.execute(
        "INSERT INTO clinic_settings (settings) VALUES ("
        "'{\"chatbot_config\": {\"enabled\": true, "
        "\"greeting_message\": \"Hola! Soy el asistente virtual de la clinica. En que puedo ayudarte?\"}, "
        "\"telemedicine_config\": {\"enabled\": false}, "
        "\"production_goals\": {\"monthly_target_cents\": 0, \"doctor_goals\": {}}}"
        "'::jsonb)"
    )


def downgrade() -> None:
    op.drop_table("clinic_settings")
