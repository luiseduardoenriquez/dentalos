"""Add patients table to tenant schema

Revision ID: 003_add_patients
Revises: 002_audit_log
Create Date: 2026-02-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, UUID

# revision identifiers, used by Alembic.
revision: str = "003_add_patients"
down_revision: Union[str, None] = "002_audit_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "patients",
        # Primary key
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),

        # Identity
        sa.Column("document_type", sa.String(10), nullable=False),
        sa.Column("document_number", sa.String(30), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("birthdate", sa.Date, nullable=True),
        sa.Column("gender", sa.String(10), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("phone_secondary", sa.String(20), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state_province", sa.String(100), nullable=True),

        # Emergency contact
        sa.Column("emergency_contact_name", sa.String(200), nullable=True),
        sa.Column("emergency_contact_phone", sa.String(20), nullable=True),

        # Insurance
        sa.Column("insurance_provider", sa.String(100), nullable=True),
        sa.Column("insurance_policy_number", sa.String(50), nullable=True),

        # Clinical
        sa.Column("blood_type", sa.String(5), nullable=True),
        sa.Column("allergies", ARRAY(sa.Text), nullable=True),
        sa.Column("chronic_conditions", ARRAY(sa.Text), nullable=True),

        # Metadata
        sa.Column("referral_source", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),

        # Status
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),

        # Counters
        sa.Column("no_show_count", sa.Integer, nullable=False, server_default="0"),

        # Portal
        sa.Column("portal_access", sa.Boolean, nullable=False, server_default=sa.text("false")),

        # FK
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),

        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),

        # Constraints
        sa.UniqueConstraint("document_type", "document_number", name="uq_patients_document"),
        sa.CheckConstraint(
            "document_type IN ('CC', 'CE', 'PA', 'PEP', 'TI')",
            name="chk_patients_document_type",
        ),
        sa.CheckConstraint(
            "gender IS NULL OR gender IN ('male', 'female', 'other')",
            name="chk_patients_gender",
        ),
    )

    # B-tree indexes for common lookups
    op.create_index(
        "idx_patients_document",
        "patients",
        [sa.text("lower(document_type)"), sa.text("lower(document_number)")],
    )
    op.create_index("idx_patients_email", "patients", ["email"])
    op.create_index("idx_patients_is_active", "patients", ["is_active"])
    op.create_index("idx_patients_created_at", "patients", ["created_at"])

    # GIN full-text search index (Spanish dictionary)
    op.execute("""
        CREATE INDEX idx_patients_fts ON patients USING GIN (
            to_tsvector('spanish', coalesce(first_name, '') || ' ' || coalesce(last_name, '') || ' ' || coalesce(document_number, '') || ' ' || coalesce(phone, ''))
        )
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_patients_fts")
    op.drop_index("idx_patients_created_at", table_name="patients")
    op.drop_index("idx_patients_is_active", table_name="patients")
    op.drop_index("idx_patients_email", table_name="patients")
    op.drop_index("idx_patients_document", table_name="patients")
    op.drop_table("patients")
