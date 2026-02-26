"""Add patient_documents table to tenant schema

Revision ID: 008_add_patient_documents
Revises: 007_add_service_catalog
Create Date: 2026-02-26

One table:
  - patient_documents: uploaded files (X-rays, consents, lab results, etc.)
    linked to a patient with S3 storage and soft-delete.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "008_add_patient_documents"
down_revision: Union[str, None] = "007_add_service_catalog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "patient_documents",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("document_type", sa.String(20), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("file_size_bytes", sa.Integer, nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("tooth_number", sa.Integer, nullable=True),
        sa.Column("uploaded_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "document_type IN ('xray','consent','lab_result','referral','photo','other')",
            name="chk_patient_documents_type",
        ),
    )
    op.create_index("idx_patient_documents_patient", "patient_documents", ["patient_id"])
    op.create_index("idx_patient_documents_type", "patient_documents", ["patient_id", "document_type"])


def downgrade() -> None:
    op.drop_index("idx_patient_documents_type", table_name="patient_documents")
    op.drop_index("idx_patient_documents_patient", table_name="patient_documents")
    op.drop_table("patient_documents")
