"""Add radiograph_analyses table for AI radiograph analysis (AI-01).

Revision ID: 027
Revises: 026_invoice_tax_fields
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "radiograph_analyses",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            UUID(as_uuid=True),
            sa.ForeignKey("patients.id"),
            nullable=False,
        ),
        sa.Column(
            "doctor_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("patient_documents.id"),
            nullable=False,
        ),
        sa.Column("radiograph_type", sa.String(20), nullable=False),
        sa.Column("findings", JSONB, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("radiograph_quality", sa.String(20), nullable=True),
        sa.Column("recommendations", sa.Text, nullable=True),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column(
            "input_tokens", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column(
            "output_tokens", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="processing",
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_notes", sa.Text, nullable=True),
        sa.Column(
            "is_active", sa.Boolean, nullable=False, server_default="true"
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('processing', 'completed', 'failed', 'reviewed')",
            name="chk_radiograph_analyses_status",
        ),
        sa.CheckConstraint(
            "radiograph_type IN ('periapical', 'bitewing', 'panoramic', "
            "'cephalometric', 'occlusal')",
            name="chk_radiograph_analyses_type",
        ),
    )

    op.create_index(
        "idx_radiograph_analyses_patient", "radiograph_analyses", ["patient_id"]
    )
    op.create_index(
        "idx_radiograph_analyses_doctor", "radiograph_analyses", ["doctor_id"]
    )
    op.create_index(
        "idx_radiograph_analyses_status", "radiograph_analyses", ["status"]
    )
    op.create_index(
        "idx_radiograph_analyses_created", "radiograph_analyses", ["created_at"]
    )
    op.create_index(
        "idx_radiograph_analyses_document",
        "radiograph_analyses",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_table("radiograph_analyses")
